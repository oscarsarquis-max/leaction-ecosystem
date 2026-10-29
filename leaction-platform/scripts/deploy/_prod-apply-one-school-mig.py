#!/usr/bin/env python3
"""Apply a single School migration if not yet in school_schema_migrations."""
from __future__ import annotations

import sys
from pathlib import Path

import psycopg2

MIG_NAME = sys.argv[1] if len(sys.argv) > 1 else "036_school_roteiro_respostas.sql"
MIG_PATH = Path("/var/www/inove4us-school/infra/db/migrations") / MIG_NAME


def load(path: str) -> dict:
    env = {}
    p = Path(path)
    if not p.exists():
        return env
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def main() -> None:
    school = load("/var/www/inove4us-school/.env")
    if not MIG_PATH.exists():
        # allow override path as argv2
        alt = Path(sys.argv[2]) if len(sys.argv) > 2 else None
        if alt and alt.exists():
            path = alt
        else:
            raise SystemExit(f"missing {MIG_PATH}")
    else:
        path = MIG_PATH

    conn = psycopg2.connect(
        dbname=school.get("DB_NAME") or "inove4us_school",
        user=school["DB_USER"],
        password=school.get("DB_PASS") or school.get("DB_PASSWORD"),
        host=school["DB_HOST"],
        port=int(school.get("DB_PORT") or 5432),
        sslmode=school.get("DB_SSLMODE") or "require",
    )
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            "CREATE TABLE IF NOT EXISTS school_schema_migrations (filename text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())"
        )
        cur.execute(
            "SELECT 1 FROM school_schema_migrations WHERE filename=%s", (MIG_NAME,)
        )
        if cur.fetchone():
            print(f"skip {MIG_NAME} (already applied)")
            return
        print(f"==> applying {MIG_NAME} from {path}")
        cur.execute(path.read_text(encoding="utf-8"))
        cur.execute(
            "INSERT INTO school_schema_migrations(filename) VALUES (%s)", (MIG_NAME,)
        )
        print("OK", MIG_NAME)
    conn.close()


if __name__ == "__main__":
    main()
