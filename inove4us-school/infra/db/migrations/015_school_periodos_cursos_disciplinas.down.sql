-- Rollback 015
BEGIN;
DROP TABLE IF EXISTS public.school_disciplinas CASCADE;
DROP TABLE IF EXISTS public.school_cursos CASCADE;
DROP TABLE IF EXISTS public.school_periodos_letivos CASCADE;
COMMIT;
