"""Aplica migração 007 (curtida do roteiro)."""
from sqlalchemy import text

from database.models import get_engine

engine = get_engine()

statements = [
    """
    ALTER TABLE roteiros
        ADD COLUMN IF NOT EXISTS curtido_em TIMESTAMP NULL
    """,
]

with engine.begin() as conn:
    for stmt in statements:
        conn.execute(text(stmt))

print("migration_007_ok")
