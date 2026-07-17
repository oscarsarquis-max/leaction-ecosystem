-- Freemium local: créditos de IA para geração de planos (ActionHub cuidará de upgrade depois)
ALTER TABLE public.ctdi_clie
    ADD COLUMN IF NOT EXISTS creditos_ia INTEGER NOT NULL DEFAULT 10;

-- Usuários já existentes passam a ter o saldo inicial freemium
UPDATE public.ctdi_clie
SET creditos_ia = 10
WHERE creditos_ia IS NULL OR creditos_ia < 0;
