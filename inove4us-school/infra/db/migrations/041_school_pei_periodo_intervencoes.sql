-- PEI individual: período letivo (recorte do dossiê) + cronograma simples.

BEGIN;

ALTER TABLE public.school_pei_alunos
    ADD COLUMN IF NOT EXISTS periodo_letivo_id UUID
        REFERENCES public.school_periodos_letivos (id) ON DELETE SET NULL;

ALTER TABLE public.school_pei_alunos
    ADD COLUMN IF NOT EXISTS intervencoes_previstas JSONB NOT NULL DEFAULT '[]'::jsonb;

CREATE INDEX IF NOT EXISTS idx_school_pei_alunos_periodo
    ON public.school_pei_alunos (periodo_letivo_id)
    WHERE periodo_letivo_id IS NOT NULL;

COMMENT ON COLUMN public.school_pei_alunos.periodo_letivo_id IS
  'Período letivo declarado neste PEI — recorte temporal do Relatório de Execução.';
COMMENT ON COLUMN public.school_pei_alunos.intervencoes_previstas IS
  'Cronograma sumário: [{descricao, frequencia, observacao}].';

COMMIT;
