from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.domain.attendance import fold_text
from app.domain.bakery_time import bakery_today
from app.domain.email_outbox import enqueue_date_request_email
from app.domain.errors import ConfirmationError, ConflictError, NotFoundError
from app.domain.orders import (
    add_internal_note,
    confirm_order,
    delivery_has_any_field,
    new_public_reference,
    order_delivery_pending,
)
from app.domain.storefront_orders import (
    _quote_product,
    apply_delivery_address,
    parse_delivery_address,
)
from app.models.date_requests import DateRequest, DateRequestEvent
from app.models.enums import EditorialStatus, FinancialStatus, OrderStatus, PaymentProvider
from app.models.orders import Order, OrderItem
from app.models.payments import PaymentRecord
from app.models.products import Product, ProductVariant

STATUS_CONVERTED = "converted"
STATUS_AWAITING = "awaiting_details"
GENERIC_COMMERCIAL_GAP = "faltam os pães e as quantidades da encomenda"


def date_request_access_token(settings: Settings, request: DateRequest) -> str:
    secret = settings.admin_session_secret.encode("utf-8")
    material = f"date-request-access:{request.id}".encode("utf-8")
    return hmac.new(secret, material, hashlib.sha256).hexdigest()


def verify_date_request_token(settings: Settings, request: DateRequest, token: str | None) -> bool:
    if not token:
        return False
    expected = date_request_access_token(settings, request)
    return len(token) == len(expected) and hmac.compare_digest(token, expected)


def _address_from(request: DateRequest, payload_address: dict | None) -> dict | None:
    raw = dict(request.complement or {})
    if payload_address:
        raw.update({key: value for key, value in payload_address.items() if value})
    if not raw.get("delivery_street"):
        return None
    try:
        return parse_delivery_address(raw)
    except ConfirmationError:
        return None


def _cart_lines(request: DateRequest) -> list[dict]:
    lines = []
    for line in request.cart_context or []:
        if not isinstance(line, dict) or not line.get("variant_id"):
            continue
        quantity = line.get("quantity")
        if quantity is None:
            continue
        try:
            parsed = int(quantity)
        except (TypeError, ValueError):
            continue
        if parsed < 1:
            continue
        lines.append({"variant_id": str(line["variant_id"]), "quantity": parsed})
    return lines


def _informed_quantity(request: DateRequest) -> int | None:
    quantity = request.intended_quantity
    if quantity is None or quantity < 1:
        return None
    return int(quantity)


def commercial_resolution_gap(quantity: int) -> str:
    return (
        f"A quantidade {quantity} está informada. "
        "O pão está na mensagem. Confirme o produto do catálogo para ver o preço vigente e aceitar."
    )


def _payload_lines(payload) -> list[dict]:
    raw_lines = getattr(payload, "lines", None) or []
    parsed: list[dict] = []
    for line in raw_lines:
        if hasattr(line, "model_dump"):
            parsed.append(line.model_dump())
        elif isinstance(line, dict):
            parsed.append(line)
    return parsed


def resolve_acceptance_lines(
    request: DateRequest, candidate: list[dict] | None
) -> tuple[list[dict], list[str]]:
    """Itens já estruturados prevalecem. Texto livre não vira SKU."""
    structured = _cart_lines(request)
    if structured:
        return structured, []
    informed = _informed_quantity(request)
    raw_lines = list(candidate or [])
    if not raw_lines:
        if informed is not None:
            return [], [commercial_resolution_gap(informed)]
        return [], [GENERIC_COMMERCIAL_GAP]
    cleaned: list[dict] = []
    for raw in raw_lines:
        variant_id = raw.get("variant_id")
        if not variant_id:
            return [], ["escolha o produto do catálogo; texto livre não vira pão"]
        quantity = raw.get("quantity")
        if quantity is None:
            return [], ["informe a quantidade de cada pão escolhido"]
        try:
            parsed = int(quantity)
        except (TypeError, ValueError):
            return [], ["informe a quantidade de cada pão escolhido"]
        if parsed < 1:
            return [], ["cada pão precisa de quantidade 1 ou mais"]
        cleaned.append({"variant_id": str(variant_id), "quantity": parsed})
    if informed is not None and len(cleaned) > 1:
        distributed = sum(row["quantity"] for row in cleaned)
        if distributed != informed:
            return [], [
                f"A quantidade informada é {informed}. "
                "Distribua esse total entre os pães escolhidos; "
                "cada um precisa de quantidade explícita."
            ]
    return cleaned, []


