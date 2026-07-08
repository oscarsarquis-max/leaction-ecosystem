"""Aplica migração 002 (ui_content) no banco configurado via env."""
from sqlalchemy import text

from database.models import Base, UiContent, get_engine

engine = get_engine()
Base.metadata.create_all(engine)

sql_path = __file__.replace("apply_002.py", "002_ui_content.sql")
with open(sql_path, encoding="utf-8") as f:
    sql = f.read()

with engine.begin() as conn:
    for stmt in sql.split(";"):
        s = stmt.strip()
        if s and not s.startswith("--"):
            conn.execute(text(s))

print("migration_002_ok")
