"""Read-only: print alembic_version for panne_demo and panne. Never print secrets."""
from __future__ import annotations

import json
import ssl

import boto3
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL


def probe(secret_id: str, expect_db: str, expect_user: str) -> None:
    sm = boto3.client("secretsmanager", region_name="us-east-2")
    sec = json.loads(sm.get_secret_value(SecretId=secret_id)["SecretString"])
    assert sec["dbname"] == expect_db, f"dbname={sec['dbname']}"
    assert sec["username"] == expect_user, f"user={sec['username']}"
    url = URL.create(
        "postgresql+psycopg",
        username=sec["username"],
        password=sec["password"],
        host=sec["host"],
        port=int(sec["port"]),
        database=sec["dbname"],
    )
    engine = create_engine(url, connect_args={"sslmode": "require"}, pool_pre_ping=True)
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT version_num FROM alembic_version")).fetchall()
        print(f"{expect_db} versions={[r[0] for r in rows]}")
    engine.dispose()


if __name__ == "__main__":
    probe("panne/demo/db/migrator", "panne_demo", "panne_demo_migrator")
    probe("panne/prod/db/migrator", "panne", "panne_migrator")
