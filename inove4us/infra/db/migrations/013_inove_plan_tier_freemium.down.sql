-- Down: 013_inove_plan_tier_freemium
BEGIN;
ALTER TABLE public.ctdi_clie DROP COLUMN IF EXISTS plan_tier;
ALTER TABLE public.ctdi_clie ALTER COLUMN creditos_ia SET DEFAULT 3;
COMMIT;
