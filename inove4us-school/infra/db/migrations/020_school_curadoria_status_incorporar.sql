-- Curadoria bottom-up: status do fluxo pedagogo + flag is_customizado.
-- Idempotente (também garantido em curadoria_routes._ensure_curadoria_schema).

BEGIN;

ALTER TABLE public.school_metodologia_config
    ADD COLUMN IF NOT EXISTS is_customizado BOOLEAN NOT NULL DEFAULT FALSE;

COMMENT ON COLUMN public.school_metodologia_config.is_customizado IS
  'TRUE quando a diretriz foi enriquecida por curadoria (incorporar sugestão da trincheira).';

ALTER TABLE public.school_curadoria_metodologias
    DROP CONSTRAINT IF EXISTS school_curadoria_metodologias_status_analise_check;

ALTER TABLE public.school_curadoria_metodologias
    ADD CONSTRAINT school_curadoria_metodologias_status_analise_check
    CHECK (status_analise IN (
        'pendente',
        'em_analise',
        'incorporada',
        'incorporado',
        'rejeitada',
        'mantido_apenas_na_aula'
    ));

COMMIT;
