"""Leitura do caso LPF891F9E5D1. Não grava, não envia e não cobra."""

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_engine
from app.domain.attendance import date_request_reference
from app.domain.order_board import classify_payment
from app.models.date_requests import DateRequest, DateRequestEvent
from app.models.email_outbox import EmailOutbox
from app.models.orders import Order, OrderInternalNote, OrderStatusHistory
from app.models.payments import PaymentRecord

ZONE = ZoneInfo("America/Sao_Paulo")
CASE = "LPF891F9E5D1"


def stamp(value: datetime | None) -> str:
    if value is None:
        return "null"
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(ZONE).strftime("%Y-%m-%d %H:%M:%S %Z")


def actor_kind(actor: str | None) -> str:
    if not actor:
        return "absent"
    if actor.startswith("admin:"):
        return "admin"
    if actor.startswith("system:") or actor == "system":
        return "system"
    if actor.startswith("customer:"):
        return "customer"
    return "other"


def main() -> None:
    session = Session(get_engine())
    try:
        before_orders = int(session.scalar(select(func.count()).select_from(Order)) or 0)
        before_history = int(session.scalar(select(func.count()).select_from(OrderStatusHistory)) or 0)
        before_outbox = int(session.scalar(select(func.count()).select_from(EmailOutbox)) or 0)
        before_payments = int(session.scalar(select(func.count()).select_from(PaymentRecord)) or 0)
        order = session.scalar(select(Order).where(Order.public_reference == CASE))
        print("found", order is not None)
        if order is None:
            session.rollback()
            return
        origin = None
        if order.source_date_request_id is not None:
            origin = date_request_reference(order.source_date_request_id)
        records = list(session.scalars(select(PaymentRecord).where(PaymentRecord.order_id == order.id)))
        print("origin", origin)
        print("source_linked", order.source_date_request_id is not None)
        print("status", order.status)
        print("total_cents", order.total_cents)
        print("currency", order.currency)
        print("payment", classify_payment(order, records))
        print("holds_capacity", order.holds_capacity)
        print("delivery_confirmed", order.delivery_confirmed_at is not None)
        print("confirmed_at", stamp(order.confirmed_at))
        print("production_started_at", stamp(order.production_started_at))
        print("ready_at", stamp(order.ready_at))
        print("completed_at", stamp(order.completed_at))
        print("fulfilled_at", stamp(order.fulfilled_at))
        print("cancelled_at", stamp(order.cancelled_at))
        print("updated_at", stamp(getattr(order, "updated_at", None)))
        print("created_at", stamp(order.created_at))
        history = list(
            session.scalars(
                select(OrderStatusHistory)
                .where(OrderStatusHistory.order_id == order.id)
                .order_by(OrderStatusHistory.created_at.asc(), OrderStatusHistory.id.asc())
            )
        )
        print("history_rows", len(history))
        for row in history:
            reason = row.reason or ""
            print(
                "history",
                stamp(row.created_at),
                row.from_status,
                row.to_status,
                actor_kind(row.actor_ref),
                row.actor_ref or "ACTOR_ABSENT",
                "reason" if reason else "no_reason",
                reason if "@" not in reason else "redacted",
            )
        print("payment_rows", len(records))
        for row in records:
            print(
                "payment",
                row.financial_status,
                row.amount_paid_cents,
                row.expected_cents,
                stamp(row.created_at),
                stamp(getattr(row, "updated_at", None)),
                row.provider,
            )
        notes = list(
            session.scalars(
                select(OrderInternalNote)
                .where(OrderInternalNote.order_id == order.id)
                .order_by(OrderInternalNote.created_at.asc())
            )
        )
        print("notes", len(notes))
        for note in notes:
            print("note", stamp(note.created_at), actor_kind(note.author_ref), len(note.body or ""))
        notices = list(
            session.scalars(
                select(EmailOutbox)
                .where(EmailOutbox.order_id == order.id)
                .order_by(EmailOutbox.created_at.asc())
            )
        )
        print("notices", len(notices))
        for notice in notices:
            print("notice", notice.kind, notice.status, stamp(notice.created_at), stamp(notice.sent_at))
        if order.source_date_request_id is not None:
            request = session.get(DateRequest, order.source_date_request_id)
            print("request_status", None if request is None else request.status)
            events = list(
                session.scalars(
                    select(DateRequestEvent)
                    .where(DateRequestEvent.request_id == order.source_date_request_id)
                    .order_by(DateRequestEvent.created_at.asc())
                )
            )
            print("request_events", len(events))
            for event in events:
                detail = event.detail or ""
                print(
                    "request_event",
                    stamp(event.created_at),
                    event.action,
                    actor_kind(event.actor_ref),
                    event.actor_ref or "ACTOR_ABSENT",
                    detail if "@" not in detail and len(detail) <= 160 else f"len={len(detail)}",
                )
        ready_orders = list(session.scalars(select(Order).where(Order.status == "ready")))
        print("ready_now", len(ready_orders))
        for other in ready_orders:
            rows = list(
                session.scalars(
                    select(OrderStatusHistory)
                    .where(
                        OrderStatusHistory.order_id == other.id,
                        OrderStatusHistory.to_status == "ready",
                    )
                    .order_by(OrderStatusHistory.created_at.asc())
                )
            )
            print(
                "ready_case",
                other.public_reference,
                "rows",
                len(rows),
                "delivery_confirmed",
                other.delivery_confirmed_at is not None,
            )
            for row in rows:
                print(
                    "ready_transition",
                    other.public_reference,
                    stamp(row.created_at),
                    row.from_status,
                    actor_kind(row.actor_ref),
                    row.actor_ref or "ACTOR_ABSENT",
                    "no_reason" if not row.reason else "has_reason",
                )
        missing = 0
        for other in ready_orders:
            count = session.scalar(
                select(func.count())
                .select_from(OrderStatusHistory)
                .where(
                    OrderStatusHistory.order_id == other.id,
                    OrderStatusHistory.to_status == "ready",
                )
            )
            if not count:
                missing += 1
                print("ready_without_history", other.public_reference)
        print("ready_without_history_count", missing)
        session.rollback()
        after_orders = int(session.scalar(select(func.count()).select_from(Order)) or 0)
        after_history = int(session.scalar(select(func.count()).select_from(OrderStatusHistory)) or 0)
        after_outbox = int(session.scalar(select(func.count()).select_from(EmailOutbox)) or 0)
        after_payments = int(session.scalar(select(func.count()).select_from(PaymentRecord)) or 0)
        print(
            "unchanged",
            (before_orders, before_history, before_outbox, before_payments)
            == (after_orders, after_history, after_outbox, after_payments),
        )
    finally:
        session.close()


if __name__ == "__main__":
    settings = get_settings()
    print("timezone", settings.bakery_timezone)
    main()
