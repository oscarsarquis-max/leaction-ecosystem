BEGIN;

ALTER TABLE public.school_metodologias_catalogo
    DROP COLUMN IF EXISTS vetor_desafio,
    DROP COLUMN IF EXISTS vetor_dia_a_dia;

ALTER TABLE public.school_metodologia_config
    DROP COLUMN IF EXISTS ativo_desafio,
    DROP COLUMN IF EXISTS ativo_dia_a_dia;

COMMIT;