def sellable_catalog(session: Session) -> list[dict]:
    rows = session.execute(
        select(Product, ProductVariant)
        .join(ProductVariant, ProductVariant.product_id == Product.id)
        .where(
            Product.editorial_status == EditorialStatus.PUBLISHED.value,
            Product.is_available.is_(True),
            ProductVariant.is_active.is_(True),
            ProductVariant.price_cents.is_not(None),
        )
        .order_by(
            Product.sort_order,
            Product.name,
            ProductVariant.sort_order,
            ProductVariant.display_name,
        )
    ).all()
    choices = []
    for product, variant in rows:
        if variant.price_cents is None or variant.price_cents <= 0:
            continue
        choices.append(
            {
                "product_id": str(product.id),
                "variant_id": str(variant.id),
                "product_name": product.name,
                "variant_name": variant.display_name,
                "unit_cents": variant.price_cents,
            }
        )
    return choices


def suggest_catalog_match(message: str | None, choices: list[dict]) -> dict | None:
    folded = fold_text(message or "")
    if len(folded) < 8:
        return None
    by_product: dict[str, list[dict]] = {}
    for choice in choices:
        name = fold_text(choice["product_name"])
        if len(name) >= 8 and name in folded:
            by_product.setdefault(choice["product_id"], []).append(choice)
    if len(by_product) != 1:
        return None
    variants = next(iter(by_product.values()))
    product_name = variants[0]["product_name"]
    if len(variants) != 1:
        return {
            "product_name": product_name,
            "variant_name": None,
            "variant_id": None,
            "unit_cents": None,
            "reason": (
                "o nome aparece na mensagem, mas há mais de uma opção; "
                "escolha a opção e a quantidade"
            ),
        }
    only = variants[0]
    return {
        "product_name": only["product_name"],
        "variant_name": only["variant_name"],
        "variant_id": only["variant_id"],
        "unit_cents": only["unit_cents"],
        "reason": "correspondência única com o nome na mensagem; confirme antes de aceitar",
    }


def _complementary_pending(request: DateRequest, address: dict | None) -> list[str]:
    pending: list[str] = []
    if address is None:
        pending.append("endereço de entrega")
    phone = ""
    if isinstance(request.complement, dict):
        phone = str(request.complement.get("customer_phone") or "").strip()
    if not phone:
        pending.append("telefone")
    return pending


def accept_preview(
    session: Session,
    settings: Settings,
    request: DateRequest,
    candidate_lines: list[dict] | None = None,
) -> dict:
    today = bakery_today(settings)
    target = request.proposed_date or request.desired_date
    structured = _cart_lines(request)
    lines, commercial_gaps = resolve_acceptance_lines(request, candidate_lines)
    items = []
    gaps: list[str] = list(commercial_gaps)
    total = 0
    for raw in lines:
        try:
            quoted, _proposed = _quote_product(session, raw, raw["quantity"])
        except (ConfirmationError, NotFoundError, ConflictError) as exc:
            gaps.append(str(exc))
            continue
        items.append(
            {
                "product_name": quoted["product_name"],
                "variant_name": quoted["variant_name"],
                "quantity": quoted["quantity"],
                "unit_cents": quoted["unit_cents"],
                "line_cents": quoted["line_cents"],
                "variant_id": quoted["variant_id"],
            }
        )
        total += quoted["line_cents"]
    if lines and not items and not commercial_gaps:
        gaps.append(GENERIC_COMMERCIAL_GAP)
    address = _address_from(request, None)
    if target < today:
        gaps.append("a data pedida já passou; informe outra data para reservar")
    from app.domain.schedule_closures import accept_block_message, matching_date_block

    if matching_date_block(session, target) is not None:
        gaps.append(accept_block_message(target))
    needs_catalog_choice = not structured and request.status not in {STATUS_CONVERTED, "closed"}
    informed = _informed_quantity(request)
    choices = sellable_catalog(session) if needs_catalog_choice else []
    return {
        "can_accept": not gaps,
        "gaps": gaps,
        "desired_date": request.desired_date.isoformat(),
        "accepted_date": target.isoformat(),
        "items": items,
        "total_cents": total if items else None,
        "currency": "BRL",
        "has_address": address is not None,
        "delivery_pending": address is None,
        "converted_order_id": (
            str(request.converted_order_id) if request.converted_order_id else None
        ),
        "awaiting_details": request.status == STATUS_AWAITING,
        "needs_catalog_choice": needs_catalog_choice,
        "informed_quantity": informed,
        "ask_customer": (
            not structured
            and informed is None
            and request.status not in {STATUS_CONVERTED, "closed"}
        ),
        "suggestion": (
            suggest_catalog_match(request.message, choices) if needs_catalog_choice else None
        ),
        "catalog_choices": choices,
        "complementary_pending": _complementary_pending(request, address),
    }


