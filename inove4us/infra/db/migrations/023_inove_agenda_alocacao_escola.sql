-- inove4us B2C — agenda: flag de alocação institucional (School → professor).
-- Numeração: 023.

BEGIN;

ALTER TABLE public.inove_agenda_eventos
    ADD COLUMN IF NOT EXISTS is_from_school BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE public.inove_agenda_eventos
    DROP CONSTRAINT IF EXISTS chk_inove_agenda_eventos_origem;

ALTER TABLE public.inove_agenda_eventos
    ADD CONSTRAINT chk_inove_agenda_eventos_origem
        CHECK (origem IN (
            'manual',
            'wizard_ia',
            'importacao',
            'comunicado_escola',
            'alocacao_escola'
        ));

-- Idempotência do webhook TEACHER_ALLOCATED (id_externo = alocacao_id do School)
CREATE UNIQUE INDEX IF NOT EXISTS uq_inove_agenda_alocacao_escola
    ON public.inove_agenda_eventos (id_clie, id_externo_importacao)
    WHERE origem = 'alocacao_escola'
      AND id_externo_importacao IS NOT NULL
      AND trim(id_externo_importacao) <> '';

CREATE INDEX IF NOT EXISTS idx_inove_agenda_from_school
    ON public.inove_agenda_eventos (id_clie, is_from_school)
    WHERE is_from_school = TRUE;

COMMENT ON COLUMN public.inove_agenda_eventos.is_from_school IS
  'TRUE quando o evento veio da alocação docente do inove4us-school (TEACHER_ALLOCATED).';
COMMENT ON COLUMN public.inove_agenda_eventos.origem IS
  'manual | wizard_ia | importacao | comunicado_escola | alocacao_escola';

COMMIT;
