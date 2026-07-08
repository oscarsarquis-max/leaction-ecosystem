"""Aplica migração 004 (rótulos do logotipo no admin)."""
from sqlalchemy import text

from database.models import get_engine

engine = get_engine()

sql_path = __file__.replace("apply_004.py", "004_ui_labels_logo.sql")
with open(sql_path, encoding="utf-8") as f:
    sql = f.read()

with engine.begin() as conn:
    for stmt in sql.split(";"):
        s = stmt.strip()
        if s and not s.startswith("--"):
            conn.execute(text(s))

print("migration_004_ok")
