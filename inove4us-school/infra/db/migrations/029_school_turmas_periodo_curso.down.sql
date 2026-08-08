DROP INDEX IF EXISTS public.idx_school_turmas_curso;
DROP INDEX IF EXISTS public.idx_school_turmas_periodo;

ALTER TABLE public.school_turmas
    DROP COLUMN IF EXISTS curso_id;

ALTER TABLE public.school_turmas
    DROP COLUMN IF EXISTS periodo_letivo_id;
