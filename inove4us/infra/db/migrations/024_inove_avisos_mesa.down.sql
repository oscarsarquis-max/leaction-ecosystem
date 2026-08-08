-- Rollback 024_inove_avisos_mesa

BEGIN;

DROP INDEX IF EXISTS public.idx_inove_avisos_mesa_inst_ativos;
DROP INDEX IF EXISTS public.idx_inove_avisos_mesa_ativos;
DROP TABLE IF EXISTS public.inove_avisos_mesa;

COMMIT;
