-- Gatekeeper / homologação produtiva — configuração global do sistema
CREATE TABLE IF NOT EXISTS public.system_config (
    config_key   VARCHAR(128) PRIMARY KEY,
    config_value VARCHAR(512) NOT NULL
);

INSERT INTO public.system_config (config_key, config_value)
VALUES ('system_locked', 'true')
ON CONFLICT (config_key) DO NOTHING;
