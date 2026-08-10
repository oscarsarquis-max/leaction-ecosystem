#!/usr/bin/env python3
"""Create inove4us_school DB + apply numbered migrations (Hub EC2 / paneldx RDS)."""
from __future__ import annotations

import os
import sys
import urllib.parse
from pathlib import Path

import psycopg2

MIG_DIR = Path(sys.argv[1] if len(sys.argv) > 1 else "/var/www/inove4us-school/infra/db/migrations")


def connect(dbname: str):
    u = os.environ["DATABASE_URL"]
    p = urllib.parse.urlparse(u)
    return psycopg2.connect(
        dbname=dbname,
        user=p.username,
        password=urllib.parse.unquote(p.password or ""),
        host=p.hostname,
        port=p.port or 5432,
        sslmode="require",
    )


def main() -> None:
    conn = connect("postgres")
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM pg_database WHERE datname=%s", ("inove4us_school",))
        if not cur.fetchone():
            print("CREATE DATABASE inove4us_school")
            cur.execute(
                "CREATE DATABASE inove4us_school ENCODING 'UTF8' TEMPLATE template0"
            )
        else:
            print("DB exists: inove4us_school")
    conn.close()

    migs = sorted(
        p
        for p in MIG_DIR.glob("[0-9][0-9][0-9]_*.sql")
        if not p.name.endswith(".down.sql")
    )
    if not migs:
        raise SystemExit(f"No migrations in {MIG_DIR}")

    conn = connect("inove4us_school")
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS school_schema_migrations (
              filename text PRIMARY KEY,
              applied_at timestamptz NOT NULL DEFAULT now()
            )
            """
        )
        for mig in migs:
            cur.execute(
                "SELECT 1 FROM school_schema_migrations WHERE filename=%s",
                (mig.name,),
            )
            if cur.fetchone():
                print(f"skip {mig.name}")
                continue
            print(f"==> {mig.name}")
            sql = mig.read_text(encoding="utf-8")
            cur.execute(sql)
            cur.execute(
                "INSERT INTO school_schema_migrations(filename) VALUES (%s)",
                (mig.name,),
            )
        cur.execute(
            "SELECT count(*) FROM pg_tables WHERE schemaname='public' AND tablename LIKE 'school_%'"
        )
        print("school_tables=", cur.fetchone()[0])
    conn.close()
    print("DONE")


if __name__ == "__main__":
    main()
