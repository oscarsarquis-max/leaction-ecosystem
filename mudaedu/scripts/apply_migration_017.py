"""Aplica migration 017 (dx_planos, dx_contratos — CRM)."""
import os
from pathlib import Path

from dotenv import load_dotenv
import psycopg2

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / "LeAction_SysF" / ".env")

sql = (ROOT / "migrations" / "017_crm_contratos.sql").read_text(encoding="utf-8")
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
cur.execute("SELECT COUNT(*) FROM public.dx_planos;")
planos = cur.fetchone()[0]
cur.execute(
    """
    SELECT table_name FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name IN ('dx_planos', 'dx_contratos')
    ORDER BY table_name;
    """
)
tables = [r[0] for r in cur.fetchall()]
print(f"Tabelas CRM: {tables}")
print(f"Planos seed: {planos}")
cur.close()
conn.close()
print("Migration 017 applied.")
