"""Detalha diferenças visuais entre rubricas canônicas e setoriais."""
from __future__ import annotations

import os
import sys
from collections import Counter

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
        for kind, subset in [
            ("canonical", [i for i in items if not is_sector(i)]),
            ("sector", [i for i in items if is_sector(i)]),
        ]:
            labels = Counter()
            max_label = 0
            same = 0
            for item in subset:
                for opt in item.options or []:
                    label = (opt.get("label_rubr") or opt.get("text") or "").strip()
                    desc = (opt.get("desc_rubr") or opt.get("description") or "").strip()
                    labels[label] += 1
                    max_label = max(max_label, len(label))
                    if label == desc:
                        same += 1
            print(f"\n=== {kind} ({len(subset)} questions) ===")
            print(f"max label len: {max_label}")
            print(f"label==desc count: {same}")
            print("top labels:", labels.most_common(8))


if __name__ == "__main__":
    main()
