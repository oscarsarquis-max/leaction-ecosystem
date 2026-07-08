"""Aplica migração 001 (admin) no banco configurado via env."""
from sqlalchemy import text

from database.models import Base, get_engine

engine = get_engine()
Base.metadata.create_all(engine)

seed = """
INSERT INTO vocabulary_rules (keyword, rule_type, replacement, is_active)
VALUES
    ('metodologias ativas', 'substituir', 'metodologias inov-ativas', 1),
    ('metodologia ativa',   'substituir', 'metodologias inov-ativas', 1),
    ('dor',                 'substituir', 'desafio',                  1),
    ('dores',               'substituir', 'desafios',                 1)
ON CONFLICT (keyword) DO NOTHING
"""

with engine.begin() as conn:
    conn.execute(text(seed))

print("migration_ok")
