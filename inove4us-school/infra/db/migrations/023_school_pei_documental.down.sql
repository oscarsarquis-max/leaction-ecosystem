-- Rollback 023_school_pei_documental
BEGIN;
DROP TABLE IF EXISTS public.school_pei_aluno_documental CASCADE;
DROP TABLE IF EXISTS public.school_pei_matriz_documental CASCADE;
DROP TYPE IF EXISTS public.school_pei_matriz_status;
COMMIT;
