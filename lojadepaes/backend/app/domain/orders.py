from __future__ import annotations

import secrets
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session

from app.domain.capacity import (
    dough_limit_for,
    lock_batch_and_slot,
    occupied_batch_dough_units,
    occupied_batch_units,
    occupied_slot_units,
    utc_now,
)
from app.domain.catalog_rules import assert_item_sellable
from app.domain.errors import CapacityError, ConfirmationError, NotFoundError, TransitionError
from app.models.enums import ALLOWED_TRANSITIONS, OrderStatus
from app.models.orders import (
    Order,
    OrderInternalNote,
    OrderItem,
    OrderItemIngredient,
    OrderStatusHistory,
)
from app.models.production import FulfillmentSlot, ProductionBatch


def new_public_reference() -> str:
    return "LP" + secrets.token_hex(5).upper()


def _lock_order(session: Session, order_id: UUID) -> Order:
    try:
        return session.execute(
            select(Order).where(Order.id == order_id).with_for_update()
        ).scalar_one()
    except NoResultFound as exc:
        raise NotFoundError("pedido não encontrado") from exc


def _require_transition(current: str, target: str) -> None:
    allowed = ALLOWED_TRANSITIONS.get(current, frozenset())
    if target not in allowed:
        raise TransitionError(f"transição {current} → {target} não permitida")


def _append_history(
    session: Session,
    order: Order,
    to_status: str,
    reason: str | None,
    actor_ref: str | None = None,
) -> None:
    session.add(
        OrderStatusHistory(
            order_id=order.id,
            from_status=order.status,
            to_status=to_status,
            reason=reason,
            actor_ref=actor_ref,
        )
    )


def _delivery_complete(order: Order) -> bool:
    return all(
        [
            order.delivery_street,
            order.delivery_number,
            order.delivery_district,
            order.delivery_city,
            order.delivery_state,
            order.delivery_postal_code,
        ]
    )


def confirm_order(session: Session, order_id: UUID, *, actor_ref: str | None = None) -> Order:
    """Confirma reserva de capacidade. Idempotente se o pedido já está confirmado ou além."""
    order = _lock_order(session, order_id)
    if order.status in {
        OrderStatus.CONFIRMED.value,
        OrderStatus.IN_PRODUCTION.value,
        OrderStatus.READY.value,
        OrderStatus.COMPLETED.value,
    }:
        return order
    if order.status == OrderStatus.CANCELLED.value:
        raise TransitionError("pedido cancelado não pode ser confirmado")
    _require_transition(order.status, OrderStatus.CONFIRMED.value)

    if order.fulfillment_slot_id is None:
        raise ConfirmationError("janela de recebimento ausente")
    slot = session.get(FulfillmentSlot, order.fulfillment_slot_id)
    if slot is None:
        raise ConfirmationError("janela de recebimento inválida")
    batch = lock_batch_and_slot(session, slot)

    _validate_slot_and_batch(order, slot, batch)
    items = session.scalars(select(OrderItem).where(OrderItem.order_id == order.id)).all()
    if not items:
        raise ConfirmationError("pedido sem itens")

    subtotal = 0
    needed = 0
    dough_needed: dict[UUID, int] = {}
    for item in items:
        dough, shape, extras = assert_item_sellable(session, item)
        if dough.base_price_cents is None:
            raise ConfirmationError("preço da massa não configurado")
        extra_cents = 0
        for ingredient, link in _paired_extras(session, item, extras):
            if ingredient.surcharge_cents is None:
                raise ConfirmationError("acréscimo da inclusão não configurado")
            extra_cents += ingredient.surcharge_cents
            link.name_snapshot = ingredient.name
            link.surcharge_cents = ingredient.surcharge_cents
        unit = dough.base_price_cents + extra_cents
        item.dough_name_snapshot = dough.name
        item.shape_name_snapshot = shape.name
        item.unit_price_cents = unit
        item.line_total_cents = unit * item.quantity
        subtotal += item.line_total_cents
        needed += item.quantity
        dough_needed[dough.id] = dough_needed.get(dough.id, 0) + item.quantity

    if not order.customer_name or not (order.customer_email or order.customer_phone):
        raise ConfirmationError("nome e ao menos um contato são obrigatórios na confirmação")
    if order.fulfillment_modality == "delivery" and not _delivery_complete(order):
        raise ConfirmationError("endereço de entrega incompleto")

    held_batch = occupied_batch_units(session, batch.id, exclude_order_id=order.id)
    held_slot = occupied_slot_units(session, slot.id, exclude_order_id=order.id)
    if held_batch + needed > batch.capacity_units:
        raise CapacityError("capacidade da fornada esgotada")
    if held_slot + needed > slot.capacity_units:
        raise CapacityError("capacidade da janela esgotada")
    for dough_id, qty in dough_needed.items():
        limit = dough_limit_for(session, batch.id, dough_id)
        if limit is None:
            continue
        held_dough = occupied_batch_dough_units(
            session, batch.id, dough_id, exclude_order_id=order.id
        )
        if held_dough + qty > limit:
            raise CapacityError("capacidade da massa nesta fornada esgotada")

    delivery_fee = order.delivery_fee_cents or 0
    discount = order.discount_cents or 0
    order.production_batch_id = batch.id
    order.subtotal_cents = subtotal
    order.delivery_fee_cents = delivery_fee
    order.discount_cents = discount
    order.total_cents = subtotal + delivery_fee - discount
    if order.total_cents < 0:
        raise ConfirmationError("total inválido")
    now = utc_now()
    _append_history(session, order, OrderStatus.CONFIRMED.value, None, actor_ref)
    order.status = OrderStatus.CONFIRMED.value
    order.confirmed_at = now
    order.holds_capacity = True
    session.flush()
    return order


