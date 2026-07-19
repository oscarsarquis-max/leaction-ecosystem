"""Aplica migration 015 (nivel_implementacao + meta_cliente)."""
import os
from pathlib import Path

from dotenv import load_dotenv
import psycopg2

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / "LeAction_SysF" / ".env")

sql = (ROOT / "migrations" / "015_okr_nivel_implementacao.sql").read_text(encoding="utf-8")
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
for table, col in [
    ("dx_objetivos", "nivel_implementacao"),
    ("ctdi_okr_objetivos_dt", "nivel_implementacao"),
    ("ctdi_okr_krs", "meta_cliente"),
]:
    cur.execute(
        """
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s AND column_name = %s
        """,
        (table, col),
    )
    ok = "OK" if cur.fetchone() else "MISSING"
    print(f"{table}.{col}: {ok}")
cur.close()
conn.close()
print("Migration 015 applied.")
