BEGIN;
DROP INDEX IF EXISTS public.idx_inove_agenda_from_school;
DROP INDEX IF EXISTS public.uq_inove_agenda_alocacao_escola;
ALTER TABLE public.inove_agenda_eventos
    DROP CONSTRAINT IF EXISTS chk_inove_agenda_eventos_origem;
ALTER TABLE public.inove_agenda_eventos
    ADD CONSTRAINT chk_inove_agenda_eventos_origem
        CHECK (origem IN ('manual', 'wizard_ia', 'importacao', 'comunicado_escola'));
ALTER TABLE public.inove_agenda_eventos
    DROP COLUMN IF EXISTS is_from_school;
COMMIT;
