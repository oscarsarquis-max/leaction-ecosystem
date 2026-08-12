BEGIN;
DROP TABLE IF EXISTS public.school_unidade_equipe CASCADE;
ALTER TABLE public.school_unidades
    DROP COLUMN IF EXISTS logradouro,
    DROP COLUMN IF EXISTS numero,
    DROP COLUMN IF EXISTS bairro,
    DROP COLUMN IF EXISTS cep,
    DROP COLUMN IF EXISTS telefone,
    DROP COLUMN IF EXISTS email_institucional;
COMMIT;
