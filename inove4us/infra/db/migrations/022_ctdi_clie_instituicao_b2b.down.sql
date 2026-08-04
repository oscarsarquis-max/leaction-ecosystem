BEGIN;
DROP INDEX IF EXISTS public.idx_ctdi_clie_instituicao_b2b;
ALTER TABLE public.ctdi_clie
    DROP COLUMN IF EXISTS institutional_name,
    DROP COLUMN IF EXISTS instituicao_b2b_id;
COMMIT;
