"""Aplica migration 016 (dx_kr_id em ctdi_okr_atividades)."""
import os
from pathlib import Path

from dotenv import load_dotenv
import psycopg2

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / "LeAction_SysF" / ".env")

sql = (ROOT / "migrations" / "016_atividades_vinculo_dx_kr.sql").read_text(encoding="utf-8")
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
    SELECT column_name, is_nullable
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'ctdi_okr_atividades'
      AND column_name = 'dx_kr_id'
    """
)
row = cur.fetchone()
print(f"ctdi_okr_atividades.dx_kr_id: {'OK' if row else 'MISSING'} nullable={row[1] if row else 'n/a'}")
cur.close()
conn.close()
print("Migration 016 applied.")
