"""Registra produto PANELDX_ADDON no banco do Action Hub."""

from pathlib import Path

import psycopg2

ROOT = Path(__file__).resolve().parents[1]
sql = (ROOT / "shared" / "database" / "patch_paneldx_addon.sql").read_text(encoding="utf-8")

conn = psycopg2.connect("postgresql://admin:password123@localhost:5433/leaction_hub")
conn.autocommit = True
cur = conn.cursor()
cur.execute(sql)
cur.execute("SELECT sku, name FROM products WHERE sku = 'PANELDX_ADDON';")
print("Hub product:", cur.fetchone())
cur.close()
conn.close()
print("Patch applied.")
