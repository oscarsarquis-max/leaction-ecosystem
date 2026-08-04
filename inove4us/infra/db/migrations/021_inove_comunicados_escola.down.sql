BEGIN;

ALTER TABLE public.inove_agenda_eventos
    DROP CONSTRAINT IF EXISTS chk_inove_agenda_eventos_origem;

ALTER TABLE public.inove_agenda_eventos
    ADD CONSTRAINT chk_inove_agenda_eventos_origem
        CHECK (origem IN ('manual', 'wizard_ia', 'importacao'));

DROP INDEX IF EXISTS idx_inove_agenda_comunicado_escola;

ALTER TABLE public.inove_agenda_eventos
    DROP COLUMN IF EXISTS comunicado_escola_id;

DROP TABLE IF EXISTS public.inove_comunicados_escola_destinatarios CASCADE;
DROP TABLE IF EXISTS public.inove_comunicados_escola CASCADE;

COMMIT;
