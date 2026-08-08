-- 029: hierarquia Período → Curso → Turma (curso opcional na turma)
-- school_cursos já existe (015). Disciplinas.curso_id já nullable (019).

ALTER TABLE public.school_turmas
    ADD COLUMN IF NOT EXISTS periodo_letivo_id UUID
        REFERENCES public.school_periodos_letivos (id) ON DELETE RESTRICT;

ALTER TABLE public.school_turmas
    ADD COLUMN IF NOT EXISTS curso_id UUID
        REFERENCES public.school_cursos (id) ON DELETE SET NULL;

-- Backfill: período da mesma instituição cujo ano de início = ano_letivo da turma
UPDATE public.school_turmas t
SET periodo_letivo_id = p.id
FROM public.school_periodos_letivos p
WHERE t.periodo_letivo_id IS NULL
  AND p.instituicao_id = t.instituicao_id
  AND EXTRACT(YEAR FROM p.data_inicio)::int = t.ano_letivo;

-- Fallback: período mais recente da instituição
UPDATE public.school_turmas t
SET periodo_letivo_id = sub.pid
FROM (
    SELECT DISTINCT ON (p.instituicao_id)
           p.instituicao_id,
           p.id AS pid
    FROM public.school_periodos_letivos p
    ORDER BY p.instituicao_id, p.data_inicio DESC
) sub
WHERE t.periodo_letivo_id IS NULL
  AND t.instituicao_id = sub.instituicao_id;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM public.school_turmas WHERE periodo_letivo_id IS NULL
    ) THEN
        RAISE EXCEPTION
            '029: school_turmas sem periodo_letivo_id após backfill — crie um período letivo na instituição';
    END IF;
END $$;

ALTER TABLE public.school_turmas
    ALTER COLUMN periodo_letivo_id SET NOT NULL;

CREATE INDEX IF NOT EXISTS idx_school_turmas_periodo
    ON public.school_turmas (periodo_letivo_id);

CREATE INDEX IF NOT EXISTS idx_school_turmas_curso
    ON public.school_turmas (curso_id)
    WHERE curso_id IS NOT NULL;

COMMENT ON COLUMN public.school_turmas.periodo_letivo_id IS
  'Período letivo da turma (hierarquia Estrutura Acadêmica).';
COMMENT ON COLUMN public.school_turmas.curso_id IS
  'Curso opcional (híbrido). NULL = turma flat no período, sem curso.';
COMMENT ON COLUMN public.school_turmas.ano_letivo IS
  'Mantido por compatibilidade; preferir derivar do período letivo na UI.';
