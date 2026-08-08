-- inove4us School — Quadro de Avisos para Mesa do Professor (B2C).
-- Avisos curtos fixados no topo dos cards da Mesa no Inove.

BEGIN;

CREATE TABLE IF NOT EXISTS public.school_avisos_mesa (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instituicao_id          UUID NOT NULL
        REFERENCES public.school_instituicoes (id) ON DELETE CASCADE,
    texto                   TEXT NOT NULL,
    disciplina_id           UUID
        REFERENCES public.school_disciplinas (id) ON DELETE SET NULL,
    turma_id                UUID
        REFERENCES public.school_turmas (id) ON DELETE SET NULL,
    ativo                   BOOLEAN NOT NULL DEFAULT TRUE,
    replicado_b2c           BOOLEAN NOT NULL DEFAULT FALSE,
    replicado_b2c_em        TIMESTAMPTZ,
    criado_por_gestor_id    UUID
        REFERENCES public.school_gestores (id) ON DELETE SET NULL,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_school_avisos_mesa_texto
        CHECK (char_length(trim(texto)) BETWEEN 1 AND 500)
);

CREATE INDEX IF NOT EXISTS idx_school_avisos_mesa_instituicao
    ON public.school_avisos_mesa (instituicao_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_school_avisos_mesa_ativos
    ON public.school_avisos_mesa (instituicao_id)
    WHERE ativo = TRUE;

COMMENT ON TABLE public.school_avisos_mesa IS
  'Avisos curtos do coordenador → fixados no topo da Mesa do Professor (Inove).';
COMMENT ON COLUMN public.school_avisos_mesa.disciplina_id IS
  'NULL + turma NULL = todos; disciplina e/ou turma restringem o público.';
COMMENT ON COLUMN public.school_avisos_mesa.turma_id IS
  'NULL = todas as turmas (ou filtro só por disciplina).';

COMMIT;
