from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from datetime import UTC, date, datetime, time
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.domain.actionhub_client import (
    HubConflictError,
    HubUnavailableError,
    cancel_amount_checkout,
    lookup_amount_checkout,
    request_amount_checkout,
)
from app.domain.adaptations import (
    adaptations_for_order,
    create_adaptation,
    order_has_pending_adaptation,
    parse_customer_adaptation,
    public_adaptation_view,
)
from app.domain.custom_loaf import FLOUR_REVIEW_MESSAGE, validate_public_custom_choices
from app.domain.email_outbox import enqueue_admin_order_email, enqueue_order_email
from app.domain.errors import (
    AuthError,
    CapacityError,
    ConfirmationError,
    NotFoundError,
    PriceChangedError,
)
from app.domain.orders import new_public_reference
from app.domain.payments import order_is_financially_settled
from app.domain.schedule import (
    REASON_UNKNOWN_BASE,
    REASON_UNKNOWN_UNITS,
    ProposedLine,
    ensure_schedule_settings,
    evaluate_day,
    resolve_proposed_lines,
)
from app.models.catalog import BreadShape, DoughType, Ingredient
from app.models.enums import EditorialStatus, FinancialStatus, OrderStatus, PaymentProvider
from app.models.orders import Order, OrderItem, OrderItemIngredient
from app.models.payments import PaymentRecord
from app.models.products import Product, ProductVariant

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
ACTIVE_PAYMENT = frozenset({"pending", "paid", "unknown"})


def hash_access_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def email_access_token(settings: Settings, order: Order) -> str:
    secret = settings.admin_session_secret.encode("utf-8")
    material = f"order-access:{order.id}".encode("utf-8")
    return hmac.new(secret, material, hashlib.sha256).hexdigest()


def protected_order_url(settings: Settings, order: Order) -> str:
    origin = settings.public_origin.rstrip("/")
    token = email_access_token(settings, order)
    return f"{origin}/pedido/{order.public_reference}?token={token}"


def _email(value: str) -> str:
    cleaned = value.strip().lower()
    if not EMAIL_RE.fullmatch(cleaned) or len(cleaned) > 254:
        raise ConfirmationError("informe um e-mail válido")
    return cleaned


def _crm_session(value: object) -> str | None:
    from app.domain.crm_tracking import optional_session_id

    return optional_session_id(value)


def _load_variant(session: Session, variant_id: UUID) -> tuple[Product, ProductVariant]:
    variant = session.get(ProductVariant, variant_id)
    if variant is None:
        raise NotFoundError("variação não encontrada")
    product = session.get(Product, variant.product_id)
    if product is None:
        raise NotFoundError("produto não encontrado")
    return product, variant


def _order_contains_custom(session: Session, order: Order) -> bool:
    items = list(session.scalars(select(OrderItem).where(OrderItem.order_id == order.id)))
    return any(item.product_variant_id is None for item in items)


def _custom_rule(session: Session) -> tuple[int, int]:
    row = ensure_schedule_settings(session)
    price = int(row.custom_loaf_price_cents or 0)
    weight = int(row.custom_loaf_weight_grams or 0)
    if price <= 0 or weight <= 0:
        raise ConfirmationError("o preço do pão personalizado ainda não foi configurado")
    return price, weight


def _adaptation_from_raw(raw: dict) -> dict | None:
    raw_adapt = raw.get("adaptation")
    if not isinstance(raw_adapt, dict):
        raw_adapt = {
            "text": raw.get("adaptation_text"),
            "reason": raw.get("adaptation_reason"),
        }
    adaptation = parse_customer_adaptation(raw_adapt)
    if adaptation is not None:
        return adaptation
    free_text = raw.get("free_ingredient_text")
    if free_text is None or not str(free_text).strip():
        return None
    return parse_customer_adaptation({"text": free_text, "reason": "preference"})


def _quote_product(session: Session, raw: dict, quantity: int) -> tuple[dict, ProposedLine]:
    variant_id = UUID(str(raw["variant_id"]))
    product, variant = _load_variant(session, variant_id)
    if product.editorial_status != EditorialStatus.PUBLISHED.value or not product.is_available:
        raise ConfirmationError(f"{product.name} não está à venda")
    if not variant.is_active or variant.price_cents is None or variant.price_cents <= 0:
        raise ConfirmationError(f"a opção de {product.name} não está à venda")
    client_unit = raw.get("unit_cents")
    if client_unit is not None and int(client_unit) != variant.price_cents:
        raise PriceChangedError(int(client_unit), variant.price_cents)
    line_cents = variant.price_cents * quantity
    quoted = {
        "origin": "product",
        "product_id": str(product.id),
        "variant_id": str(variant.id),
        "product_name": product.name,
        "variant_name": variant.display_name,
        "quantity": quantity,
        "unit_cents": variant.price_cents,
        "line_cents": line_cents,
        "physical_units": None if variant.physical_units is None else variant.physical_units * quantity,
        "catalog_base_pending": product.recipe_base_id is None,
        "weight_grams": variant.net_weight_grams,
        "ingredients": [],
        "adaptation": _adaptation_from_raw(raw),
    }
    return quoted, ProposedLine(kind="product", quantity=quantity, variant_id=variant.id)


