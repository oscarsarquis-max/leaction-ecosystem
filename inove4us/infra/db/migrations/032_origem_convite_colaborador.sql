-- inove4us B2C — origem convite_colaborador (seed do grafo ao aceitar convite).
-- Numeração: 032.

BEGIN;

ALTER TABLE public.inove_agenda_eventos
    DROP CONSTRAINT IF EXISTS chk_inove_agenda_eventos_origem;

ALTER TABLE public.inove_agenda_eventos
    ADD CONSTRAINT chk_inove_agenda_eventos_origem
        CHECK (origem IN (
            'manual',
            'wizard_ia',
            'importacao',
            'comunicado_escola',
            'alocacao_escola',
            'planejamento_escola',
            'convite_colaborador'
        ));

COMMENT ON COLUMN public.inove_agenda_eventos.origem IS
  'manual | wizard_ia | importacao | comunicado_escola | alocacao_escola | planejamento_escola | convite_colaborador';

COMMIT;
