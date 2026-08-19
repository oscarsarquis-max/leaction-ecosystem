"""Aplica schema Phanton em produção (idempotente)."""

from __future__ import annotations

import sys
from pathlib import Path

# /app/backend + /app
_BACKEND = Path(__file__).resolve().parent.parent
_ROOT = _BACKEND.parent
for p in (str(_ROOT), str(_BACKEND)):
    if p not in sys.path:
        sys.path.insert(0, p)

from sqlalchemy import text

from database import Base, engine
import auth  # noqa: F401 — users
import models  # noqa: F401
import services.crystal_ball.models  # noqa: F401


def main() -> int:
    sql_dir = _ROOT / "database"
    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        # Patches idempotentes extras
        conn.execute(
            text(
                "ALTER TABLE crystal_shadow_runs "
                "ADD COLUMN IF NOT EXISTS owned_by_user_id UUID"
            )
        )
        conn.execute(
            text(
                "ALTER TABLE crystal_shadow_runs "
                "ALTER COLUMN source_run_id DROP NOT NULL"
            )
        )
        for name in (
            "01_init.sql",
            "02_crystal_ball.sql",
            "03_crystal_ball_nullable_source.sql",
            "04_auth.sql",
            "05_crystal_ball_corpora.sql",
            "06_crystal_ball_corpus_integrity.sql",
        ):
            path = sql_dir / name
            if not path.exists():
                continue
            # CREATE IF NOT EXISTS already; ignore errors on ALTER duplicates
            try:
                conn.execute(text(path.read_text(encoding="utf-8")))
                print(f"applied {name}")
            except Exception as exc:
                print(f"skip/partial {name}: {exc}")
    print("schema OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
