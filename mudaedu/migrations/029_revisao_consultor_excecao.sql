-- 029: Revisão excepcional do consultor humano sobre a nota do Modulador
-- Só ocorre quando o Cliente solicita.

BEGIN;

ALTER TABLE public.ctdi_sprn
    ADD COLUMN IF NOT EXISTS revisao_consultor_solicitada BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS revisao_consultor_solicitada_em TIMESTAMP WITHOUT TIME ZONE,
    ADD COLUMN IF NOT EXISTS revisao_consultor_motivo TEXT;

COMMENT ON COLUMN public.ctdi_sprn.revisao_consultor_solicitada IS
    'true = Cliente pediu revisão excepcional da nota do Modulador por consultor humano.';
COMMENT ON COLUMN public.ctdi_sprn.revisao_consultor_motivo IS
    'Motivo informado pelo Cliente ao solicitar a revisão.';

COMMIT;
