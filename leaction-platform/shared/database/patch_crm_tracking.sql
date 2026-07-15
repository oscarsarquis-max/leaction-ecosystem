-- CRM Visitas / PLG Tracking (Action Hub = provedor central)
-- Bancos: leaction_hub

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS crm_sessoes (
    id_sessao UUID PRIMARY KEY,
    sistema_origem VARCHAR(64) NOT NULL,
    id_usuario_origem INTEGER NULL,
    ip_hash VARCHAR(128) NULL,
    user_agent TEXT NULL,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS crm_eventos (
    id SERIAL PRIMARY KEY,
    id_sessao UUID NOT NULL REFERENCES crm_sessoes (id_sessao) ON DELETE CASCADE,
    tipo_evento VARCHAR(128) NOT NULL,
    url_pagina VARCHAR(2048) NULL,
    tempo_gasto_segundos INTEGER NOT NULL DEFAULT 0,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_crm_sessoes_sistema_origem
    ON crm_sessoes (sistema_origem);

CREATE INDEX IF NOT EXISTS idx_crm_eventos_url_pagina
    ON crm_eventos (url_pagina);

CREATE INDEX IF NOT EXISTS idx_crm_eventos_tipo_evento
    ON crm_eventos (tipo_evento);

CREATE INDEX IF NOT EXISTS idx_crm_eventos_sessao_criado
    ON crm_eventos (id_sessao, criado_em DESC);

CREATE INDEX IF NOT EXISTS idx_crm_eventos_criado
    ON crm_eventos (criado_em DESC);
