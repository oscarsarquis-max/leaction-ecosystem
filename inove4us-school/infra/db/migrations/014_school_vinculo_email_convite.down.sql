-- Rollback 014
BEGIN;
DROP INDEX IF EXISTS public.uq_school_prof_vinculo_inst_email;
ALTER TABLE public.school_professores_vinculo
    DROP COLUMN IF EXISTS email_convite;
COMMIT;
