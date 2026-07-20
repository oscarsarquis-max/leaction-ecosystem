-- Gatekeeper (lock/unlock) — estado global em system_config
-- Idempotente. Default: system_locked=true (lançamento sob manutenção).

BEGIN;

CREATE TABLE IF NOT EXISTS public.system_config (
    config_key   TEXT PRIMARY KEY,
    config_value TEXT NOT NULL,
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO public.system_config (config_key, config_value)
VALUES ('system_locked', 'true')
ON CONFLICT (config_key) DO NOTHING;

COMMIT;
