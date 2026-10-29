from __future__ import annotations

import unicodedata
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import Settings
from app.domain.bakery_time import bakery_today
from app.domain.email_outbox import enqueue_ops_attendance_summary
from app.domain.order_board import (
    classify_payment,
    date_visible,
    payment_attention_label,
    visible_label_for_order,
    visible_stage_for_order,
)
from app.domain.orders import order_delivery_pending
from app.domain.payments import financial_list_kind
from app.models.date_requests import DateRequest
from app.models.email_outbox import EmailOutbox
from app.models.enums import AdaptationStatus, OrderStatus
from app.models.orders import Order, OrderItem, OrderItemAdaptation
from app.models.payments import PaymentRecord
from app.models.production import FulfillmentSlot, ProductionBatch
from app.schemas.admin import MoneyOut, OrderListItemOut, OrderListOut, OrderListQuery

ACTIVE_ORDER = (
    OrderStatus.CONFIRMED.value,
    OrderStatus.IN_PRODUCTION.value,
    OrderStatus.READY.value,
)
# Fila vigente: etapas do fluxo e a exceção Pronto sem confirmação de entrega.
DEFAULT_ORDER = (
    OrderStatus.SUBMITTED.value,
    OrderStatus.CONFIRMED.value,
    OrderStatus.IN_PRODUCTION.value,
    OrderStatus.READY.value,
)
OPEN_DATE_REQUESTS = ("pending", "alternative_proposed", "awaiting_details")
STATUS_ALL = "all"
OPS_SUMMARY_DEDUPE = "ops:attendance_summary:prompt67"


def fold_text(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value)
    return "".join(char for char in normalized if unicodedata.category(char) != "Mn").casefold()


def _searching(query: OrderListQuery) -> bool:
    return bool(query.reference and query.reference.strip())


def date_request_reference(request_id: UUID) -> str:
    return f"SD{str(request_id).replace('-', '')[:8].upper()}"


