-- Rollback 028_school_alocacao_turma

BEGIN;

ALTER TABLE public.school_alocacoes_docentes
    DROP CONSTRAINT IF EXISTS uq_school_alocacao_unica;

DROP INDEX IF EXISTS public.idx_school_alocacoes_turma;

ALTER TABLE public.school_alocacoes_docentes
    DROP COLUMN IF EXISTS turma_id;

ALTER TABLE public.school_alocacoes_docentes
    ADD CONSTRAINT uq_school_alocacao_unica
        UNIQUE (unidade_id, periodo_id, disciplina_id, professor_vinculo_id);

COMMIT;
