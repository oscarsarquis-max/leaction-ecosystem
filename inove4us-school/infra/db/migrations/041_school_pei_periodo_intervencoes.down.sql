BEGIN;

DROP INDEX IF EXISTS public.idx_school_pei_alunos_periodo;
ALTER TABLE public.school_pei_alunos DROP COLUMN IF EXISTS intervencoes_previstas;
ALTER TABLE public.school_pei_alunos DROP COLUMN IF EXISTS periodo_letivo_id;

COMMIT;
