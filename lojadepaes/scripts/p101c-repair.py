"""Reparação única de LPF891F9E5D1. Não cobra, não avisa e não marca entrega."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_engine
from app.domain.attendance import date_request_reference
from app.domain.order_board import classify_payment
from app.domain.orders import correct_ready_to_in_production
from app.models.email_outbox import EmailOutbox
from app.models.orders import Order, OrderItem, OrderStatusHistory
from app.models.payments import PaymentRecord

CASE = "LPF891F9E5D1"
ORIGIN = "SD3CC4C139"


def counts(session: Session) -> tuple[int, int, int, int, int]:
    return (
        int(session.scalar(select(func.count()).select_from(Order)) or 0),
        int(session.scalar(select(func.count()).select_from(EmailOutbox)) or 0),
        int(session.scalar(select(func.count()).select_from(PaymentRecord)) or 0),
        int(session.scalar(select(func.count()).select_from(OrderItem)) or 0),
        int(session.scalar(select(func.count()).select_from(OrderStatusHistory)) or 0),
    )


def main() -> None:
    session = Session(get_engine())
    try:
        before = counts(session)
        order = session.scalar(select(Order).where(Order.public_reference == CASE))
        if order is None:
            print("blocked missing")
            session.rollback()
            raise SystemExit(2)
        records = list(session.scalars(select(PaymentRecord).where(PaymentRecord.order_id == order.id)))
        origin = None
        if order.source_date_request_id is not None:
            origin = date_request_reference(order.source_date_request_id)
        others = list(
            session.scalars(
                select(Order.public_reference).where(
                    Order.status == "ready", Order.public_reference != CASE
                )
            )
        )
        print("other_ready", list(others))
        paid = [row for row in records if row.financial_status == "paid"]
        last = session.scalar(
            select(OrderStatusHistory)
            .where(OrderStatusHistory.order_id == order.id)
            .order_by(OrderStatusHistory.created_at.desc(), OrderStatusHistory.id.desc())
        )
        block = None
        if order.status != "ready":
            block = f"status={order.status}"
        elif order.delivery_confirmed_at is not None:
            block = "delivery_confirmed"
        elif order.total_cents != 7000:
            block = f"total={order.total_cents}"
        elif classify_payment(order, records) != "paid":
            block = "payment_not_paid"
        elif sum(row.amount_paid_cents or 0 for row in paid) != 7000:
            block = "paid_cents"
        elif origin != ORIGIN:
            block = f"origin={origin}"
        elif order.holds_capacity is not True:
            block = "capacity"
        elif last is None or last.to_status != "ready":
            block = "later_history"
        if block:
            print("blocked", block)
            session.rollback()
            raise SystemExit(2)
        started = order.production_started_at
        ready_at = order.ready_at
        correct_ready_to_in_production(session, order.id, actor_ref="assisted:101c")
        session.flush()
        session.refresh(order)
        after_records = list(
            session.scalars(select(PaymentRecord).where(PaymentRecord.order_id == order.id))
        )
        last = session.scalar(
            select(OrderStatusHistory)
            .where(OrderStatusHistory.order_id == order.id)
            .order_by(OrderStatusHistory.created_at.desc(), OrderStatusHistory.id.desc())
        )
        after = counts(session)
        history_grew_once = after[4] == before[4] + 1 and after[:4] == before[:4]
        if (
            order.status != "in_production"
            or order.total_cents != 7000
            or order.production_started_at != started
            or order.ready_at != ready_at
            or order.delivery_confirmed_at is not None
            or order.holds_capacity is not True
            or classify_payment(order, after_records) != "paid"
            or not history_grew_once
            or last is None
            or last.actor_ref != "assisted:101c"
            or last.from_status != "ready"
            or last.to_status != "in_production"
        ):
            session.rollback()
            print("rolled_back")
            raise SystemExit(2)
        session.commit()
        print("repaired", CASE, "ready_to_in_production")
        print("preserved_total", 7000)
        print("preserved_ready_at", ready_at is not None)
        print("preserved_production_started", started is not None)
    finally:
        session.close()


if __name__ == "__main__":
    main()
