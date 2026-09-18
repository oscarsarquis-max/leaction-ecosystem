BEGIN;

ALTER TABLE public.school_curadoria_pei
    DROP COLUMN IF EXISTS resultado_analise;
ALTER TABLE public.school_curadoria_pei
    DROP COLUMN IF EXISTS retorno_docente;

COMMIT;
