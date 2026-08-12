-- Reverte 033: devolve unicidade (curso_id, school_disciplina_id).
-- Não recria linhas duplicadas desativadas na consolidação.

BEGIN;

DROP INDEX IF EXISTS uq_inove_disciplina_school_por_instituicao;

CREATE UNIQUE INDEX IF NOT EXISTS uq_inove_disciplina_school_por_curso
    ON public.inove_disciplinas (curso_id, school_disciplina_id)
    WHERE school_disciplina_id IS NOT NULL AND ativo = TRUE;

DROP TABLE IF EXISTS public.inove_curso_disciplinas CASCADE;

DROP INDEX IF EXISTS idx_inove_disciplinas_instituicao;

ALTER TABLE public.inove_disciplinas
    DROP COLUMN IF EXISTS instituicao_id;

COMMENT ON TABLE public.inove_disciplinas IS
  'Disciplina dentro de um curso; soft-delete via ativo.';

COMMIT;
