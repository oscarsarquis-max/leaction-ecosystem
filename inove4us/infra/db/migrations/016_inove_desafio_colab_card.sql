-- Convite multidisciplinar: card associado + snapshots para o e-mail.
-- Aplicar: psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f infra/db/migrations/016_inove_desafio_colab_card.sql

BEGIN;

ALTER TABLE public.inove_desafio_colaboradores
    ADD COLUMN IF NOT EXISTS card_id VARCHAR(64);

ALTER TABLE public.inove_desafio_colaboradores
    ADD COLUMN IF NOT EXISTS card_titulo VARCHAR(200);

ALTER TABLE public.inove_desafio_colaboradores
    ADD COLUMN IF NOT EXISTS card_descricao TEXT;

ALTER TABLE public.inove_desafio_colaboradores
    ADD COLUMN IF NOT EXISTS desafio_descricao TEXT;

CREATE INDEX IF NOT EXISTS idx_inove_desafio_colab_card
    ON public.inove_desafio_colaboradores (desafio_id, card_id)
    WHERE card_id IS NOT NULL;

COMMENT ON COLUMN public.inove_desafio_colaboradores.card_id IS
  'Card do Kanban (JSON id) que o professor convidado assume neste desafio.';

COMMIT;
