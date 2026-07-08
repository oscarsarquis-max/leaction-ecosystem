-- =====================================================================
-- MAtivas - Migração 001: Área administrativa
-- ---------------------------------------------------------------------
-- Cria tabelas para autenticação admin e regras de vocabulário.
--
-- Aplicar no PostgreSQL local:
--   psql -d MAtivas -U postgres -f database/migrations/001_admin_area.sql
--
-- Ou via Python (na raiz do projeto):
--   python -c "from database.models import Base, get_engine; Base.metadata.create_all(get_engine())"
-- =====================================================================

-- ---------------------------------------------------------------------
-- Tabela: admin_users
-- Usuários com acesso à área administrativa.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS admin_users (
    id              SERIAL PRIMARY KEY,
    username        VARCHAR(100) UNIQUE NOT NULL,
    password_hash   VARCHAR(255) NOT NULL
);

-- ---------------------------------------------------------------------
-- Tabela: vocabulary_rules
-- Regras de vocabulário (bloqueada, substituir, obrigatoria).
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS vocabulary_rules (
    id              SERIAL PRIMARY KEY,
    keyword         VARCHAR(100) NOT NULL UNIQUE,
    rule_type       VARCHAR(50) NOT NULL,
    replacement     VARCHAR(255),
    is_active       INTEGER NOT NULL DEFAULT 1
);

-- Índices de apoio
CREATE INDEX IF NOT EXISTS idx_vocabulary_rules_keyword   ON vocabulary_rules (keyword);
CREATE INDEX IF NOT EXISTS idx_vocabulary_rules_rule_type ON vocabulary_rules (rule_type);
CREATE INDEX IF NOT EXISTS idx_vocabulary_rules_active    ON vocabulary_rules (is_active);

-- Regras iniciais (guardrails de negócio)
INSERT INTO vocabulary_rules (keyword, rule_type, replacement, is_active)
VALUES
    ('metodologias ativas', 'substituir', 'metodologias inov-ativas', 1),
    ('metodologia ativa',   'substituir', 'metodologias inov-ativas', 1),
    ('dor',                 'substituir', 'desafio',                  1),
    ('dores',               'substituir', 'desafios',                 1)
ON CONFLICT (keyword) DO NOTHING;
