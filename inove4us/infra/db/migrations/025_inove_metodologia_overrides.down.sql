-- Rollback 025_inove_metodologia_overrides

BEGIN;

DROP INDEX IF EXISTS public.idx_inove_metodologia_overrides_inst;
DROP TABLE IF EXISTS public.inove_metodologia_overrides;

COMMIT;
