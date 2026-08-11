-- Espelho acadêmico School → B2C (fonte da verdade institucional)
--
-- Aplicar:
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f infra/db/migrations/029_school_academic_mirror.sql

BEGIN;

-- ---------------------------------------------------------------------------
-- Chaves lógicas School nas tabelas acadêmicas do professor
-- ---------------------------------------------------------------------------
ALTER TABLE public.inove_instituicoes
    ADD COLUMN IF NOT EXISTS school_instituicao_id UUID,
    ADD COLUMN IF NOT EXISTS origem_school BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE public.inove_periodos_letivos
    ADD COLUMN IF NOT EXISTS school_periodo_id UUID,
    ADD COLUMN IF NOT EXISTS origem_school BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE public.inove_cursos
    ADD COLUMN IF NOT EXISTS school_curso_id UUID,
    ADD COLUMN IF NOT EXISTS origem_school BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE public.inove_disciplinas
    ADD COLUMN IF NOT EXISTS school_disciplina_id UUID,
    ADD COLUMN IF NOT EXISTS origem_school BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE public.inove_turmas
    ADD COLUMN IF NOT EXISTS school_turma_id UUID,
    ADD COLUMN IF NOT EXISTS origem_school BOOLEAN NOT NULL DEFAULT FALSE;

-- Um espelho School por professor (id_clie dono da instituição)
CREATE UNIQUE INDEX IF NOT EXISTS uq_inove_inst_school_por_clie
    ON public.inove_instituicoes (id_clie, school_instituicao_id)
    WHERE school_instituicao_id IS NOT NULL AND ativo = TRUE;

CREATE UNIQUE INDEX IF NOT EXISTS uq_inove_periodo_school_por_inst
    ON public.inove_periodos_letivos (instituicao_id, school_periodo_id)
    WHERE school_periodo_id IS NOT NULL AND ativo = TRUE;

CREATE UNIQUE INDEX IF NOT EXISTS uq_inove_curso_school_por_periodo
    ON public.inove_cursos (periodo_letivo_id, school_curso_id)
    WHERE school_curso_id IS NOT NULL AND ativo = TRUE;

CREATE UNIQUE INDEX IF NOT EXISTS uq_inove_disciplina_school_por_curso
    ON public.inove_disciplinas (curso_id, school_disciplina_id)
    WHERE school_disciplina_id IS NOT NULL AND ativo = TRUE;

CREATE UNIQUE INDEX IF NOT EXISTS uq_inove_turma_school_por_curso
    ON public.inove_turmas (curso_id, school_turma_id)
    WHERE school_turma_id IS NOT NULL AND ativo = TRUE;

-- ---------------------------------------------------------------------------
-- Alocações espelhadas (disciplina + turma atribuídas pela Secretaria)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.inove_alocacoes_escola (
    id                      BIGSERIAL PRIMARY KEY,
    id_clie                 INTEGER NOT NULL
                              REFERENCES public.ctdi_clie (id_clie) ON DELETE CASCADE,
    school_alocacao_id      UUID NOT NULL,
    school_instituicao_id   UUID,
    school_vinculo_id       UUID,
    instituicao_id          BIGINT
                              REFERENCES public.inove_instituicoes (id) ON DELETE SET NULL,
    periodo_id              BIGINT
                              REFERENCES public.inove_periodos_letivos (id) ON DELETE SET NULL,
    curso_id                BIGINT
                              REFERENCES public.inove_cursos (id) ON DELETE SET NULL,
    disciplina_id           BIGINT
                              REFERENCES public.inove_disciplinas (id) ON DELETE SET NULL,
    turma_id                BIGINT
                              REFERENCES public.inove_turmas (id) ON DELETE SET NULL,
    instituicao_nome        VARCHAR(255),
    periodo_nome            VARCHAR(160),
    curso_nome              VARCHAR(255),
    disciplina_nome         VARCHAR(255),
    turma_nome              VARCHAR(120),
    turma_turno             VARCHAR(40),
    unidade_nome            VARCHAR(160),
    ativo                   BOOLEAN NOT NULL DEFAULT TRUE,
    meta_json               JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_inove_alocacoes_escola_school_id UNIQUE (school_alocacao_id)
);

CREATE INDEX IF NOT EXISTS idx_inove_alocacoes_escola_clie_ativo
    ON public.inove_alocacoes_escola (id_clie, ativo)
    WHERE ativo = TRUE;

COMMENT ON TABLE public.inove_alocacoes_escola IS
  'Alocação docente empurrada pelo School (Secretaria). Fonte da verdade institucional.';

-- ---------------------------------------------------------------------------
-- Eventos School chegados antes da conta B2C existir
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.inove_school_pending (
    id              BIGSERIAL PRIMARY KEY,
    email           VARCHAR(320) NOT NULL,
    event_type      VARCHAR(80) NOT NULL,
    payload         JSONB NOT NULL DEFAULT '{}'::jsonb,
    school_key      VARCHAR(120),
    processed_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_inove_school_pending_email_open
    ON public.inove_school_pending (lower(email), created_at)
    WHERE processed_at IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_inove_school_pending_key_open
    ON public.inove_school_pending (event_type, school_key)
    WHERE processed_at IS NULL AND school_key IS NOT NULL;

COMMENT ON TABLE public.inove_school_pending IS
  'Convites/alocações School aguardando conta B2C (replay no aceite).';

COMMIT;
