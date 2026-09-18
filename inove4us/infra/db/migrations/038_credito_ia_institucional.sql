-- Pool de crédito de IA por licença institucional (prompt 98).
-- Idempotente por professor × instituição × origem.
--
-- Aplicar:
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f infra/db/migrations/038_credito_ia_institucional.sql

BEGIN;

CREATE TABLE IF NOT EXISTS public.inove_credito_ia_concessoes (
    id              BIGSERIAL PRIMARY KEY,
    id_clie         INTEGER NOT NULL,
    instituicao_id  UUID NOT NULL,
    origem          VARCHAR(64) NOT NULL,
    credits         INTEGER NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (id_clie, instituicao_id, origem)
);

COMMENT ON TABLE public.inove_credito_ia_concessoes IS
  'Concessão idempotente de pool de IA por licença institucional (professor×escola).';

CREATE TABLE IF NOT EXISTS public.inove_hub_webhook_processed (
    idempotency_key TEXT PRIMARY KEY,
    event_type      VARCHAR(64) NOT NULL,
    processed_at   TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE public.inove_hub_webhook_processed IS
  'Idempotência do consumidor CREDITS_GRANTED (X-Hub-Idempotency-Key / order_id).';

COMMIT;
