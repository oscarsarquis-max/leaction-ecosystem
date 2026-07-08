"""Insere a questão universal faltante DA/dc Futuro nos frameworks existentes (89 → 90)."""

from __future__ import annotations

import os
import sys
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from app import create_app
from app.data.legacy_quest_loader import (
    DA_DC_FUTURE_QUESTION_TEXT,
    _build_da_dc_future_gap_item,
    _load_from_legacy_database,
)
from app.database.models import AssessmentItem, Framework, db


def _load_rubrics_map() -> dict:
    items = _load_from_legacy_database(for_new_framework=False)
    if not items:
        return {}
    gap = _build_da_dc_future_gap_item({157: []})
    # Re-load with rubrics via loader internals — use gap item from full load
    for item in items:
        meta = item.get("metadata") or {}
        if meta.get("dimension_key") == "DA" and meta.get("domain_key") == "dc" and meta.get("prefu_ques") == "F":
            return item
    return gap


def main() -> int:
    app = create_app()
    with app.app_context():
        template = None
        loaded = _load_from_legacy_database(for_new_framework=False) or []
        for item in loaded:
            meta = item.get("metadata") or {}
            if (
                meta.get("dimension_key") == "DA"
                and meta.get("domain_key") == "dc"
                and meta.get("prefu_ques") == "F"
            ):
                template = item
                break
        if not template:
            template = _build_da_dc_future_gap_item({})

        inserted = 0
        for framework in Framework.query.all():
            existing = AssessmentItem.query.filter_by(framework_id=framework.id).all()
            has_future = any(
                (i.item_metadata or {}).get("dimension_key") == "DA"
                and (i.item_metadata or {}).get("domain_key") == "dc"
                and (i.item_metadata or {}).get("prefu_ques") == "F"
                for i in existing
            )
            if has_future:
                continue

            meta = dict(template.get("metadata") or {})
            db.session.add(
                AssessmentItem(
                    id=uuid.uuid4(),
                    framework_id=framework.id,
                    axis=template["axis"],
                    question_text=template.get("question_text") or DA_DC_FUTURE_QUESTION_TEXT,
                    question_type=template.get("question_type") or "multiple_choice",
                    options=template.get("options") or [],
                    item_metadata=meta,
                )
            )
            inserted += 1
            print(f"[+] {framework.id}: DA/dc Futuro inserida")

        db.session.commit()
        print(f"Concluído: {inserted} framework(s) atualizado(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
