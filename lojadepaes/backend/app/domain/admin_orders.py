import logging
from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.domain.adaptations import (
    adaptation_is_resolved,
    adaptations_for_order,
    admin_adaptation_view,
)
from app.domain.cpf import mask_cpf
from app.domain.errors import NotFoundError
from app.domain.order_board import (
    classify_payment,
    payment_attention_label,
    visible_label_for_order,
    visible_stage_for_order,
)
from app.domain.orders import (
    DELIVERY_REQUIRED_FIELDS,
    delivery_missing_fields,
    order_delivery_pending,
)
from app.domain.payments import financial_list_kind, order_is_financially_settled
from app.models.customers import CustomerAccount
from app.models.date_requests import DateRequest
from app.models.email_outbox import EmailOutbox
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
    NotificationOut,
    OrderDetailOut,
    OrderListOut,
    OrderListQuery,
    PaymentEventOut,
    PaymentRecordOut,
)

logger = logging.getLogger("lojadepaes.ops")

QUEUE_CONFIRMED = (
    OrderStatus.CONFIRMED.value,
    OrderStatus.IN_PRODUCTION.value,
    OrderStatus.READY.value,
    OrderStatus.COMPLETED.value,
)
OPEN_DATE_REQUESTS = ("pending", "alternative_proposed")
DEFAULT_PAGE_SIZE = 20


def _fidelity_mask(session: Session, order: Order) -> str | None:
    if order.fidelity_account_id is None:
        return None
    account = session.get(CustomerAccount, order.fidelity_account_id)
    if account is None:
        return None
    return mask_cpf(account.cpf_last2)


def queue_membership(now: datetime | None = None):
    """Fila operacional: encomendas em curso e toda solicitação ainda aguardando avaliação.

    Pedido `submitted` permanece acessível até aceite ou cancelamento, sem corte de 24h,
    independentemente de pagamento, modalidade histórica ou composição.
    """
    del now
    return or_(
        Order.status.in_(QUEUE_CONFIRMED),
        Order.status == OrderStatus.SUBMITTED.value,
    )


def attendance_health(session: Session) -> dict:
    """Leitura: pendências no banco versus a consulta administrativa equivalente.

    `queue_total` é o mesmo recorte de `list_orders` sem filtro extra. Paginação
    não entra nesta conta — `hidden_submitted` é perda de recorte, não de página.
    """
    now = datetime.now(UTC)
    submitted = int(
        session.scalar(
            select(func.count()).select_from(Order).where(Order.status == OrderStatus.SUBMITTED.value)
        )
        or 0
    )
    queue_ids = select(Order.id).where(queue_membership(now))
    queue_total = int(session.scalar(select(func.count()).select_from(queue_ids.subquery())) or 0)
    submitted_in_queue = int(
        session.scalar(
            select(func.count()).select_from(
                queue_ids.where(Order.status == OrderStatus.SUBMITTED.value).subquery()
            )
        )
        or 0
    )
    hidden_submitted = max(0, submitted - submitted_in_queue)
    open_date_requests = int(
        session.scalar(
            select(func.count())
            .select_from(DateRequest)
            .where(DateRequest.status.in_(OPEN_DATE_REQUESTS))
        )
        or 0
    )
    default_orders = int(
        session.scalar(
            select(func.count())
            .select_from(Order)
            .where(
                Order.status.in_(
                    (
                        OrderStatus.SUBMITTED.value,
                        OrderStatus.CONFIRMED.value,
                        OrderStatus.IN_PRODUCTION.value,
                        OrderStatus.READY.value,
                    )
                )
            )
        )
        or 0
    )
    payload = {
        "submitted_orders": submitted,
        "submitted_in_admin_queue": submitted_in_queue,
        "hidden_submitted": hidden_submitted,
        "hidden_date_requests": 0,
        "queue_total": default_orders + open_date_requests,
        "open_date_requests": open_date_requests,
        "page_size_default": DEFAULT_PAGE_SIZE,
        "discrepancy": hidden_submitted > 0,
    }
    if payload["discrepancy"]:
        logger.warning(
            "attendance_health discrepancy hidden_submitted=%s submitted_orders=%s "
            "queue_total=%s open_date_requests=%s",
            hidden_submitted,
            submitted,
            queue_total,
            open_date_requests,
        )
    return payload


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


def _notification_views(session: Session, order_id: UUID) -> list[NotificationOut]:
    rows = session.scalars(
        select(EmailOutbox)
        .where(EmailOutbox.order_id == order_id)
        .order_by(EmailOutbox.created_at.asc())
    )
    return [
        NotificationOut(
            id=row.id,
            kind=row.kind,
            status=row.status,
            last_error=row.last_error,
            created_at=row.created_at,
            sent_at=row.sent_at,
        )
        for row in rows
    ]


