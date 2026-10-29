"""Leitura 101C. Não grava, não envia e não cobra."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_engine
from app.domain.attendance import date_request_reference
from app.domain.order_board import classify_payment, managerial_board
from app.domain.orders import order_delivery_pending
from app.models.email_outbox import EmailOutbox
from app.models.orders import Order, OrderStatusHistory
from app.models.payments import PaymentRecord

CASE = "LPF891F9E5D1"


def counts(session: Session) -> dict[str, int]:
    return {
        "orders": int(session.scalar(select(func.count()).select_from(Order)) or 0),
        "outbox": int(session.scalar(select(func.count()).select_from(EmailOutbox)) or 0),
        "payments": int(session.scalar(select(func.count()).select_from(PaymentRecord)) or 0),
        "history": int(session.scalar(select(func.count()).select_from(OrderStatusHistory)) or 0),
    }


def main() -> None:
    session = Session(get_engine())
    try:
        before = counts(session)
        settings = get_settings()
        board, keys = managerial_board(session, settings)
        order = session.scalar(select(Order).where(Order.public_reference == CASE))
        print("operational_total", board["operational_total"])
        print("composition_note", board.get("composition_note"))
        main_total = sum(item["count"] for item in board["stages"])
        extra_total = sum(item["count"] for item in board["exceptions"])
        print("main_stages", main_total)
        print("exceptions_total", extra_total)
        print("total_matches", main_total + extra_total == board["operational_total"])
        print("unique_would_match", board["operational_total"])
        for group in ("stages", "exceptions", "history", "payments", "pendings"):
            for item in board[group]:
                print(f"{item['lens']} {item['count']} {item['label']}")
        case = {"found": False}
        if order is not None:
            anchor = f"order:{order.id}"
            records = list(
                session.scalars(select(PaymentRecord).where(PaymentRecord.order_id == order.id))
            )
            origin = None
            if order.source_date_request_id is not None:
                origin = date_request_reference(order.source_date_request_id)
            paid = sum(row.amount_paid_cents or 0 for row in records if row.financial_status == "paid")
            case = {
                "found": True,
                "status": order.status,
                "origin": origin,
                "total_cents": order.total_cents,
                "paid_cents": paid,
                "payment": classify_payment(order, records),
                "holds_capacity": order.holds_capacity,
                "delivery_confirmed": order.delivery_confirmed_at is not None,
                "delivery_pending": order_delivery_pending(order),
                "in_production_lens": anchor in keys["stage:in_production"],
                "ready_lens": anchor in keys["stage:ready_legacy"],
                "paid_lens": anchor in keys["stage:paid"],
                "address_lens": anchor in keys["pending:address"],
                "payment_paid_lens": anchor in keys.get("payment:paid", set()),
            }
            last = session.scalar(
                select(OrderStatusHistory)
                .where(OrderStatusHistory.order_id == order.id)
                .order_by(OrderStatusHistory.created_at.desc(), OrderStatusHistory.id.desc())
            )
            if last is not None:
                case["last_from"] = last.from_status
                case["last_to"] = last.to_status
                case["last_actor"] = last.actor_ref
                case["last_reason"] = last.reason
        after = counts(session)
        session.rollback()
        print("case", case)
        print("counts_before", before)
        print("counts_after", after)
        print("unchanged", before == after)
    finally:
        session.close()


if __name__ == "__main__":
    main()
