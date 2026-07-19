"""Aplica migration 018 (periodicidade e benefícios na vitrine)."""
import os
from pathlib import Path

from dotenv import load_dotenv
import psycopg2

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / "LeAction_SysF" / ".env")

sql = (ROOT / "migrations" / "018_planos_detalhes_vitrine.sql").read_text(encoding="utf-8")
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
    SELECT column_name FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'dx_planos'
      AND column_name IN ('periodicidade', 'descricao_beneficios')
    ORDER BY column_name;
    """
)
cols = [r[0] for r in cur.fetchall()]
print(f"Colunas vitrine: {cols}")
cur.close()
conn.close()
print("Migration 018 applied.")
