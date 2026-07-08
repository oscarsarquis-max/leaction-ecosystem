"""Aplica migration 024 (Portal do Parceiro — consultores, contratos e demandas)."""

import os
from pathlib import Path

from dotenv import load_dotenv
import psycopg2

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / "LeAction_SysF" / ".env")

sql = (ROOT / "migrations" / "024_gestao_consultores.sql").read_text(encoding="utf-8")

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

checks = [
    ("dx_consultores", "SELECT to_regclass('public.dx_consultores');"),
    ("dx_demandas_consultor", "SELECT to_regclass('public.dx_demandas_consultor');"),
    (
        "dx_contratos.id_consultor_origem",
        """
        SELECT column_name FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'dx_contratos'
          AND column_name = 'id_consultor_origem';
        """,
    ),
    (
        "dx_planos.direito_consultoria_tecnica",
        """
        SELECT column_name FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'dx_planos'
          AND column_name = 'direito_consultoria_tecnica';
        """,
    ),
]

for label, query in checks:
    cur.execute(query)
    row = cur.fetchone()
    ok = bool(row and row[0])
    print(f"{label}: {'ok' if ok else 'missing'}")

cur.close()
conn.close()
print("Migration 024 applied.")
