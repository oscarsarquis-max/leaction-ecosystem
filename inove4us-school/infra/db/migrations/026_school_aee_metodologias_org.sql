-- Adaptações metodológicas na prática — versão da escola por condição AEE.

BEGIN;

CREATE TABLE IF NOT EXISTS public.school_aee_metodologias_org (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    aee_matriz_id        UUID NOT NULL
        REFERENCES public.school_aee_matrizes (id) ON DELETE CASCADE,
    metodologia_nome     VARCHAR(255) NOT NULL,
    passos_customizados  TEXT NOT NULL DEFAULT '',
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_school_aee_metodologias_org_matriz_met
        UNIQUE (aee_matriz_id, metodologia_nome)
);

CREATE INDEX IF NOT EXISTS idx_school_aee_metodologias_org_matriz
    ON public.school_aee_metodologias_org (aee_matriz_id);

COMMENT ON TABLE public.school_aee_metodologias_org IS
  'Versão da escola da metodologia adaptada por condição AEE (ex.: TEA).';
COMMENT ON COLUMN public.school_aee_metodologias_org.passos_customizados IS
  'Roteiro final da escola para esta metodologia × condição. Vazio = ainda não customizado.';

COMMIT;
