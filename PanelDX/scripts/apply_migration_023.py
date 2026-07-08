"""Aplica migration 023 (add-ons de licenças — tipo_plano e dx_contratos_addons)."""

import os
from pathlib import Path

from dotenv import load_dotenv
import psycopg2

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / "LeAction_SysF" / ".env")

sql = (ROOT / "migrations" / "023_planos_adicionais_addons.sql").read_text(encoding="utf-8")

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
    WHERE table_schema = 'public'
      AND table_name = 'dx_planos'
      AND column_name = 'tipo_plano';
    """
)
row = cur.fetchone()
print(f"Coluna dx_planos.tipo_plano: {'ok' if row else 'missing'}")
cur.execute(
    """
    SELECT to_regclass('public.dx_contratos_addons');
    """
)
tbl = cur.fetchone()
print(f"Tabela dx_contratos_addons: {'ok' if tbl and tbl[0] else 'missing'}")
cur.execute(
    """
    SELECT id, nome FROM public.dx_planos
    WHERE tipo_plano = 'addon'
    ORDER BY id ASC
    LIMIT 3;
    """
)
addons = cur.fetchall()
print(f"Planos add-on seed: {addons}")
cur.close()
conn.close()
print("Migration 023 applied.")
