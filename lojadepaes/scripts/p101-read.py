"""Leitura do resumo em produção. Não grava, não envia e não cobra."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_engine
from app.domain.attendance import date_request_reference
from app.domain.order_board import classify_payment, managerial_board
from app.domain.orders import order_delivery_pending
from app.models.date_requests import DateRequest
from app.models.email_outbox import EmailOutbox
from app.models.orders import Order
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
        order = session.scalar(select(Order).where(Order.public_reference == "LPF891F9E5D1"))
        case = {"found": False}
        if order is not None:
            records = list(
                session.scalars(select(PaymentRecord).where(PaymentRecord.order_id == order.id))
            )
            origin = None
            if order.source_date_request_id is not None:
                origin = date_request_reference(order.source_date_request_id)
            case = {
                "found": True,
                "status": order.status,
                "total_cents": order.total_cents,
                "payment": classify_payment(order, records),
                "delivery_pending": order_delivery_pending(order),
                "phone_present": bool((order.customer_phone or "").strip()),
                "origin": origin,
            }
        after = counts(session)
        session.rollback()
        print("timezone", board["timezone"])
        print("updated_label", board["updated_label"])
        print("scope", board["scope"])
        print("operational_total", board["operational_total"])
        for group in ("stages", "history", "payments", "payment_other", "pendings"):
            for item in board[group]:
                print(f"{item['lens']} {item['count']} {item['label']}")
        for item in board["not_tracked"]:
            print(f"not_tracked {item['label']}")
        print("payment_orders", board["payment_orders"])
        print("case", case)
        print("counts_before", before)
        print("counts_after", after)
        print("unchanged", before == after)
    finally:
        session.close()


if __name__ == "__main__":
    main()
