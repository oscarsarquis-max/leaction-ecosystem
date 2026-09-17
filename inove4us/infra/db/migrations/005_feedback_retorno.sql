-- Devolutiva do revisor (Hub/Sponge) ao autor do feedback da Nina.
ALTER TABLE public.inove_user_feedbacks
    ADD COLUMN IF NOT EXISTS retorno_texto TEXT;
ALTER TABLE public.inove_user_feedbacks
    ADD COLUMN IF NOT EXISTS retorno_em TIMESTAMP WITHOUT TIME ZONE;
