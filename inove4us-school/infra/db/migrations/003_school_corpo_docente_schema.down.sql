-- Rollback 003_school_corpo_docente_schema.sql

BEGIN;

DROP TABLE IF EXISTS public.school_professor_turma CASCADE;

COMMIT;
