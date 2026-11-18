-- Sincronização manual de transações externas do ActionHub Pay.
-- Não cria título, recebimento, baixa, movimento ou saldo.
-- Vínculo futuro com título fica sem FK nesta fatia.

CREATE TABLE actionfinance.pay_receipt_sync_run (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    company_id UUID NOT NULL,
    origin_system VARCHAR(32) NOT NULL,
    environment VARCHAR(16) NOT NULL,
    status VARCHAR(16) NOT NULL,
    root_correlation_id VARCHAR(80) NOT NULL,
    spider_message_id VARCHAR(80),
    start_cursor VARCHAR(400),
    resume_cursor VARCHAR(400),
    page_count INTEGER NOT NULL DEFAULT 0,
    imported_count INTEGER NOT NULL DEFAULT 0,
    updated_count INTEGER NOT NULL DEFAULT 0,
    review_count INTEGER NOT NULL DEFAULT 0,
    last_error VARCHAR(200),
    started_at TIMESTAMPTZ NOT NULL,
    finished_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT pay_receipt_sync_run_origin_chk CHECK (origin_system = 'ACTIONHUB_PAY'),
    CONSTRAINT pay_receipt_sync_run_env_chk CHECK (environment IN ('HOMOLOG', 'SANDBOX')),
    CONSTRAINT pay_receipt_sync_run_status_chk CHECK (status IN ('RUNNING', 'SUCCESS', 'PARTIAL', 'FAILED', 'EMPTY')),
    CONSTRAINT pay_receipt_sync_run_company_fk FOREIGN KEY (tenant_id, company_id)
        REFERENCES actionfinance.company (tenant_id, id) ON DELETE RESTRICT
);

CREATE UNIQUE INDEX pay_receipt_sync_run_one_running
    ON actionfinance.pay_receipt_sync_run (tenant_id, company_id, origin_system, environment)
    WHERE status = 'RUNNING';

CREATE INDEX pay_receipt_sync_run_scope_idx
    ON actionfinance.pay_receipt_sync_run (tenant_id, company_id, origin_system, environment, started_at DESC);

CREATE TABLE actionfinance.pay_receipt_sync_page (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    company_id UUID NOT NULL,
    run_id UUID NOT NULL,
    page_no INTEGER NOT NULL,
    cursor_sent VARCHAR(400),
    cursor_next VARCHAR(400),
    item_count INTEGER NOT NULL,
    correlation_id VARCHAR(80) NOT NULL,
    spider_message_id VARCHAR(80),
    outcome VARCHAR(16) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT pay_receipt_sync_page_outcome_chk CHECK (outcome IN ('APPLIED', 'FAILED')),
    CONSTRAINT pay_receipt_sync_page_run_fk FOREIGN KEY (run_id)
        REFERENCES actionfinance.pay_receipt_sync_run (id) ON DELETE RESTRICT,
    CONSTRAINT pay_receipt_sync_page_company_fk FOREIGN KEY (tenant_id, company_id)
        REFERENCES actionfinance.company (tenant_id, id) ON DELETE RESTRICT,
    CONSTRAINT pay_receipt_sync_page_unique UNIQUE (run_id, page_no)
);

CREATE TABLE actionfinance.pay_receipt_checkpoint (
    tenant_id UUID NOT NULL,
    company_id UUID NOT NULL,
    origin_system VARCHAR(32) NOT NULL,
    environment VARCHAR(16) NOT NULL,
    last_origin_updated_at TIMESTAMPTZ,
    last_transaction_id VARCHAR(80),
    last_cursor VARCHAR(400),
    last_completed_run_id UUID,
    updated_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT pay_receipt_checkpoint_pk PRIMARY KEY (tenant_id, company_id, origin_system, environment),
    CONSTRAINT pay_receipt_checkpoint_origin_chk CHECK (origin_system = 'ACTIONHUB_PAY'),
    CONSTRAINT pay_receipt_checkpoint_env_chk CHECK (environment IN ('HOMOLOG', 'SANDBOX')),
    CONSTRAINT pay_receipt_checkpoint_company_fk FOREIGN KEY (tenant_id, company_id)
        REFERENCES actionfinance.company (tenant_id, id) ON DELETE RESTRICT
);

