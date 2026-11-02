"""Anula um pedido duplicado sem mudar o status persistido nem avisar o cliente."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.duplicates import customer_match_reason
from app.domain.errors import ConflictError, NotFoundError
from app.domain.managerial_exclusion import _active, exclude_subject
from app.models.house_fidelity import HouseFidelityEvent
from app.models.orders import Order, OrderItem, OrderStatusHistory
from app.models.payments import PaymentRecord

PROVIDER_MESSAGE = "Este pedido tem pagamento no provedor; resolva o estorno antes de anular"
STAMP_MESSAGE = (
    "Este pedido tem carimbo de fidelidade. A reversão atual só ocorre no cancelamento ou no estorno, "
    "e anular não muda o status."
)


def void_duplicate(
    session: Session,
    order_id: UUID,
    *,
    original_order_id: UUID,
    reason: str,
    actor_ref: str,
) -> Order:
    text = " ".join((reason or "").split())
    if not text or len(text) > 280:
        raise ConflictError("informe o motivo, com até 280 caracteres")
    if order_id == original_order_id:
        raise ConflictError("um pedido não pode ser anulado como duplicado de si mesmo")
    order = session.get(Order, order_id, with_for_update=True)
    original = session.get(Order, original_order_id, with_for_update=True)
    if order is None or original is None:
        raise NotFoundError("pedido não encontrado")
    current = _active(session, "order", order.id)
    if current is not None and getattr(current, "kind", "test") == "duplicate":
        raise ConflictError("este pedido já foi anulado por duplicidade")
    if current is not None:
        raise ConflictError("este pedido já está fora da operação")
    original_exclusion = _active(session, "order", original.id)
    if original_exclusion is not None and getattr(original_exclusion, "kind", "test") == "duplicate":
        raise ConflictError("o pedido original também está anulado")
    left_items = list(session.scalars(select(OrderItem).where(OrderItem.order_id == order.id)))
    right_items = list(session.scalars(select(OrderItem).where(OrderItem.order_id == original.id)))
    if customer_match_reason(order, original, left_items, right_items, require_items=False) is None:
        raise ConflictError("os pedidos não são do mesmo cliente")
    records = list(session.scalars(select(PaymentRecord).where(PaymentRecord.order_id == order.id)))
    if any(row.financial_status == "paid" or (row.external_reference or "").strip() for row in records):
        raise ConflictError(PROVIDER_MESSAGE)
    if _has_applied_stamp(session, order):
        raise ConflictError(STAMP_MESSAGE)
    for row in records:
        if row.financial_status == "pending" and not (row.external_reference or "").strip():
            row.financial_status = "cancelled"
    order.holds_capacity = False
    exclude_subject(
        session,
        "order",
        order.id,
        author_ref=actor_ref,
        reason=text,
        kind="duplicate",
        original_order_id=original.id,
    )
    session.add(
        OrderStatusHistory(
            order_id=order.id,
            from_status=order.status,
            to_status=order.status,
            reason=f"anulado como duplicado de {original.public_reference}. Motivo: {text}"[:280],
            actor_ref=actor_ref,
        )
    )
    session.add(
        OrderStatusHistory(
            order_id=original.id,
            from_status=original.status,
            to_status=original.status,
            reason=f"{order.public_reference} anulado como duplicado deste pedido. Motivo: {text}"[:280],
            actor_ref=actor_ref,
        )
    )
    session.flush()
    return order


def _has_applied_stamp(session: Session, order: Order) -> bool:
    if order.fidelity_account_id is None:
        return False
    found = session.scalar(
        select(HouseFidelityEvent.id).where(
            HouseFidelityEvent.order_id == order.id,
            HouseFidelityEvent.kind == "qualify",
            HouseFidelityEvent.status == "applied",
        )
    )
    return found is not None
