"""Compara amostras de rubricas canônicas vs setoriais."""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from app import create_app
from app.database.models import AssessmentItem


def is_sector(item: AssessmentItem) -> bool:
    meta = item.item_metadata or {}
    return meta.get("dimension_type") == "sector" or item.axis.startswith("TA")


def main() -> None:
    app = create_app()
    with app.app_context():
        items = AssessmentItem.query.filter_by(framework_id="telecomunicacoes-v1").all()
        canon = next(i for i in items if not is_sector(i))
        sector = next(i for i in items if is_sector(i))
        for label, item in [("CANONICAL", canon), ("SECTOR", sector)]:
            print(f"\n=== {label}: {item.axis[:70]} ===")
            for opt in item.options or []:
                print(
                    json.dumps(
                        {
                            "grad": opt.get("grad_rubr"),
                            "label": opt.get("label_rubr"),
                            "desc": (opt.get("desc_rubr") or "")[:80],
                        },
                        ensure_ascii=False,
                    )
                )


if __name__ == "__main__":
    main()
