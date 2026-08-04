BEGIN;

ALTER TABLE public.school_instituicoes
    DROP COLUMN IF EXISTS link_plano_actionhub,
    DROP COLUMN IF EXISTS licencas_contratadas;

DROP TABLE IF EXISTS public.school_comunicacoes_eventos CASCADE;

COMMIT;
