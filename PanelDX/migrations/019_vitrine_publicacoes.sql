-- Log de publicações da vitrine PanelDX → ActionHub
BEGIN;

CREATE TABLE IF NOT EXISTS public.dx_vitrine_publicacoes (
    id              SERIAL PRIMARY KEY,
    sync_id         UUID NOT NULL,
    planos_count    INTEGER NOT NULL DEFAULT 0,
    hub_received    BOOLEAN NOT NULL DEFAULT FALSE,
    hub_received_at TIMESTAMP WITHOUT TIME ZONE,
    hub_response    JSONB,
    criado_em       TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_dx_vitrine_publicacoes_sync
    ON public.dx_vitrine_publicacoes (sync_id);

COMMENT ON TABLE public.dx_vitrine_publicacoes IS
    'Auditoria de sync em lote do catálogo CRM para o ActionHub';

COMMIT;
