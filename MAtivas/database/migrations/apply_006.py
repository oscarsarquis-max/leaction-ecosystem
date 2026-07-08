"""Aplica migração 006 (idempotência de envio de e-mail)."""
from sqlalchemy import text

from database.models import get_engine

engine = get_engine()

statements = [
    """
    CREATE TABLE IF NOT EXISTS roteiro_email_envios (
        id              SERIAL PRIMARY KEY,
        roteiro_id      INT NOT NULL REFERENCES roteiros(id) ON DELETE CASCADE,
        tipo            VARCHAR(20) NOT NULL,
        destinatario    VARCHAR(255) NOT NULL,
        ses_message_id  VARCHAR(255),
        criado_em       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE UNIQUE INDEX IF NOT EXISTS uq_roteiro_email_envio_automatico
        ON roteiro_email_envios (roteiro_id)
        WHERE tipo = 'automatico'
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_roteiro_email_envios_lookup
        ON roteiro_email_envios (roteiro_id, tipo, destinatario, criado_em DESC)
    """,
    """
    ALTER TABLE roteiros
        ADD COLUMN IF NOT EXISTS processando_desde TIMESTAMP NULL
    """,
]

with engine.begin() as conn:
    for stmt in statements:
        conn.execute(text(stmt))

print("migration_006_ok")
