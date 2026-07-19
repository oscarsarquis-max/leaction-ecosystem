#!/usr/bin/env python3
"""Repara squads faltantes nas sprints do lead demo (sem reset completo)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from seed_dev_client import (  # noqa: E402
    DEV_EMAIL,
    get_db_config,
    load_env_files,
    repair_sprint_squads_for_client,
)


def main() -> int:
    load_env_files()
    host = os.getenv("DB_HOST", "127.0.0.1")
    if host not in ("127.0.0.1", "localhost", "::1"):
        if not os.getenv("SEED_DEV_ALLOW"):
            raise SystemExit("Produção: defina SEED_DEV_ALLOW=1")
        if os.getenv("SEED_PROD_CONFIRM") != "paneldx-repair-squads":
            raise SystemExit("Produção: defina SEED_PROD_CONFIRM=paneldx-repair-squads")

    import psycopg2
    from psycopg2.extras import RealDictCursor

    cfg = get_db_config()
    conn = psycopg2.connect(**cfg)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute(
            """
            SELECT id_clie FROM public.ctdi_clie
            WHERE LOWER(TRIM(mail_clie)) = LOWER(TRIM(%s))
            """,
            (DEV_EMAIL,),
        )
        row = cur.fetchone()
        if not row:
            print(f"Lead demo não encontrado: {DEV_EMAIL}")
            return 1
        id_clie = row["id_clie"]
        n = repair_sprint_squads_for_client(cur, id_clie)
        conn.commit()
        print(f"[OK] id_clie={id_clie} — {n} sprint(s) vinculada(s) a squad vazia")
        return 0
    except Exception as exc:
        conn.rollback()
        print(f"[ERRO] {exc}", file=sys.stderr)
        return 1
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
