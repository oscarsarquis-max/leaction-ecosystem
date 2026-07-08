"""Audita conformidade das rubricas (canônicas + setoriais) com padrão PanelDX."""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from app import create_app
from app.database.models import AssessmentItem


def audit_item(item: AssessmentItem) -> dict:
    meta = item.item_metadata or {}
    options = item.options or []
    issues = []
    if len(options) != 6:
        issues.append(f"options_count={len(options)} (expected 6)")
    for i, opt in enumerate(options):
        label = (opt.get("label_rubr") or opt.get("text") or opt.get("label") or "").strip()
        desc = (opt.get("desc_rubr") or opt.get("description") or opt.get("desc") or "").strip()
        grad = opt.get("grad_rubr", opt.get("weight"))
        if not label:
            issues.append(f"opt[{i}] missing label")
        if not desc:
            issues.append(f"opt[{i}] missing desc")
        if label and desc and label == desc and len(label) > 40:
            issues.append(f"opt[{i}] label==long_text")
        if grad is None:
            issues.append(f"opt[{i}] missing grad/weight")
    return {
        "axis": item.axis[:60],
        "type": meta.get("dimension_type", "canonical"),
        "options": len(options),
        "issues": issues,
        "sample": options[0] if options else None,
    }


def main() -> None:
    app = create_app()
    with app.app_context():
        items = AssessmentItem.query.filter_by(framework_id="telecomunicacoes-v1").all()
        bad = []
        for item in items:
            result = audit_item(item)
            if result["issues"]:
                bad.append(result)

        print(f"Total items: {len(items)}")
        print(f"Non-compliant: {len(bad)}")
        for row in bad[:15]:
            print(f"\n[{row['type']}] {row['axis']}")
            print(f"  issues: {row['issues']}")
            if row["sample"]:
                print(f"  sample: {json.dumps(row['sample'], ensure_ascii=False)[:200]}")


if __name__ == "__main__":
    main()
