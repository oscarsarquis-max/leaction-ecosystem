-- Rollback 004_school_governanca_pedagogica_schema.sql
-- Ordem: filhos antes dos pais. Recria school_editor_pedagogico (estado pós-001).

BEGIN;

DROP TABLE IF EXISTS public.school_planos_aula_espelhados CASCADE;
DROP TABLE IF EXISTS public.school_pei_individualizado CASCADE;
DROP TABLE IF EXISTS public.school_pei_diretriz_base CASCADE;
DROP TABLE IF EXISTS public.school_metodologia_config CASCADE;
DROP TABLE IF EXISTS public.school_metodologias_catalogo CASCADE;

-- Recria school_editor_pedagogico como estava após a migration 001.
CREATE TABLE IF NOT EXISTS public.school_editor_pedagogico (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instituicao_id     UUID NOT NULL
        REFERENCES public.school_instituicoes (id) ON DELETE CASCADE,
    metodologia_base   VARCHAR(64) NOT NULL DEFAULT 'PBL',
    diretriz_customizada TEXT,
    is_active          BOOLEAN NOT NULL DEFAULT TRUE,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_school_editor_instituicao
    ON public.school_editor_pedagogico (instituicao_id);

CREATE INDEX IF NOT EXISTS idx_school_editor_active
    ON public.school_editor_pedagogico (instituicao_id)
    WHERE is_active = TRUE;

COMMENT ON TABLE public.school_editor_pedagogico IS
  'Diretrizes pedagógicas da instituição. A School é fonte de verdade; o B2C consome via integração.';
COMMENT ON COLUMN public.school_editor_pedagogico.metodologia_base IS
  'Metodologia âncora (ex.: PBL, EduScrum, Design Thinking).';

COMMIT;
