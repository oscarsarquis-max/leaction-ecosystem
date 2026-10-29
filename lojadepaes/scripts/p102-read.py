"""Leitura 102 no código já publicado. Não grava."""

import json
import unicodedata

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_engine
from app.domain.order_board import managerial_board
from app.core.config import get_settings
from app.models.date_requests import DateRequest
from app.models.orders import Order

EXACT = {"rastro", "oscar"}


def folded(value: str | None) -> str:
    raw = unicodedata.normalize("NFKD", value or "")
    ascii_name = "".join(char for char in raw if not unicodedata.combining(char))
    return " ".join(ascii_name.casefold().split())


def kind(name: str | None) -> str:
    text = folded(name)
    if text in EXACT:
        return "exact"
    if set(text.split()) & EXACT:
        return "ambiguous"
    return "other"


def main() -> None:
    session = Session(get_engine())
    try:
        settings = get_settings()
        board, _keys = managerial_board(session, settings)
        exact = []
        ambiguous = []
        holding = []
        for order in session.scalars(select(Order)):
            label = kind(order.customer_name)
            if label == "other":
                continue
            row = {
                "source": "order",
                "reference": order.public_reference,
                "name": folded(order.customer_name),
                "status": order.status,
                "holds_capacity": bool(order.holds_capacity),
                "production_date": order.production_local_date.isoformat()
                if order.production_local_date
                else None,
            }
            if label == "exact":
                exact.append(row)
                if order.holds_capacity:
                    holding.append(order.public_reference)
            else:
                ambiguous.append(row)
        for request in session.scalars(select(DateRequest)):
            label = kind(request.customer_name)
            if label == "other":
                continue
            row = {
                "source": "date_request",
                "reference": f"SD{str(request.id).replace('-', '')[:8].upper()}",
                "name": folded(request.customer_name),
                "status": request.status,
                "holds_capacity": False,
                "production_date": request.desired_date.isoformat(),
            }
            if label == "exact":
                exact.append(row)
            else:
                ambiguous.append(row)
        print(
            json.dumps(
                {
                    "operational_total": board["operational_total"],
                    "exact": exact,
                    "ambiguous": ambiguous,
                    "still_holding_capacity": holding,
                },
                ensure_ascii=False,
            )
        )
    finally:
        session.close()


if __name__ == "__main__":
    main()
