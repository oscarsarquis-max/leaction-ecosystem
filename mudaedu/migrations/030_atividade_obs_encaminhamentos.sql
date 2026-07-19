-- 030: Observações e encaminhamentos no registro da atividade operacional
BEGIN;

ALTER TABLE public.ctdi_okr_atividades
    ADD COLUMN IF NOT EXISTS obs_encaminhamentos TEXT;

COMMENT ON COLUMN public.ctdi_okr_atividades.obs_encaminhamentos IS
    'Observações e encaminhamentos registrados na execução da atividade (visível no registro da sprint).';

COMMIT;
