BEGIN;
DROP TABLE IF EXISTS public.school_curadoria_metodologias CASCADE;
DROP INDEX IF EXISTS public.uq_school_planos_origem_b2c;
ALTER TABLE public.school_planos_aula_espelhados
    DROP COLUMN IF EXISTS mesa_payload_json;
COMMIT;
