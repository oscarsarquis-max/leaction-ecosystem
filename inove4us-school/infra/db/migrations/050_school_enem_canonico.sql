-- Catálogo escolar ENEM (prompt 148): disciplina real × habilidade oficial.
-- Texto continua só na tabela oficial; aqui é o mapeamento aprovado.

BEGIN;

CREATE TABLE IF NOT EXISTS public.school_enem_habilidades_canonico (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instituicao_id       UUID NOT NULL
        REFERENCES public.school_instituicoes (id) ON DELETE CASCADE,
    disciplina_id        UUID
        REFERENCES public.school_disciplinas (id) ON DELETE SET NULL,
    disciplina_nome      TEXT,
    curso_id             UUID
        REFERENCES public.school_cursos (id) ON DELETE SET NULL,
    curso_ano            TEXT NOT NULL DEFAULT '1ª série',
    etapa                VARCHAR(8) NOT NULL DEFAULT 'EM',
    area_codigo          VARCHAR(8) NOT NULL,
    habilidade_codigo    TEXT
        REFERENCES public.enem_habilidades_oficial (codigo) ON DELETE RESTRICT,
    redacao_codigo       TEXT
        REFERENCES public.enem_redacao_competencias_oficial (codigo) ON DELETE RESTRICT,
    competencia_numero   INTEGER,
    rotulo               TEXT NOT NULL,
    mapeamento_regra     TEXT NOT NULL,
    nuance               TEXT,
    origem               VARCHAR(40) NOT NULL DEFAULT 'enem_oficial',
    status               VARCHAR(32) NOT NULL DEFAULT 'aprovado',
    fonte_proveniencia   TEXT,
    dataset_versao       TEXT NOT NULL DEFAULT 'enem-oficial-2026.09.1',
    aprovado_em          TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_enem_canonico_area
        CHECK (area_codigo IN ('LC', 'MT', 'CN', 'CH', 'RED')),
    CONSTRAINT ck_enem_canonico_status
        CHECK (status IN ('pendente_revisao', 'aprovado', 'rejeitado')),
    CONSTRAINT ck_enem_canonico_origem
        CHECK (origem = 'enem_oficial'),
    CONSTRAINT ck_enem_canonico_ref
        CHECK (
            (habilidade_codigo IS NOT NULL AND redacao_codigo IS NULL)
            OR (habilidade_codigo IS NULL AND redacao_codigo IS NOT NULL)
        )
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_enem_canonico_hab_disc
    ON public.school_enem_habilidades_canonico (
        instituicao_id,
        habilidade_codigo,
        COALESCE(disciplina_id, '00000000-0000-0000-0000-000000000000'::uuid)
    )
    WHERE habilidade_codigo IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_enem_canonico_red_disc
    ON public.school_enem_habilidades_canonico (
        instituicao_id,
        redacao_codigo,
        COALESCE(disciplina_id, '00000000-0000-0000-0000-000000000000'::uuid)
    )
    WHERE redacao_codigo IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_enem_canonico_inst_disc
    ON public.school_enem_habilidades_canonico (instituicao_id, disciplina_id, status);
CREATE INDEX IF NOT EXISTS idx_enem_canonico_area
    ON public.school_enem_habilidades_canonico (instituicao_id, area_codigo);

COMMENT ON TABLE public.school_enem_habilidades_canonico IS
  'Mapeamento curado instituição × disciplina real → habilidade/competência oficial do ENEM. Sem reescrita de texto.';
COMMENT ON COLUMN public.school_enem_habilidades_canonico.disciplina_id IS
  'NULL = disponível na escola, ainda sem disciplina cadastrada (ex.: Matemática, Química, História).';
COMMENT ON COLUMN public.school_enem_habilidades_canonico.rotulo IS
  'Cópia do enunciado oficial — sem paráfrase.';
COMMENT ON COLUMN public.school_enem_habilidades_canonico.nuance IS
  'Por que a habilidade foi (ou não) ligada a esta disciplina, lendo o texto oficial.';

COMMIT;
