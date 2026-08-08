-- Rollback 026_inove_pei_overrides

BEGIN;

DROP INDEX IF EXISTS public.idx_inove_pei_overrides_indiv_nome;
DROP INDEX IF EXISTS public.idx_inove_pei_overrides_indiv_inst;
DROP TABLE IF EXISTS public.inove_pei_overrides_individual;

DROP INDEX IF EXISTS public.idx_inove_pei_overrides_base_inst;
DROP TABLE IF EXISTS public.inove_pei_overrides_base;

COMMIT;
