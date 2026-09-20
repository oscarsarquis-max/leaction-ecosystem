from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.domain.errors import NotFoundError
from app.domain.payments import financial_list_kind, order_is_financially_settled
from app.models.enums import ALLOWED_TRANSITIONS, OrderStatus
from app.models.orders import (
    Order,
    OrderInternalNote,
    OrderItem,
    OrderItemIngredient,
    OrderStatusHistory,
)
from app.models.payments import PaymentIntegrationEvent, PaymentRecord
from app.models.production import FulfillmentSlot, ProductionBatch
from app.schemas.admin import (
    AddressOut,
    ExtraOut,
    HistoryOut,
    ItemOut,
    MoneyOut,
    NoteOut,
    OrderDetailOut,
    OrderListItemOut,
    OrderListOut,
    OrderListQuery,
    PaymentEventOut,
    PaymentRecordOut,
)

ACTION_BY_TARGET = {
    OrderStatus.CONFIRMED.value: "confirm",
    OrderStatus.IN_PRODUCTION.value: "start_production",
    OrderStatus.READY.value: "mark_ready",
    OrderStatus.COMPLETED.value: "complete",
    OrderStatus.CANCELLED.value: "cancel",
}


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def bakery_day_range(day: date, timezone_name: str, *, end_exclusive: bool) -> datetime:
    tz = ZoneInfo(timezone_name)
    moment = datetime.combine(day, time.min, tzinfo=tz)
    if end_exclusive:
        moment = moment + timedelta(days=1)
    return moment.astimezone(UTC)


def _money(cents: int | None, currency: str = "BRL") -> MoneyOut:
    return MoneyOut(cents=cents, currency=currency)


def _name_or_provisional(snapshot: str | None, fallback: str) -> tuple[str, bool]:
    if snapshot:
        return snapshot, True
    return fallback or "Não informado", False


def allowed_actions(status: str) -> list[str]:
    return [ACTION_BY_TARGET[target] for target in sorted(ALLOWED_TRANSITIONS.get(status, frozenset()))]


def list_orders(session: Session, settings: Settings, query: OrderListQuery) -> OrderListOut:
    stmt = select(Order)
    if query.reference:
        stmt = stmt.where(
            Order.public_reference.ilike(f"%{_escape_like(query.reference.strip())}%", escape="\\")
        )
    if query.status:
        stmt = stmt.where(Order.status == query.status)
    if query.production_batch_id:
        stmt = stmt.where(Order.production_batch_id == query.production_batch_id)
    if query.fulfillment_slot_id:
        stmt = stmt.where(Order.fulfillment_slot_id == query.fulfillment_slot_id)
    if query.modality:
        stmt = stmt.where(Order.fulfillment_modality == query.modality)
    if query.created_from:
        stmt = stmt.where(
            Order.created_at >= bakery_day_range(query.created_from, settings.bakery_timezone, False)
        )
    if query.created_to:
        stmt = stmt.where(
            Order.created_at < bakery_day_range(query.created_to, settings.bakery_timezone, True)
        )

    total = int(session.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0)
    offset = (query.page - 1) * query.page_size
    orders = session.scalars(
        stmt.order_by(Order.created_at.desc(), Order.id.desc()).offset(offset).limit(query.page_size)
    ).all()
    ids = [order.id for order in orders]
    units = dict.fromkeys(ids, 0)
    if ids:
        for order_id, quantity in session.execute(
            select(OrderItem.order_id, func.coalesce(func.sum(OrderItem.quantity), 0))
            .where(OrderItem.order_id.in_(ids))
            .group_by(OrderItem.order_id)
        ):
            units[order_id] = int(quantity)
    records_by_order: dict[UUID, list[PaymentRecord]] = {order_id: [] for order_id in ids}
    if ids:
        for record in session.scalars(
            select(PaymentRecord).where(PaymentRecord.order_id.in_(ids))
        ):
            records_by_order.setdefault(record.order_id, []).append(record)
    batch_ids = {order.production_batch_id for order in orders if order.production_batch_id}
    slot_ids = {order.fulfillment_slot_id for order in orders if order.fulfillment_slot_id}
    batches = {
        row.id: row
        for row in session.scalars(select(ProductionBatch).where(ProductionBatch.id.in_(batch_ids))).all()
    } if batch_ids else {}
    slots = {
        row.id: row
        for row in session.scalars(select(FulfillmentSlot).where(FulfillmentSlot.id.in_(slot_ids))).all()
    } if slot_ids else {}

    items = []
    for order in orders:
        batch = batches.get(order.production_batch_id) if order.production_batch_id else None
        slot = slots.get(order.fulfillment_slot_id) if order.fulfillment_slot_id else None
        items.append(
            OrderListItemOut(
                id=order.id,
                public_reference=order.public_reference,
                created_at=order.created_at,
                status=order.status,
                customer_name=order.customer_name,
                bread_units=units.get(order.id, 0),
                fulfillment_modality=order.fulfillment_modality,
                production_batch_id=order.production_batch_id,
                production_batch_code=batch.code if batch else None,
                fulfillment_slot_id=order.fulfillment_slot_id,
                slot_starts_at=slot.starts_at if slot else None,
                slot_ends_at=slot.ends_at if slot else None,
                total=_money(order.total_cents, order.currency),
                financial_kind=financial_list_kind(order, records_by_order.get(order.id, [])),
            )
        )
    return OrderListOut(items=items, page=query.page, page_size=query.page_size, total=total)


