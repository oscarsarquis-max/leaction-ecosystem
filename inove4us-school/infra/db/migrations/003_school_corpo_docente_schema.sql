-- inove4us School (B2B) — Pilar 2: Corpo Docente (papel professor↔turma↔disciplina).
-- Pré-requisitos:
--   001_school_b2b_schema.sql (school_professores_vinculo)
--   002_school_gestao_academica_schema.sql (school_turmas)
-- Prefixo obrigatório: school_*
-- Aplicar: via bootstrap-db.ps1 ou
--   psql -h 127.0.0.1 -p 5434 -U admin -d inove4us_school -v ON_ERROR_STOP=1 \
--     -f infra/db/migrations/003_school_corpo_docente_schema.sql
--
-- Fora de escopo: catálogo de metodologias, PEI, endpoints Flask, telas FE.

BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ---------------------------------------------------------------------------
-- Papel do professor por turma e disciplina
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.school_professor_turma (
    id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    professor_vinculo_id   UUID NOT NULL
        REFERENCES public.school_professores_vinculo (id) ON DELETE CASCADE,
    turma_id               UUID NOT NULL
        REFERENCES public.school_turmas (id) ON DELETE CASCADE,
    disciplina             TEXT NOT NULL,
    ativo                  BOOLEAN NOT NULL DEFAULT TRUE,
    created_at             TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at             TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_school_professor_turma_vinculo_turma_disc
        UNIQUE (professor_vinculo_id, turma_id, disciplina)
);

CREATE INDEX IF NOT EXISTS idx_school_professor_turma_vinculo
    ON public.school_professor_turma (professor_vinculo_id);

CREATE INDEX IF NOT EXISTS idx_school_professor_turma_turma
    ON public.school_professor_turma (turma_id);

CREATE INDEX IF NOT EXISTS idx_school_professor_turma_ativo
    ON public.school_professor_turma (turma_id, disciplina)
    WHERE ativo = TRUE;

COMMENT ON TABLE public.school_professor_turma IS
  'Papel do professor por turma e disciplina. Liga school_professores_vinculo a school_turmas.';
COMMENT ON COLUMN public.school_professor_turma.professor_vinculo_id IS
  'FK para o vínculo professor↔escola (school_professores_vinculo).';
COMMENT ON COLUMN public.school_professor_turma.turma_id IS
  'FK para a turma (school_turmas).';
COMMENT ON COLUMN public.school_professor_turma.disciplina IS
  'Disciplina que o professor leciona nesta turma.';

COMMIT;
