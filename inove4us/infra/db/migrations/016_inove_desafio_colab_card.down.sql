BEGIN;

DROP INDEX IF EXISTS public.idx_inove_desafio_colab_card;
ALTER TABLE public.inove_desafio_colaboradores DROP COLUMN IF EXISTS desafio_descricao;
ALTER TABLE public.inove_desafio_colaboradores DROP COLUMN IF EXISTS card_descricao;
ALTER TABLE public.inove_desafio_colaboradores DROP COLUMN IF EXISTS card_titulo;
ALTER TABLE public.inove_desafio_colaboradores DROP COLUMN IF EXISTS card_id;

COMMIT;
