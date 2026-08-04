-- inove4us B2C — vínculo do professor a instituição School (B2B).
-- Chave Mestra UX: is_institutional = (instituicao_b2b_id IS NOT NULL).
-- Numeração: 022.

BEGIN;

ALTER TABLE public.ctdi_clie
    ADD COLUMN IF NOT EXISTS instituicao_b2b_id UUID;

ALTER TABLE public.ctdi_clie
    ADD COLUMN IF NOT EXISTS institutional_name TEXT;

COMMENT ON COLUMN public.ctdi_clie.instituicao_b2b_id IS
  'UUID da instituição no School (B2B). Sem FK cross-DB. NULL = professor solo.';
COMMENT ON COLUMN public.ctdi_clie.institutional_name IS
  'Nome de exibição da escola patrocinadora (cache local; sem join School).';

CREATE INDEX IF NOT EXISTS idx_ctdi_clie_instituicao_b2b
    ON public.ctdi_clie (instituicao_b2b_id)
    WHERE instituicao_b2b_id IS NOT NULL;

COMMIT;
