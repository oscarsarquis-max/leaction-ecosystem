-- inove4us School — Etapa 9: schema do plano geral de PEI.
-- Numeração: 011 (010 = cadeia de desafio no espelho).
-- Amplia school_pei_diretriz_base (área geral) e cria school_pei_campo_experiencia
-- (BNCC Educação Infantil — 5 campos fixos, múltiplos objetivos por campo).
-- Não altera school_pei_individualizado nem demais tabelas.

BEGIN;

-- ---------------------------------------------------------------------------
-- 1) Área geral do plano (diretriz base institucional)
-- ---------------------------------------------------------------------------
ALTER TABLE public.school_pei_diretriz_base
    ADD COLUMN IF NOT EXISTS capacidades_interesses TEXT,
    ADD COLUMN IF NOT EXISTS necessidades TEXT,
    ADD COLUMN IF NOT EXISTS metas_prazos TEXT,
    ADD COLUMN IF NOT EXISTS recursos_estrategias TEXT,
    ADD COLUMN IF NOT EXISTS profissionais_envolvidos TEXT;

COMMENT ON COLUMN public.school_pei_diretriz_base.capacidades_interesses IS
  'Área geral: o que o aluno sabe / do que gosta.';
COMMENT ON COLUMN public.school_pei_diretriz_base.necessidades IS
  'Área geral: o que ainda precisa aprender.';
COMMENT ON COLUMN public.school_pei_diretriz_base.metas_prazos IS
  'Área geral: metas e prazos (texto livre).';
COMMENT ON COLUMN public.school_pei_diretriz_base.recursos_estrategias IS
  'Área geral: o que utilizar para ensinar e como.';
COMMENT ON COLUMN public.school_pei_diretriz_base.profissionais_envolvidos IS
  'Área geral: quem planeja e quem aplica (texto livre nesta etapa; sem FK).';
COMMENT ON COLUMN public.school_pei_diretriz_base.diretriz IS
  'Resumo geral livre (legado da migration 004). Convive com os campos estruturados da área geral.';

COMMENT ON TABLE public.school_pei_diretriz_base IS
  'Plano geral de PEI por tipo de neurodivergência: área geral + campos de experiência (BNCC EI).';

-- ---------------------------------------------------------------------------
-- 2) Campos de experiência (BNCC Educação Infantil) — um ou mais objetivos
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.school_pei_campo_experiencia (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pei_diretriz_base_id    UUID NOT NULL
        REFERENCES public.school_pei_diretriz_base (id) ON DELETE CASCADE,
    campo_experiencia       TEXT NOT NULL,
    objetivo                TEXT NOT NULL,
    curriculo_habilidades   TEXT,
    estrategias_ensino      TEXT,
    prazo                   TEXT,
    ativo                   BOOLEAN NOT NULL DEFAULT TRUE,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_school_pei_campo_experiencia_bncc
        CHECK (campo_experiencia IN (
            'o_eu_o_outro_e_o_nos',
            'corpo_gestos_e_movimentos',
            'escuta_fala_pensamento_e_imaginacao',
            'tracos_sons_cores_e_formas',
            'espacos_tempos_quantidades_relacoes_e_transformacoes'
        ))
);

CREATE INDEX IF NOT EXISTS idx_school_pei_campo_experiencia_diretriz
    ON public.school_pei_campo_experiencia (pei_diretriz_base_id);

CREATE INDEX IF NOT EXISTS idx_school_pei_campo_experiencia_campo
    ON public.school_pei_campo_experiencia (pei_diretriz_base_id, campo_experiencia);

CREATE INDEX IF NOT EXISTS idx_school_pei_campo_experiencia_ativo
    ON public.school_pei_campo_experiencia (pei_diretriz_base_id)
    WHERE ativo = TRUE;

COMMENT ON TABLE public.school_pei_campo_experiencia IS
  'Objetivos do plano geral por campo de experiência BNCC (Educação Infantil). Sem UNIQUE: vários objetivos por campo.';
COMMENT ON COLUMN public.school_pei_campo_experiencia.campo_experiencia IS
  'Um dos 5 campos BNCC EI. Vocabulário de Fundamental/Médio fica para etapa futura.';
COMMENT ON COLUMN public.school_pei_campo_experiencia.estrategias_ensino IS
  'Âncora futura para adaptações de card do B2C migradas ao PEI. Só o campo nesta etapa.';
COMMENT ON COLUMN public.school_pei_campo_experiencia.prazo IS
  'Prazo em texto livre (ex.: "3 meses", "até dez/2026").';

COMMIT;
