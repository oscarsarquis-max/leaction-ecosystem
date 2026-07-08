-- Nível de implementação por objetivo (baseline canônico + instância por cliente)
-- meta_cliente nos KRs para metas reais do LED (substitui placeholders X/Y/Z)

BEGIN;

ALTER TABLE public.dx_objetivos
    ADD COLUMN IF NOT EXISTS nivel_implementacao VARCHAR(32) NOT NULL DEFAULT 'nao_iniciado';

ALTER TABLE public.ctdi_okr_objetivos_dt
    ADD COLUMN IF NOT EXISTS nivel_implementacao VARCHAR(32) NOT NULL DEFAULT 'nao_iniciado';

ALTER TABLE public.ctdi_okr_krs
    ADD COLUMN IF NOT EXISTS meta_cliente TEXT;

COMMENT ON COLUMN public.dx_objetivos.nivel_implementacao IS
    'Baseline do catálogo: nao_iniciado | em_andamento | avancado';

COMMENT ON COLUMN public.ctdi_okr_objetivos_dt.nivel_implementacao IS
    'Nível de implementação do objetivo para o cliente (editável pelo gestor)';

COMMENT ON COLUMN public.ctdi_okr_krs.meta_cliente IS
    'Meta real definida pelo cliente (substitui placeholder canônico do KR)';

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'dx_objetivos_nivel_chk'
    ) THEN
        ALTER TABLE public.dx_objetivos
            ADD CONSTRAINT dx_objetivos_nivel_chk
            CHECK (nivel_implementacao IN ('nao_iniciado', 'em_andamento', 'avancado'));
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'ctdi_okr_obj_nivel_chk'
    ) THEN
        ALTER TABLE public.ctdi_okr_objetivos_dt
            ADD CONSTRAINT ctdi_okr_obj_nivel_chk
            CHECK (nivel_implementacao IN ('nao_iniciado', 'em_andamento', 'avancado'));
    END IF;
END $$;

COMMIT;
