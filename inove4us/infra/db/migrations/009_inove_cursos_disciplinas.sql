-- Estruturação Pedagógica — Etapa 2/4: Cursos + Disciplinas
-- Autorização do professor: JOIN até inove_instituicoes.id_clie (igual períodos).
-- Freemium: FKs futuras em aulas serão opcionais.
--
-- Aplicar:
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f infra/db/migrations/009_inove_cursos_disciplinas.sql

BEGIN;

CREATE TABLE IF NOT EXISTS public.inove_cursos (
    id                          BIGSERIAL PRIMARY KEY,
    periodo_letivo_id           BIGINT NOT NULL
                                  REFERENCES public.inove_periodos_letivos (id) ON DELETE CASCADE,
    nome                        VARCHAR(255) NOT NULL,
    nivel                       VARCHAR(40)
                                  CHECK (
                                    nivel IS NULL OR nivel IN (
                                      'fundamental',
                                      'medio',
                                      'tecnico',
                                      'superior',
                                      'livre',
                                      'corporativo',
                                      'idiomas',
                                      'outro'
                                    )
                                  ),
    turma_turno                 VARCHAR(120),
    carga_horaria_total_horas   NUMERIC(8, 2),
    observacoes                 TEXT,
    ativo                       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_inove_cursos_periodo_ativo
    ON public.inove_cursos (periodo_letivo_id, ativo)
    WHERE ativo = TRUE;

CREATE INDEX IF NOT EXISTS idx_inove_cursos_periodo_nome
    ON public.inove_cursos (periodo_letivo_id, lower(nome));

COMMENT ON TABLE public.inove_cursos IS
  'Curso ofertado em um período letivo (registro novo a cada período; sem catálogo compartilhado).';

CREATE TABLE IF NOT EXISTS public.inove_disciplinas (
    id                      BIGSERIAL PRIMARY KEY,
    curso_id                BIGINT NOT NULL
                              REFERENCES public.inove_cursos (id) ON DELETE CASCADE,
    nome                    VARCHAR(255) NOT NULL,
    codigo                  VARCHAR(80),
    carga_horaria_horas     NUMERIC(8, 2),
    ementa                  TEXT,
    ativo                   BOOLEAN NOT NULL DEFAULT TRUE,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_inove_disciplinas_curso_ativo
    ON public.inove_disciplinas (curso_id, ativo)
    WHERE ativo = TRUE;

CREATE INDEX IF NOT EXISTS idx_inove_disciplinas_curso_nome
    ON public.inove_disciplinas (curso_id, lower(nome));

COMMENT ON TABLE public.inove_disciplinas IS
  'Disciplina dentro de um curso; soft-delete via ativo.';

COMMIT;
