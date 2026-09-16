-- Sponge: identidades legíveis (prompt 137).
-- Aditivo. Sem backfill. Não altera funil nem ingestão de eventos.
--
-- Aplicar:
--   psql "$DATABASE_URL" -f shared/database/patch_crm_identidades.sql
--   (ou via scripts/deploy/remote-db-migrate.sh — inclui patch_*.sql)

CREATE TABLE IF NOT EXISTS crm_identidades (
    tipo            TEXT NOT NULL
                    CHECK (tipo IN ('instituicao', 'usuario')),
    chave           TEXT NOT NULL,
    nome            TEXT NOT NULL,
    sistema_origem  TEXT NULL,
    instituicao_id  UUID NULL,
    visto_em        TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (tipo, chave)
);

COMMENT ON TABLE crm_identidades IS
  'Nomes de instituição e de usuário adulto (gestor/professor) para o painel Sponge. Sem e-mail, CPF ou aluno.';
COMMENT ON COLUMN crm_identidades.chave IS
  'instituicao: UUID da instituição. usuario: sistema_origem || '':'' || usuario_origem_ref.';
COMMENT ON COLUMN crm_identidades.instituicao_id IS
  'Preenchido só para tipo=instituicao. NULL para tipo=usuario.';

CREATE INDEX IF NOT EXISTS idx_crm_identidades_instituicao
    ON crm_identidades (instituicao_id)
    WHERE instituicao_id IS NOT NULL;

ALTER TABLE crm_sessoes
    ADD COLUMN IF NOT EXISTS usuario_nome TEXT NULL;

ALTER TABLE crm_sessoes
    ADD COLUMN IF NOT EXISTS instituicao_nome TEXT NULL;

COMMENT ON COLUMN crm_sessoes.usuario_nome IS
  'Nome de exibição gravado na época da sessão (não sobrescreve com NULL).';
COMMENT ON COLUMN crm_sessoes.instituicao_nome IS
  'Nome da instituição gravado na época da sessão (não sobrescreve com NULL).';