def _hours_since(moment: datetime, now: datetime) -> int:
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return max(0, int((now - moment).total_seconds() // 3600))


def _context_label(row: DateRequest) -> str | None:
    if row.cart_context:
        parts = []
        for line in row.cart_context:
            quantity = line.get("quantity") or 1
            name = line.get("product_name") or "pão"
            variant = line.get("variant_name") or ""
            label = f"{quantity}× {name}"
            if variant:
                label += f" ({variant})"
            parts.append(label)
        return "; ".join(parts) if parts else None
    if row.intended_quantity:
        return f"{row.intended_quantity} pão(ães)"
    return None


def _rank(item: OrderListItemOut, today) -> tuple[int, datetime, str]:
    created = item.created_at if item.created_at.tzinfo else item.created_at.replace(tzinfo=UTC)
    if item.source == "date_request" and item.status in OPEN_DATE_REQUESTS:
        return (0 if item.overdue else 1, created, item.row_key)
    if item.status == OrderStatus.SUBMITTED.value:
        if item.adaptation_attention:
            return (2, created, item.row_key)
        if item.financial_kind == "settled":
            return (3, created, item.row_key)
        return (4, created, item.row_key)
    if item.status in ACTIVE_ORDER:
        return (5, datetime.max.replace(tzinfo=UTC) - created, item.row_key)
    return (6, datetime.max.replace(tzinfo=UTC) - created, item.row_key)


def _order_row(
    order: Order,
    *,
    units: int,
    records: list[PaymentRecord],
    custom: bool,
    unresolved: bool,
    batch_code: str | None,
    slot,
    now: datetime,
    today,
) -> OrderListItemOut:
    created = order.created_at if order.created_at.tzinfo else order.created_at.replace(tzinfo=UTC)
    pending = order.status == OrderStatus.SUBMITTED.value
    desired = order.production_local_date or order.proposed_production_date
    bucket = classify_payment(order, records)
    return OrderListItemOut(
        id=order.id,
        public_reference=order.public_reference,
        created_at=order.created_at,
        status=order.status,
        customer_name=order.customer_name,
        bread_units=units,
        fulfillment_modality=order.fulfillment_modality,
        production_batch_id=order.production_batch_id,
        production_batch_code=batch_code,
        fulfillment_slot_id=order.fulfillment_slot_id,
        slot_starts_at=slot.starts_at if slot else None,
        slot_ends_at=slot.ends_at if slot else None,
        total=MoneyOut(cents=order.total_cents, currency=order.currency),
        financial_kind=financial_list_kind(order, records),
        adaptation_attention=unresolved,
        has_custom=custom,
        custom_awaiting=custom and order.status == OrderStatus.SUBMITTED.value,
        source="order",
        row_key=f"order:{order.id}",
        desired_date=desired,
        context_label=None,
        pending_hours=_hours_since(created, now) if pending else None,
        overdue=bool(desired and desired < today and pending),
        delivery_pending=order_delivery_pending(order),
        visible_stage=visible_stage_for_order(order, bucket),
        visible_label=visible_label_for_order(order, bucket),
        payment_attention=payment_attention_label(order, bucket),
    )


def _date_row(row: DateRequest, now: datetime, today) -> OrderListItemOut:
    created = row.created_at if row.created_at.tzinfo else row.created_at.replace(tzinfo=UTC)
    open_row = row.status in OPEN_DATE_REQUESTS
    stage, label = date_visible(row.status)
    return OrderListItemOut(
        id=row.id,
        public_reference=date_request_reference(row.id),
        created_at=row.created_at,
        status=row.status,
        customer_name=row.customer_name,
        bread_units=int(row.intended_quantity or 0),
        fulfillment_modality=None,
        production_batch_id=None,
        production_batch_code=None,
        fulfillment_slot_id=None,
        slot_starts_at=None,
        slot_ends_at=None,
        total=MoneyOut(cents=None, currency="BRL"),
        financial_kind="none",
        source="date_request",
        row_key=f"date_request:{row.id}",
        desired_date=row.desired_date,
        context_label=_context_label(row),
        pending_hours=_hours_since(created, now) if open_row else None,
        overdue=bool(open_row and row.desired_date < today),
        delivery_pending=False,
        visible_stage=stage,
        visible_label=label,
    )


def _matches_search(item: OrderListItemOut, raw: str) -> bool:
    needle = fold_text(raw.strip())
    if needle and needle in fold_text(item.public_reference):
        return True
    if item.customer_name and needle and needle in fold_text(item.customer_name):
        return True
    compact = raw.strip().upper().replace("SD", "")
    if compact and compact in str(item.id).replace("-", "").upper():
        return True
    return False


def _state_counts(session: Session) -> dict[str, int]:
    from app.domain.managerial_exclusion import active_exclusion_sets

    excluded_orders, excluded_dates = active_exclusion_sets(session)
    order_stmt = (
        select(Order.status, func.count())
        .where(Order.status != OrderStatus.DRAFT.value)
        .group_by(Order.status)
    )
    date_stmt = (
        select(DateRequest.status, func.count())
        .where(DateRequest.status != "converted")
        .group_by(DateRequest.status)
    )
    if excluded_orders:
        order_stmt = order_stmt.where(Order.id.notin_(excluded_orders))
    if excluded_dates:
        date_stmt = date_stmt.where(DateRequest.id.notin_(excluded_dates))
    order_rows = list(session.execute(order_stmt))
    by_status = {status: int(count) for status, count in order_rows}
    date_rows = list(session.execute(date_stmt))
    date_by_status = {status: int(count) for status, count in date_rows}
    queue = sum(by_status.get(status, 0) for status in DEFAULT_ORDER) + sum(
        date_by_status.get(status, 0) for status in OPEN_DATE_REQUESTS
    )
    return {
        "queue": queue,
        "all": sum(by_status.values()) + sum(date_by_status.values()),
        "completed": by_status.get(OrderStatus.COMPLETED.value, 0),
        "cancelled": by_status.get(OrderStatus.CANCELLED.value, 0),
        "date_closed": date_by_status.get("closed", 0) + date_by_status.get("converted", 0),
    }


def _load_orders(session: Session, settings: Settings, query: OrderListQuery) -> list[Order]:
    from app.domain.admin_orders import bakery_day_range

    if query.status in {"date_pending", "date_closed", "closed"}:
        return []
    stmt = select(Order).where(Order.status != OrderStatus.DRAFT.value)
    if query.status == STATUS_ALL:
        pass
    elif query.status and query.status not in {"date_pending", "date_closed", "closed", STATUS_ALL}:
        stmt = stmt.where(Order.status == query.status)
    elif not _searching(query):
        stmt = stmt.where(Order.status.in_(DEFAULT_ORDER))
    if query.reference:
        needle = query.reference.strip()
        if needle.upper().startswith(("LP", "SD")):
            stmt = stmt.where(
                or_(
                    Order.public_reference.ilike(f"%{needle}%", escape="\\"),
                    Order.customer_name.ilike(f"%{needle}%", escape="\\"),
                )
            )
    if query.production_batch_id:
        stmt = stmt.where(Order.production_batch_id == query.production_batch_id)
    if query.fulfillment_slot_id:
        stmt = stmt.where(Order.fulfillment_slot_id == query.fulfillment_slot_id)
    if query.modality:
        stmt = stmt.where(Order.fulfillment_modality == query.modality)
    if query.created_from:
        stmt = stmt.where(
            Order.created_at
            >= bakery_day_range(
                query.created_from, settings.bakery_timezone, end_exclusive=False
            )
        )
    if query.created_to:
        stmt = stmt.where(
            Order.created_at
            < bakery_day_range(query.created_to, settings.bakery_timezone, end_exclusive=True)
        )
    return list(session.scalars(stmt))


def _load_date_requests(
    session: Session, settings: Settings, query: OrderListQuery
) -> list[DateRequest]:
    from app.domain.admin_orders import bakery_day_range

    if query.modality or query.production_batch_id or query.fulfillment_slot_id:
        return []
    if query.status in {
        OrderStatus.CONFIRMED.value,
        OrderStatus.IN_PRODUCTION.value,
        OrderStatus.READY.value,
        OrderStatus.COMPLETED.value,
        OrderStatus.CANCELLED.value,
        OrderStatus.DRAFT.value,
    }:
        return []
    stmt = select(DateRequest)
    if query.status == STATUS_ALL or (_searching(query) and not query.status):
        pass
    elif query.reference and not query.status:
        pass
    elif not query.status or query.status in {OrderStatus.SUBMITTED.value, "date_pending"}:
        stmt = stmt.where(DateRequest.status.in_(OPEN_DATE_REQUESTS))
    elif query.status in {"date_closed", "closed"}:
        stmt = stmt.where(DateRequest.status.in_(("closed", "converted")))
    elif query.status in {*OPEN_DATE_REQUESTS, "closed"}:
        stmt = stmt.where(DateRequest.status == query.status)
    else:
        return []
    if query.created_from:
        stmt = stmt.where(
            DateRequest.created_at
            >= bakery_day_range(
                query.created_from, settings.bakery_timezone, end_exclusive=False
            )
        )
    if query.created_to:
        stmt = stmt.where(
            DateRequest.created_at
            < bakery_day_range(
                query.created_to, settings.bakery_timezone, end_exclusive=True
            )
        )
    return list(session.scalars(stmt))


def list_attendance(session: Session, settings: Settings, query: OrderListQuery) -> OrderListOut:
    lens = (query.lens or "").strip()
    if lens:
        from app.domain.order_board import lens_fetch_status

        fetch_status = lens_fetch_status(lens)
        if fetch_status:
            query = query.model_copy(update={"status": fetch_status})
    now = datetime.now(UTC)
    today = bakery_today(settings)
    orders_error = None
    dates_error = None
    orders: list[Order] = []
    dates: list[DateRequest] = []
    try:
        orders = _load_orders(session, settings, query)
    except Exception:
        from app.domain.admin_orders import logger

        logger.exception("admin_attendance_orders_failed")
        orders_error = "Não foi possível carregar as encomendas."
    try:
        dates = _load_date_requests(session, settings, query)
    except Exception:
        from app.domain.admin_orders import logger

        logger.exception("admin_attendance_dates_failed")
        dates_error = "Não foi possível carregar as solicitações de data."

    from app.domain.managerial_exclusion import active_exclusion_sets

    excluded_orders, excluded_dates = active_exclusion_sets(session)
    if lens == "audit:tests":
        orders = [order for order in orders if order.id in excluded_orders]
        dates = [row for row in dates if row.id in excluded_dates]
    else:
        orders = [order for order in orders if order.id not in excluded_orders]
        dates = [
            row
            for row in dates
            if row.id not in excluded_dates and row.status != "converted"
        ]

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
        for record in session.scalars(select(PaymentRecord).where(PaymentRecord.order_id.in_(ids))):
            records_by_order.setdefault(record.order_id, []).append(record)
    custom_ids: set[UUID] = set()
    unresolved_ids: set[UUID] = set()
    if ids:
        for order_id in session.scalars(
            select(OrderItem.order_id)
            .where(OrderItem.order_id.in_(ids), OrderItem.product_variant_id.is_(None))
            .distinct()
        ):
            custom_ids.add(order_id)
        for order_id in session.scalars(
            select(OrderItem.order_id)
            .join(OrderItemAdaptation, OrderItemAdaptation.order_item_id == OrderItem.id)
            .where(OrderItem.order_id.in_(ids))
            .where(
                OrderItemAdaptation.status.notin_(
                    (AdaptationStatus.ACCEPTED.value, AdaptationStatus.ALTERNATIVE_ACCEPTED.value)
                )
            )
        ):
            unresolved_ids.add(order_id)
    batch_ids = {order.production_batch_id for order in orders if order.production_batch_id}
    slot_ids = {order.fulfillment_slot_id for order in orders if order.fulfillment_slot_id}
    batches = {}
    if batch_ids:
        batches = {
            row.id: row
            for row in session.scalars(
                select(ProductionBatch).where(ProductionBatch.id.in_(batch_ids))
            )
        }
    slots = {}
    if slot_ids:
        slots = {
            row.id: row
            for row in session.scalars(
                select(FulfillmentSlot).where(FulfillmentSlot.id.in_(slot_ids))
            )
        }

    items = []
    for order in orders:
        batch = batches.get(order.production_batch_id)
        items.append(
            _order_row(
                order,
                units=units.get(order.id, 0),
                records=records_by_order.get(order.id, []),
                custom=order.id in custom_ids,
                unresolved=order.id in unresolved_ids,
                batch_code=batch.code if batch else None,
                slot=slots.get(order.fulfillment_slot_id) if order.fulfillment_slot_id else None,
                now=now,
                today=today,
            )
        )
    items.extend(_date_row(row, now, today) for row in dates)
    if query.reference:
        items = [item for item in items if _matches_search(item, query.reference)]
    filter_label = None
    if lens:
        from app.domain.order_board import LENS_LABELS, managerial_board

        _board, keys = managerial_board(session, settings)
        allowed = keys.get(lens, set())
        items = [item for item in items if item.row_key in allowed]
        filter_label = LENS_LABELS.get(lens, lens)
    items.sort(key=lambda item: _rank(item, today))
    total = len(items)
    offset = (query.page - 1) * query.page_size
    page_items = items[offset : offset + query.page_size]
    search_scope = None
    if lens and filter_label:
        search_scope = filter_label
    elif _searching(query) and (not query.status or query.status == STATUS_ALL):
        search_scope = "histórico completo"
    elif query.status == STATUS_ALL:
        search_scope = "todos os estados"
    elif not query.status:
        search_scope = "fila operacional"
    return OrderListOut(
        items=page_items,
        page=query.page,
        page_size=query.page_size,
        total=total,
        orders_error=orders_error,
        date_requests_error=dates_error,
        search_scope=search_scope,
        filter_label=filter_label,
        state_counts=(
            _state_counts(session) if orders_error is None and dates_error is None else None
        ),
    )


def attendance_summary(session: Session, settings: Settings) -> dict:
    today = bakery_today(settings)
    from app.domain.managerial_exclusion import active_exclusion_sets

    excluded_orders, excluded_dates = active_exclusion_sets(session)
    submitted = [
        order
        for order in session.scalars(select(Order).where(Order.status == OrderStatus.SUBMITTED.value))
        if order.id not in excluded_orders
    ]
    confirmed = [
        order
        for order in session.scalars(select(Order).where(Order.status.in_(ACTIVE_ORDER)))
        if order.id not in excluded_orders
    ]
    dates = [
        row
        for row in session.scalars(
            select(DateRequest)
            .options(selectinload(DateRequest.events))
            .where(DateRequest.status.in_(OPEN_DATE_REQUESTS))
        )
        if row.id not in excluded_dates
    ]
    submitted_ids = [order.id for order in submitted]
    settled: set[UUID] = set()
    adaptations: set[UUID] = set()
    records_by_order: dict[UUID, list[PaymentRecord]] = {order.id: [] for order in submitted}
    if submitted_ids:
        for record in session.scalars(
            select(PaymentRecord).where(PaymentRecord.order_id.in_(submitted_ids))
        ):
            records_by_order.setdefault(record.order_id, []).append(record)
        for order in submitted:
            if financial_list_kind(order, records_by_order.get(order.id, [])) == "settled":
                settled.add(order.id)
        for order_id in session.scalars(
            select(OrderItem.order_id)
            .join(OrderItemAdaptation, OrderItemAdaptation.order_item_id == OrderItem.id)
            .where(OrderItem.order_id.in_(submitted_ids))
            .where(
                OrderItemAdaptation.status.notin_(
                    (AdaptationStatus.ACCEPTED.value, AdaptationStatus.ALTERNATIVE_ACCEPTED.value)
                )
            )
        ):
            adaptations.add(order_id)
    paid_awaiting = [order for order in submitted if order.id in settled]
    awaiting_eval = [order for order in submitted if order.id not in settled]
    overdue_dates = [row for row in dates if row.desired_date < today]
    priority = []
    for row in sorted(dates, key=lambda item: (item.desired_date >= today, item.created_at)):
        priority.append(
            {
                "source": "date_request",
                "id": str(row.id),
                "row_key": f"date_request:{row.id}",
                "public_reference": date_request_reference(row.id),
                "kind_label": "Solicitação de data",
                "action_label": "Responder",
                "href": f"/admin/pedidos/solicitacao/{row.id}",
                "desired_date": row.desired_date.isoformat(),
                "overdue": row.desired_date < today,
            }
        )
    for order in paid_awaiting + awaiting_eval:
        desired = order.production_local_date or order.proposed_production_date
        priority.append(
            {
                "source": "order",
                "id": str(order.id),
                "row_key": f"order:{order.id}",
                "public_reference": order.public_reference,
                "kind_label": "Pedido",
                "action_label": "Avaliar",
                "href": f"/admin/pedidos/{order.id}",
                "desired_date": desired.isoformat() if desired else None,
                "overdue": bool(desired and desired < today),
            }
        )
    from app.domain.order_board import managerial_board
    from app.domain.owner_alerts import channel_status, recent_alert_failures

    board, _keys = managerial_board(session, settings)
    alerts = channel_status(session, settings)
    alerts["failures"] = recent_alert_failures(session)
    return {
        "date_requests_awaiting": len(dates),
        "orders_awaiting_evaluation": len(awaiting_eval),
        "orders_awaiting_adaptation": len(adaptations),
        "paid_awaiting_accept": len(paid_awaiting),
        "confirmed_awaiting_delivery": len(confirmed),
        "overdue_dates": len(overdue_dates),
        "unique_records": board["operational_total"],
        "counts_are_subsets": True,
        "priority": priority[:8],
        "updated_at": datetime.now(UTC).isoformat(),
        "board": board,
        "owner_alerts": alerts,
    }


def enqueue_authorized_ops_summary(session: Session, settings: Settings) -> EmailOutbox:
    payload = attendance_summary(session, settings)
    return enqueue_ops_attendance_summary(session, settings, payload, dedupe_key=OPS_SUMMARY_DEDUPE)
