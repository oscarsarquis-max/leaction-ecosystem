-- Secretaria Acadêmica — turma opcional na alocação docente.
-- Numeração: 028.

BEGIN;

ALTER TABLE public.school_alocacoes_docentes
    ADD COLUMN IF NOT EXISTS turma_id UUID
        REFERENCES public.school_turmas (id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_school_alocacoes_turma
    ON public.school_alocacoes_docentes (turma_id)
    WHERE turma_id IS NOT NULL;

ALTER TABLE public.school_alocacoes_docentes
    DROP CONSTRAINT IF EXISTS uq_school_alocacao_unica;

ALTER TABLE public.school_alocacoes_docentes
    ADD CONSTRAINT uq_school_alocacao_unica
        UNIQUE (unidade_id, periodo_id, disciplina_id, professor_vinculo_id, turma_id);

COMMENT ON COLUMN public.school_alocacoes_docentes.turma_id IS
  'Turma opcional da alocação. Incluída no payload TEACHER_ALLOCATED quando presente.';

COMMIT;
