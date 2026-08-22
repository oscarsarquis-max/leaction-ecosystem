from urllib.parse import urlparse, urlunparse

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from tests.conftest import postgres_url

RUNTIME_USER = "panne_runtime"
RUNTIME_PASSWORD = "panne_runtime_test"


def runtime_postgres_url() -> str:
    parsed = urlparse(postgres_url())
    netloc = f"{RUNTIME_USER}:{RUNTIME_PASSWORD}@{parsed.hostname}:{parsed.port}"
    return urlunparse(("postgresql+psycopg", netloc, "/panne", "", "", ""))


def ensure_runtime_role(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                DO $$
                BEGIN
                  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'panne_runtime') THEN
                    CREATE ROLE panne_runtime LOGIN PASSWORD 'panne_runtime_test'
                      NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS;
                  ELSE
                    ALTER ROLE panne_runtime WITH LOGIN PASSWORD 'panne_runtime_test'
                      NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS;
                  END IF;
                END
                $$
                """
            )
        )
        connection.execute(text("GRANT CONNECT ON DATABASE panne TO panne_runtime"))
        connection.execute(text("GRANT USAGE ON SCHEMA public TO panne_runtime"))
        connection.execute(
            text(
                "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES "
                "IN SCHEMA public TO panne_runtime"
            )
        )
        connection.execute(
            text("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO panne_runtime")
        )
        connection.execute(text("REVOKE ALL ON TABLE alembic_version FROM panne_runtime"))


def runtime_engine(admin_engine: Engine) -> Engine:
    ensure_runtime_role(admin_engine)
    return create_engine(runtime_postgres_url(), future=True, pool_size=1)
