-- Reverte 034: devolve curso_id em disciplinas (1 curso por disciplina) e
-- torna turma.curso_id opcional de novo.

BEGIN;

DROP TABLE IF EXISTS public.school_professor_disciplina_habilitacao CASCADE;

ALTER TABLE public.school_disciplinas
    ADD COLUMN IF NOT EXISTS curso_id UUID
        REFERENCES public.school_cursos (id) ON DELETE CASCADE;

UPDATE public.school_disciplinas d
SET curso_id = sub.curso_id
FROM (
    SELECT DISTINCT ON (cd.disciplina_id)
        cd.disciplina_id,
        cd.curso_id
    FROM public.school_curso_disciplinas cd
    ORDER BY cd.disciplina_id, cd.created_at
) sub
WHERE d.id = sub.disciplina_id
  AND d.curso_id IS NULL;

DROP TABLE IF EXISTS public.school_curso_disciplinas CASCADE;

ALTER TABLE public.school_turmas
    ALTER COLUMN curso_id DROP NOT NULL;

COMMIT;
