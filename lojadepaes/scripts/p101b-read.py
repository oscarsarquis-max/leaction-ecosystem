"""Leitura do quadro em produção. Não grava, não envia e não cobra."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_engine
from app.domain.attendance import date_request_reference
from app.domain.order_board import classify_payment, managerial_board, visible_stage_for_order
from app.domain.orders import order_delivery_pending
from app.models.date_requests import DateRequest
from app.models.email_outbox import EmailOutbox
from app.models.orders import Order, OrderStatusHistory
from app.models.payments import PaymentRecord


def counts(session: Session) -> dict[str, int]:
    return {
        "orders": int(session.scalar(select(func.count()).select_from(Order)) or 0),
        "date_requests": int(session.scalar(select(func.count()).select_from(DateRequest)) or 0),
        "outbox": int(session.scalar(select(func.count()).select_from(EmailOutbox)) or 0),
        "payments": int(session.scalar(select(func.count()).select_from(PaymentRecord)) or 0),
    }


def main() -> None:
    session = Session(get_engine())
    try:
        before = counts(session)
        settings = get_settings()
        board, _keys = managerial_board(session, settings)
        statuses = dict(
            session.execute(
                select(Order.status, func.count()).group_by(Order.status).order_by(Order.status)
            ).all()
        )
        confirmed_rows = int(
            session.scalar(
                select(func.count()).select_from(Order).where(Order.delivery_confirmed_at.is_not(None))
            )
            or 0
        )
        canned = 0
        explicit = 0
        other = 0
        for reason, count in session.execute(
            select(OrderStatusHistory.reason, func.count())
            .where(OrderStatusHistory.to_status == "completed")
            .group_by(OrderStatusHistory.reason)
        ):
            if reason == "entregue ou retirado":
                canned += int(count)
            elif reason == "entrega confirmada pelo gestor":
                explicit += int(count)
            else:
                other += int(count)
        order = session.scalar(select(Order).where(Order.public_reference == "LPF891F9E5D1"))
        case = {"found": False}
        if order is not None:
            records = list(
                session.scalars(select(PaymentRecord).where(PaymentRecord.order_id == order.id))
            )
            bucket = classify_payment(order, records)
            origin = None
            if order.source_date_request_id is not None:
                origin = date_request_reference(order.source_date_request_id)
            case = {
                "found": True,
                "status": order.status,
                "visible_stage": visible_stage_for_order(order, bucket),
                "total_cents": order.total_cents,
                "payment": bucket,
                "delivery_pending": order_delivery_pending(order),
                "delivery_confirmed": order.delivery_confirmed_at is not None,
                "phone_present": bool((order.customer_phone or "").strip()),
                "origin": origin,
            }
        after = counts(session)
        session.rollback()
        print("timezone", board["timezone"])
        print("updated_label", board["updated_label"])
        print("operational_total", board["operational_total"])
        print("legacy_note", board.get("legacy_note"))
        for group in ("stages", "history", "payments", "payment_other", "pendings"):
            for item in board[group]:
                print(f"{item['lens']} {item['count']} {item['label']}")
        print("payment_orders", board["payment_orders"])
        print("statuses", {key: int(value) for key, value in statuses.items()})
        print("delivery_confirmed_rows", confirmed_rows)
        print(
            "completed_history",
            {"canned_complete": canned, "explicit_delivery": explicit, "other": other},
        )
        print("case", case)
        print("counts_before", before)
        print("counts_after", after)
        print("unchanged", before == after)
    finally:
        session.close()


if __name__ == "__main__":
    main()
