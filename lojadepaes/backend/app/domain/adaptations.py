from __future__ import annotations

import re
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.domain.capacity import utc_now
from app.domain.email_outbox import enqueue_order_email
from app.domain.errors import ConfirmationError, NotFoundError
from app.models.enums import (
    AdaptationClientDecision,
    AdaptationReason,
    AdaptationStatus,
    OrderStatus,
)
from app.models.orders import Order, OrderItem, OrderItemAdaptation, OrderItemAdaptationEvent

CUSTOMER_TEXT_MAX = 500
BAKERY_RESPONSE_MAX = 2000
_TAG_RE = re.compile(r"<[^>]*>")
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
RESOLVED_STATUSES = frozenset(
    {AdaptationStatus.ACCEPTED.value, AdaptationStatus.ALTERNATIVE_ACCEPTED.value}
)


def sanitize_plain_text(value: str | None, *, max_len: int, required: bool) -> str:
    cleaned = _TAG_RE.sub(" ", value or "")
    cleaned = _CONTROL_RE.sub("", cleaned)
    cleaned = " ".join(cleaned.split())
    if required and not cleaned:
        raise ConfirmationError("descreva a adaptação solicitada")
    if len(cleaned) > max_len:
        raise ConfirmationError(f"texto excede {max_len} caracteres")
    return cleaned


def parse_reason(value: object) -> str | None:
    if value is None or value == "":
        return None
    raw = str(value).strip()
    allowed = {item.value for item in AdaptationReason}
    if raw not in allowed:
        raise ConfirmationError("motivo de adaptação inválido")
    return raw


def parse_customer_adaptation(raw: dict | None) -> dict | None:
    if not raw:
        return None
    text = sanitize_plain_text(str(raw.get("text") or raw.get("adaptation_text") or ""), max_len=CUSTOMER_TEXT_MAX, required=False)
    if not text:
        return None
    return {"text": text, "reason": parse_reason(raw.get("reason") or raw.get("adaptation_reason"))}


def _append_event(
    session: Session,
    row: OrderItemAdaptation,
    to_status: str,
    *,
    actor_kind: str,
    actor_ref: str | None,
    note: str | None,
) -> None:
    session.add(
        OrderItemAdaptationEvent(
            adaptation_id=row.id,
            from_status=row.status,
            to_status=to_status,
            actor_kind=actor_kind,
            actor_ref=actor_ref,
            note=note,
        )
    )


def create_adaptation(
    session: Session, item: OrderItem, text: str, reason: str | None
) -> OrderItemAdaptation:
    row = OrderItemAdaptation(
        order_item_id=item.id,
        customer_text=text,
        reason=reason,
        status=AdaptationStatus.PENDING.value,
        bakery_response="",
    )
    session.add(row)
    session.flush()
    _append_event(session, row, AdaptationStatus.PENDING.value, actor_kind="customer", actor_ref=None, note=None)
    session.flush()
    return row


def adaptations_for_order(session: Session, order_id: UUID) -> dict[UUID, OrderItemAdaptation]:
    items = list(session.scalars(select(OrderItem).where(OrderItem.order_id == order_id)))
    if not items:
        return {}
    item_ids = [item.id for item in items]
    rows = list(
        session.scalars(select(OrderItemAdaptation).where(OrderItemAdaptation.order_item_id.in_(item_ids)))
    )
    return {row.order_item_id: row for row in rows}


def order_has_unresolved_adaptations(session: Session, order_id: UUID) -> bool:
    return bool(unresolved_adaptations(session, order_id))


def unresolved_adaptations(session: Session, order_id: UUID) -> list[OrderItemAdaptation]:
    mapping = adaptations_for_order(session, order_id)
    return [row for row in mapping.values() if not adaptation_is_resolved(row)]


def adaptation_is_resolved(row: OrderItemAdaptation) -> bool:
    if row.status == AdaptationStatus.ACCEPTED.value:
        return True
    if row.status == AdaptationStatus.ALTERNATIVE_ACCEPTED.value:
        return True
    return False


def order_has_pending_adaptation(session: Session, order_id: UUID) -> bool:
    return any(
        row.status == AdaptationStatus.PENDING.value for row in adaptations_for_order(session, order_id).values()
    )


def assert_adaptations_resolved(session: Session, order_id: UUID) -> None:
    unresolved = unresolved_adaptations(session, order_id)
    if not unresolved:
        return
    statuses = {row.status for row in unresolved}
    if AdaptationStatus.PENDING.value in statuses:
        raise ConfirmationError("há adaptação pendente de avaliação; resolva antes de aceitar o pedido")
    if AdaptationStatus.ALTERNATIVE_PROPOSED.value in statuses:
        raise ConfirmationError(
            "há alternativa de adaptação sem concordância explícita do cliente; silêncio não confirma"
        )
    if AdaptationStatus.DECLINED.value in statuses:
        raise ConfirmationError(
            "há adaptação que não pode ser atendida; o item não pode ser aceito como pão sem alteração"
        )
    raise ConfirmationError("há adaptação sem resolução; o pedido não pode ser aceito")


