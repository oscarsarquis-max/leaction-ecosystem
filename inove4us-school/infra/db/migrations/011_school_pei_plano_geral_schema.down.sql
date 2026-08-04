BEGIN;

DROP TABLE IF EXISTS public.school_pei_campo_experiencia CASCADE;

ALTER TABLE public.school_pei_diretriz_base
    DROP COLUMN IF EXISTS profissionais_envolvidos,
    DROP COLUMN IF EXISTS recursos_estrategias,
    DROP COLUMN IF EXISTS metas_prazos,
    DROP COLUMN IF EXISTS necessidades,
    DROP COLUMN IF EXISTS capacidades_interesses;

COMMENT ON TABLE public.school_pei_diretriz_base IS
  'Diretriz institucional de PEI por tipo de neurodivergência (texto livre até haver taxonomia oficial).';
COMMENT ON COLUMN public.school_pei_diretriz_base.diretriz IS NULL;

COMMIT;
