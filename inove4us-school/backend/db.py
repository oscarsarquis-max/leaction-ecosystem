"""Conexão PostgreSQL — banco dedicado `inove4us_school` (isolado do B2C)."""
from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Iterator

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()


def _dsn() -> dict[str, Any]:
    return {
        "host": os.getenv("DB_HOST", "127.0.0.1"),
        "port": int(os.getenv("DB_PORT", "5434")),
        "dbname": os.getenv("DB_NAME", "inove4us_school"),
        "user": os.getenv("DB_USER", "admin"),
        "password": os.getenv("DB_PASS", "password123"),
        "sslmode": os.getenv("DB_SSLMODE", "prefer"),
    }


@contextmanager
def get_conn() -> Iterator[Any]:
    conn = psycopg2.connect(**_dsn())
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def ping() -> bool:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            return cur.fetchone()[0] == 1
