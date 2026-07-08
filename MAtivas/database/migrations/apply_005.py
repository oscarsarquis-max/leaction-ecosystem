"""Aplica migração 005 (controle de envio automático de e-mail do roteiro)."""
from sqlalchemy import text

from database.models import get_engine

engine = get_engine()

statements = [
    """
    ALTER TABLE roteiros
        ADD COLUMN IF NOT EXISTS email_automatico_enviado_em TIMESTAMP NULL
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_roteiros_email_auto_enviado
        ON roteiros (email_automatico_enviado_em)
    """,
]

with engine.begin() as conn:
    for stmt in statements:
        conn.execute(text(stmt))

print("migration_005_ok")
