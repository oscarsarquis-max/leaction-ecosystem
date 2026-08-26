-- Gestão de Identidade — catálogo central de perfis para satélites
-- Banco: leaction_hub
-- Não é autenticação: login permanece em cada satélite.

CREATE TABLE IF NOT EXISTS identidade_usuarios (
    id SERIAL PRIMARY KEY,
    nome TEXT NOT NULL,
    email TEXT NOT NULL,
    sistema TEXT NOT NULL,
    nivel TEXT NOT NULL,
    funcao TEXT NULL,
    status TEXT NOT NULL DEFAULT 'ativo',
    criado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_identidade_usuarios_nivel CHECK (
        nivel IN ('admin', 'gestor_produtivo', 'usuario_executor')
    ),
    CONSTRAINT chk_identidade_usuarios_status CHECK (status IN ('ativo', 'inativo')),
    CONSTRAINT uq_identidade_usuarios_sistema_email UNIQUE (sistema, email)
);

CREATE INDEX IF NOT EXISTS idx_identidade_usuarios_sistema
    ON identidade_usuarios (sistema);

CREATE INDEX IF NOT EXISTS idx_identidade_usuarios_sistema_status
    ON identidade_usuarios (sistema, status);

CREATE TABLE IF NOT EXISTS identidade_funcoes (
    id SERIAL PRIMARY KEY,
    sistema TEXT NOT NULL,
    nome TEXT NOT NULL,
    nivel_associado TEXT NOT NULL,
    permissoes JSONB NOT NULL DEFAULT '[]'::jsonb,
    CONSTRAINT chk_identidade_funcoes_nivel CHECK (
        nivel_associado IN ('admin', 'gestor_produtivo', 'usuario_executor')
    ),
    CONSTRAINT uq_identidade_funcoes_sistema_nome UNIQUE (sistema, nome)
);

CREATE INDEX IF NOT EXISTS idx_identidade_funcoes_sistema
    ON identidade_funcoes (sistema);

CREATE TABLE IF NOT EXISTS identidade_permissoes (
    id SERIAL PRIMARY KEY,
    sistema TEXT NOT NULL,
    chave TEXT NOT NULL,
    descricao TEXT NOT NULL DEFAULT '',
    CONSTRAINT uq_identidade_permissoes_sistema_chave UNIQUE (sistema, chave)
);

CREATE INDEX IF NOT EXISTS idx_identidade_permissoes_sistema
    ON identidade_permissoes (sistema);
