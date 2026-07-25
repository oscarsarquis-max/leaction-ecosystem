-- Estruturação Pedagógica — Etapa 4/4: lotes de importação + idempotência
-- Pré-requisito: 007 (aulas_simples), 010 (disciplina_id/origem).
--
-- Aplicar:
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f infra/db/migrations/011_inove_importacoes_lote.sql

BEGIN;

CREATE TABLE IF NOT EXISTS public.inove_importacoes_lote (
    id               BIGSERIAL PRIMARY KEY,
    id_clie          INTEGER NOT NULL
                       REFERENCES public.ctdi_clie (id_clie) ON DELETE CASCADE,
    nome_arquivo     TEXT NOT NULL DEFAULT '',
    formato          VARCHAR(10) NOT NULL
                       CHECK (formato IN ('json', 'csv')),
    total_registros  INTEGER NOT NULL DEFAULT 0,
    total_sucesso    INTEGER NOT NULL DEFAULT 0,
    total_erro       INTEGER NOT NULL DEFAULT 0,
    total_aviso      INTEGER NOT NULL DEFAULT 0,
    relatorio_json   JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_inove_importacoes_lote_clie
    ON public.inove_importacoes_lote (id_clie, created_at DESC);

COMMENT ON TABLE public.inove_importacoes_lote IS
  'Histórico de importações de aulas/eventos (JSON/CSV) por professor.';

-- Idempotência: chave externa do arquivo por professor
ALTER TABLE public.inove_agenda_eventos
    ADD COLUMN IF NOT EXISTS id_externo_importacao VARCHAR(160);

ALTER TABLE public.inove_aulas_simples
    ADD COLUMN IF NOT EXISTS id_externo_importacao VARCHAR(160);

CREATE UNIQUE INDEX IF NOT EXISTS uq_inove_agenda_id_externo_clie
    ON public.inove_agenda_eventos (id_clie, id_externo_importacao)
    WHERE id_externo_importacao IS NOT NULL
      AND trim(id_externo_importacao) <> '';

CREATE UNIQUE INDEX IF NOT EXISTS uq_inove_aulas_simples_id_externo_clie
    ON public.inove_aulas_simples (id_clie, id_externo_importacao)
    WHERE id_externo_importacao IS NOT NULL
      AND trim(id_externo_importacao) <> '';

CREATE INDEX IF NOT EXISTS idx_inove_agenda_importacao_origem
    ON public.inove_agenda_eventos (id_clie, origem)
    WHERE origem = 'importacao';

COMMENT ON COLUMN public.inove_agenda_eventos.id_externo_importacao IS
  'id_externo do arquivo de importação; idempotência (id_clie, id_externo).';
COMMENT ON COLUMN public.inove_aulas_simples.id_externo_importacao IS
  'Espelho da chave de importação; alinhado à agenda.';

COMMIT;