def _quote_custom(session: Session, raw: dict, quantity: int) -> tuple[dict, ProposedLine]:
    if not raw.get("dough_type_id") or not raw.get("bread_shape_id"):
        raise ConfirmationError("informe a fermentação e o preparo e o formato do pão personalizado")
    dough = session.get(DoughType, UUID(str(raw["dough_type_id"])))
    shape = session.get(BreadShape, UUID(str(raw["bread_shape_id"])))
    if shape is None or not shape.is_active:
        raise ConfirmationError("esse formato não está disponível")
    ingredient_ids = raw.get("ingredient_ids") or []
    resolved_ingredients: list[Ingredient] = []
    for raw_id in ingredient_ids:
        ingredient = session.get(Ingredient, UUID(str(raw_id)))
        if ingredient is None:
            raise ConfirmationError("um dos ingredientes escolhidos não está disponível")
        resolved_ingredients.append(ingredient)
    validate_public_custom_choices(dough, resolved_ingredients)
    if dough is None or not dough.is_active:
        raise ConfirmationError("essa massa não está disponível")
    for ingredient in resolved_ingredients:
        if not ingredient.is_active:
            if ingredient.assistant_role == "flour":
                raise ConfirmationError(FLOUR_REVIEW_MESSAGE)
            raise ConfirmationError("um dos ingredientes escolhidos não está disponível")
    if dough.recipe_base_id is None:
        raise ConfirmationError(
            f"a receita-base de {dough.name} ainda está pendente. A Loja precisa vinculá-la na agenda antes do pedido."
        )
    price, weight = _custom_rule(session)
    client_unit = raw.get("unit_cents")
    if client_unit is not None and int(client_unit) != price:
        raise PriceChangedError(int(client_unit), price)
    client_weight = raw.get("weight_grams")
    if client_weight is not None and int(client_weight) != weight:
        raise ConfirmationError("o peso do pão personalizado é definido por A Loja")
    ingredients = [
        {
            "id": str(ingredient.id),
            "name": ingredient.name,
            "assistant_role": ingredient.assistant_role,
            "surcharge_cents": None,
        }
        for ingredient in resolved_ingredients
    ]
    line_cents = price * quantity
    quoted = {
        "origin": "custom",
        "dough_type_id": str(dough.id),
        "bread_shape_id": str(shape.id),
        "recipe_base_id": str(dough.recipe_base_id),
        "product_name": dough.name,
        "variant_name": shape.name,
        "quantity": quantity,
        "unit_cents": price,
        "line_cents": line_cents,
        "physical_units": quantity,
        "weight_grams": weight,
        "ingredients": ingredients,
        "adaptation": _adaptation_from_raw(raw),
        "flour_name": next(
            (row["name"] for row in ingredients if row["assistant_role"] == "flour"),
            None,
        ),
    }
    return quoted, ProposedLine(kind="custom", quantity=quantity, dough_type_id=dough.id)


def _eligible_credit_items(session: Session, quoted: list[dict]) -> list[dict]:
    from app.domain.house_fidelity import is_500g_unit, product_is_fidelity_eligible
    from app.models.products import Product, ProductVariant

    items = []
    seen: set[str] = set()
    for line in quoted:
        variant_id = line.get("variant_id")
        if not variant_id or variant_id in seen:
            continue
        variant = session.get(ProductVariant, UUID(str(variant_id)))
        product = session.get(Product, variant.product_id) if variant is not None else None
        if variant is None or product is None or not is_500g_unit(variant) or not product_is_fidelity_eligible(product):
            continue
        seen.add(str(variant_id))
        items.append(
            {
                "variant_id": str(variant_id),
                "product_name": line["product_name"],
                "variant_name": line["variant_name"],
                "unit_cents": line["unit_cents"],
            }
        )
    return items


def apply_checkout_credit(session: Session, settings: Settings, payload: dict, quote: dict) -> dict:
    from sqlalchemy import select as sql_select

    from app.domain.house_fidelity import campaign_is_publicly_active, current_campaign
    from app.models.house_fidelity import HouseFidelityCredit as CreditRow
    eligible = quote.get("eligible_credit_items") or []
    quote["credit_applied"] = False
    quote["discount_cents"] = 0
    quote["total_cents"] = quote["subtotal_cents"]
    if not payload.get("apply_fidelity_credit"):
        return quote
    account = payload.get("_fidelity_account")
    if account is None:
        quote["credit_notice"] = "Identifique-se para usar um crédito. O saldo não é consultado só com CPF."
        return quote
    campaign = current_campaign(session)
    if campaign is None or not campaign_is_publicly_active(settings, campaign):
        quote["credit_notice"] = "A fidelidade da casa ainda não está em vigor."
        return quote
    available = session.scalar(
        sql_select(CreditRow)
        .where(
            CreditRow.campaign_id == campaign.id,
            CreditRow.account_id == account.id,
            CreditRow.status == "available",
        )
        .order_by(CreditRow.created_at)
    )
    if available is None:
        quote["credit_notice"] = "Não há crédito disponível para usar neste pedido."
        return quote
    if not eligible:
        quote["credit_notice"] = (
            "Este item não participa da fidelidade. "
            "Pode comprar normalmente ou escolher um pão da vitrine elegível. O crédito não foi aplicado."
        )
        return quote
    chosen = str(payload.get("fidelity_variant_id") or "")
    if not chosen and len(eligible) == 1:
        chosen = eligible[0]["variant_id"]
    match = next((row for row in eligible if row["variant_id"] == chosen), None)
    if match is None:
        quote["credit_notice"] = "Escolha qual pão de 500 g receberá o crédito."
        return quote
    discount = int(match["unit_cents"])
    quote["discount_cents"] = discount
    quote["total_cents"] = max(quote["subtotal_cents"] - discount, 0)
    quote["credit_applied"] = True
    quote["credit_variant_id"] = match["variant_id"]
    quote["credit_label"] = f"{match['product_name']} · {match['variant_name']}"
    quote["credit_notice"] = None
    return quote