def _paired_extras(session: Session, item: OrderItem, extras):
    links = session.scalars(
        select(OrderItemIngredient).where(OrderItemIngredient.order_item_id == item.id)
    ).all()
    by_id = {ingredient.id: ingredient for ingredient in extras}
    return [(by_id[link.ingredient_id], link) for link in links]


def _validate_slot_and_batch(order: Order, slot: FulfillmentSlot, batch: ProductionBatch) -> None:
    if not slot.is_active:
        raise ConfirmationError("janela inativa")
    if batch.status != "open":
        raise ConfirmationError("fornada não está aberta para pedidos")
    if order.fulfillment_modality is None:
        raise ConfirmationError("modalidade ausente")
    if order.fulfillment_modality != slot.modality:
        raise ConfirmationError("modalidade incompatível com a janela")
    if slot.starts_at < batch.breads_available_at:
        raise ConfirmationError("janela anterior à disponibilidade da fornada")
    now = utc_now()
    if now > batch.order_deadline_at:
        raise ConfirmationError("prazo de pedidos encerrado")


def cancel_order(
    session: Session,
    order_id: UUID,
    reason: str | None = None,
    *,
    actor_ref: str | None = None,
) -> Order:
    order = _lock_order(session, order_id)
    if order.status == OrderStatus.CANCELLED.value:
        return order
    if order.status == OrderStatus.COMPLETED.value:
        raise TransitionError("pedido concluído não pode ser cancelado")
    _require_transition(order.status, OrderStatus.CANCELLED.value)
    if not reason or not reason.strip():
        raise ConfirmationError("cancelamento exige motivo")
    reason = reason.strip()
    if order.fulfillment_slot_id is not None:
        slot = session.get(FulfillmentSlot, order.fulfillment_slot_id)
        if slot is not None:
            lock_batch_and_slot(session, slot)
    _append_history(session, order, OrderStatus.CANCELLED.value, reason, actor_ref)
    order.status = OrderStatus.CANCELLED.value
    order.cancelled_at = utc_now()
    order.cancellation_reason = reason
    if order.production_started_at is None:
        order.holds_capacity = False
    session.flush()
    return order


def transition_order(
    session: Session,
    order_id: UUID,
    target: str,
    reason: str | None = None,
    *,
    actor_ref: str | None = None,
) -> Order:
    if target == OrderStatus.CONFIRMED.value:
        return confirm_order(session, order_id, actor_ref=actor_ref)
    if target == OrderStatus.CANCELLED.value:
        return cancel_order(session, order_id, reason, actor_ref=actor_ref)
    order = _lock_order(session, order_id)
    if order.status == target:
        return order
    _require_transition(order.status, target)
    now = utc_now()
    _append_history(session, order, target, reason, actor_ref)
    order.status = target
    if target == OrderStatus.IN_PRODUCTION.value:
        order.production_started_at = now
    elif target == OrderStatus.READY.value:
        order.ready_at = now
    elif target == OrderStatus.COMPLETED.value:
        order.completed_at = now
    session.flush()
    return order


def assert_items_immutable_after_confirm(order: Order) -> None:
    if order.status != OrderStatus.DRAFT.value:
        raise ConfirmationError("itens não podem ser alterados após a confirmação")


def add_internal_note(
    session: Session, order_id: UUID, body: str, *, actor_ref: str
) -> OrderInternalNote:
    order = session.get(Order, order_id)
    if order is None:
        raise NotFoundError("pedido não encontrado")
    text = body.strip()
    if not text:
        raise ConfirmationError("nota interna vazia")
    if len(text) > 2000:
        raise ConfirmationError("nota interna excede 2000 caracteres")
    note = OrderInternalNote(order_id=order.id, body=text, author_ref=actor_ref)
    session.add(note)
    session.flush()
    return note
