-- 012: a chave de idempotência da linha vale dentro do lote, não da empresa.
-- Reenvio do mesmo arquivo após CONFIRMED é um lote novo; o hash sozinho não resume.

ALTER TABLE actionfinance.counterparty_import_line
    DROP CONSTRAINT counterparty_import_line_idem_unique;

ALTER TABLE actionfinance.counterparty_import_line
    ADD CONSTRAINT counterparty_import_line_idem_unique
        UNIQUE (tenant_id, company_id, batch_id, idempotency_key);
