"""Aplica migration 019 (log de publicações vitrine → ActionHub)."""

import os

from pathlib import Path



from dotenv import load_dotenv

import psycopg2



ROOT = Path(__file__).resolve().parents[1]

load_dotenv(ROOT / "LeAction_SysF" / ".env")



sql = (ROOT / "migrations" / "019_vitrine_publicacoes.sql").read_text(encoding="utf-8")

conn = psycopg2.connect(

    host=os.getenv("DB_HOST", "127.0.0.1"),

    port=os.getenv("DB_PORT", "5432"),

    dbname=os.getenv("DB_NAME", "LeAction_SysF"),

    user=os.getenv("DB_USER", "postgres"),

    password=os.getenv("DB_PASS", ""),

)

conn.autocommit = True

cur = conn.cursor()

cur.execute(sql)

cur.execute(

    """

    SELECT table_name FROM information_schema.tables

    WHERE table_schema = 'public' AND table_name = 'dx_vitrine_publicacoes';

    """

)

row = cur.fetchone()

print(f"Tabela dx_vitrine_publicacoes: {'ok' if row else 'missing'}")

cur.close()

conn.close()

print("Migration 019 applied.")

