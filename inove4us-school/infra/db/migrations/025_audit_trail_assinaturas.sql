-- Carimbos de auditoria de assinaturas (AEE + PEI) e versionamento do PEI.

BEGIN;

-- ---------------------------------------------------------------------------
-- AEE: timestamps nominais de assinatura
-- ---------------------------------------------------------------------------
ALTER TABLE public.school_aee_matrizes
    ADD COLUMN IF NOT EXISTS data_assinatura_coordenador TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS data_assinatura_psicopedagogo TIMESTAMPTZ;

COMMENT ON COLUMN public.school_aee_matrizes.data_assinatura_coordenador IS
  'Carimbo UTC do clique de assinatura do coordenador.';
COMMENT ON COLUMN public.school_aee_matrizes.data_assinatura_psicopedagogo IS
  'Carimbo UTC do clique de assinatura do psicopedagogo.';

-- ---------------------------------------------------------------------------
-- PEI: timestamps + versão + linha (grupo de versões do mesmo aluno)
-- ---------------------------------------------------------------------------
ALTER TABLE public.school_pei_alunos
    ADD COLUMN IF NOT EXISTS data_assinatura_coordenador TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS data_assinatura_psicopedagogo TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS versao INTEGER NOT NULL DEFAULT 1,
    ADD COLUMN IF NOT EXISTS pei_linha_id UUID,
    ADD COLUMN IF NOT EXISTS status VARCHAR(32) NOT NULL DEFAULT 'rascunho';

-- Backfill: cada registro atual é a linha e a v1
UPDATE public.school_pei_alunos
SET pei_linha_id = id
WHERE pei_linha_id IS NULL;

ALTER TABLE public.school_pei_alunos
    ALTER COLUMN pei_linha_id SET NOT NULL;

-- Status derivado para já assinados
UPDATE public.school_pei_alunos
SET status = 'ativo'
WHERE assinado_coordenador = TRUE
  AND assinado_psicopedagogo = TRUE
  AND status = 'rascunho';

-- Backfill carimbos a partir de data_assinatura legada (quando ambas já assinadas)
UPDATE public.school_aee_matrizes
SET data_assinatura_coordenador = COALESCE(data_assinatura_coordenador, updated_at),
    data_assinatura_psicopedagogo = COALESCE(data_assinatura_psicopedagogo, updated_at)
WHERE assinado_coordenador = TRUE
  AND assinado_psicopedagogo = TRUE
  AND (data_assinatura_coordenador IS NULL OR data_assinatura_psicopedagogo IS NULL);

UPDATE public.school_pei_alunos
SET data_assinatura_coordenador = COALESCE(data_assinatura_coordenador, data_assinatura, updated_at),
    data_assinatura_psicopedagogo = COALESCE(data_assinatura_psicopedagogo, data_assinatura, updated_at)
WHERE assinado_coordenador = TRUE
  AND assinado_psicopedagogo = TRUE
  AND (data_assinatura_coordenador IS NULL OR data_assinatura_psicopedagogo IS NULL);

CREATE INDEX IF NOT EXISTS idx_school_pei_alunos_linha_versao
    ON public.school_pei_alunos (pei_linha_id, versao DESC);

CREATE UNIQUE INDEX IF NOT EXISTS uq_school_pei_alunos_linha_versao
    ON public.school_pei_alunos (pei_linha_id, versao);

CREATE INDEX IF NOT EXISTS idx_school_pei_alunos_inst_status
    ON public.school_pei_alunos (instituicao_id, status);

COMMIT;
