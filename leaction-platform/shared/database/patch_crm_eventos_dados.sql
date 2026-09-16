-- Sponge: payload opcional nos eventos de uso (prompt 132).
-- Aditivo. Sem backfill. Não altera funil nem crm_sessoes.
--
-- Aplicar:
--   psql "$DATABASE_URL" -f shared/database/patch_crm_eventos_dados.sql
--   (ou via scripts/deploy/remote-db-migrate.sh — inclui patch_*.sql)

ALTER TABLE crm_eventos
    ADD COLUMN IF NOT EXISTS dados JSONB NULL;

COMMENT ON COLUMN crm_eventos.dados IS
  'Payload opcional do evento (ids, códigos, booleanos, enums curtos). Sem PII.';

CREATE INDEX IF NOT EXISTS idx_crm_eventos_tipo_evento
    ON crm_eventos (tipo_evento);
