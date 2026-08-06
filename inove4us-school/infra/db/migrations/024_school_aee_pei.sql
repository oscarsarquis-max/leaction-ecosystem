-- AEE (diretriz por condição) + PEI individual do aluno.
-- Separa matriz institucional por condição (AEE) do plano individual (PEI).

BEGIN;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_type WHERE typname = 'school_aee_matriz_status'
    ) THEN
        CREATE TYPE public.school_aee_matriz_status AS ENUM (
            'rascunho',
            'aguardando_assinaturas',
            'ativo',
            'arquivado'
        );
    END IF;
END$$;

CREATE TABLE IF NOT EXISTS public.school_aee_matrizes (
    id                              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instituicao_id                  UUID NOT NULL
        REFERENCES public.school_instituicoes (id) ON DELETE CASCADE,
    versao                          INTEGER NOT NULL DEFAULT 1,
    condicao_categoria              VARCHAR(80) NOT NULL,
    texto_escola                    TEXT NOT NULL DEFAULT '',
    campos_experiencia_metodologica TEXT NOT NULL DEFAULT '',
    status                          public.school_aee_matriz_status NOT NULL DEFAULT 'rascunho',
    assinado_coordenador            BOOLEAN NOT NULL DEFAULT FALSE,
    assinado_psicopedagogo          BOOLEAN NOT NULL DEFAULT FALSE,
    created_at                      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at                      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_school_aee_matriz_inst_cond_versao
        UNIQUE (instituicao_id, condicao_categoria, versao)
);

CREATE INDEX IF NOT EXISTS idx_school_aee_matrizes_inst_cond_status
    ON public.school_aee_matrizes (instituicao_id, condicao_categoria, status);

COMMENT ON TABLE public.school_aee_matrizes IS
  'Matriz AEE por condição (diretriz legal + campos de experiência metodológica), versionada.';

CREATE TABLE IF NOT EXISTS public.school_pei_alunos (
    id                                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instituicao_id                      UUID NOT NULL
        REFERENCES public.school_instituicoes (id) ON DELETE CASCADE,
    aee_matriz_id                       UUID NOT NULL
        REFERENCES public.school_aee_matrizes (id) ON DELETE RESTRICT,
    nome_completo                       TEXT NOT NULL,
    matricula                           TEXT NOT NULL DEFAULT '',
    nome_responsavel                    TEXT NOT NULL DEFAULT '',
    perfil_atual_habilidades            TEXT NOT NULL DEFAULT '',
    barreiras_identificadas             TEXT NOT NULL DEFAULT '',
    metas_desenvolvimento               TEXT NOT NULL DEFAULT '',
    recursos_assistivos                 TEXT NOT NULL DEFAULT '',
    criterios_avaliacao_flexibilizados  TEXT NOT NULL DEFAULT '',
    experiencias_adaptadas_individuais  TEXT NOT NULL DEFAULT '',
    assinado_coordenador                BOOLEAN NOT NULL DEFAULT FALSE,
    assinado_psicopedagogo              BOOLEAN NOT NULL DEFAULT FALSE,
    data_assinatura                     TIMESTAMPTZ,
    created_at                          TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at                          TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_school_pei_alunos_inst
    ON public.school_pei_alunos (instituicao_id);

CREATE INDEX IF NOT EXISTS idx_school_pei_alunos_aee
    ON public.school_pei_alunos (aee_matriz_id);

COMMENT ON TABLE public.school_pei_alunos IS
  'PEI individual do aluno vinculado à matriz AEE ativa da condição.';

COMMIT;
