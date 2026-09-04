-- Cofre de credenciais — banco leaction_vault (isolado de leaction_hub)
-- A chave mestra (VAULT_MASTER_KEY) NUNCA fica neste banco.

CREATE TABLE IF NOT EXISTS vault_admins (
    id SERIAL PRIMARY KEY,
    email TEXT NOT NULL,
    senha_hash TEXT NOT NULL,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT uq_vault_admins_email UNIQUE (email)
);

CREATE TABLE IF NOT EXISTS secrets (
    id SERIAL PRIMARY KEY,
    sistema TEXT NOT NULL,
    tipo TEXT NOT NULL,
    valor_cifrado BYTEA NOT NULL,
    versao INTEGER NOT NULL DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'ativo',
    criado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_por TEXT NOT NULL,
    expira_em TIMESTAMPTZ NULL,
    usuario_email TEXT NULL,
    CONSTRAINT chk_secrets_status CHECK (status IN ('ativo', 'pendente_aplicacao', 'revogado'))
);

CREATE INDEX IF NOT EXISTS idx_secrets_sistema ON secrets (sistema);
CREATE INDEX IF NOT EXISTS idx_secrets_sistema_status ON secrets (sistema, status);

CREATE TABLE IF NOT EXISTS secrets_audit_log (
    id SERIAL PRIMARY KEY,
    secret_id INTEGER NULL REFERENCES secrets(id) ON DELETE SET NULL,
    acao TEXT NOT NULL,
    ator TEXT NOT NULL,
    origem_ip TEXT NULL,
    detalhe JSONB NULL,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_secrets_audit_acao CHECK (
        acao IN ('criado', 'lido', 'rotacionado', 'revogado', 'falha_rotacao', 'falha_criacao')
    )
);

CREATE INDEX IF NOT EXISTS idx_secrets_audit_secret_id ON secrets_audit_log (secret_id);
CREATE INDEX IF NOT EXISTS idx_secrets_audit_criado_em ON secrets_audit_log (criado_em DESC);

CREATE TABLE IF NOT EXISTS sistemas_rotacao (
    sistema TEXT PRIMARY KEY,
    rotation_webhook_url TEXT NULL,
    rotation_secret TEXT NULL,
    suporta_rotacao_automatica BOOLEAN NOT NULL DEFAULT FALSE,
    conta_webhook_url TEXT NULL,
    conta_secret TEXT NULL
);