def quote_lines(session: Session, settings: Settings, payload: dict) -> dict:
    requested = date.fromisoformat(str(payload["requested_date"]))
    raw_items = payload.get("items") or []
    if not raw_items:
        raise ConfirmationError("selecione ao menos um pão")
    quoted = []
    proposed: list[ProposedLine] = []
    subtotal = 0
    for raw in raw_items:
        quantity = int(raw["quantity"])
        if quantity < 1:
            raise ConfirmationError("quantidade deve ser maior que zero")
        if raw.get("variant_id"):
            line, proposed_line = _quote_product(session, raw, quantity)
        elif raw.get("dough_type_id"):
            line, proposed_line = _quote_custom(session, raw, quantity)
        else:
            raise ConfirmationError("selecione um pão do catálogo ou monte um pão personalizado")
        subtotal += line["line_cents"]
        quoted.append(line)
        proposed.append(proposed_line)
    day = evaluate_day(session, settings, requested, resolve_proposed_lines(session, proposed))
    catalog_gap = day.reason in {REASON_UNKNOWN_UNITS, REASON_UNKNOWN_BASE}
    if not day.eligible_for_selection and not catalog_gap:
        raise CapacityError(day.accessible_label)
    pending_units = any(item.get("origin") == "product" and item.get("physical_units") is None for item in quoted)
    pending_base = any(item.get("origin") == "product" and item.get("catalog_base_pending") for item in quoted)
    notice = None
    if pending_units or pending_base:
        missing = []
        if pending_units:
            missing.append("quantos pães físicos há em cada unidade")
        if pending_base:
            missing.append("o tipo de pão")
        notice = (
            "Dá para enviar o pedido. A ficha ainda não informa "
            + " nem ".join(missing)
            + ". A data só fica reservada no aceite, quando isso estiver completo."
        )
    quote = {
        "requested_date": requested.isoformat(),
        "currency": "BRL",
        "subtotal_cents": subtotal,
        "discount_cents": 0,
        "total_cents": subtotal,
        "items": quoted,
        "date_label": day.accessible_label,
        "occupies_capacity": False,
        "notice": notice,
        "credit_applied": False,
        "credit_notice": None,
        "eligible_credit_items": _eligible_credit_items(session, quoted),
        "fidelity_qualifies": _lines_qualify(session, quoted),
    }
    return apply_checkout_credit(session, settings, payload, quote)


def _lines_qualify(session: Session, quoted: list[dict]) -> bool:
    from app.domain.house_fidelity import lines_qualify_for_stamp

    return lines_qualify_for_stamp(session, quoted)


_UFS = frozenset(
    {
        "AC",
        "AL",
        "AP",
        "AM",
        "BA",
        "CE",
        "DF",
        "ES",
        "GO",
        "MA",
        "MT",
        "MS",
        "MG",
        "PA",
        "PB",
        "PR",
        "PE",
        "PI",
        "RJ",
        "RN",
        "RS",
        "RO",
        "RR",
        "SC",
        "SP",
        "SE",
        "TO",
    }
)


_DELIVERY_KEYS = (
    "delivery_street",
    "delivery_number",
    "delivery_complement",
    "delivery_district",
    "delivery_city",
    "delivery_state",
    "delivery_postal_code",
)


_PREFERRED_TIME = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)(?::([0-5]\d))?$")


def parse_preferred_time(value: object) -> time | None:
    if value is None:
        return None
    if isinstance(value, time):
        return time(value.hour, value.minute)
    text = str(value).strip()
    if not text:
        return None
    match = _PREFERRED_TIME.fullmatch(text)
    if match is None:
        raise ConfirmationError("informe o horário preferido como 16:30, ou deixe em branco")
    return time(int(match.group(1)), int(match.group(2)))


def format_preferred_time(value: time | None) -> str | None:
    if value is None:
        return None
    return f"{value.hour:02d}:{value.minute:02d}"


def _has_delivery_input(payload: dict) -> bool:
    return any(str(payload.get(key) or "").strip() for key in _DELIVERY_KEYS)


