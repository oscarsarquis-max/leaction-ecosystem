-- Rollback 001_school_b2b_schema.sql
BEGIN;

DROP TABLE IF EXISTS public.school_editor_pedagogico CASCADE;
DROP TABLE IF EXISTS public.school_professores_vinculo CASCADE;
DROP TABLE IF EXISTS public.school_gestores CASCADE;
DROP TABLE IF EXISTS public.school_instituicoes CASCADE;

COMMIT;
