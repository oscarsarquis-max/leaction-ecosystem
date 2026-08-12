-- Catálogo curricular N:N (curso ↔ disciplina) + turma sempre vinculada a curso.
-- Reverte o híbrido "curso opcional" (019/029, nó Sem curso).
--
-- Escolha: DROP de school_disciplinas.curso_id após migrar para
-- school_curso_disciplinas (sem ciclo de depreciação — o modelo híbrido
-- era recente e o dado sem curso é só smoke/seed).
--
-- Alocação normativa continua em school_alocacoes_docentes
-- (professor_vinculo_id + turma_id + disciplina_id). school_professor_turma
-- é legado (disciplina TEXT, 0 linhas) e não é o mecanismo da Secretaria.

BEGIN;

-- ---------------------------------------------------------------------------
-- 1) Turmas sem curso (smoke/seed) → um curso do mesmo período
-- ---------------------------------------------------------------------------
UPDATE public.school_turmas t
SET curso_id = sub.curso_id
FROM (
    SELECT
        t2.id AS turma_id,
        (
            SELECT c.id
            FROM public.school_cursos c
            WHERE c.periodo_letivo_id = t2.periodo_letivo_id
            ORDER BY
                CASE
                    WHEN t2.nome ILIKE '%6%' AND c.nome ILIKE '%6%' THEN 0
                    WHEN c.nome ILIKE '%smoke%' THEN 1
                    ELSE 2
                END,
                c.created_at NULLS LAST
            LIMIT 1
        ) AS curso_id
    FROM public.school_turmas t2
    WHERE t2.curso_id IS NULL
) sub
WHERE t.id = sub.turma_id
  AND t.curso_id IS NULL
  AND sub.curso_id IS NOT NULL;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM public.school_turmas WHERE curso_id IS NULL) THEN
        RAISE EXCEPTION
            '034: ainda há turmas sem curso_id — recusar NOT NULL';
    END IF;
END $$;

ALTER TABLE public.school_turmas
    ALTER COLUMN curso_id SET NOT NULL;

COMMENT ON COLUMN public.school_turmas.curso_id IS
  'Curso da turma (obrigatório). Turma é unidade temporal de execução de um curso.';

-- ---------------------------------------------------------------------------
-- 2) Catálogo N:N
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.school_curso_disciplinas (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    curso_id        UUID NOT NULL
        REFERENCES public.school_cursos (id) ON DELETE CASCADE,
    disciplina_id   UUID NOT NULL
        REFERENCES public.school_disciplinas (id) ON DELETE CASCADE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_school_curso_disciplina UNIQUE (curso_id, disciplina_id)
);

CREATE INDEX IF NOT EXISTS idx_school_curso_disciplinas_disc
    ON public.school_curso_disciplinas (disciplina_id);

INSERT INTO public.school_curso_disciplinas (curso_id, disciplina_id)
SELECT d.curso_id, d.id
FROM public.school_disciplinas d
WHERE d.curso_id IS NOT NULL
ON CONFLICT (curso_id, disciplina_id) DO NOTHING;

COMMENT ON TABLE public.school_curso_disciplinas IS
  'Catálogo curricular normativo N:N. Uma disciplina institucional pode estar em vários cursos.';

-- ---------------------------------------------------------------------------
-- 3) Disciplina vira catálogo institucional (sem dono fixo de curso)
-- ---------------------------------------------------------------------------
ALTER TABLE public.school_disciplinas
    DROP CONSTRAINT IF EXISTS school_disciplinas_curso_id_fkey;

DROP INDEX IF EXISTS idx_school_disciplinas_curso;

ALTER TABLE public.school_disciplinas
    DROP COLUMN IF EXISTS curso_id;

COMMENT ON TABLE public.school_disciplinas IS
  'Disciplina do catálogo institucional. Vínculo a cursos = school_curso_disciplinas.';

-- ---------------------------------------------------------------------------
-- 4) Habilitação professor↔disciplina (informativo — não trava alocação)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.school_professor_disciplina_habilitacao (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    professor_vinculo_id    UUID NOT NULL
        REFERENCES public.school_professores_vinculo (id) ON DELETE CASCADE,
    disciplina_id           UUID NOT NULL
        REFERENCES public.school_disciplinas (id) ON DELETE CASCADE,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_school_prof_disc_habilitacao
        UNIQUE (professor_vinculo_id, disciplina_id)
);

CREATE INDEX IF NOT EXISTS idx_school_prof_disc_hab_disc
    ON public.school_professor_disciplina_habilitacao (disciplina_id);

COMMENT ON TABLE public.school_professor_disciplina_habilitacao IS
  'Habilitação informativa. Não filtra nem bloqueia school_alocacoes_docentes.';

COMMIT;
