BEGIN;
DROP TABLE IF EXISTS public.school_alocacoes_docentes CASCADE;
DROP INDEX IF EXISTS public.idx_school_disciplinas_instituicao;
-- curso_id permanece nullable (reversão total de NOT NULL exigiria limpeza de NULLs).
ALTER TABLE public.school_disciplinas
    DROP COLUMN IF EXISTS instituicao_id;
COMMIT;
