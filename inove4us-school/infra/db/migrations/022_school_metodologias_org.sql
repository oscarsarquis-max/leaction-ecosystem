-- inove4us School — especialização de metodologias por organização (Editor Pedagógico).
-- Tabela canônica: school_metodologias_org
-- Migra dados de school_metodologia_config quando existir.

BEGIN;

CREATE TABLE IF NOT EXISTS public.school_metodologias_org (
    id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instituicao_id           UUID NOT NULL
        REFERENCES public.school_instituicoes (id) ON DELETE CASCADE,
    metodologia_id_canonica  UUID NOT NULL
        REFERENCES public.school_metodologias_catalogo (id) ON DELETE CASCADE,
    -- Texto unificado da instituição (Versão da Escola / saída da IA editável)
    passos_customizados      TEXT,
    ativo_dia_a_dia          BOOLEAN NOT NULL DEFAULT TRUE,
    ativo_desafio            BOOLEAN NOT NULL DEFAULT TRUE,
    uso_estrelas             INTEGER NOT NULL DEFAULT 1
        CONSTRAINT chk_school_metodologias_org_estrelas
            CHECK (uso_estrelas BETWEEN 1 AND 3),
    is_active                BOOLEAN NOT NULL DEFAULT TRUE,
    created_at               TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at               TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_school_metodologias_org_inst_met
        UNIQUE (instituicao_id, metodologia_id_canonica)
);

CREATE INDEX IF NOT EXISTS idx_school_metodologias_org_instituicao
    ON public.school_metodologias_org (instituicao_id);

CREATE INDEX IF NOT EXISTS idx_school_metodologias_org_canonica
    ON public.school_metodologias_org (metodologia_id_canonica);

COMMENT ON TABLE public.school_metodologias_org IS
  'Especialização da metodologia canônica por instituição (versão da escola, vetores e popularidade).';
COMMENT ON COLUMN public.school_metodologias_org.passos_customizados IS
  'Versão da Escola — texto unificado (canônico mesclado com sugestões / IA). NULL = usa canônico.';
COMMENT ON COLUMN public.school_metodologias_org.uso_estrelas IS
  'Indicador 1–3 de uso/popularidade pelos professores.';

-- Migra override legado (JSONB passos → texto)
INSERT INTO public.school_metodologias_org (
    instituicao_id,
    metodologia_id_canonica,
    passos_customizados,
    ativo_dia_a_dia,
    ativo_desafio,
    uso_estrelas,
    is_active,
    created_at,
    updated_at
)
SELECT
    cfg.instituicao_id,
    cfg.metodologia_catalogo_id,
    CASE
        WHEN cfg.passos_customizados IS NULL AND cfg.diretriz_customizada IS NULL THEN NULL
        WHEN cfg.passos_customizados IS NULL THEN cfg.diretriz_customizada
        WHEN jsonb_typeof(cfg.passos_customizados) = 'array' THEN (
            SELECT string_agg(
                COALESCE(
                    NULLIF(trim(elem->>'titulo'), '') ||
                      CASE
                        WHEN NULLIF(trim(COALESCE(elem->>'mecanica_passo_a_passo', elem->>'como_executar_detalhado', '')), '') IS NOT NULL
                          AND NULLIF(trim(elem->>'titulo'), '') IS NOT NULL
                          AND NULLIF(trim(elem->>'titulo'), '')
                              IS DISTINCT FROM NULLIF(trim(COALESCE(elem->>'mecanica_passo_a_passo', elem->>'como_executar_detalhado', '')), '')
                        THEN ': ' || trim(COALESCE(elem->>'mecanica_passo_a_passo', elem->>'como_executar_detalhado', ''))
                        ELSE ''
                      END,
                    NULLIF(trim(elem #>> '{}'), '')
                ),
                E'\n'
                ORDER BY ordinality
            )
            FROM jsonb_array_elements(cfg.passos_customizados) WITH ORDINALITY AS t(elem, ordinality)
        )
        WHEN jsonb_typeof(cfg.passos_customizados) = 'string' THEN trim(both '"' from cfg.passos_customizados::text)
        ELSE coalesce(cfg.diretriz_customizada, cfg.passos_customizados::text)
    END,
    COALESCE(cfg.ativo_dia_a_dia, TRUE),
    COALESCE(cfg.ativo_desafio, TRUE),
    1,
    COALESCE(cfg.is_active, TRUE),
    cfg.created_at,
    cfg.updated_at
FROM public.school_metodologia_config cfg
ON CONFLICT (instituicao_id, metodologia_id_canonica) DO NOTHING;

COMMIT;
