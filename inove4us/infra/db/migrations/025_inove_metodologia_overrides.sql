-- inove4us B2C — overrides de metodologia vindos do School (Editor Pedagógico).
-- Chave: instituicao_b2b_id (mesmo vínculo de mural/planejamento) + metodologia_key
-- (id canônico do catálogo B2C das 39, resolvido a partir de codigo/nome).
-- Numeração: 025.

BEGIN;

CREATE TABLE IF NOT EXISTS public.inove_metodologia_overrides (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instituicao_b2b_id          UUID NOT NULL,
    metodologia_key             TEXT NOT NULL,
    metodologia_nome            TEXT,
    diretriz_customizada        TEXT,
    disponivel_dia_a_dia        BOOLEAN NOT NULL DEFAULT TRUE,
    disponivel_desafio          BOOLEAN NOT NULL DEFAULT TRUE,
    is_active                   BOOLEAN NOT NULL DEFAULT TRUE,
    versao                      BIGINT NOT NULL DEFAULT 0,
    atualizado_em               TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    origem_config_school_id     UUID,
    synced_at                   TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_inove_metodologia_overrides_inst_key
        UNIQUE (instituicao_b2b_id, metodologia_key)
);

CREATE INDEX IF NOT EXISTS idx_inove_metodologia_overrides_inst
    ON public.inove_metodologia_overrides (instituicao_b2b_id)
    WHERE is_active = TRUE;

COMMENT ON TABLE public.inove_metodologia_overrides IS
  'Diretrizes da escola por metodologia (METHODOLOGY_OVERRIDE_UPDATED). Freemium sem vínculo ignora.';
COMMENT ON COLUMN public.inove_metodologia_overrides.metodologia_key IS
  'Id canônico B2C (ex.: criativa_pbl_problemas) — alinha a school_metodologias_catalogo.codigo / catálogo 39.';
COMMENT ON COLUMN public.inove_metodologia_overrides.instituicao_b2b_id IS
  'UUID da instituição School; mesmo conceito de ctdi_clie.instituicao_b2b_id.';

COMMIT;
