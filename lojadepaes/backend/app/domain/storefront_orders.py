from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from datetime import UTC, date, datetime
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
from app.domain.email_outbox import enqueue_order_email
from app.domain.errors import (
    AuthError,
    CapacityError,
    ConfirmationError,
    NotFoundError,
    PriceChangedError,
)
from app.domain.orders import new_public_reference
from app.domain.payments import order_is_financially_settled
from app.domain.schedule import ProposedLine, evaluate_day, resolve_proposed_lines
from app.models.enums import EditorialStatus, FinancialStatus, OrderStatus, PaymentProvider
from app.models.orders import Order, OrderItem
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


def quote_lines(session: Session, settings: Settings, payload: dict) -> dict:
    requested = date.fromisoformat(str(payload["requested_date"]))
    raw_items = payload.get("items") or []
    if not raw_items:
        raise ConfirmationError("selecione ao menos um pão")
    quoted = []
    proposed: list[ProposedLine] = []
    subtotal = 0
    for raw in raw_items:
        variant_id = UUID(str(raw["variant_id"]))
        quantity = int(raw["quantity"])
        if quantity < 1:
            raise ConfirmationError("quantidade deve ser maior que zero")
        product, variant = _load_variant(session, variant_id)
        if product.editorial_status != EditorialStatus.PUBLISHED.value or not product.is_available:
            raise ConfirmationError(f"{product.name} não está à venda")
        if not variant.is_active or variant.price_cents is None or variant.price_cents <= 0:
            raise ConfirmationError(f"a opção de {product.name} não está à venda")
        if variant.physical_units is None:
            raise ConfirmationError(
                f"cadastre os pães físicos de {product.name} antes de receber pedidos"
            )
        if product.recipe_base_id is None:
            raise ConfirmationError(f"vincule a receita-base de {product.name} antes de receber pedidos")
        line_cents = variant.price_cents * quantity
        subtotal += line_cents
        raw_adapt = raw.get("adaptation")
        if not isinstance(raw_adapt, dict):
            raw_adapt = {
                "text": raw.get("adaptation_text"),
                "reason": raw.get("adaptation_reason"),
            }
        adaptation = parse_customer_adaptation(raw_adapt)
        quoted.append(
            {
                "product_id": str(product.id),
                "variant_id": str(variant.id),
                "product_name": product.name,
                "variant_name": variant.display_name,
                "quantity": quantity,
                "unit_cents": variant.price_cents,
                "line_cents": line_cents,
                "physical_units": variant.physical_units * quantity,
                "adaptation": adaptation,
            }
        )
        proposed.append(
            ProposedLine(kind="product", quantity=quantity, variant_id=variant.id)
        )
    day = evaluate_day(session, settings, requested, resolve_proposed_lines(session, proposed))
    if not day.eligible_for_selection:
        raise CapacityError(day.accessible_label)
    return {
        "requested_date": requested.isoformat(),
        "currency": "BRL",
        "subtotal_cents": subtotal,
        "total_cents": subtotal,
        "items": quoted,
        "date_label": day.accessible_label,
        "occupies_capacity": False,
    }


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
        raise ConfirmationError("informe o nome de quem vai receber")
    email = _email(str(payload.get("customer_email") or ""))
    phone = str(payload.get("customer_phone") or "").strip() or None
    address = (
        parse_delivery_address(payload) if _has_delivery_input(payload) else None
    )
    token = secrets.token_urlsafe(32)
    order = Order(
        public_reference=new_public_reference(),
        status=OrderStatus.SUBMITTED.value,
        fulfillment_modality="delivery" if address else "pickup",
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
        discount_cents=0,
        total_cents=quote["total_cents"],
        holds_capacity=False,
        access_token_hash=hash_access_token(token),
        submit_idempotency_key=idempotency_key,
        crm_id_sessao=_crm_session(payload.get("id_sessao")),
    )
    session.add(order)
    session.flush()
    for item in quote["items"]:
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
        )
        session.add(order_item)
        session.flush()
        if item.get("adaptation"):
            create_adaptation(
                session,
                order_item,
                item["adaptation"]["text"],
                item["adaptation"]["reason"],
            )
    session.add(
        PaymentRecord(
            order_id=order.id,
            provider=PaymentProvider.ACTIONHUB.value,
            expected_cents=order.total_cents or 0,
            currency="BRL",
            financial_status=FinancialStatus.PENDING.value,
        )
    )
    enqueue_order_email(session, settings, order, "order_submitted")
    session.flush()
    from app.domain.crm_tracking import emit_order_fact

    emit_order_fact(session, settings, order, "pedido_enviar", situacao="submitted")
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
    adaptations = adaptations_for_order(session, order.id)
    latest = records[-1] if records else None
    pending = order_has_pending_adaptation(session, order.id)
    notice = (
        "Após o pagamento, vamos conferir sua solicitação e confirmar a data da sua fornada por e-mail."
    )
    if pending:
        notice = (
            "Recebemos o pedido. Há adaptação pendente de avaliação — isso ainda não confirma a alteração. "
            "Os detalhes estão nesta página protegida. Depois do pagamento, vamos conferir a data da fornada."
        )
    return {
        "public_reference": order.public_reference,
        "status": order.status,
        "visitor_state": visitor_state(order, records),
        "requested_date": order.production_local_date.isoformat()
        if order.production_local_date
        else None,
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
                "line_cents": item.line_total_cents,
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
    if order.status != OrderStatus.SUBMITTED.value:
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
    result = recover_or_create_checkout(settings, prepared)
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
        return public_order_view(session, order)
    session.flush()
    return public_order_view(session, order)


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
