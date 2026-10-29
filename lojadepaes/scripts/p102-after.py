"""Leitura depois da marcação. Não grava e não imprime contato."""

import json

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_engine
from app.domain.attendance import list_attendance
from app.domain.order_board import managerial_board
from app.domain.production_agenda import production_agenda
from app.schemas.admin import OrderListQuery

MARKED = (
    "LP42E1CA0A1A",
    "LP72EC1CB055",
    "LP7968212021",
    "LP242E207138",
    "LP18AE314D6C",
    "LPB0DA668D3F",
)
LEFT = ("LP87D4BCF4E1", "LP23FF6F00E2", "SD51A91EFF")


def _visible(session, settings, reference: str, lens: str | None) -> bool:
    payload = list_attendance(
        session,
        settings,
        OrderListQuery(reference=reference, status="all", lens=lens, page=1, page_size=20),
    )
    return reference in {item.public_reference for item in payload.items}


def main() -> None:
    session = Session(get_engine())
    try:
        settings = get_settings()
        board, _keys = managerial_board(session, settings)
        commercial = list_attendance(
            session, settings, OrderListQuery(status="all", page=1, page_size=50)
        )
        audit = list_attendance(
            session, settings, OrderListQuery(lens="audit:tests", page=1, page_size=50)
        )
        october = production_agenda(session, settings, 2026, 10)
        september = production_agenda(session, settings, 2026, 9)
        agenda_refs = set()
        for month in (october, september):
            for day in month["days"]:
                for key in ("open", "historical", "pending", "cancelled"):
                    for entry in day[key]:
                        agenda_refs.add(entry["reference"])
            for entry in month["undated"]:
                agenda_refs.add(entry["reference"])
        print(
            json.dumps(
                {
                    "operational_total": board["operational_total"],
                    "excluded_tests": board["excluded_tests"],
                    "excluded_holding_capacity": board["excluded_holding_capacity"],
                    "commercial_total": commercial.total,
                    "audit_total": audit.total,
                    "marked_in_commercial": {
                        reference: _visible(session, settings, reference, None) for reference in MARKED
                    },
                    "marked_in_audit": {
                        reference: _visible(session, settings, reference, "audit:tests")
                        for reference in MARKED
                    },
                    "left_in_commercial": {
                        reference: _visible(session, settings, reference, None) for reference in LEFT
                    },
                    "left_in_audit": {
                        reference: _visible(session, settings, reference, "audit:tests")
                        for reference in LEFT
                    },
                    "left_in_agenda": sorted(set(LEFT) & agenda_refs),
                    "marked_in_agenda": sorted(set(MARKED) & agenda_refs),
                    "october_order_days": sum(1 for day in october["days"] if day["orders"]),
                    "october_orders": sum(day["orders"] for day in october["days"]),
                    "october_filled": [
                        {
                            "date": day["date"],
                            "orders": day["orders"],
                            "bread_units": day["bread_units"],
                            "open": [entry["reference"] for entry in day["open"]],
                            "historical": [entry["reference"] for entry in day["historical"]],
                            "pending": [entry["reference"] for entry in day["pending"]],
                        }
                        for day in october["days"]
                        if day["orders"] or day["pending_requests"]
                    ],
                    "undated": [entry["reference"] for entry in october["undated"]],
                },
                ensure_ascii=False,
            )
        )
    finally:
        session.close()


if __name__ == "__main__":
    main()