CREATE TABLE actionfinance.pay_receipt_transaction (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    company_id UUID NOT NULL,
    origin_system VARCHAR(32) NOT NULL,
    environment VARCHAR(16) NOT NULL,
    transaction_id VARCHAR(80) NOT NULL,
    order_reference VARCHAR(80) NOT NULL,
    processor_reference VARCHAR(80),
    original_status VARCHAR(32),
    normalized_status VARCHAR(32) NOT NULL,
    amount_minor NUMERIC(19, 0),
    currency CHAR(3),
    amount_absent BOOLEAN NOT NULL,
    review_required BOOLEAN NOT NULL,
    test_labeled BOOLEAN NOT NULL,
    origin_created_at TIMESTAMPTZ,
    origin_updated_at TIMESTAMPTZ,
    origin_revision TIMESTAMPTZ,
    last_sync_run_id UUID NOT NULL,
    last_correlation_id VARCHAR(80),
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT pay_receipt_txn_origin_chk CHECK (origin_system = 'ACTIONHUB_PAY'),
    CONSTRAINT pay_receipt_txn_env_chk CHECK (environment IN ('HOMOLOG', 'SANDBOX')),
    CONSTRAINT pay_receipt_txn_status_chk CHECK (normalized_status IN (
        'IN_PROGRESS', 'CONFIRMED', 'REFUSED', 'REFUNDED', 'REVIEW_REQUIRED', 'UNKNOWN'
    )),
    CONSTRAINT pay_receipt_txn_currency_chk CHECK (currency IS NULL OR currency ~ '^[A-Z]{3}$'),
    CONSTRAINT pay_receipt_txn_amount_chk CHECK (
        (amount_minor IS NULL AND amount_absent = true)
        OR (amount_minor IS NOT NULL AND amount_absent = false)
    ),
    CONSTRAINT pay_receipt_txn_identity UNIQUE (tenant_id, company_id, origin_system, environment, transaction_id),
    CONSTRAINT pay_receipt_txn_company_fk FOREIGN KEY (tenant_id, company_id)
        REFERENCES actionfinance.company (tenant_id, id) ON DELETE RESTRICT,
    CONSTRAINT pay_receipt_txn_run_fk FOREIGN KEY (last_sync_run_id)
        REFERENCES actionfinance.pay_receipt_sync_run (id) ON DELETE RESTRICT
);

CREATE INDEX pay_receipt_txn_list_idx
    ON actionfinance.pay_receipt_transaction (tenant_id, company_id, environment, origin_updated_at DESC, transaction_id DESC);

CREATE TABLE actionfinance.pay_receipt_transaction_revision (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    company_id UUID NOT NULL,
    transaction_pk UUID NOT NULL,
    original_status VARCHAR(32),
    normalized_status VARCHAR(32) NOT NULL,
    amount_minor NUMERIC(19, 0),
    currency CHAR(3),
    review_required BOOLEAN NOT NULL,
    origin_revision TIMESTAMPTZ,
    sync_run_id UUID NOT NULL,
    correlation_id VARCHAR(80),
    observed_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT pay_receipt_rev_txn_fk FOREIGN KEY (transaction_pk)
        REFERENCES actionfinance.pay_receipt_transaction (id) ON DELETE RESTRICT,
    CONSTRAINT pay_receipt_rev_run_fk FOREIGN KEY (sync_run_id)
        REFERENCES actionfinance.pay_receipt_sync_run (id) ON DELETE RESTRICT,
    CONSTRAINT pay_receipt_rev_company_fk FOREIGN KEY (tenant_id, company_id)
        REFERENCES actionfinance.company (tenant_id, id) ON DELETE RESTRICT
);

COMMENT ON TABLE actionfinance.pay_receipt_transaction IS
    'Representação externa importada. Sem FK para título. Importar não baixa nem movimenta conta.';
COMMENT ON TABLE actionfinance.pay_receipt_checkpoint IS
    'Marco global da janela concluída. Página confirmada fica em pay_receipt_sync_run.resume_cursor.';
COMMENT ON COLUMN actionfinance.pay_receipt_transaction.amount_minor IS
    'Unidades mínimas. Nulo só quando amount_absent. Nunca persistir zero no lugar de ausência.';

GRANT SELECT, INSERT, UPDATE ON TABLE actionfinance.pay_receipt_sync_run TO actionfinance_runtime;
GRANT SELECT, INSERT ON TABLE actionfinance.pay_receipt_sync_page TO actionfinance_runtime;
GRANT SELECT, INSERT, UPDATE ON TABLE actionfinance.pay_receipt_checkpoint TO actionfinance_runtime;
GRANT SELECT, INSERT, UPDATE ON TABLE actionfinance.pay_receipt_transaction TO actionfinance_runtime;
GRANT SELECT, INSERT ON TABLE actionfinance.pay_receipt_transaction_revision TO actionfinance_runtime;

REVOKE DELETE ON TABLE actionfinance.pay_receipt_sync_run FROM actionfinance_runtime;
REVOKE UPDATE, DELETE ON TABLE actionfinance.pay_receipt_sync_page FROM actionfinance_runtime;
REVOKE DELETE ON TABLE actionfinance.pay_receipt_checkpoint FROM actionfinance_runtime;
REVOKE DELETE ON TABLE actionfinance.pay_receipt_transaction FROM actionfinance_runtime;
REVOKE UPDATE, DELETE ON TABLE actionfinance.pay_receipt_transaction_revision FROM actionfinance_runtime;
