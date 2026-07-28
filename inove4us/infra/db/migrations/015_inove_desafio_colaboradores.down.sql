BEGIN;

DROP INDEX IF EXISTS public.idx_inove_agenda_eventos_responsavel;
ALTER TABLE public.inove_agenda_eventos DROP COLUMN IF EXISTS id_clie_responsavel;
DROP TABLE IF EXISTS public.inove_desafio_colaboradores;

COMMIT;
