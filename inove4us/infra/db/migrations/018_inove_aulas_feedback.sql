-- Feedback Loop pós-aula (retroalimentação estruturada do professor).
-- Aplicar: psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f infra/db/migrations/018_inove_aulas_feedback.sql

BEGIN;

CREATE TABLE IF NOT EXISTS public.inove_aulas_feedback (
    id                SERIAL PRIMARY KEY,
    id_evento         INTEGER NOT NULL
        REFERENCES public.inove_agenda_eventos (id_evento) ON DELETE CASCADE,
    id_clie           INTEGER NOT NULL
        REFERENCES public.ctdi_clie (id_clie) ON DELETE CASCADE,
    desafio_id        UUID,
    metodologia_ok    BOOLEAN NOT NULL,
    engajamento       VARCHAR(16) NOT NULL
        CHECK (engajamento IN ('alto', 'medio', 'baixo')),
    estrutura_ok      BOOLEAN NOT NULL,
    observacoes       TEXT,
    criado_em         TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_inove_aulas_feedback_evento
    ON public.inove_aulas_feedback (id_evento);

CREATE INDEX IF NOT EXISTS idx_inove_aulas_feedback_clie
    ON public.inove_aulas_feedback (id_clie, criado_em DESC);

CREATE INDEX IF NOT EXISTS idx_inove_aulas_feedback_desafio
    ON public.inove_aulas_feedback (desafio_id)
    WHERE desafio_id IS NOT NULL;

COMMENT ON TABLE public.inove_aulas_feedback IS
  'Retroalimentação pós-aula: metodologia, engajamento, estrutura e observações (voz/texto).';

COMMIT;
