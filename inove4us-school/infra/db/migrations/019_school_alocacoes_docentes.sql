-- inove4us School — alocações docentes + disciplinas de catálogo flat (Secretaria Acadêmica).
-- Numeração: 019.

BEGIN;

-- Disciplinas podem existir no catálogo institucional (sem curso) para alocação operacional.
ALTER TABLE public.school_disciplinas
    ALTER COLUMN curso_id DROP NOT NULL;

ALTER TABLE public.school_disciplinas
    ADD COLUMN IF NOT EXISTS instituicao_id UUID
        REFERENCES public.school_instituicoes (id) ON DELETE CASCADE;

UPDATE public.school_disciplinas d
SET instituicao_id = p.instituicao_id
FROM public.school_cursos c
JOIN public.school_periodos_letivos p ON p.id = c.periodo_letivo_id
WHERE d.curso_id = c.id
  AND d.instituicao_id IS NULL;

CREATE INDEX IF NOT EXISTS idx_school_disciplinas_instituicao
    ON public.school_disciplinas (instituicao_id, ativo)
    WHERE instituicao_id IS NOT NULL;

COMMENT ON COLUMN public.school_disciplinas.instituicao_id IS
  'Instituição dona (catálogo flat Secretaria Acadêmica). Preenchido também via curso→período.';
COMMENT ON COLUMN public.school_disciplinas.curso_id IS
  'Opcional: NULL = disciplina de catálogo institucional; preenchido = disciplina de um curso.';

-- Casamento operacional: unidade + período + disciplina + professor
CREATE TABLE IF NOT EXISTS public.school_alocacoes_docentes (
    id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instituicao_id         UUID NOT NULL
        REFERENCES public.school_instituicoes (id) ON DELETE CASCADE,
    unidade_id             UUID NOT NULL
        REFERENCES public.school_unidades (id) ON DELETE CASCADE,
    periodo_id             UUID NOT NULL
        REFERENCES public.school_periodos_letivos (id) ON DELETE CASCADE,
    disciplina_id          UUID NOT NULL
        REFERENCES public.school_disciplinas (id) ON DELETE CASCADE,
    professor_vinculo_id   UUID NOT NULL
        REFERENCES public.school_professores_vinculo (id) ON DELETE CASCADE,
    ativo                  BOOLEAN NOT NULL DEFAULT TRUE,
    notificado_b2c         BOOLEAN NOT NULL DEFAULT FALSE,
    created_at             TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at             TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_school_alocacao_unica
        UNIQUE (unidade_id, periodo_id, disciplina_id, professor_vinculo_id)
);

CREATE INDEX IF NOT EXISTS idx_school_alocacoes_instituicao
    ON public.school_alocacoes_docentes (instituicao_id, ativo);

CREATE INDEX IF NOT EXISTS idx_school_alocacoes_professor
    ON public.school_alocacoes_docentes (professor_vinculo_id);

COMMENT ON TABLE public.school_alocacoes_docentes IS
  'Alocação docente (Secretaria Acadêmica). Dispara TEACHER_ALLOCATED → B2C.';

COMMIT;
