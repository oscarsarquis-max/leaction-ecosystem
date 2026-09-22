"""One-off upgrade of the logical database panne. Never prints credentials."""

from __future__ import annotations

import os
import sys

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

RELAX_FORCE_SQL = """
DO $migration$
DECLARE r record;
BEGIN
  FOR r IN
    SELECT c.relname AS rel
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'public' AND c.relkind = 'r' AND c.relforcerowsecurity
  LOOP
    EXECUTE format('ALTER TABLE public.%I NO FORCE ROW LEVEL SECURITY', r.rel);
  END LOOP;
END
$migration$;
"""

RESTORE_FORCE_SQL = """
DO $migration$
DECLARE r record;
BEGIN
  FOR r IN
    SELECT c.relname AS rel
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'public' AND c.relkind = 'r' AND c.relrowsecurity
  LOOP
    EXECUTE format('ALTER TABLE public.%I FORCE ROW LEVEL SECURITY', r.rel);
  END LOOP;
END
$migration$;
"""


def main() -> None:
    database = os.environ.get("PGDATABASE", "panne")
    if database != "panne":
        print("REFUSING_DATABASE")
        raise SystemExit(2)
    url = URL.create(
        "postgresql+psycopg",
        username=os.environ["PGUSER"],
        password=os.environ["PGPASSWORD"],
        host=os.environ["PGHOST"],
        port=int(os.environ["PGPORT"]),
        database=database,
        query={"sslmode": "require"},
    )
    engine = create_engine(url, pool_pre_ping=True)
    config = Config("alembic.ini")
    with engine.connect() as connection:
        current = connection.execute(text("SELECT current_database()")).scalar()
        if current != "panne":
            print("REFUSING_DATABASE")
            raise SystemExit(2)
        before = connection.execute(
            text(
                "SELECT to_regclass('public.alembic_version') IS NOT NULL"
            )
        ).scalar()
        version_before = None
        if before:
            version_before = connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar()
        print("BEFORE", version_before or "absent")
        connection.execute(text(RELAX_FORCE_SQL))
        connection.commit()
        config.attributes["connection"] = connection
        command.upgrade(config, "head")
        connection.execute(text(RESTORE_FORCE_SQL))
        connection.commit()
        version_after = connection.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar()
        print("AFTER", version_after)
        tables = connection.execute(
            text("SELECT count(*) FROM pg_tables WHERE schemaname = 'public'")
        ).scalar()
        orgs = connection.execute(text("SELECT count(*) FROM organization")).scalar()
        users = connection.execute(text("SELECT count(*) FROM app_user")).scalar()
        products = connection.execute(
            text("SELECT count(*) FROM technical_product")
        ).scalar()
        print("TABLES", int(tables or 0))
        print("COUNT organization", int(orgs or 0))
        print("COUNT app_user", int(users or 0))
        print("COUNT technical_product", int(products or 0))
        rls = connection.execute(
            text(
                """
                SELECT count(*) AS tables,
                       count(*) FILTER (WHERE NOT c.relrowsecurity OR NOT c.relforcerowsecurity) AS weak
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = 'public' AND c.relkind = 'r'
                """
            )
        ).one()
        print("RLS_TABLES", int(rls.tables), "WITHOUT_RLS_OR_FORCE", int(rls.weak))
    print("MIGRATION_OK")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("MIGRATION_FAIL", type(exc).__name__)
        sys.exit(1)
