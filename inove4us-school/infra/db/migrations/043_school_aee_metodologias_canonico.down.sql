BEGIN;

DROP INDEX IF EXISTS public.idx_school_aee_met_canonico_status;
DROP INDEX IF EXISTS public.idx_school_aee_met_canonico_cond;
DROP TABLE IF EXISTS public.school_aee_metodologias_canonico;

COMMIT;
