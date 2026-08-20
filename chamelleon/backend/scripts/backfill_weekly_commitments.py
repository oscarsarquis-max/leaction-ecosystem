"""Migra OperationalSite.weekly_goals (JSONB legado) → WeeklyCommitment.

Idempotente: se já existir qualquer compromisso para (tenant, site, data),
pula aquele par. Não apaga weekly_goals.
"""

from __future__ import annotations

import os
import sys
from datetime import date, datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

from app import create_app
from app.database.models import db
from app.models.operational_models import OperationalSite, WeeklyCommitment


def _parse_day(value: object) -> date | None:
    if not value:
        return None
    try:
        text = str(value).strip()
        if "T" in text:
            return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def main() -> int:
    app = create_app()
    with app.app_context():
        sites = OperationalSite.query.all()
        sites_processed = 0
        created = 0
        skipped_existing = 0
        skipped_empty = 0

        for site in sites:
            goals = site.weekly_goals if isinstance(site.weekly_goals, dict) else {}
            if not goals:
                continue
            sites_processed += 1

            for raw_day, raw_text in goals.items():
                day = _parse_day(raw_day)
                text = str(raw_text or "").strip()
                if not day or not text:
                    skipped_empty += 1
                    continue

                exists = (
                    WeeklyCommitment.query.filter_by(
                        tenant_id=site.tenant_id,
                        operational_site_id=site.id,
                        commitment_date=day,
                    )
                    .limit(1)
                    .first()
                )
                if exists:
                    skipped_existing += 1
                    continue

                db.session.add(
                    WeeklyCommitment(
                        tenant_id=site.tenant_id,
                        operational_site_id=site.id,
                        commitment_date=day,
                        description=text,
                        sequence=0,
                        is_completed=None,
                    )
                )
                created += 1

        db.session.commit()
        print(
            "backfill_weekly_commitments: "
            f"sites={sites_processed} created={created} "
            f"skipped_existing={skipped_existing} skipped_empty={skipped_empty}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
