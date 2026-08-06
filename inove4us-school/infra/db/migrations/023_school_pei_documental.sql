-- PEI Documental: matriz versionada da escola + individualização do aluno.
-- Também relaxa school_pei_metodologia_adaptacao para adaptações institucionais (sem aluno).

BEGIN;

-- ---------------------------------------------------------------------------
-- Matriz documental (versão institucional / legal)
-- ---------------------------------------------------------------------------
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_type WHERE typname = 'school_pei_matriz_status'
    ) THEN
        CREATE TYPE public.school_pei_matriz_status AS ENUM (
            'rascunho',
            'aguardando_assinaturas',
            'ativo',
            'arquivado'
        );
    END IF;
END$$;

CREATE TABLE IF NOT EXISTS public.school_pei_matriz_documental (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instituicao_id          UUID NOT NULL
        REFERENCES public.school_instituicoes (id) ON DELETE CASCADE,
    versao                  INTEGER NOT NULL DEFAULT 1,
    texto_canonico          TEXT NOT NULL DEFAULT '',
    texto_escola            TEXT NOT NULL DEFAULT '',
    status                  public.school_pei_matriz_status NOT NULL DEFAULT 'rascunho',
    assinado_coordenador    BOOLEAN NOT NULL DEFAULT FALSE,
    assinado_psicopedagogo  BOOLEAN NOT NULL DEFAULT FALSE,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_school_pei_matriz_inst_versao
        UNIQUE (instituicao_id, versao)
);

CREATE INDEX IF NOT EXISTS idx_school_pei_matriz_inst_status
    ON public.school_pei_matriz_documental (instituicao_id, status);

COMMENT ON TABLE public.school_pei_matriz_documental IS
  'Matriz PEI documental da escola — versionamento legal com assinaturas nominais.';

-- ---------------------------------------------------------------------------
-- Individualização documental (aluno × matriz)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.school_pei_aluno_documental (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instituicao_id          UUID NOT NULL
        REFERENCES public.school_instituicoes (id) ON DELETE CASCADE,
    matriz_versao_id        UUID NOT NULL
        REFERENCES public.school_pei_matriz_documental (id) ON DELETE RESTRICT,
    nome_completo           TEXT NOT NULL,
    matricula               TEXT NOT NULL DEFAULT '',
    nome_responsavel        TEXT NOT NULL DEFAULT '',
    documento_final_texto   TEXT NOT NULL DEFAULT '',
    assinado_coordenador    BOOLEAN NOT NULL DEFAULT FALSE,
    assinado_psicopedagogo  BOOLEAN NOT NULL DEFAULT FALSE,
    data_assinatura         TIMESTAMPTZ,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_school_pei_aluno_doc_inst
    ON public.school_pei_aluno_documental (instituicao_id);

CREATE INDEX IF NOT EXISTS idx_school_pei_aluno_doc_matriz
    ON public.school_pei_aluno_documental (matriz_versao_id);

COMMENT ON TABLE public.school_pei_aluno_documental IS
  'PEI documental individual — associa dados do aluno à matriz ativa e exige duas assinaturas.';

-- ---------------------------------------------------------------------------
-- Adaptações metodológicas institucionais (Editor → aba Adaptações)
-- ---------------------------------------------------------------------------
ALTER TABLE public.school_pei_metodologia_adaptacao
    ALTER COLUMN pei_aluno_id DROP NOT NULL;

ALTER TABLE public.school_pei_metodologia_adaptacao
    ADD COLUMN IF NOT EXISTS metodologia_catalogo_id UUID
        REFERENCES public.school_metodologias_catalogo (id) ON DELETE SET NULL;

ALTER TABLE public.school_pei_metodologia_adaptacao
    DROP CONSTRAINT IF EXISTS uq_school_pei_met_adapt_pei_met;
DROP INDEX IF EXISTS uq_school_pei_met_adapt_pei_met;

CREATE UNIQUE INDEX IF NOT EXISTS uq_school_pei_met_adapt_aluno
    ON public.school_pei_metodologia_adaptacao (pei_aluno_id, metodologia_nome)
    WHERE pei_aluno_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_school_pei_met_adapt_inst
    ON public.school_pei_metodologia_adaptacao (instituicao_id, metodologia_nome)
    WHERE pei_aluno_id IS NULL;

COMMIT;
