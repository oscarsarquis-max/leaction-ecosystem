BEGIN;
ALTER TABLE public.inove_aulas_simples
    DROP COLUMN IF EXISTS habilidades_bncc;
COMMIT;
