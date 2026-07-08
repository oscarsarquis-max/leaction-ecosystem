"""Verifica estrutura Presente vs Futuro nas canônicas."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from app import create_app
from app.database.models import AssessmentItem


def main() -> None:
    app = create_app()
    with app.app_context():
        items = AssessmentItem.query.filter_by(framework_id="telecomunicacoes-v1").all()
        for prefu in ("Presente", "Futuro"):
            subset = [i for i in items if f"({prefu})" in i.axis]
            counts = {}
            for item in subset:
                n = len(item.options or [])
                counts[n] = counts.get(n, 0) + 1
            sample = subset[0] if subset else None
            print(f"\n{prefu}: {len(subset)} items, option counts: {counts}")
            if sample:
                print(f"  sample axis: {sample.axis}")
                for opt in sample.options or []:
                    print(
                        f"    grad={opt.get('grad_rubr')} label={opt.get('label_rubr')!r} "
                        f"desc={opt.get('desc_rubr','')[:50]!r}"
                    )


if __name__ == "__main__":
    main()
