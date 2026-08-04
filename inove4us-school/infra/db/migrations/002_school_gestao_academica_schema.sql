-- inove4us School (B2B) — Pilar 1: Gestão Acadêmica (onde, quando, o quê).
-- Pré-requisito: 001_school_b2b_schema.sql (school_instituicoes).
-- Prefixo obrigatório: school_*
-- Aplicar: via bootstrap-db.ps1 ou
--   psql -h 127.0.0.1 -p 5434 -U admin -d inove4us_school -v ON_ERROR_STOP=1 \
--     -f infra/db/migrations/002_school_gestao_academica_schema.sql
--
-- Fora de escopo: PEI, school_professor_turma, catálogo de metodologias.

BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ---------------------------------------------------------------------------
-- 1) Turmas
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.school_turmas (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instituicao_id  UUID NOT NULL
        REFERENCES public.school_instituicoes (id) ON DELETE CASCADE,
    nome            TEXT NOT NULL,
    serie_ano       TEXT NOT NULL,
    turno           TEXT NOT NULL,
    ano_letivo      INTEGER NOT NULL,
    ativa           BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_school_turmas_inst_nome_ano
        UNIQUE (instituicao_id, nome, ano_letivo),
    CONSTRAINT chk_school_turmas_turno
        CHECK (turno IN ('manha', 'tarde', 'integral', 'noite'))
);

CREATE INDEX IF NOT EXISTS idx_school_turmas_instituicao
    ON public.school_turmas (instituicao_id);

CREATE INDEX IF NOT EXISTS idx_school_turmas_ano_letivo
    ON public.school_turmas (instituicao_id, ano_letivo)
    WHERE ativa = TRUE;

COMMENT ON TABLE public.school_turmas IS
  'Turmas por instituição/ano letivo (ex.: "6º Ano A"). Pré-requisito para vínculo professor↔turma.';
COMMENT ON COLUMN public.school_turmas.turno IS
  'manha | tarde | integral | noite';

-- ---------------------------------------------------------------------------
-- 2) Alunos — dossiê base (pré-requisito do futuro PEI individualizado)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.school_alunos (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instituicao_id    UUID NOT NULL
        REFERENCES public.school_instituicoes (id) ON DELETE CASCADE,
    turma_id          UUID
        REFERENCES public.school_turmas (id) ON DELETE SET NULL,
    nome              TEXT NOT NULL,
    matricula         TEXT NOT NULL,
    data_nascimento   DATE,
    ativo             BOOLEAN NOT NULL DEFAULT TRUE,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_school_alunos_inst_matricula
        UNIQUE (instituicao_id, matricula)
);

CREATE INDEX IF NOT EXISTS idx_school_alunos_instituicao
    ON public.school_alunos (instituicao_id);

CREATE INDEX IF NOT EXISTS idx_school_alunos_turma
    ON public.school_alunos (turma_id)
    WHERE turma_id IS NOT NULL;

COMMENT ON TABLE public.school_alunos IS
  'Dossiê base do aluno. Pré-requisito direto para school_pei_individualizado (etapa 3).';
COMMENT ON COLUMN public.school_alunos.turma_id IS
  'NULLABLE: aluno pode existir sem turma atribuída ainda.';

-- ---------------------------------------------------------------------------
-- 3) Calendário letivo
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.school_calendario_letivo (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instituicao_id  UUID NOT NULL
        REFERENCES public.school_instituicoes (id) ON DELETE CASCADE,
    titulo          TEXT NOT NULL,
    tipo            TEXT NOT NULL,
    data_inicio     DATE NOT NULL,
    data_fim        DATE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_school_calendario_tipo
        CHECK (tipo IN ('letivo', 'feriado', 'avaliacao', 'evento'))
);

CREATE INDEX IF NOT EXISTS idx_school_calendario_instituicao
    ON public.school_calendario_letivo (instituicao_id);

CREATE INDEX IF NOT EXISTS idx_school_calendario_periodo
    ON public.school_calendario_letivo (instituicao_id, data_inicio, data_fim);

COMMENT ON TABLE public.school_calendario_letivo IS
  'Eventos do calendário letivo: datas letivas, feriados, avaliações e eventos.';
COMMENT ON COLUMN public.school_calendario_letivo.tipo IS
  'letivo | feriado | avaliacao | evento';

-- ---------------------------------------------------------------------------
-- 4) Currículo — disciplinas/ementas por série
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.school_curriculo (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instituicao_id  UUID NOT NULL
        REFERENCES public.school_instituicoes (id) ON DELETE CASCADE,
    serie_ano       TEXT NOT NULL,
    disciplina      TEXT NOT NULL,
    ementa          TEXT,
    ativo           BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_school_curriculo_inst_serie_disc
        UNIQUE (instituicao_id, serie_ano, disciplina)
);

CREATE INDEX IF NOT EXISTS idx_school_curriculo_instituicao
    ON public.school_curriculo (instituicao_id);

CREATE INDEX IF NOT EXISTS idx_school_curriculo_serie
    ON public.school_curriculo (instituicao_id, serie_ano)
    WHERE ativo = TRUE;

COMMENT ON TABLE public.school_curriculo IS
  'Disciplinas/ementas por série-ano, por instituição.';

COMMIT;