def parse_delivery_address(payload: dict) -> dict:
    def text(key: str) -> str:
        return str(payload.get(key) or "").strip()

    street = text("delivery_street")
    number = text("delivery_number")
    complement = text("delivery_complement") or None
    district = text("delivery_district")
    city = text("delivery_city")
    state = text("delivery_state").upper()
    postal = "".join(ch for ch in text("delivery_postal_code") if ch.isdigit())
    if not street or len(street) > 160:
        raise ConfirmationError("informe a rua do endereço de entrega")
    if not number or len(number) > 20:
        raise ConfirmationError("informe o número do endereço de entrega")
    if complement is not None and len(complement) > 80:
        raise ConfirmationError("o complemento do endereço é longo demais")
    if not district or len(district) > 80:
        raise ConfirmationError("informe o bairro da entrega")
    if not city or len(city) > 80:
        raise ConfirmationError("informe a cidade da entrega")
    if state not in _UFS:
        raise ConfirmationError("informe a sigla do estado, como SP")
    if len(postal) != 8:
        raise ConfirmationError("informe o CEP com 8 dígitos")
    return {
        "delivery_street": street,
        "delivery_number": number,
        "delivery_complement": complement,
        "delivery_district": district,
        "delivery_city": city,
        "delivery_state": state,
        "delivery_postal_code": postal,
    }


def apply_delivery_address(order: Order, address: dict) -> None:
    order.fulfillment_modality = "delivery"
    order.delivery_street = address["delivery_street"]
    order.delivery_number = address["delivery_number"]
    order.delivery_complement = address["delivery_complement"]
    order.delivery_district = address["delivery_district"]
    order.delivery_city = address["delivery_city"]
    order.delivery_state = address["delivery_state"]
    order.delivery_postal_code = address["delivery_postal_code"]
    if order.delivery_fee_cents is None:
        order.delivery_fee_cents = 0


def public_delivery_address(order: Order) -> dict | None:
    if not order.delivery_street:
        return None
    return {
        "street": order.delivery_street,
        "number": order.delivery_number,
        "complement": order.delivery_complement,
        "district": order.delivery_district,
        "city": order.delivery_city,
        "state": order.delivery_state,
        "postal_code": order.delivery_postal_code,
    }


def submit_order(session: Session, settings: Settings, payload: dict) -> tuple[Order, str]:
    idempotency_key = str(payload.get("idempotency_key") or "").strip()
    if not idempotency_key or len(idempotency_key) > 120:
        raise ConfirmationError("chave de envio obrigatória")
    existing = session.scalar(
        select(Order).where(Order.submit_idempotency_key == idempotency_key)
    )
    quoted_cents = int(payload["quoted_cents"])
    quote = quote_lines(session, settings, payload)
    if quote["total_cents"] != quoted_cents:
        raise PriceChangedError(quoted_cents, quote["total_cents"])
    if existing is not None:
        if existing.total_cents != quote["total_cents"]:
            raise PriceChangedError(quoted_cents, quote["total_cents"])
        return existing, ""

    name = str(payload.get("customer_name") or "").strip()
    if not name or len(name) > 160:
        raise ConfirmationError("informe o nome de quem pede")
    email = _email(str(payload.get("customer_email") or ""))
    phone = str(payload.get("customer_phone") or "").strip() or None
    address = (
        parse_delivery_address(payload) if _has_delivery_input(payload) else None
    )
    preferred = parse_preferred_time(payload.get("preferred_time"))
    token = secrets.token_urlsafe(32)
    order = Order(
        public_reference=new_public_reference(),
        status=OrderStatus.SUBMITTED.value,
        fulfillment_modality="delivery" if address else "pickup",
        preferred_time=preferred,
        production_local_date=date.fromisoformat(quote["requested_date"]),
        customer_name=name,
        customer_email=email,
        customer_phone=phone,
        delivery_street=address["delivery_street"] if address else None,
        delivery_number=address["delivery_number"] if address else None,
        delivery_complement=address["delivery_complement"] if address else None,
        delivery_district=address["delivery_district"] if address else None,
        delivery_city=address["delivery_city"] if address else None,
        delivery_state=address["delivery_state"] if address else None,
        delivery_postal_code=address["delivery_postal_code"] if address else None,
        customer_note=str(payload.get("customer_note") or "")[:2000],
        currency="BRL",
        subtotal_cents=quote["subtotal_cents"],
        delivery_fee_cents=0,
        discount_cents=int(quote.get("discount_cents") or 0),
        total_cents=quote["total_cents"],
        holds_capacity=False,
        access_token_hash=hash_access_token(token),
        submit_idempotency_key=idempotency_key,
        crm_id_sessao=_crm_session(payload.get("id_sessao")),
        order_kind="standard",
        fidelity_opt_in=False,
    )
    session.add(order)
    session.flush()
    contains_custom = any(item["origin"] == "custom" for item in quote["items"])
    for item in quote["items"]:
        if item["origin"] == "custom":
            order_item = OrderItem(
                order_id=order.id,
                dough_type_id=UUID(item["dough_type_id"]),
                bread_shape_id=UUID(item["bread_shape_id"]),
                recipe_base_id=UUID(item["recipe_base_id"]),
                physical_units=item["physical_units"],
                quantity=item["quantity"],
                dough_name_snapshot=item["product_name"],
                shape_name_snapshot=item["variant_name"],
                unit_price_cents=item["unit_cents"],
                line_total_cents=item["line_cents"],
                net_weight_grams=item["weight_grams"],
            )
        else:
            variant = session.get(ProductVariant, UUID(item["variant_id"]))
            product = session.get(Product, UUID(item["product_id"]))
            assert variant is not None and product is not None
            order_item = OrderItem(
                order_id=order.id,
                product_id=product.id,
                product_variant_id=variant.id,
                recipe_base_id=product.recipe_base_id,
                physical_units=item["physical_units"],
                quantity=item["quantity"],
                dough_name_snapshot=item["product_name"],
                shape_name_snapshot=item["variant_name"],
                unit_price_cents=item["unit_cents"],
                line_total_cents=item["line_cents"],
                net_weight_grams=item.get("weight_grams"),
            )
        session.add(order_item)
        session.flush()
        for extra in item.get("ingredients") or []:
            session.add(
                OrderItemIngredient(
                    order_item_id=order_item.id,
                    ingredient_id=UUID(extra["id"]),
                    name_snapshot=extra["name"],
                    surcharge_cents=None,
                )
            )
        if item.get("adaptation"):
            create_adaptation(
                session,
                order_item,
                item["adaptation"]["text"],
                item["adaptation"]["reason"],
            )
    if (order.total_cents or 0) > 0:
        session.add(
            PaymentRecord(
                order_id=order.id,
                provider=PaymentProvider.ACTIONHUB.value,
                expected_cents=order.total_cents or 0,
                currency="BRL",
                financial_status=FinancialStatus.PENDING.value,
            )
        )
    attach_fidelity_opt_in(session, settings, order, payload)
    order.fidelity_qualifies = bool(quote.get("fidelity_qualifies"))
    if quote.get("credit_applied"):
        from app.domain.house_fidelity_ledger import reserve_credit

        account = payload.get("_fidelity_account")
        if account is None:
            raise ConfirmationError("identifique-se para usar o crédito neste pedido")
        reserve_credit(session, settings, account.id, order)
    enqueue_order_email(session, settings, order, "order_submitted")
    enqueue_admin_order_email(session, settings, order)
    session.flush()
    from app.domain.crm_tracking import emit_order_fact

    emit_order_fact(session, settings, order, "pedido_enviar", situacao="submitted")
    if settings.public_payments_enabled and not contains_custom and (order.total_cents or 0) > 0:
        try:
            start_checkout(session, settings, order, "pix")
        except ConfirmationError:
            pass
    return order, token


