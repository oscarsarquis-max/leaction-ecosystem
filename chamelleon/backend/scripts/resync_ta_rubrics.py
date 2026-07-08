"""Re-normaliza rubricas das questões TA (dimensão setorial) para padrão PanelDX.

Uso:
  python scripts/resync_ta_rubrics.py [--framework-id educacao-v1]
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from app import create_app
from app.data.rubric_patterns import (
    normalize_sector_question_options,
    repair_rubric_options,
    validate_rubric_options,
)
from app.database.models import AssessmentItem, db


def is_ta_item(item: AssessmentItem) -> bool:
    meta = item.item_metadata or {}
    if meta.get("dimension_type") == "sector":
        return True
    return item.axis.startswith("TA")


def resync(framework_id: str) -> int:
    updated = 0
    items = AssessmentItem.query.filter_by(framework_id=framework_id).all()
    for item in items:
        if not is_ta_item(item):
            continue
        meta = item.item_metadata or {}
        prefu = str(meta.get("prefu_ques") or "").upper()
        temporal_key = "future" if prefu == "F" else "present"
        options = repair_rubric_options(item.options or [], temporal_key=temporal_key)
        validate_rubric_options(options)
        item.options = options
        updated += 1
    db.session.commit()
    return updated


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--framework-id", default="educacao-v1")
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        count = resync(args.framework_id)
        print(f"Questões TA atualizadas: {count} (framework '{args.framework_id}').")


if __name__ == "__main__":
    main()
