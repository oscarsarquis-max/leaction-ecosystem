-- Onboarding da Nina: conclusão persistida no cliente (não só localStorage).
-- Aplicar: psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f infra/db/migrations/017_ctdi_clie_nina_onboarding.sql

ALTER TABLE public.ctdi_clie
    ADD COLUMN IF NOT EXISTS nina_onboarding_done BOOLEAN NOT NULL DEFAULT FALSE;

COMMENT ON COLUMN public.ctdi_clie.nina_onboarding_done IS
    'True quando o professor concluiu ou pulou o onboarding da Nina (escopo + convite escola).';
