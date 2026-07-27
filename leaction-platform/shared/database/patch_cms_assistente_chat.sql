-- CMS Assistente Chat — árvore de decisão (Nina / satélites)
-- Banco: leaction_hub
-- MVP: no máximo 1 rascunho + 1 publicado por sistema_destino (sem tabela de histórico)

CREATE TABLE IF NOT EXISTS cms_assistente_chat (
    id SERIAL PRIMARY KEY,
    sistema_destino VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'rascunho',
    tree JSONB NOT NULL,
    publicado_em TIMESTAMPTZ NULL,
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_por TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_cms_assistente_chat_status CHECK (status IN ('rascunho', 'publicado')),
    CONSTRAINT chk_cms_assistente_chat_destino CHECK (
        sistema_destino IN (
            'hub-publico',
            'actionhub',
            'inove4us',
            'paneldx',
            'todos'
        )
    ),
    CONSTRAINT uq_cms_assistente_chat_destino_status UNIQUE (sistema_destino, status)
);

CREATE INDEX IF NOT EXISTS idx_cms_assistente_chat_sistema_destino
    ON cms_assistente_chat (sistema_destino);

CREATE INDEX IF NOT EXISTS idx_cms_assistente_chat_status
    ON cms_assistente_chat (status);

CREATE INDEX IF NOT EXISTS idx_cms_assistente_chat_publicado
    ON cms_assistente_chat (status, publicado_em DESC NULLS LAST)
    WHERE status = 'publicado';
