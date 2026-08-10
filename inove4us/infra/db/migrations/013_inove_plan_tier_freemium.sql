-- Planos HVLT: tier de assinatura + freemium Starter (1 desafio; Dia a Dia sem registro)
-- Aplicar: psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f infra/db/migrations/013_inove_plan_tier_freemium.sql

BEGIN;

ALTER TABLE public.ctdi_clie
    ADD COLUMN IF NOT EXISTS plan_tier VARCHAR(32) NOT NULL DEFAULT 'starter';

COMMENT ON COLUMN public.ctdi_clie.plan_tier IS
  'starter | profissional | mentor — definido via webhook Hub (SKU/assinatura)';

-- Novos leads: 1 crédito IA (1 desafio freemium). Não altera saldo de quem já existe.
ALTER TABLE public.ctdi_clie
    ALTER COLUMN creditos_ia SET DEFAULT 1;

COMMIT;