def set_delivery_address(session: Session, settings: Settings, order: Order, payload: dict) -> Order:
    if order.status != OrderStatus.SUBMITTED.value:
        raise ConfirmationError("o endereço deste pedido não pode mais ser alterado")
    records = list(
        session.scalars(select(PaymentRecord).where(PaymentRecord.order_id == order.id))
    )
    if order_is_financially_settled(order, records):
        raise ConfirmationError("o endereço não muda depois do pagamento")
    apply_delivery_address(order, parse_delivery_address(payload))
    session.flush()
    from app.domain.email_outbox import refresh_order_email

    refresh_order_email(session, settings, order, "order_submitted")
    return order


def require_order_token(
    session: Session, settings: Settings, public_reference: str, token: str | None
) -> Order:
    order = session.scalar(select(Order).where(Order.public_reference == public_reference))
    if order is None or not order.access_token_hash:
        raise NotFoundError("pedido não encontrado")
    if token and hash_access_token(token) == order.access_token_hash:
        return order
    expected = email_access_token(settings, order)
    if token and len(token) == len(expected) and hmac.compare_digest(token, expected):
        return order
    raise AuthError("acesso ao pedido recusado")


def visitor_state(order: Order, records: list[PaymentRecord]) -> str:
    if order.status == OrderStatus.CANCELLED.value:
        if order.proposed_production_date:
            return "resolution_pending"
        return "cancelled"
    if order.status in {
        OrderStatus.CONFIRMED.value,
        OrderStatus.IN_PRODUCTION.value,
        OrderStatus.READY.value,
        OrderStatus.COMPLETED.value,
    }:
        return "accepted"
    if order.proposed_production_date and order.status == OrderStatus.SUBMITTED.value:
        return "date_alternative"
    settled = order_is_financially_settled(order, records)
    if settled:
        return "paid_awaiting_accept"
    if any(row.financial_status == FinancialStatus.PENDING.value for row in records):
        if any(row.external_reference for row in records):
            return "payment_processing"
        return "awaiting_payment"
    if any(row.financial_status in {"failed", "cancelled"} for row in records):
        return "payment_failed"
    return "awaiting_payment"