def get_order_detail(session: Session, order_id: UUID) -> OrderDetailOut:
    order = session.get(Order, order_id)
    if order is None:
        raise NotFoundError("pedido não encontrado")
    items = session.scalars(select(OrderItem).where(OrderItem.order_id == order.id)).all()
    item_ids = [item.id for item in items]
    extras_by_item: dict[UUID, list[OrderItemIngredient]] = {item_id: [] for item_id in item_ids}
    if item_ids:
        for extra in session.scalars(
            select(OrderItemIngredient).where(OrderItemIngredient.order_item_id.in_(item_ids))
        ):
            extras_by_item.setdefault(extra.order_item_id, []).append(extra)
    from app.models.catalog import BreadShape, DoughType, Ingredient

    dough_ids = {item.dough_type_id for item in items}
    shape_ids = {item.bread_shape_id for item in items}
    ingredient_ids = {extra.ingredient_id for extras in extras_by_item.values() for extra in extras}
    doughs = {
        row.id: row for row in session.scalars(select(DoughType).where(DoughType.id.in_(dough_ids))).all()
    } if dough_ids else {}
    shapes = {
        row.id: row for row in session.scalars(select(BreadShape).where(BreadShape.id.in_(shape_ids))).all()
    } if shape_ids else {}
    ingredients = {
        row.id: row
        for row in session.scalars(select(Ingredient).where(Ingredient.id.in_(ingredient_ids))).all()
    } if ingredient_ids else {}

    locked = order.status != OrderStatus.DRAFT.value
    item_out = []
    for item in items:
        dough = doughs.get(item.dough_type_id)
        shape = shapes.get(item.bread_shape_id)
        dough_name, dough_snap = _name_or_provisional(
            item.dough_name_snapshot, dough.name if dough else ""
        )
        shape_name, shape_snap = _name_or_provisional(
            item.shape_name_snapshot, shape.name if shape else ""
        )
        extra_out = []
        extras_complete = True
        for extra in extras_by_item.get(item.id, []):
            ingredient = ingredients.get(extra.ingredient_id)
            extra_name, extra_snap = _name_or_provisional(
                extra.name_snapshot, ingredient.name if ingredient else ""
            )
            extra_complete = extra_snap and extra.surcharge_cents is not None
            extras_complete = extras_complete and extra_complete
            extra_out.append(
                ExtraOut(
                    ingredient_id=extra.ingredient_id,
                    name=extra_name,
                    surcharge=_money(extra.surcharge_cents, order.currency),
                    snapshot_complete=extra_complete,
                )
            )
        snapshot_complete = (
            dough_snap
            and shape_snap
            and item.unit_price_cents is not None
            and item.line_total_cents is not None
            and extras_complete
        )
        item_out.append(
            ItemOut(
                id=item.id,
                dough_type_id=item.dough_type_id,
                bread_shape_id=item.bread_shape_id,
                dough_name=dough_name,
                shape_name=shape_name,
                quantity=item.quantity,
                unit_price=_money(item.unit_price_cents, order.currency),
                line_total=_money(item.line_total_cents, order.currency),
                extras=extra_out,
                snapshot_complete=snapshot_complete,
                provisional=not locked or not snapshot_complete,
            )
        )

    history = session.scalars(
        select(OrderStatusHistory)
        .where(OrderStatusHistory.order_id == order.id)
        .order_by(OrderStatusHistory.created_at.asc(), OrderStatusHistory.id.asc())
    ).all()
    notes = session.scalars(
        select(OrderInternalNote)
        .where(OrderInternalNote.order_id == order.id)
        .order_by(OrderInternalNote.created_at.asc(), OrderInternalNote.id.asc())
    ).all()
    records = session.scalars(
        select(PaymentRecord)
        .where(PaymentRecord.order_id == order.id)
        .order_by(PaymentRecord.created_at.asc())
    ).all()
    record_ids = [record.id for record in records]
    events: list[PaymentIntegrationEvent] = []
    if record_ids:
        events = list(
            session.scalars(
                select(PaymentIntegrationEvent)
                .where(PaymentIntegrationEvent.payment_record_id.in_(record_ids))
                .order_by(PaymentIntegrationEvent.received_at.asc())
            )
        )

    batch = session.get(ProductionBatch, order.production_batch_id) if order.production_batch_id else None
    slot = session.get(FulfillmentSlot, order.fulfillment_slot_id) if order.fulfillment_slot_id else None

    return OrderDetailOut(
        id=order.id,
        public_reference=order.public_reference,
        created_at=order.created_at,
        updated_at=order.updated_at,
        status=order.status,
        allowed_actions=allowed_actions(order.status),
        customer_name=order.customer_name,
        customer_email=order.customer_email,
        customer_phone=order.customer_phone,
        address=AddressOut(
            street=order.delivery_street,
            number=order.delivery_number,
            complement=order.delivery_complement,
            district=order.delivery_district,
            city=order.delivery_city,
            state=order.delivery_state,
            postal_code=order.delivery_postal_code,
        ),
        customer_note=order.customer_note,
        fulfillment_modality=order.fulfillment_modality,
        production_batch_id=order.production_batch_id,
        production_batch_code=batch.code if batch else None,
        fulfillment_slot_id=order.fulfillment_slot_id,
        slot_starts_at=slot.starts_at if slot else None,
        slot_ends_at=slot.ends_at if slot else None,
        confirmed_at=order.confirmed_at,
        production_started_at=order.production_started_at,
        ready_at=order.ready_at,
        completed_at=order.completed_at,
        cancelled_at=order.cancelled_at,
        cancellation_reason=order.cancellation_reason,
        currency=order.currency,
        subtotal=_money(order.subtotal_cents, order.currency),
        delivery_fee=_money(order.delivery_fee_cents, order.currency),
        discount=_money(order.discount_cents, order.currency),
        total=_money(order.total_cents, order.currency),
        items=item_out,
        history=[
            HistoryOut(
                id=row.id,
                from_status=row.from_status,
                to_status=row.to_status,
                reason=row.reason,
                actor_ref=row.actor_ref,
                created_at=row.created_at,
            )
            for row in history
        ],
        notes=[
            NoteOut(id=row.id, body=row.body, author_ref=row.author_ref, created_at=row.created_at)
            for row in notes
        ],
        payment_records=[
            PaymentRecordOut(
                id=row.id,
                provider=row.provider,
                external_reference=row.external_reference,
                expected_cents=row.expected_cents,
                currency=row.currency,
                financial_status=row.financial_status,
                external_status_raw=row.external_status_raw,
                amount_paid_cents=row.amount_paid_cents,
                amount_refunded_cents=row.amount_refunded_cents,
                confirmed_at=row.confirmed_at,
                last_synced_at=row.last_synced_at,
            )
            for row in records
        ],
        payment_events=[
            PaymentEventOut(
                id=row.id,
                external_event_id=row.external_event_id,
                payment_record_id=row.payment_record_id,
                external_type=row.external_type,
                received_at=row.received_at,
                provider_occurred_at=row.provider_occurred_at,
                process_status=row.process_status,
                sanitized_error=row.sanitized_error,
            )
            for row in events
        ],
        financial_kind=financial_list_kind(order, records),
        financially_settled=order_is_financially_settled(order, records),
        holds_capacity=order.holds_capacity,
        snapshots_locked=locked,
    )
