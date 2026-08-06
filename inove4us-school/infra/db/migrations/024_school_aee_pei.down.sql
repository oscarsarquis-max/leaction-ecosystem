-- Rollback 024_school_aee_pei.sql
BEGIN;
DROP TABLE IF EXISTS public.school_pei_alunos;
DROP TABLE IF EXISTS public.school_aee_matrizes;
DROP TYPE IF EXISTS public.school_aee_matriz_status;
COMMIT;