def public_order_view(session: Session, order: Order) -> dict:
    records = list(
        session.scalars(select(PaymentRecord).where(PaymentRecord.order_id == order.id))
    )
    items = list(session.scalars(select(OrderItem).where(OrderItem.order_id == order.id)))
    extras = (
        list(
            session.scalars(
                select(OrderItemIngredient).where(
                    OrderItemIngredient.order_item_id.in_([item.id for item in items])
                )
            )
        )
        if items
        else []
    )
    extra_roles = {row.id: session.get(Ingredient, row.ingredient_id) for row in extras}
    extras_by_item: dict[UUID, list[dict]] = {}
    for row in extras:
        ingredient = extra_roles.get(row.id)
        extras_by_item.setdefault(row.order_item_id, []).append(
            {
                "name": row.name_snapshot or (ingredient.name if ingredient else "Ingrediente"),
                "assistant_role": ingredient.assistant_role if ingredient else None,
            }
        )
    adaptations = adaptations_for_order(session, order.id)
    latest = records[-1] if records else None
    pending = order_has_pending_adaptation(session, order.id)
    custom = any(item.product_variant_id is None for item in items)
    accepted = order.status in {
        OrderStatus.CONFIRMED.value,
        OrderStatus.IN_PRODUCTION.value,
        OrderStatus.READY.value,
        OrderStatus.COMPLETED.value,
    }
    payment_available = (accepted if custom else order.status == OrderStatus.SUBMITTED.value) and not (
        order_is_financially_settled(order, records)
    )
    notice = (
        "Após o pagamento, vamos conferir sua solicitação e confirmar a data da sua fornada por e-mail."
    )
    if custom and not accepted:
        notice = (
            "Aguardando o aceite de A Loja. A data escolhida é uma preferência. "
            "Depois do aceite, você poderá pagar por Pix ou cartão. O pagamento não reserva a fornada."
        )
    elif custom and accepted and not order_is_financially_settled(order, records):
        notice = "A Loja aceitou o pedido e reservou a fornada. Você pode pagar por Pix ou cartão."
    elif pending:
        notice = (
            "Recebemos o pedido. Há adaptação pendente de avaliação — isso ainda não confirma a alteração. "
            "Os detalhes estão nesta página protegida. Depois do pagamento, vamos conferir a data da fornada."
        )
    if (order.total_cents or 0) == 0:
        notice = "Sem valor a pagar — benefício de fidelidade. A data ainda depende do aceite de A Loja."
    elif order.fidelity_opt_in:
        notice = (
            notice
            + " Se A Loja aceitar este pedido e o pagamento for confirmado, ele poderá contar um carimbo. "
            "O saldo só muda depois do aceite e do pagamento."
        )
    return {
        "public_reference": order.public_reference,
        "status": order.status,
        "visitor_state": (
            "awaiting_bakery"
            if custom and not accepted and not order_is_financially_settled(order, records)
            else visitor_state(order, records)
        ),
        "requested_date": order.production_local_date.isoformat()
        if order.production_local_date
        else None,
        "preferred_time": format_preferred_time(order.preferred_time),
        "fulfillment_modality": order.fulfillment_modality,
        "proposed_date": order.proposed_production_date.isoformat()
        if order.proposed_production_date
        else None,
        "confirmed": order.status
        in {
            OrderStatus.CONFIRMED.value,
            OrderStatus.IN_PRODUCTION.value,
            OrderStatus.READY.value,
            OrderStatus.COMPLETED.value,
        },
        "holds_capacity": order.holds_capacity,
        "financially_settled": order_is_financially_settled(order, records),
        "payment_available": payment_available,
        "customer_name": order.customer_name,
        "customer_email": order.customer_email,
        "delivery_address": public_delivery_address(order),
        "total_cents": order.total_cents,
        "currency": order.currency,
        "items": [
            {
                "id": str(item.id),
                "product_name": item.dough_name_snapshot,
                "variant_name": item.shape_name_snapshot,
                "quantity": item.quantity,
                "unit_cents": item.unit_price_cents,
                "line_cents": item.line_total_cents,
                "weight_grams": item.net_weight_grams,
                "origin": "custom" if item.product_variant_id is None else "product",
                "ingredients": extras_by_item.get(item.id, []),
                "adaptation": public_adaptation_view(adaptations.get(item.id)),
            }
            for item in items
        ],
        "payment": {
            "financial_status": latest.financial_status if latest else None,
            "expected_cents": latest.expected_cents if latest else None,
            "amount_paid_cents": latest.amount_paid_cents if latest else None,
            "external_reference": latest.external_reference if latest else None,
            "sanitized_error": latest.sanitized_error if latest else None,
            "method": latest.method if latest else None,
            "pix": {
                "qr_code": latest.pix_qr_code,
                "qr_code_base64": latest.pix_qr_code_base64,
                "ticket_url": latest.pix_ticket_url,
                "date_of_expiration": latest.pix_expires_at.isoformat()
                if latest.pix_expires_at
                else None,
                "mp_payment_id": latest.mp_payment_id,
            }
            if latest and latest.method == "pix" and not order_is_financially_settled(order, records)
            else None,
        },
        "notice": notice,
        "fidelity_opt_in": bool(order.fidelity_opt_in),
        "fidelity_stamp_preview": bool(
            order.fidelity_opt_in and not order_is_financially_settled(order, records)
        ),
        "order_kind": order.order_kind or "standard",
    }


def _active_payment(session: Session, order: Order) -> PaymentRecord:
    records = list(
        session.scalars(
            select(PaymentRecord)
            .where(PaymentRecord.order_id == order.id)
            .order_by(PaymentRecord.created_at.asc())
        )
    )
    if not records:
        raise ConfirmationError("pedido sem registro financeiro")
    return records[-1]


