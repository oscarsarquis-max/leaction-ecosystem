"""Aplica migração 003 (assets.logo) no banco configurado via env."""
from sqlalchemy import text

from database.models import get_engine

engine = get_engine()

sql_path = __file__.replace("apply_003.py", "003_logo_asset.sql")
with open(sql_path, encoding="utf-8") as f:
    sql = f.read()

with engine.begin() as conn:
    for stmt in sql.split(";"):
        s = stmt.strip()
        if s and not s.startswith("--"):
            conn.execute(text(s))

print("migration_003_ok")
