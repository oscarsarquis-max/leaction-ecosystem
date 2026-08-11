-- Curso 1:N Turmas (antes turma_turno era 1:1 no curso)
--
-- Aplicar:
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f infra/db/migrations/027_inove_turmas.sql

BEGIN;

CREATE TABLE IF NOT EXISTS public.inove_turmas (
    id              BIGSERIAL PRIMARY KEY,
    curso_id        BIGINT NOT NULL
                      REFERENCES public.inove_cursos (id) ON DELETE CASCADE,
    nome            VARCHAR(120) NOT NULL,
    turno           VARCHAR(40),
    ativo           BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_inove_turmas_curso_ativo
    ON public.inove_turmas (curso_id, ativo)
    WHERE ativo = TRUE;

CREATE UNIQUE INDEX IF NOT EXISTS uq_inove_turmas_curso_nome_ativo
    ON public.inove_turmas (curso_id, lower(nome))
    WHERE ativo = TRUE;

COMMENT ON TABLE public.inove_turmas IS
  'Turma vinculada a um curso (1 curso → N turmas).';

-- Migra turma_turno legado (um valor → uma turma)
INSERT INTO public.inove_turmas (curso_id, nome, turno)
SELECT c.id,
       trim(c.turma_turno),
       NULL
  FROM public.inove_cursos c
 WHERE c.ativo = TRUE
   AND c.turma_turno IS NOT NULL
   AND trim(c.turma_turno) <> ''
   AND NOT EXISTS (
         SELECT 1 FROM public.inove_turmas t
          WHERE t.curso_id = c.id
            AND t.ativo = TRUE
            AND lower(t.nome) = lower(trim(c.turma_turno))
       );

COMMIT;
