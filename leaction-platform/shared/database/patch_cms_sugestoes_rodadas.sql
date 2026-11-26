-- BLOG-024c/d — Rodadas assíncronas de sugestões + limpeza pontual. Aditivo e idempotente.
-- Banco: leaction_hub. Não apaga linha.
-- O gateway também executa o bloco CREATE (mesmo texto de RODADAS_DDL em
-- cms-sugestoes-rodadas.js) ao iniciar o scheduler; este patch é a fonte para o deploy manual.

CREATE TABLE IF NOT EXISTS cms_sugestoes_rodadas (
  id          SERIAL PRIMARY KEY,
  started_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  finished_at TIMESTAMPTZ,
  status      TEXT NOT NULL DEFAULT 'running',
  progress    JSONB NOT NULL DEFAULT '{}'::jsonb,
  result      JSONB,
  trigger     TEXT NOT NULL DEFAULT 'manual',
  CONSTRAINT chk_cms_sugestoes_rodadas_status CHECK (status IN ('running', 'done', 'error')),
  CONSTRAINT chk_cms_sugestoes_rodadas_trigger CHECK (trigger IN ('auto', 'manual'))
);

-- No máximo 1 rodada em andamento.
CREATE UNIQUE INDEX IF NOT EXISTS uq_cms_sugestoes_rodadas_running
  ON cms_sugestoes_rodadas ((true)) WHERE status = 'running';

-- No máximo 1 rodada automática por dia (America/Sao_Paulo). Rodada manual não conta.
CREATE UNIQUE INDEX IF NOT EXISTS uq_cms_sugestoes_rodadas_auto_dia
  ON cms_sugestoes_rodadas (((started_at AT TIME ZONE 'America/Sao_Paulo')::date))
  WHERE trigger = 'auto';

-- One-shot: descarta sugestões pendentes de 19/11 que ainda não foram publicadas.
-- Só toca status = 'sugestao'; o par já publicado (Olivier) fica intacto.
-- Cobre 2025-11-19 (data do pedido) e 2026-11-19 (ano do BLOG-024 no repositório).
UPDATE cms_posts
   SET status = 'descartado', atualizado_em = now()
 WHERE status = 'sugestao'
   AND secao = 'right_now'
   AND sistema_destino = 'lepain'
   AND (criado_em AT TIME ZONE 'America/Sao_Paulo')::date IN (DATE '2025-11-19', DATE '2026-11-19');
