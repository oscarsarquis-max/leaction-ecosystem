-- inove4us School — hierarquia acadêmica alinhada ao B2C (integração futura).
-- Numeração: 015.
--
-- Cadeia: instituição → unidade → período letivo → curso → disciplina (ementa).
-- Espelha inove_periodos_letivos / inove_cursos / inove_disciplinas, com UUID
-- e vínculo a school_unidades (School é multi-unidade; B2C não tem unidade).
--
-- Sem alunos nesta frente (produto não controla dossiê de aluno na Secretaria).

BEGIN;

-- ---------------------------------------------------------------------------
-- 1) Período letivo
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.school_periodos_letivos (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instituicao_id    UUID NOT NULL
        REFERENCES public.school_instituicoes (id) ON DELETE CASCADE,
    unidade_id        UUID
        REFERENCES public.school_unidades (id) ON DELETE CASCADE,
    rotulo            TEXT NOT NULL,
    ano_letivo        INTEGER NOT NULL
        CHECK (ano_letivo BETWEEN 1990 AND 2100),
    tipo_periodo      TEXT NOT NULL DEFAULT 'semestral'
        CHECK (tipo_periodo IN ('anual', 'semestral', 'trimestral', 'modular')),
    etapa             TEXT,
    data_inicio       DATE NOT NULL,
    data_fim          DATE NOT NULL,
    status            TEXT NOT NULL DEFAULT 'planejamento'
        CHECK (status IN ('planejamento', 'em_andamento', 'encerrado')),
    em_curso          BOOLEAN NOT NULL DEFAULT FALSE,
    ativo             BOOLEAN NOT NULL DEFAULT TRUE,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_school_periodo_datas CHECK (data_fim > data_inicio)
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_school_periodo_em_curso_por_unidade
    ON public.school_periodos_letivos (instituicao_id, COALESCE(unidade_id, '00000000-0000-0000-0000-000000000000'::uuid))
    WHERE em_curso = TRUE AND ativo = TRUE;

CREATE INDEX IF NOT EXISTS idx_school_periodos_instituicao
    ON public.school_periodos_letivos (instituicao_id, ativo, ano_letivo DESC);

CREATE INDEX IF NOT EXISTS idx_school_periodos_unidade
    ON public.school_periodos_letivos (unidade_id)
    WHERE unidade_id IS NOT NULL;

COMMENT ON TABLE public.school_periodos_letivos IS
  'Período letivo (espelho B2C). unidade_id NULL = institucional; preenchido = só aquela unidade.';

-- ---------------------------------------------------------------------------
-- 2) Curso (dentro do período)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.school_cursos (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    periodo_letivo_id UUID NOT NULL
        REFERENCES public.school_periodos_letivos (id) ON DELETE CASCADE,
    nome              TEXT NOT NULL,
    nivel             TEXT
        CHECK (
            nivel IS NULL OR nivel IN (
                'fundamental', 'medio', 'tecnico', 'superior',
                'livre', 'corporativo', 'idiomas', 'outro'
            )
        ),
    turma_turno       TEXT,
    observacoes       TEXT,
    ativo             BOOLEAN NOT NULL DEFAULT TRUE,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_school_cursos_periodo
    ON public.school_cursos (periodo_letivo_id, ativo)
    WHERE ativo = TRUE;

COMMENT ON TABLE public.school_cursos IS
  'Curso ofertado em um período letivo (alinhado a inove_cursos).';

-- ---------------------------------------------------------------------------
-- 3) Disciplina + ementa (dentro do curso)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.school_disciplinas (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    curso_id            UUID NOT NULL
        REFERENCES public.school_cursos (id) ON DELETE CASCADE,
    nome                TEXT NOT NULL,
    codigo              TEXT,
    carga_horaria_horas NUMERIC(8, 2),
    ementa              TEXT,
    ativo               BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_school_disciplinas_curso
    ON public.school_disciplinas (curso_id, ativo)
    WHERE ativo = TRUE;

COMMENT ON TABLE public.school_disciplinas IS
  'Disciplina do curso; ementa fica aqui (mesmo contrato do B2C inove_disciplinas).';
COMMENT ON COLUMN public.school_disciplinas.ementa IS
  'Ementa da disciplina no contexto do curso.';

COMMIT;
