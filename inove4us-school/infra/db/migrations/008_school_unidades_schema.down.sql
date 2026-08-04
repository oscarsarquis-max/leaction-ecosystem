-- Rollback 008_school_unidades_schema.sql
BEGIN;

ALTER TABLE public.school_planos_aula_espelhados
    DROP CONSTRAINT IF EXISTS chk_school_planos_aula_espelhados_tipo_aula;

DROP INDEX IF EXISTS idx_school_planos_aula_tipo;

ALTER TABLE public.school_planos_aula_espelhados
    DROP COLUMN IF EXISTS tipo_aula;

DROP INDEX IF EXISTS idx_school_calendario_unidade;

ALTER TABLE public.school_calendario_letivo
    DROP COLUMN IF EXISTS unidade_id;

DROP INDEX IF EXISTS idx_school_gestores_unidade;

ALTER TABLE public.school_gestores
    DROP COLUMN IF EXISTS unidade_id;

DROP INDEX IF EXISTS idx_school_turmas_unidade;

ALTER TABLE public.school_turmas
    DROP COLUMN IF EXISTS unidade_id;

DROP TABLE IF EXISTS public.school_unidades CASCADE;

COMMIT;
