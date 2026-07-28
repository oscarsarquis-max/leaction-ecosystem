BEGIN;

DROP INDEX IF EXISTS public.idx_inove_agenda_eventos_desafio;
ALTER TABLE public.inove_agenda_eventos DROP COLUMN IF EXISTS desafio_id;
DROP TABLE IF EXISTS public.inove_desafios;

COMMIT;
