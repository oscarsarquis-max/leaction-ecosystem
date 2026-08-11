-- Rollback 032 — remove convite_colaborador da origem da agenda.

BEGIN;

UPDATE public.inove_agenda_eventos
   SET origem = 'manual'
 WHERE origem = 'convite_colaborador';

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
            'planejamento_escola'
        ));

COMMIT;
