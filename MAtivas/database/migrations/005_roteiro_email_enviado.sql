ALTER TABLE roteiros
    ADD COLUMN IF NOT EXISTS email_automatico_enviado_em TIMESTAMP NULL;

CREATE INDEX IF NOT EXISTS idx_roteiros_email_auto_enviado
    ON roteiros (email_automatico_enviado_em);