def public_adaptation_view(row: OrderItemAdaptation | None) -> dict | None:
    if row is None:
        return None
    return {
        "status": row.status,
        "customer_text": row.customer_text,
        "reason": row.reason,
        "bakery_response": row.bakery_response or "",
        "client_decision": row.client_decision,
        "applies_to_all_units_of_this_line": True,
    }


def admin_adaptation_view(session: Session, row: OrderItemAdaptation | None) -> dict | None:
    if row is None:
        return None
    events = list(
        session.scalars(
            select(OrderItemAdaptationEvent)
            .where(OrderItemAdaptationEvent.adaptation_id == row.id)
            .order_by(OrderItemAdaptationEvent.created_at.asc(), OrderItemAdaptationEvent.id.asc())
        )
    )
    payload = public_adaptation_view(row) or {}
    payload["id"] = str(row.id)
    payload["resolved"] = adaptation_is_resolved(row)
    payload["history"] = [
        {
            "id": str(event.id),
            "from_status": event.from_status,
            "to_status": event.to_status,
            "actor_kind": event.actor_kind,
            "created_at": event.created_at,
            "has_note": bool(event.note),
        }
        for event in events
    ]
    return payload


def evaluate_adaptation(
    session: Session,
    order_id: UUID,
    item_id: UUID,
    *,
    decision: str,
    response: str,
    actor_ref: str,
) -> OrderItemAdaptation:
    order = session.get(Order, order_id)
    if order is None:
        raise NotFoundError("pedido não encontrado")
    if order.status not in {OrderStatus.SUBMITTED.value, OrderStatus.DRAFT.value}:
        raise ConfirmationError("adaptação só pode ser avaliada antes do aceite do pedido")
    item = session.get(OrderItem, item_id)
    if item is None or item.order_id != order.id:
        raise NotFoundError("item não encontrado")
    row = session.scalar(select(OrderItemAdaptation).where(OrderItemAdaptation.order_item_id == item.id))
    if row is None:
        raise ConfirmationError("este item não tem solicitação de adaptação")
    if row.status == AdaptationStatus.ALTERNATIVE_ACCEPTED.value:
        raise ConfirmationError("esta adaptação já foi acordada com o cliente")
    note = sanitize_plain_text(response, max_len=BAKERY_RESPONSE_MAX, required=decision != "accept")
    if decision == "accept":
        target = AdaptationStatus.ACCEPTED.value
        row.client_decision = None
        row.client_decided_at = None
    elif decision == "propose_alternative":
        if not note:
            raise ConfirmationError("escreva a alternativa proposta")
        target = AdaptationStatus.ALTERNATIVE_PROPOSED.value
        row.client_decision = None
        row.client_decided_at = None
    elif decision == "decline":
        if not note:
            raise ConfirmationError("explique por que a adaptação não pode ser atendida")
        target = AdaptationStatus.DECLINED.value
        row.client_decision = None
        row.client_decided_at = None
    else:
        raise ConfirmationError("decisão de adaptação inválida")
    _append_event(session, row, target, actor_kind="bakery", actor_ref=actor_ref, note=note or None)
    row.status = target
    row.bakery_response = note
    session.flush()
    if target == AdaptationStatus.ALTERNATIVE_PROPOSED.value:
        enqueue_order_email(session, get_settings(), order, "adaptation_proposed")
    return row


def client_respond_adaptation(
    session: Session, order: Order, item_id: UUID, decision: str
) -> OrderItemAdaptation:
    item = session.get(OrderItem, item_id)
    if item is None or item.order_id != order.id:
        raise NotFoundError("item não encontrado")
    row = session.scalar(select(OrderItemAdaptation).where(OrderItemAdaptation.order_item_id == item.id))
    if row is None:
        raise ConfirmationError("este item não tem solicitação de adaptação")
    if row.status != AdaptationStatus.ALTERNATIVE_PROPOSED.value:
        raise ConfirmationError("não há alternativa pendente de concordância neste item")
    if decision == "accept_alternative":
        target = AdaptationStatus.ALTERNATIVE_ACCEPTED.value
        row.client_decision = AdaptationClientDecision.ACCEPTED_ALTERNATIVE.value
    elif decision == "decline":
        target = AdaptationStatus.ALTERNATIVE_PROPOSED.value
        row.client_decision = AdaptationClientDecision.DECLINED.value
    else:
        raise ConfirmationError("resposta de adaptação inválida")
    now = utc_now()
    _append_event(session, row, target, actor_kind="customer", actor_ref=None, note=decision)
    row.status = target
    row.client_decided_at = now
    session.flush()
    return row