def allowed_actions(status: str) -> list[str]:
    if status in {OrderStatus.IN_PRODUCTION.value, OrderStatus.READY.value}:
        return ["confirm_delivery", "cancel"]
    return [ACTION_BY_TARGET[target] for target in sorted(ALLOWED_TRANSITIONS.get(status, frozenset()))]


def list_orders(session: Session, settings: Settings, query: OrderListQuery) -> OrderListOut:
    from app.domain.attendance import list_attendance

    result = list_attendance(session, settings, query)
    health = attendance_health(session)
    if health["discrepancy"]:
        logger.warning(
            "admin_orders_list inaccessible_pending hidden_submitted=%s page=%s page_size=%s total=%s",
            health["hidden_submitted"],
            query.page,
            query.page_size,
            result.total,
        )
    return result


def _linked_delivery_filled(session: Session, order: Order) -> list[str]:
    if not order.source_date_request_id:
        return []
    request = session.get(DateRequest, order.source_date_request_id)
    raw = getattr(request, "complement", None) or {}
    labels = []
    for field, label in DELIVERY_REQUIRED_FIELDS:
        if str(raw.get(field) or "").strip():
            labels.append(label)
    return labels


def _detail_tracks(order: Order, bucket: str, adaptations: dict) -> dict:
    from app.core.config import get_settings
    from app.domain.bakery_time import bakery_today
    from app.domain.order_tracks import order_tracks

    text = None
    unresolved = False
    for row in adaptations.values():
        if adaptation_is_resolved(row):
            continue
        unresolved = True
        text = text or row.customer_text
    projection = order_tracks(
        order,
        bucket,
        unresolved_adaptation=unresolved,
        adaptation_text=text,
        today=bakery_today(get_settings()),
    )
    return {
        "tracks": {
            name: projection[name] for name in ("commercial", "payment", "production", "delivery")
        },
        "next_action": projection["next_action"],
        "attention": projection["attention"],
    }


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

    dough_ids = {item.dough_type_id for item in items if item.dough_type_id}
    shape_ids = {item.bread_shape_id for item in items if item.bread_shape_id}
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
    adaptations = adaptations_for_order(session, order.id)
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
            included = item.product_variant_id is None and extra.surcharge_cents is None
            extra_complete = bool(extra_snap) and (extra.surcharge_cents is not None or included)
            extras_complete = extras_complete and extra_complete
            extra_out.append(
                ExtraOut(
                    ingredient_id=extra.ingredient_id,
                    name=extra_name,
                    surcharge=_money(extra.surcharge_cents, order.currency)
                    if extra.surcharge_cents is not None
                    else None,
                    included_in_loaf_price=included,
                    snapshot_complete=extra_complete,
                    assistant_role=ingredient.assistant_role if ingredient else None,
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
                origin="custom" if item.product_variant_id is None else "product",
                weight_grams=item.net_weight_grams,
                snapshot_complete=snapshot_complete,
                provisional=not locked or not snapshot_complete,
                adaptation=admin_adaptation_view(session, adaptations.get(item.id)),
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
    _bucket = classify_payment(order, records)

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
        fulfilled_at=order.fulfilled_at,
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
                sanitized_error=row.sanitized_error,
                method=row.method,
                pix_expires_at=row.pix_expires_at,
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
        production_local_date=order.production_local_date,
        preferred_time=(
            f"{order.preferred_time.hour:02d}:{order.preferred_time.minute:02d}"
            if order.preferred_time
            else None
        ),
        proposed_production_date=order.proposed_production_date,
        has_unresolved_adaptations=any(
            not adaptation_is_resolved(row) for row in adaptations.values()
        ),
        fidelity_opt_in=bool(order.fidelity_opt_in),
        order_kind=order.order_kind or "standard",
        fidelity_cpf_masked=_fidelity_mask(session, order),
        has_custom=any(item.origin == "custom" for item in item_out),
        notifications=_notification_views(session, order.id),
        delivery_pending=order_delivery_pending(order),
        delivery_missing_fields=delivery_missing_fields(order)
        if order.fulfillment_modality == "delivery"
        else [],
        linked_delivery_filled_fields=_linked_delivery_filled(session, order),
        visible_stage=visible_stage_for_order(order, _bucket),
        visible_label=visible_label_for_order(order, _bucket),
        payment_attention=payment_attention_label(order, _bucket),
        delivery_confirmed_at=order.delivery_confirmed_at,
        **_detail_tracks(order, _bucket, adaptations),
    )
