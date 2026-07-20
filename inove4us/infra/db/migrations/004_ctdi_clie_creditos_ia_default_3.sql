-- Freemium: cota padrão de créditos IA = 3 (antes 10).
-- Não altera saldos já existentes; só o DEFAULT para novos leads.

ALTER TABLE public.ctdi_clie
    ADD COLUMN IF NOT EXISTS creditos_ia INTEGER NOT NULL DEFAULT 3;

ALTER TABLE public.ctdi_clie
    ALTER COLUMN creditos_ia SET DEFAULT 3;
