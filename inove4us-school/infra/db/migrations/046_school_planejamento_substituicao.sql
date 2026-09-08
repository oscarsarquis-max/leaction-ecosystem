-- 046: substituição institucional no Planejamento Escolar (prompt 104)
-- Permite overlap deliberado só quando a Secretaria marca substituição
-- e referencia o item substituído (auditável).

BEGIN;

ALTER TABLE public.school_planejamento_escolar
    ADD COLUMN IF NOT EXISTS substituicao BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE public.school_planejamento_escolar
    ADD COLUMN IF NOT EXISTS substitui_item_id UUID
        REFERENCES public.school_planejamento_escolar (id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_school_planejamento_substitui
    ON public.school_planejamento_escolar (instituicao_id, substitui_item_id)
    WHERE substitui_item_id IS NOT NULL;

COMMENT ON COLUMN public.school_planejamento_escolar.substituicao IS
  'True só na substituição institucional (mesmo slot). Professor no B2C não usa este campo.';
COMMENT ON COLUMN public.school_planejamento_escolar.substitui_item_id IS
  'Item de planejamento cujo horário está sendo ocupado de propósito (troca de professor / reorganização).';

COMMIT;
