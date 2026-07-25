BEGIN;
DROP INDEX IF EXISTS public.idx_inove_agenda_eventos_tema;
ALTER TABLE public.inove_agenda_eventos DROP COLUMN IF EXISTS tema;
COMMIT;
