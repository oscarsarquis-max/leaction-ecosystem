-- PRM_009 ADENDO_002: ambiente operacional da Loja, sem reclassificar sintéticos.

ALTER TABLE actionfinance.pay_company_mapping
    DROP CONSTRAINT pay_company_mapping_env_chk;
ALTER TABLE actionfinance.pay_company_mapping
    ADD CONSTRAINT pay_company_mapping_env_chk
    CHECK (environment IN ('HOMOLOG', 'SANDBOX', 'PRODUCTION'));

ALTER TABLE actionfinance.pay_receipt_sync_run
    DROP CONSTRAINT pay_receipt_sync_run_env_chk;
ALTER TABLE actionfinance.pay_receipt_sync_run
    ADD CONSTRAINT pay_receipt_sync_run_env_chk
    CHECK (environment IN ('HOMOLOG', 'SANDBOX', 'PRODUCTION'));

ALTER TABLE actionfinance.pay_receipt_checkpoint
    DROP CONSTRAINT pay_receipt_checkpoint_env_chk;
ALTER TABLE actionfinance.pay_receipt_checkpoint
    ADD CONSTRAINT pay_receipt_checkpoint_env_chk
    CHECK (environment IN ('HOMOLOG', 'SANDBOX', 'PRODUCTION'));

ALTER TABLE actionfinance.pay_receipt_transaction
    DROP CONSTRAINT pay_receipt_txn_env_chk;
ALTER TABLE actionfinance.pay_receipt_transaction
    ADD CONSTRAINT pay_receipt_txn_env_chk
    CHECK (environment IN ('HOMOLOG', 'SANDBOX', 'PRODUCTION'));

COMMENT ON COLUMN actionfinance.pay_company_mapping.environment IS
    'HOMOLOG/SANDBOX = trilha de teste. PRODUCTION = leitura operacional autorizada da Loja.';

ALTER TABLE actionfinance.pay_receipt_transaction
    ADD COLUMN classification VARCHAR(16);
ALTER TABLE actionfinance.pay_receipt_transaction
    ADD COLUMN classification_reason VARCHAR(240);

UPDATE actionfinance.pay_receipt_transaction
SET classification = CASE
    WHEN test_labeled THEN 'TEST'
    ELSE 'INDETERMINATE'
END
WHERE classification IS NULL;

ALTER TABLE actionfinance.pay_receipt_transaction
    ALTER COLUMN classification SET DEFAULT 'INDETERMINATE';
ALTER TABLE actionfinance.pay_receipt_transaction
    ALTER COLUMN classification SET NOT NULL;
ALTER TABLE actionfinance.pay_receipt_transaction
    ADD CONSTRAINT pay_receipt_txn_class_chk
    CHECK (classification IN ('REAL', 'TEST', 'INDETERMINATE'));

COMMENT ON COLUMN actionfinance.pay_receipt_transaction.classification IS
    'REAL só com evidência independente. INDETERMINATE fica fora dos totais operacionais.';

ALTER TABLE actionfinance.pay_receipt_transaction
    ADD COLUMN paid_amount_minor NUMERIC(19, 0);
ALTER TABLE actionfinance.pay_receipt_transaction
    ADD COLUMN paid_amount_absent BOOLEAN NOT NULL DEFAULT true;

COMMENT ON COLUMN actionfinance.pay_receipt_transaction.amount_minor IS
    'Valor cobrado na origem (amount_cents). Ausência ≠ zero.';
COMMENT ON COLUMN actionfinance.pay_receipt_transaction.paid_amount_minor IS
    'Valor pago informado pelo provedor. Só com evidência; não é líquido de taxas.';
