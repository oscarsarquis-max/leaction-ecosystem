-- Espelho B2C: disciplina School única por instituição do professor + catálogo N:N.
-- Alinha inove_disciplinas ao modelo do School (034_school_curso_disciplina_nn).
--
-- Unicidade School: (instituicao_id, school_disciplina_id) — o espelho é por
-- professor (inove_instituicoes.id_clie), não global no UUID do School.
--
-- Aplicar:
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f infra/db/migrations/033_inove_curso_disciplinas_nn.sql

BEGIN;

-- ---------------------------------------------------------------------------
-- 1) Escopo da unicidade School (árvore do professor)
-- ---------------------------------------------------------------------------
ALTER TABLE public.inove_disciplinas
    ADD COLUMN IF NOT EXISTS instituicao_id BIGINT
        REFERENCES public.inove_instituicoes (id) ON DELETE SET NULL;

UPDATE public.inove_disciplinas d
SET instituicao_id = p.instituicao_id
FROM public.inove_cursos c
JOIN public.inove_periodos_letivos p ON p.id = c.periodo_letivo_id
WHERE d.curso_id = c.id
  AND d.instituicao_id IS NULL;

CREATE INDEX IF NOT EXISTS idx_inove_disciplinas_instituicao
    ON public.inove_disciplinas (instituicao_id)
    WHERE instituicao_id IS NOT NULL;

-- ---------------------------------------------------------------------------
-- 2) Catálogo N:N (ids locais B2C; idempotência = UNIQUE par)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.inove_curso_disciplinas (
    id              BIGSERIAL PRIMARY KEY,
    curso_id        BIGINT NOT NULL
        REFERENCES public.inove_cursos (id) ON DELETE CASCADE,
    disciplina_id   BIGINT NOT NULL
        REFERENCES public.inove_disciplinas (id) ON DELETE CASCADE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_inove_curso_disciplina UNIQUE (curso_id, disciplina_id)
);

CREATE INDEX IF NOT EXISTS idx_inove_curso_disciplinas_disc
    ON public.inove_curso_disciplinas (disciplina_id);

COMMENT ON TABLE public.inove_curso_disciplinas IS
  'Catálogo N:N curso↔disciplina. Espelha school_curso_disciplinas (origem School) e o vínculo 1:N autônomo via curso_id.';

INSERT INTO public.inove_curso_disciplinas (curso_id, disciplina_id)
SELECT d.curso_id, d.id
FROM public.inove_disciplinas d
WHERE d.curso_id IS NOT NULL
ON CONFLICT (curso_id, disciplina_id) DO NOTHING;

-- ---------------------------------------------------------------------------
-- 3) Consolidar duplicatas 1:N (mesmo school_disciplina_id na mesma instituição)
--    Canônica = menor id. Reponta FKs; nenhum histórico de aula/plano se perde.
-- ---------------------------------------------------------------------------
DO $$
DECLARE
    rec RECORD;
    canon BIGINT;
    dup BIGINT;
BEGIN
    FOR rec IN
        SELECT instituicao_id, school_disciplina_id, MIN(id) AS canon_id
        FROM public.inove_disciplinas
        WHERE school_disciplina_id IS NOT NULL
          AND instituicao_id IS NOT NULL
          AND ativo = TRUE
        GROUP BY instituicao_id, school_disciplina_id
        HAVING COUNT(*) > 1
    LOOP
        canon := rec.canon_id;
        FOR dup IN
            SELECT id
            FROM public.inove_disciplinas
            WHERE instituicao_id = rec.instituicao_id
              AND school_disciplina_id = rec.school_disciplina_id
              AND id <> canon
        LOOP
            UPDATE public.inove_aulas_simples
               SET disciplina_id = canon
             WHERE disciplina_id = dup;
            UPDATE public.inove_agenda_eventos
               SET disciplina_id = canon
             WHERE disciplina_id = dup;
            UPDATE public.inove_alocacoes_escola
               SET disciplina_id = canon
             WHERE disciplina_id = dup;
            UPDATE public.inove_desafios
               SET disciplina_id = canon
             WHERE disciplina_id = dup;

            INSERT INTO public.inove_curso_disciplinas (curso_id, disciplina_id)
            SELECT d.curso_id, canon
            FROM public.inove_disciplinas d
            WHERE d.id = dup AND d.curso_id IS NOT NULL
            ON CONFLICT (curso_id, disciplina_id) DO NOTHING;

            INSERT INTO public.inove_curso_disciplinas (curso_id, disciplina_id)
            SELECT cd.curso_id, canon
            FROM public.inove_curso_disciplinas cd
            WHERE cd.disciplina_id = dup
            ON CONFLICT (curso_id, disciplina_id) DO NOTHING;

            DELETE FROM public.inove_curso_disciplinas
            WHERE disciplina_id = dup;

            UPDATE public.inove_disciplinas
               SET ativo = FALSE,
                   updated_at = CURRENT_TIMESTAMP
             WHERE id = dup;
        END LOOP;
    END LOOP;
END $$;

-- ---------------------------------------------------------------------------
-- 4) Unicidade: uma linha School por instituição do professor
-- ---------------------------------------------------------------------------
DROP INDEX IF EXISTS uq_inove_disciplina_school_por_curso;

CREATE UNIQUE INDEX IF NOT EXISTS uq_inove_disciplina_school_por_instituicao
    ON public.inove_disciplinas (instituicao_id, school_disciplina_id)
    WHERE school_disciplina_id IS NOT NULL
      AND instituicao_id IS NOT NULL
      AND ativo = TRUE;

COMMENT ON TABLE public.inove_disciplinas IS
  'Disciplina do professor. Autônomo: dono via curso_id. School: única por (instituicao_id, school_disciplina_id); cursos em inove_curso_disciplinas.';

COMMIT;