def _parse_pix_expiration(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def _apply_hub_result(record: PaymentRecord, result) -> None:
    record.external_reference = result.order_id
    record.method = result.method
    record.mp_payment_id = result.mp_payment_id
    if result.method == "pix":
        record.pix_qr_code = result.pix_qr_code
        record.pix_qr_code_base64 = result.pix_qr_code_base64
        record.pix_ticket_url = result.pix_ticket_url
        record.pix_expires_at = _parse_pix_expiration(result.pix_date_of_expiration)
    else:
        record.pix_qr_code = None
        record.pix_qr_code_base64 = None
        record.pix_ticket_url = None
        record.pix_expires_at = None


def start_checkout(
    session: Session, settings: Settings, order: Order, method: str, *, replace: bool = False
) -> dict:
    if method not in {"pix", "card"}:
        raise ConfirmationError("escolha Pix ou cartão")
    if (order.total_cents or 0) == 0:
        raise ConfirmationError("este pedido não tem valor a pagar")
    custom = _order_contains_custom(session, order)
    if custom:
        if order.status != OrderStatus.CONFIRMED.value:
            raise ConfirmationError("o pagamento abre depois do aceite de A Loja")
    elif order.status != OrderStatus.SUBMITTED.value:
        raise ConfirmationError("este pedido não aceita nova cobrança")
    records = list(session.scalars(select(PaymentRecord).where(PaymentRecord.order_id == order.id)))
    if order_is_financially_settled(order, records):
        raise ConfirmationError("este pedido já está quitado")
    record = _active_payment(session, order)
    if record.expected_cents != (order.total_cents or 0):
        raise ConfirmationError("não é possível alterar o valor de uma cobrança existente")
    if record.financial_status == FinancialStatus.PAID.value:
        raise ConfirmationError("este pedido já está pago")

    if (
        record.external_reference
        and record.method
        and record.method != method
        and record.financial_status == FinancialStatus.PENDING.value
        and not replace
    ):
        raise ConfirmationError(
            "já há uma cobrança em andamento; confirme o estado dela antes de trocar o método"
        )

    if replace and record.external_reference and record.financial_status == FinancialStatus.PENDING.value:
        try:
            cancel_amount_checkout(settings, record.external_reference)
        except HubConflictError:
            raise ConfirmationError("o pagamento anterior já foi aprovado") from None
        record.financial_status = FinancialStatus.CANCELLED.value
        record.sanitized_error = "tentativa substituída por outro método"
        record = PaymentRecord(
            order_id=order.id,
            provider=PaymentProvider.ACTIONHUB.value,
            expected_cents=order.total_cents or 0,
            currency="BRL",
            financial_status=FinancialStatus.PENDING.value,
            method=method,
            idempotency_key=str(uuid4()),
        )
        session.add(record)
        session.flush()
    elif record.method and record.method != method and not record.external_reference:
        record.method = method

    payment_request_id = record.idempotency_key or str(uuid4())
    if record.idempotency_key is None:
        record.idempotency_key = payment_request_id
    record.method = method
    session.flush()

    if record.external_reference and record.method == method:
        checkout_url = None
        if method == "card":
            existing = lookup_amount_checkout(settings, payment_request_id=payment_request_id)
            checkout_url = existing.checkout_url if existing else None
        return {
            "checkout_url": checkout_url,
            "external_reference": record.external_reference,
            "expected_cents": record.expected_cents,
            "reused": True,
            "method": method,
            "pix": {
                "qr_code": record.pix_qr_code,
                "qr_code_base64": record.pix_qr_code_base64,
                "ticket_url": record.pix_ticket_url,
                "date_of_expiration": record.pix_expires_at.isoformat()
                if record.pix_expires_at
                else None,
            }
            if method == "pix"
            else None,
        }

    prepared = {
        "payment_request_id": payment_request_id,
        "expected_cents": record.expected_cents,
        "public_reference": order.public_reference,
        "customer_email": order.customer_email,
        "customer_name": order.customer_name,
        "description": f"Pedido Loja de Pães {order.public_reference}",
        "return_to": f"/pedido/{order.public_reference}",
        "method": method,
    }
    try:
        result = recover_or_create_checkout(settings, prepared)
    except ConfirmationError as exc:
        record.sanitized_error = str(exc)[:2000]
        session.commit()
        raise
    record.sanitized_error = None
    if result["expected_cents"] != record.expected_cents:
        raise ConfirmationError("o Hub devolveu um valor diferente do pedido")
    attach_hub_checkout(
        session,
        order,
        hub_order_id=result["external_reference"],
        amount_cents=result["expected_cents"],
        hub_result=result.get("hub_result"),
    )
    session.flush()
    record = _active_payment(session, order)
    return {
        "checkout_url": result.get("checkout_url"),
        "external_reference": record.external_reference,
        "expected_cents": record.expected_cents,
        "reused": result["reused"],
        "method": method,
        "pix": {
            "qr_code": record.pix_qr_code,
            "qr_code_base64": record.pix_qr_code_base64,
            "ticket_url": record.pix_ticket_url,
            "date_of_expiration": record.pix_expires_at.isoformat() if record.pix_expires_at else None,
        }
        if method == "pix"
        else None,
    }


def attach_hub_checkout(
    session: Session,
    order: Order,
    *,
    hub_order_id: str,
    amount_cents: int,
    hub_result=None,
) -> PaymentRecord:
    record = _active_payment(session, order)
    if amount_cents != record.expected_cents:
        raise ConfirmationError("o Hub devolveu um valor diferente do pedido")
    if record.external_reference and record.external_reference != hub_order_id:
        raise ConfirmationError("já existe outra cobrança ativa para este pedido")
    record.external_reference = hub_order_id
    if hub_result is not None:
        _apply_hub_result(record, hub_result)
    session.flush()
    return record


def recover_or_create_checkout(settings: Settings, prepared: dict) -> dict:
    payment_request_id = prepared["payment_request_id"]
    method = prepared["method"]
    try:
        result = request_amount_checkout(
            settings,
            order_reference=prepared["public_reference"],
            payment_request_id=payment_request_id,
            amount_cents=prepared["expected_cents"],
            description=prepared["description"],
            customer_email=prepared["customer_email"],
            customer_name=prepared["customer_name"] or prepared["customer_email"],
            return_to=prepared["return_to"],
            idempotency_key=payment_request_id,
            method=method,
        )
        return {
            "checkout_url": result.checkout_url,
            "external_reference": result.order_id,
            "expected_cents": result.amount_cents,
            "reused": result.reused,
            "hub_result": result,
        }
    except HubUnavailableError:
        existing = lookup_amount_checkout(settings, payment_request_id=payment_request_id)
        if existing is None:
            raise
        return {
            "checkout_url": existing.checkout_url,
            "external_reference": existing.order_id,
            "expected_cents": existing.amount_cents,
            "reused": True,
            "hub_result": existing,
        }


def reconcile_checkout(session: Session, settings: Settings, order: Order) -> dict:
    record = _active_payment(session, order)
    if not record.idempotency_key:
        return public_order_view(session, order)
    existing = lookup_amount_checkout(settings, payment_request_id=record.idempotency_key)
    if existing is None:
        return public_order_view(session, order)
    if existing.amount_cents != record.expected_cents:
        record.sanitized_error = "valor no Hub diverge do pedido"
        session.flush()
        return public_order_view(session, order)
    _apply_hub_result(record, existing)
    if str(existing.status).upper() == "PAID" and record.financial_status != FinancialStatus.PAID.value:
        record.financial_status = FinancialStatus.PAID.value
        record.amount_paid_cents = record.expected_cents
        record.confirmed_at = record.confirmed_at or datetime.now(UTC)
        record.last_synced_at = datetime.now(UTC)
        record.sanitized_error = None
        enqueue_order_email(session, settings, order, "payment_approved")
        session.flush()
        from app.domain.crm_tracking import emit_order_fact

        emit_order_fact(session, settings, order, "pagamento_registrar", situacao="paid")
        from app.domain.house_fidelity_ledger import reconcile_order

        reconcile_order(session, settings, order)
        return public_order_view(session, order)
    session.flush()
    return public_order_view(session, order)


def refresh_open_checkout(session: Session, settings: Settings, order_id: UUID) -> None:
    """Consulta a cobrança pendente no Hub. Falha de transporte não rebaixa nem inventa pagamento."""
    order = session.get(Order, order_id)
    if order is None or order.status != OrderStatus.SUBMITTED.value:
        return
    record = session.scalar(
        select(PaymentRecord)
        .where(PaymentRecord.order_id == order.id)
        .order_by(PaymentRecord.created_at.desc())
    )
    if (
        record is None
        or record.financial_status != FinancialStatus.PENDING.value
        or not record.idempotency_key
    ):
        return
    try:
        reconcile_checkout(session, settings, order)
    except HubUnavailableError:
        record.sanitized_error = (
            "A consulta ao pagamento falhou. Isso não significa que o cliente deixou de pagar."
        )
        session.flush()


def propose_production_date(session: Session, order: Order, day: date) -> Order:
    if order.status != OrderStatus.SUBMITTED.value:
        raise ConfirmationError("só a solicitação pendente recebe outra data")
    if order.production_local_date == day:
        raise ConfirmationError("a data proposta é a mesma já pedida")
    order.proposed_production_date = day
    session.flush()
    return order


def accept_proposed_date(session: Session, settings: Settings, order: Order) -> Order:
    if order.status != OrderStatus.SUBMITTED.value:
        raise ConfirmationError("só a solicitação pendente pode aceitar outra data")
    if order.proposed_production_date is None:
        raise ConfirmationError("não há data alternativa proposta")
    records = list(session.scalars(select(PaymentRecord).where(PaymentRecord.order_id == order.id)))
    if any(
        row.financial_status in ACTIVE_PAYMENT and row.external_reference
        for row in records
        if row.financial_status != FinancialStatus.FAILED.value
    ):
        for row in records:
            if row.financial_status == FinancialStatus.PENDING.value:
                raise ConfirmationError(
                    "há cobrança em andamento; a data só muda depois da resolução financeira"
                )
    order.production_local_date = order.proposed_production_date
    order.proposed_production_date = None
    session.flush()
    del settings
    return order


def attach_fidelity_opt_in(session: Session, settings: Settings, order: Order, payload: dict) -> None:
    from app.domain.customer_identity import load_customer
    from app.domain.house_fidelity import campaign_is_publicly_active, current_campaign

    if not payload.get("fidelity_opt_in"):
        order.fidelity_opt_in = False
        return
    account = payload.get("_fidelity_account")
    if account is None:
        order.fidelity_opt_in = False
        return
    campaign = current_campaign(session)
    if campaign is None or not campaign_is_publicly_active(settings, campaign):
        order.fidelity_opt_in = False
        return
    from app.domain.bakery_time import bakery_now

    if campaign.starts_at is None or bakery_now(settings) < campaign.starts_at:
        order.fidelity_opt_in = False
        return
    order.fidelity_opt_in = True
    order.fidelity_account_id = account.id
    order.fidelity_campaign_id = campaign.id
    order.fidelity_rules_version = campaign.rules_version
    del load_customer
