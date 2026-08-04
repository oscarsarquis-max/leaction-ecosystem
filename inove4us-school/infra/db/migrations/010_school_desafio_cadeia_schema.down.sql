BEGIN;

ALTER TABLE public.school_planos_aula_espelhados
    DROP CONSTRAINT IF EXISTS chk_school_planos_aula_desafio_cadeia;

DROP INDEX IF EXISTS idx_school_planos_aula_desafio_seq;
DROP INDEX IF EXISTS idx_school_planos_aula_desafio_grupo;

ALTER TABLE public.school_planos_aula_espelhados
    DROP COLUMN IF EXISTS desafio_sequencia,
    DROP COLUMN IF EXISTS desafio_titulo,
    DROP COLUMN IF EXISTS desafio_grupo_id;

COMMIT;
