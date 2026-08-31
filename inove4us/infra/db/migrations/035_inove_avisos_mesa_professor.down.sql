BEGIN;

DROP INDEX IF EXISTS public.idx_inove_avisos_mesa_professor;
ALTER TABLE public.inove_avisos_mesa DROP COLUMN IF EXISTS professor_b2c_id;
ALTER TABLE public.inove_avisos_mesa DROP COLUMN IF EXISTS tipo;
ALTER TABLE public.inove_avisos_mesa DROP COLUMN IF EXISTS meta_json;

COMMIT;
