-- Estruturação Pedagógica — Etapa 1/4: Instituição + Período Letivo
-- Professor dono = ctdi_clie.id_clie (cadastro privado por professor).
-- FKs futuras em aulas/cursos serão opcionais (freemium sem trava).
--
-- Aplicar:
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f infra/db/migrations/008_inove_instituicoes_periodos_letivos.sql

BEGIN;

CREATE TABLE IF NOT EXISTS public.inove_instituicoes (
    id                  BIGSERIAL PRIMARY KEY,
    id_clie             INTEGER NOT NULL
                          REFERENCES public.ctdi_clie (id_clie) ON DELETE CASCADE,
    nome                VARCHAR(255) NOT NULL,
    tipo_instituicao    VARCHAR(40) NOT NULL
                          CHECK (tipo_instituicao IN (
                            'escola',
                            'faculdade_universidade',
                            'curso_tecnico',
                            'curso_livre',
                            'corporativo',
                            'outro'
                          )),
    segmento            VARCHAR(120),
    rede                VARCHAR(20) NOT NULL DEFAULT 'nao_informado'
                          CHECK (rede IN ('publica', 'privada', 'nao_informado')),
    cidade              VARCHAR(120),
    uf                  VARCHAR(8),
    pais                VARCHAR(8) NOT NULL DEFAULT 'BR',
    observacoes         TEXT,
    ativo               BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_inove_instituicoes_clie_ativo
    ON public.inove_instituicoes (id_clie, ativo)
    WHERE ativo = TRUE;

CREATE INDEX IF NOT EXISTS idx_inove_instituicoes_clie_nome
    ON public.inove_instituicoes (id_clie, lower(nome));

COMMENT ON TABLE public.inove_instituicoes IS
  'Instituição de ensino do professor (dono = id_clie). Cadastro privado por professor.';

CREATE TABLE IF NOT EXISTS public.inove_periodos_letivos (
    id                          BIGSERIAL PRIMARY KEY,
    instituicao_id              BIGINT NOT NULL
                                  REFERENCES public.inove_instituicoes (id) ON DELETE CASCADE,
    rotulo                      VARCHAR(160) NOT NULL,
    ano_letivo                  INTEGER NOT NULL
                                  CHECK (ano_letivo BETWEEN 1990 AND 2100),
    tipo_periodo                VARCHAR(20) NOT NULL
                                  CHECK (tipo_periodo IN (
                                    'anual', 'semestral', 'trimestral', 'modular'
                                  )),
    etapa                       VARCHAR(80),
    data_inicio                 DATE NOT NULL,
    data_fim                    DATE NOT NULL,
    carga_horaria_total_horas   NUMERIC(8, 2),
    duracao_padrao_aula_min     INTEGER NOT NULL DEFAULT 50
                                  CHECK (duracao_padrao_aula_min BETWEEN 5 AND 480),
    dias_semana_letivos         JSONB NOT NULL DEFAULT '["seg","ter","qua","qui","sex"]'::jsonb,
    status                      VARCHAR(20) NOT NULL DEFAULT 'planejamento'
                                  CHECK (status IN (
                                    'planejamento', 'em_andamento', 'encerrado'
                                  )),
    em_curso                    BOOLEAN NOT NULL DEFAULT FALSE,
    ativo                       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_inove_periodo_datas CHECK (data_fim > data_inicio)
);

-- No máximo 1 período "em curso" por instituição (entre os ativos).
CREATE UNIQUE INDEX IF NOT EXISTS uq_inove_periodo_em_curso_por_instituicao
    ON public.inove_periodos_letivos (instituicao_id)
    WHERE em_curso = TRUE AND ativo = TRUE;

CREATE INDEX IF NOT EXISTS idx_inove_periodos_instituicao
    ON public.inove_periodos_letivos (instituicao_id, ativo, ano_letivo DESC);

COMMENT ON TABLE public.inove_periodos_letivos IS
  'Período letivo por instituição; em_curso marca o período atual (1 por instituição).';
COMMENT ON COLUMN public.inove_periodos_letivos.duracao_padrao_aula_min IS
  'Default 50 min — alinhado ao vetor Dia a Dia.';

COMMIT;
