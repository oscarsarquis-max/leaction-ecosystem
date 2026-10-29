"""Inventário 102. Sem --apply não grava. Não imprime contato."""

import json
import sys

from sqlalchemy.orm import Session

from app.db.session import get_engine
from app.domain.managerial_exclusion import classify_tests, exclude_references
from app.domain.order_board import managerial_board
from app.core.config import get_settings


def _public(found: dict) -> dict:
    return {
        "exact": found["exact"],
        "ambiguous": found["ambiguous"],
        "still_holding_capacity": found["still_holding_capacity"],
    }


REVIEWED = (
    "LP42E1CA0A1A",
    "LP72EC1CB055",
    "LP7968212021",
    "LP242E207138",
    "LP18AE314D6C",
    "LPB0DA668D3F",
)


def main() -> None:
    session = Session(get_engine())
    try:
        settings = get_settings()
        before, _keys = managerial_board(session, settings)
        found = classify_tests(session)
        report = {
            "before_operational_total": before["operational_total"],
            "inventory": _public(found),
            "applied": False,
        }
        if "--apply-reviewed" in sys.argv:
            applied = exclude_references(session, list(REVIEWED), author_ref="prompt-102")
            session.commit()
            after, _keys = managerial_board(session, settings)
            report["applied"] = True
            report["applied_reviewed"] = {
                "marked": applied["marked"],
                "missing": applied["missing"],
                "still_holding_capacity": applied["still_holding_capacity"],
            }
            report["after_operational_total"] = after["operational_total"]
            report["excluded_orders"] = applied["excluded_orders"]
        print(json.dumps(report, ensure_ascii=False))
    finally:
        session.close()


if __name__ == "__main__":
    main()
