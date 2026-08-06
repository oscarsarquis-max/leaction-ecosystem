-- Rollback 025_audit_trail_assinaturas.sql
BEGIN;

DROP INDEX IF EXISTS public.uq_school_pei_alunos_linha_versao;
DROP INDEX IF EXISTS public.idx_school_pei_alunos_linha_versao;
DROP INDEX IF EXISTS public.idx_school_pei_alunos_inst_status;

ALTER TABLE public.school_pei_alunos
    DROP COLUMN IF EXISTS data_assinatura_coordenador,
    DROP COLUMN IF EXISTS data_assinatura_psicopedagogo,
    DROP COLUMN IF EXISTS versao,
    DROP COLUMN IF EXISTS pei_linha_id,
    DROP COLUMN IF EXISTS status;

ALTER TABLE public.school_aee_matrizes
    DROP COLUMN IF EXISTS data_assinatura_coordenador,
    DROP COLUMN IF EXISTS data_assinatura_psicopedagogo;

COMMIT;
