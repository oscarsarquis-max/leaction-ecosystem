from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models.orders import Order, OrderItem
from app.models.production import FulfillmentSlot, ProductionBatch, ProductionBatchDoughLimit


def _holding_filter():
    return Order.holds_capacity.is_(True)


def occupied_batch_units(
    session: Session,
    batch_id: UUID,
    *,
    exclude_order_id: UUID | None = None,
) -> int:
    stmt: Select[tuple[int]] = (
        select(func.coalesce(func.sum(OrderItem.quantity), 0))
        .select_from(OrderItem)
        .join(Order, Order.id == OrderItem.order_id)
        .where(Order.production_batch_id == batch_id, _holding_filter())
    )
    if exclude_order_id is not None:
        stmt = stmt.where(Order.id != exclude_order_id)
    return int(session.execute(stmt).scalar_one())


def occupied_slot_units(
    session: Session,
    slot_id: UUID,
    *,
    exclude_order_id: UUID | None = None,
) -> int:
    stmt: Select[tuple[int]] = (
        select(func.coalesce(func.sum(OrderItem.quantity), 0))
        .select_from(OrderItem)
        .join(Order, Order.id == OrderItem.order_id)
        .where(Order.fulfillment_slot_id == slot_id, _holding_filter())
    )
    if exclude_order_id is not None:
        stmt = stmt.where(Order.id != exclude_order_id)
    return int(session.execute(stmt).scalar_one())


def occupied_batch_dough_units(
    session: Session,
    batch_id: UUID,
    dough_type_id: UUID,
    *,
    exclude_order_id: UUID | None = None,
) -> int:
    stmt: Select[tuple[int]] = (
        select(func.coalesce(func.sum(OrderItem.quantity), 0))
        .select_from(OrderItem)
        .join(Order, Order.id == OrderItem.order_id)
        .where(
            Order.production_batch_id == batch_id,
            OrderItem.dough_type_id == dough_type_id,
            _holding_filter(),
        )
    )
    if exclude_order_id is not None:
        stmt = stmt.where(Order.id != exclude_order_id)
    return int(session.execute(stmt).scalar_one())


def order_unit_count(session: Session, order_id: UUID) -> int:
    total = session.execute(
        select(func.coalesce(func.sum(OrderItem.quantity), 0)).where(OrderItem.order_id == order_id)
    ).scalar_one()
    return int(total)


def lock_batch_and_slot(session: Session, slot: FulfillmentSlot) -> ProductionBatch:
    batch = session.execute(
        select(ProductionBatch)
        .where(ProductionBatch.id == slot.production_batch_id)
        .with_for_update()
    ).scalar_one()
    locked_slot = session.execute(
        select(FulfillmentSlot).where(FulfillmentSlot.id == slot.id).with_for_update()
    ).scalar_one()
    slot.starts_at = locked_slot.starts_at
    return batch


def utc_now() -> datetime:
    return datetime.now(UTC)


def dough_limit_for(session: Session, batch_id: UUID, dough_type_id: UUID) -> int | None:
    row = session.execute(
        select(ProductionBatchDoughLimit.capacity_units).where(
            ProductionBatchDoughLimit.production_batch_id == batch_id,
            ProductionBatchDoughLimit.dough_type_id == dough_type_id,
        )
    ).scalar_one_or_none()
    return int(row) if row is not None else None
