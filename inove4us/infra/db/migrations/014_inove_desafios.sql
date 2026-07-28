-- Fase 2: desafio compartilhado entre execuções (turmas), sem nova chamada de IA.
-- Aplicar: psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f infra/db/migrations/014_inove_desafios.sql

BEGIN;

CREATE TABLE IF NOT EXISTS public.inove_desafios (
    id              UUID PRIMARY KEY,
    id_clie         INTEGER NOT NULL
        REFERENCES public.ctdi_clie (id_clie) ON DELETE CASCADE,
    titulo          VARCHAR(200),
    problema        TEXT,
    hipotese        TEXT,
    causas          JSONB,
    tema            VARCHAR(200),
    plan_data       JSONB,
    meta_json       JSONB,
    disciplina_id   BIGINT,
    criado_em       TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_inove_desafios_clie
    ON public.inove_desafios (id_clie, criado_em DESC);

COMMENT ON TABLE public.inove_desafios IS
  'Conteúdo canônico do desafio (hipótese/causas/tema/plano). Execuções = cadeias de aulas com o mesmo desafio_id e plano_session distinto.';

ALTER TABLE public.inove_agenda_eventos
    ADD COLUMN IF NOT EXISTS desafio_id UUID
        REFERENCES public.inove_desafios (id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_inove_agenda_eventos_desafio
    ON public.inove_agenda_eventos (desafio_id)
    WHERE desafio_id IS NOT NULL;

COMMENT ON COLUMN public.inove_agenda_eventos.desafio_id IS
  'FK ao desafio compartilhado; nullable para eventos anteriores à Fase 2.';

COMMIT;
