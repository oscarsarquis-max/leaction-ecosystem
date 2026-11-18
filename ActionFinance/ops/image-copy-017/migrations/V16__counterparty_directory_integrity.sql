-- Correção incremental 012. Não edita V14/V15.
-- Fecha integridade endereço↔unidade da mesma pessoa, unicidade externa sem NULL,
-- reivindicação única de documento na empresa e FK do match de importação.

ALTER TABLE actionfinance.counterparty_unit
    ADD CONSTRAINT counterparty_unit_party_id_unique
        UNIQUE (tenant_id, company_id, counterparty_id, id);

ALTER TABLE actionfinance.counterparty_address
    DROP CONSTRAINT counterparty_address_unit_fk;

ALTER TABLE actionfinance.counterparty_address
    ADD CONSTRAINT counterparty_address_unit_fk
        FOREIGN KEY (tenant_id, company_id, counterparty_id, unit_id)
        REFERENCES actionfinance.counterparty_unit (tenant_id, company_id, counterparty_id, id)
        ON DELETE RESTRICT;

ALTER TABLE actionfinance.counterparty_import_line
    ADD CONSTRAINT counterparty_import_line_match_fk
        FOREIGN KEY (tenant_id, company_id, match_counterparty_id)
        REFERENCES actionfinance.counterparty (tenant_id, company_id, id)
        ON DELETE RESTRICT;

UPDATE actionfinance.counterparty_external_identity
    SET connection_key = ''
    WHERE connection_key IS NULL;

ALTER TABLE actionfinance.counterparty_external_identity
    ALTER COLUMN connection_key SET DEFAULT '',
    ALTER COLUMN connection_key SET NOT NULL;

CREATE TABLE actionfinance.counterparty_document_claim (
    tenant_id UUID NOT NULL,
    company_id UUID NOT NULL,
    document_country CHAR(2) NOT NULL,
    document_type VARCHAR(16) NOT NULL,
    document_number_normalized VARCHAR(32) NOT NULL,
    counterparty_id UUID NOT NULL,
    unit_id UUID,
    mirrored BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT counterparty_document_claim_pk
        PRIMARY KEY (tenant_id, company_id, document_country, document_type, document_number_normalized),
    CONSTRAINT counterparty_document_claim_party_fk
        FOREIGN KEY (tenant_id, company_id, counterparty_id)
        REFERENCES actionfinance.counterparty (tenant_id, company_id, id) ON DELETE RESTRICT,
    CONSTRAINT counterparty_document_claim_unit_fk
        FOREIGN KEY (tenant_id, company_id, counterparty_id, unit_id)
        REFERENCES actionfinance.counterparty_unit (tenant_id, company_id, counterparty_id, id)
        ON DELETE RESTRICT
);

COMMENT ON TABLE actionfinance.counterparty_document_claim IS
    'Autoridade de documento na empresa: um número normalizado pertence a uma pessoa. Espelho na unidade principal da mesma pessoa é explícito (mirrored).';

INSERT INTO actionfinance.counterparty_document_claim (
    tenant_id, company_id, document_country, document_type, document_number_normalized,
    counterparty_id, unit_id, mirrored, created_at)
SELECT tenant_id, company_id, document_country, document_type, document_number_normalized,
       id, NULL, FALSE, now()
  FROM actionfinance.counterparty
 WHERE document_number_normalized IS NOT NULL
ON CONFLICT DO NOTHING;

INSERT INTO actionfinance.counterparty_document_claim (
    tenant_id, company_id, document_country, document_type, document_number_normalized,
    counterparty_id, unit_id, mirrored, created_at)
SELECT u.tenant_id, u.company_id, u.document_country, u.document_type, u.document_number_normalized,
       u.counterparty_id, u.id,
       EXISTS (
           SELECT 1 FROM actionfinance.counterparty c
            WHERE c.tenant_id = u.tenant_id AND c.company_id = u.company_id AND c.id = u.counterparty_id
              AND c.document_number_normalized = u.document_number_normalized
              AND u.is_primary
       ),
       now()
  FROM actionfinance.counterparty_unit u
 WHERE u.document_number_normalized IS NOT NULL
ON CONFLICT DO NOTHING;