def _existing_order(session: Session, request: DateRequest) -> Order | None:
    if request.converted_order_id is not None:
        found = session.get(Order, request.converted_order_id)
        if found is not None:
            return found
    by_key = session.scalar(
        select(Order).where(Order.submit_idempotency_key == f"date-request:{request.id}")
    )
    if by_key is not None:
        return by_key
    return session.scalar(select(Order).where(Order.source_date_request_id == request.id))


def _lock_request(session: Session, request: DateRequest) -> DateRequest:
    locked = session.execute(
        select(DateRequest).where(DateRequest.id == request.id).with_for_update()
    ).scalar_one()
    return locked


def _create_order_from_request(
    session: Session,
    settings: Settings,
    request: DateRequest,
    *,
    target,
    address: dict | None,
    items: list[dict],
    total: int,
) -> tuple[Order, str]:
    existing = _existing_order(session, request)
    if existing is not None:
        return existing, ""
    token = secrets.token_urlsafe(32)
    from app.domain.storefront_orders import hash_access_token

    addr = address or {}
    order = Order(
        public_reference=new_public_reference(),
        status=OrderStatus.SUBMITTED.value,
        fulfillment_modality="delivery",
        production_local_date=target,
        customer_name=request.customer_name,
        customer_email=request.customer_email,
        delivery_street=addr.get("delivery_street"),
        delivery_number=addr.get("delivery_number"),
        delivery_complement=addr.get("delivery_complement"),
        delivery_district=addr.get("delivery_district"),
        delivery_city=addr.get("delivery_city"),
        delivery_state=addr.get("delivery_state"),
        delivery_postal_code=addr.get("delivery_postal_code"),
        customer_note=(request.message or "")[:2000],
        currency="BRL",
        subtotal_cents=total,
        delivery_fee_cents=0,
        discount_cents=0,
        total_cents=total,
        holds_capacity=False,
        access_token_hash=hash_access_token(token),
        submit_idempotency_key=f"date-request:{request.id}",
        order_kind="standard",
        source_date_request_id=request.id,
    )
    session.add(order)
    session.flush()
    for quoted in items:
        variant = session.get(ProductVariant, UUID(quoted["variant_id"]))
        product = session.get(Product, UUID(quoted["product_id"]))
        assert variant is not None and product is not None
        session.add(
            OrderItem(
                order_id=order.id,
                product_id=product.id,
                product_variant_id=variant.id,
                recipe_base_id=product.recipe_base_id,
                physical_units=quoted["physical_units"],
                quantity=quoted["quantity"],
                dough_name_snapshot=quoted["product_name"],
                shape_name_snapshot=quoted["variant_name"],
                unit_price_cents=quoted["unit_cents"],
                line_total_cents=quoted["line_cents"],
                net_weight_grams=quoted.get("weight_grams"),
            )
        )
    if total > 0:
        session.add(
            PaymentRecord(
                order_id=order.id,
                provider=PaymentProvider.ACTIONHUB.value,
                expected_cents=total,
                currency="BRL",
                financial_status=FinancialStatus.PENDING.value,
            )
        )
    session.flush()
    return order, token


