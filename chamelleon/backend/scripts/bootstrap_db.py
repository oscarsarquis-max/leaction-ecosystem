"""Cria o banco chamelleon e aplica o schema via SQLAlchemy."""

from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env")
load_dotenv(BACKEND_DIR.parent / ".env")

from app import create_app
from app.database.models import db

DB_HOST = "127.0.0.1"
DB_PORT = 5432
DB_USER = "postgres"
DB_PASS = "Cmgv6190!@"
DB_NAME = "chamelleon"


def ensure_database() -> None:
    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASS, dbname="postgres"
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DB_NAME,))
    if not cur.fetchone():
        cur.execute(f'CREATE DATABASE "{DB_NAME}"')
        print(f"Banco {DB_NAME} criado.")
    else:
        print(f"Banco {DB_NAME} ja existe.")
    cur.close()
    conn.close()


def create_tables() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        tables = sorted(db.metadata.tables.keys())
        print(f"Tabelas criadas ({len(tables)}): {', '.join(tables)}")


if __name__ == "__main__":
    ensure_database()
    create_tables()
