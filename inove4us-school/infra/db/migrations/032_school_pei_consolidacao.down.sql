-- Rollback 032 — NÃO recria o legado Ciclo Vivo (dados já descartados).
-- Apenas relaxa aluno_id para permitir o schema pré-consolidação parcial.

BEGIN;

ALTER TABLE public.school_pei_alunos
    DROP CONSTRAINT IF EXISTS school_pei_alunos_aluno_id_fkey;

DROP INDEX IF EXISTS public.idx_school_pei_alunos_aluno;

ALTER TABLE public.school_pei_alunos
    ALTER COLUMN aluno_id DROP NOT NULL;

-- Legado não é recriado neste down (decisão de produto: AEE/pei_alunos é canônico).

COMMIT;