def accept_date_request(
    session: Session,
    settings: Settings,
    request: DateRequest,
    payload,
    *,
    actor_ref: str,
) -> DateRequest:
    request = _lock_request(session, request)
    existing = _existing_order(session, request)
    if existing is not None and request.status == STATUS_CONVERTED and request.converted_order_id:
        if existing.status == OrderStatus.SUBMITTED.value:
            confirm_order(session, existing.id, actor_ref=actor_ref)
            session.flush()
        return request
    if request.status == "closed":
        raise ConfirmationError("esta solicitação já foi encerrada")
    explicit = getattr(payload, "proposed_date", None)
    target = explicit or request.desired_date
    today = bakery_today(settings)
    if target < today:
        raise ConfirmationError("data passada exige outra data; reserva retroativa não é permitida")
    raw_address = getattr(payload, "address", None)
    if raw_address is not None and hasattr(raw_address, "model_dump"):
        raw_address = raw_address.model_dump()
    address = _address_from(request, raw_address)
    if address is None and isinstance(raw_address, dict) and raw_address.get("delivery_street"):
        request.complement = {**(request.complement or {}), **raw_address}
    confirmed_from_message = not _cart_lines(request)
    lines, problems = resolve_acceptance_lines(request, _payload_lines(payload))
    if problems:
        raise ConfirmationError(problems[0])
    quoted_items = []
    total = 0
    for raw in lines:
        quoted, _proposed = _quote_product(session, raw, raw["quantity"])
        quoted_items.append(quoted)
        total += quoted["line_cents"]
    if not quoted_items:
        raise ConfirmationError(GENERIC_COMMERCIAL_GAP)
    recovering = request.status == STATUS_AWAITING or request.accept_authorized_at is not None
    if existing is None:
        order, _token = _create_order_from_request(
            session,
            settings,
            request,
            target=target,
            address=address,
            items=quoted_items,
            total=total,
        )
    else:
        order = existing
        if address is not None and order_delivery_pending(order):
            apply_delivery_address(order, address)
    already_converted = (
        request.status == STATUS_CONVERTED and request.converted_order_id == order.id
    )
    request.converted_order_id = order.id
    request.status = STATUS_CONVERTED
    request.closed_at = request.closed_at or datetime.now(UTC)
    request.admin_note = (getattr(payload, "note", None) or "").strip() or request.admin_note
    has_converted = session.scalar(
        select(DateRequestEvent.id).where(
            DateRequestEvent.request_id == request.id, DateRequestEvent.action == "converted"
        )
    )
    if not already_converted and has_converted is None:
        from app.domain.date_requests import _append_event

        detail = f"pedido {order.public_reference} reservado em {target.isoformat()}"
        if recovering:
            detail += " — recuperação do aceite já autorizado"
        if confirmed_from_message:
            names = ", ".join(
                f"{item['quantity']}× {item['product_name']} ({item['variant_name']})"
                for item in quoted_items
            )
            detail += f" — produto confirmado na área de aceite: {names}"
        _append_event(session, request, "converted", actor_ref, detail)
    session.flush()
    confirm_order(session, order.id, actor_ref=actor_ref)
    session.flush()
    if not already_converted:
        from app.domain.owner_alerts import notify_acceptance

        notify_acceptance(session, settings, order, request)
    return request


def request_date_request_completion(
    session: Session,
    settings: Settings,
    request: DateRequest,
    *,
    note: str | None,
    actor_ref: str,
) -> DateRequest:
    if request.converted_order_id is not None or request.status == "closed":
        raise ConfirmationError("esta solicitação já foi encerrada")
    dest = (request.customer_email or "").strip()
    if not dest or "@" not in dest:
        raise ConfirmationError("esta solicitação não tem e-mail válido para pedir os dados")
    request.accept_authorized_at = request.accept_authorized_at or datetime.now(UTC)
    request.status = STATUS_AWAITING
    from app.domain.date_requests import _append_event

    _append_event(
        session,
        request,
        "awaiting_details",
        actor_ref,
        "acesso seguro enviado para completar os dados",
    )
    enqueue_date_request_email(session, settings, request, "date_request_complete", note=note)
    session.flush()
    return request


def complete_date_request(
    session: Session, settings: Settings, request: DateRequest, payload: dict
) -> DateRequest:
    address = parse_delivery_address(payload)
    request.complement = {**(request.complement or {}), **address}
    existing = _existing_order(session, request)
    if existing is not None:
        apply_delivery_address(existing, address)
        request.converted_order_id = existing.id
        session.flush()
        return request
    session.flush()
    if request.accept_authorized_at is None:
        return request

    class _Payload:
        proposed_date = None
        address = address
        note = None

    return accept_date_request(
        session, settings, request, _Payload(), actor_ref="customer:complete"
    )


def converted_order_href(request: DateRequest) -> str | None:
    if request.converted_order_id is None:
        return None
    return f"/admin/pedidos/{request.converted_order_id}"


def recover_order_address_from_linked_request(session: Session, order: Order) -> dict:
    if delivery_has_any_field(order):
        return {"applied": False, "reason": "order_has_address"}
    if order.source_date_request_id is None:
        return {"applied": False, "reason": "no_source"}
    request = session.get(DateRequest, order.source_date_request_id)
    if request is None or not request.complement:
        return {"applied": False, "reason": "no_complement"}
    try:
        address = parse_delivery_address(request.complement)
    except ConfirmationError as exc:
        return {"applied": False, "reason": str(exc)}
    apply_delivery_address(order, address)
    add_internal_note(
        session,
        order.id,
        "Endereço recuperado da solicitação vinculada. Nenhuma cobrança ou e-mail foi disparado.",
        actor_ref="system:prompt72",
    )
    session.flush()
    return {"applied": True, "reason": "from_linked_date_request"}
