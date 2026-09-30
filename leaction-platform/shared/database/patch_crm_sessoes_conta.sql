-- Sponge: identidade de conta nas sessões de tracking (prompt 130).
-- Aditivo. Sem backfill. Não altera crm_eventos nem crm_origens.
--
-- Aplicar:
--   psql "$DATABASE_URL" -f shared/database/patch_crm_sessoes_conta.sql
--   (ou via scripts/deploy/remote-db-migrate.sh — inclui patch_*.sql)

ALTER TABLE crm_sessoes
    ADD COLUMN IF NOT EXISTS usuario_origem_ref TEXT NULL;

ALTER TABLE crm_sessoes
    ADD COLUMN IF NOT EXISTS instituicao_id UUID NULL;

COMMENT ON COLUMN crm_sessoes.usuario_origem_ref IS
  'Identificador do usuário no produto de origem como texto (id_clie Inove; UUID do gestor School).';
COMMENT ON COLUMN crm_sessoes.instituicao_id IS
  'Conta B2B (UUID da instituição School). Coincide com contracts.subject_id no checkout School.';

CREATE INDEX IF NOT EXISTS idx_crm_sessoes_sistema_instituicao
    ON crm_sessoes (sistema_origem, instituicao_id);

CREATE INDEX IF NOT EXISTS idx_crm_sessoes_instituicao_criado
    ON crm_sessoes (instituicao_id, criado_em);
