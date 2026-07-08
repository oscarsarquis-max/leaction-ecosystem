"""Re-sincroniza rubricas universais na base Chamelleon a partir de ctdi_rubricas (PanelDX).

Uso (na pasta backend):
  python scripts/resync_rubrics_from_paneldx.py [--framework-id telecomunicacoes-v1]
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from app import create_app
from app.data.legacy_quest_loader import load_universal_assessment_items
from app.data.rubric_patterns import validate_rubric_options
from app.database.models import AssessmentItem, db


def resync(framework_id: str) -> int:
    catalog = load_universal_assessment_items()
    by_axis = {item["axis"]: item for item in catalog}
    updated = 0

    items = AssessmentItem.query.filter_by(framework_id=framework_id).all()
    for item in items:
        meta = item.item_metadata or {}
        if meta.get("dimension_type") == "sector":
            continue
        source = by_axis.get(item.axis)
        if not source:
            continue
        options = source.get("options") or []
        validate_rubric_options(options)
        item.options = options
        updated += 1

    db.session.commit()
    return updated


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--framework-id", default="telecomunicacoes-v1")
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        count = resync(args.framework_id)
        print(f"Rubricas atualizadas em {count} questão(ões) do framework '{args.framework_id}'.")


if __name__ == "__main__":
    main()
