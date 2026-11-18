-- Contas financeiras, baixas, movimentos e histórico. Sem seed.

ALTER TABLE actionfinance.financial_title_history
    DROP CONSTRAINT financial_title_history_action_chk;
ALTER TABLE actionfinance.financial_title_history
    ADD CONSTRAINT financial_title_history_action_chk
        CHECK (action IN ('CREATED', 'UPDATED', 'CONFIRMED', 'CANCELLED', 'SETTLEMENT_RECORDED', 'SETTLEMENT_REVERSED'));

CREATE TABLE actionfinance.financial_account (
    id UUID NOT NULL,
    tenant_id UUID NOT NULL,
    company_id UUID NOT NULL,
    code VARCHAR(40) NOT NULL,
    name VARCHAR(100) NOT NULL,
    type VARCHAR(16) NOT NULL,
    currency CHAR(3) NOT NULL,
    active BOOLEAN NOT NULL,
    opened_on DATE NOT NULL,
    version BIGINT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    created_by UUID NOT NULL,
    updated_by UUID NOT NULL,
    CONSTRAINT financial_account_pk PRIMARY KEY (id),
    CONSTRAINT financial_account_scope_id UNIQUE (tenant_id, company_id, id),
    CONSTRAINT financial_account_scope_code UNIQUE (tenant_id, company_id, code),
    CONSTRAINT financial_account_company_fk FOREIGN KEY (tenant_id, company_id)
        REFERENCES actionfinance.company (tenant_id, id) ON DELETE RESTRICT,
    CONSTRAINT financial_account_type_chk CHECK (type IN ('BANK', 'CASH', 'OTHER')),
    CONSTRAINT financial_account_currency_chk CHECK (currency = 'BRL'),
    CONSTRAINT financial_account_version_nonneg CHECK (version >= 0)
);

CREATE TABLE actionfinance.settlement (
    id UUID NOT NULL,
    tenant_id UUID NOT NULL,
    company_id UUID NOT NULL,
    account_id UUID NOT NULL,
    direction VARCHAR(16) NOT NULL,
    amount_minor NUMERIC(19, 0) NOT NULL,
    currency CHAR(3) NOT NULL,
    effective_date DATE NOT NULL,
    method VARCHAR(24) NOT NULL,
    note VARCHAR(500),
    origin_kind VARCHAR(16) NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL,
    recorded_by UUID NOT NULL,
    actor_display_name VARCHAR(160) NOT NULL,
    CONSTRAINT settlement_pk PRIMARY KEY (id),
    CONSTRAINT settlement_scope_id UNIQUE (tenant_id, company_id, id),
    CONSTRAINT settlement_scope_id_account UNIQUE (tenant_id, company_id, id, account_id),
    CONSTRAINT settlement_company_fk FOREIGN KEY (tenant_id, company_id)
        REFERENCES actionfinance.company (tenant_id, id) ON DELETE RESTRICT,
    CONSTRAINT settlement_account_fk FOREIGN KEY (tenant_id, company_id, account_id)
        REFERENCES actionfinance.financial_account (tenant_id, company_id, id) ON DELETE RESTRICT,
    CONSTRAINT settlement_direction_chk CHECK (direction IN ('RECEIVABLE', 'PAYABLE')),
    CONSTRAINT settlement_amount_positive CHECK (amount_minor > 0),
    CONSTRAINT settlement_currency_chk CHECK (currency = 'BRL'),
    CONSTRAINT settlement_method_chk CHECK (method IN ('PIX', 'BANK_TRANSFER', 'CASH', 'CARD', 'OTHER')),
    CONSTRAINT settlement_origin_chk CHECK (origin_kind = 'MANUAL')
);

CREATE TABLE actionfinance.settlement_allocation (
    id UUID NOT NULL,
    tenant_id UUID NOT NULL,
    company_id UUID NOT NULL,
    settlement_id UUID NOT NULL,
    title_id UUID NOT NULL,
    amount_minor NUMERIC(19, 0) NOT NULL,
    CONSTRAINT settlement_allocation_pk PRIMARY KEY (id),
    CONSTRAINT settlement_allocation_scope_id UNIQUE (tenant_id, company_id, id),
    CONSTRAINT settlement_allocation_scope_settlement UNIQUE (tenant_id, company_id, settlement_id),
    CONSTRAINT settlement_allocation_company_fk FOREIGN KEY (tenant_id, company_id)
        REFERENCES actionfinance.company (tenant_id, id) ON DELETE RESTRICT,
    CONSTRAINT settlement_allocation_settlement_fk FOREIGN KEY (tenant_id, company_id, settlement_id)
        REFERENCES actionfinance.settlement (tenant_id, company_id, id) ON DELETE RESTRICT,
    CONSTRAINT settlement_allocation_title_fk FOREIGN KEY (tenant_id, company_id, title_id)
        REFERENCES actionfinance.financial_title (tenant_id, company_id, id) ON DELETE RESTRICT,
    CONSTRAINT settlement_allocation_amount_positive CHECK (amount_minor > 0)
);

CREATE TABLE actionfinance.settlement_reversal (
    id UUID NOT NULL,
    tenant_id UUID NOT NULL,
    company_id UUID NOT NULL,
    settlement_id UUID NOT NULL,
    effective_date DATE NOT NULL,
    reason VARCHAR(500) NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL,
    recorded_by UUID NOT NULL,
    actor_display_name VARCHAR(160) NOT NULL,
    CONSTRAINT settlement_reversal_pk PRIMARY KEY (id),
    CONSTRAINT settlement_reversal_scope_id UNIQUE (tenant_id, company_id, id),
    CONSTRAINT settlement_reversal_scope_settlement UNIQUE (tenant_id, company_id, settlement_id),
    CONSTRAINT settlement_reversal_company_fk FOREIGN KEY (tenant_id, company_id)
        REFERENCES actionfinance.company (tenant_id, id) ON DELETE RESTRICT,
    CONSTRAINT settlement_reversal_settlement_fk FOREIGN KEY (tenant_id, company_id, settlement_id)
        REFERENCES actionfinance.settlement (tenant_id, company_id, id) ON DELETE RESTRICT,
    CONSTRAINT settlement_reversal_reason_len CHECK (char_length(btrim(reason)) BETWEEN 3 AND 500)
);

CREATE TABLE actionfinance.cash_movement (
    id UUID NOT NULL,
    tenant_id UUID NOT NULL,
    company_id UUID NOT NULL,
    account_id UUID NOT NULL,
    kind VARCHAR(24) NOT NULL,
    signed_amount_minor NUMERIC(19, 0) NOT NULL,
    currency CHAR(3) NOT NULL,
    effective_date DATE NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL,
    recorded_by UUID NOT NULL,
    settlement_id UUID,
    reversal_id UUID,
    description VARCHAR(200) NOT NULL,
    CONSTRAINT cash_movement_pk PRIMARY KEY (id),
    CONSTRAINT cash_movement_scope_id UNIQUE (tenant_id, company_id, id),
    CONSTRAINT cash_movement_company_fk FOREIGN KEY (tenant_id, company_id)
        REFERENCES actionfinance.company (tenant_id, id) ON DELETE RESTRICT,
    CONSTRAINT cash_movement_account_fk FOREIGN KEY (tenant_id, company_id, account_id)
        REFERENCES actionfinance.financial_account (tenant_id, company_id, id) ON DELETE RESTRICT,
    CONSTRAINT cash_movement_settlement_account_fk FOREIGN KEY (tenant_id, company_id, settlement_id, account_id)
        REFERENCES actionfinance.settlement (tenant_id, company_id, id, account_id) ON DELETE RESTRICT,
    CONSTRAINT cash_movement_reversal_fk FOREIGN KEY (tenant_id, company_id, reversal_id)
        REFERENCES actionfinance.settlement_reversal (tenant_id, company_id, id) ON DELETE RESTRICT,
    CONSTRAINT cash_movement_kind_chk CHECK (kind IN ('OPENING', 'SETTLEMENT', 'REVERSAL')),
    CONSTRAINT cash_movement_currency_chk CHECK (currency = 'BRL'),
    CONSTRAINT cash_movement_kind_nulls_chk CHECK (
        (kind = 'OPENING' AND settlement_id IS NULL AND reversal_id IS NULL)
        OR (kind = 'SETTLEMENT' AND settlement_id IS NOT NULL AND reversal_id IS NULL AND signed_amount_minor <> 0)
        OR (kind = 'REVERSAL' AND settlement_id IS NOT NULL AND reversal_id IS NOT NULL AND signed_amount_minor <> 0)
    )
);

CREATE UNIQUE INDEX cash_movement_opening_one_idx
    ON actionfinance.cash_movement (tenant_id, company_id, account_id)
    WHERE kind = 'OPENING';

CREATE UNIQUE INDEX cash_movement_settlement_one_idx
    ON actionfinance.cash_movement (tenant_id, company_id, settlement_id)
    WHERE kind = 'SETTLEMENT';

CREATE UNIQUE INDEX cash_movement_reversal_one_idx
    ON actionfinance.cash_movement (tenant_id, company_id, reversal_id)
    WHERE kind = 'REVERSAL';

CREATE TABLE actionfinance.financial_account_history (
    id UUID NOT NULL,
    tenant_id UUID NOT NULL,
    company_id UUID NOT NULL,
    account_id UUID NOT NULL,
    account_version BIGINT NOT NULL,
    action VARCHAR(24) NOT NULL,
    actor_id UUID NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL,
    changes JSONB NOT NULL,
    CONSTRAINT financial_account_history_pk PRIMARY KEY (id),
    CONSTRAINT financial_account_history_scope_version UNIQUE (tenant_id, company_id, account_id, account_version),
    CONSTRAINT financial_account_history_account_fk FOREIGN KEY (tenant_id, company_id, account_id)
        REFERENCES actionfinance.financial_account (tenant_id, company_id, id) ON DELETE RESTRICT,
    CONSTRAINT financial_account_history_action_chk CHECK (action IN ('CREATED', 'RENAMED', 'DEACTIVATED', 'REACTIVATED'))
);

CREATE INDEX financial_account_lookup_idx
    ON actionfinance.financial_account (tenant_id, company_id, active, name, id);

CREATE INDEX settlement_allocation_title_idx
    ON actionfinance.settlement_allocation (tenant_id, company_id, title_id, settlement_id);

CREATE INDEX settlement_account_date_idx
    ON actionfinance.settlement (tenant_id, company_id, account_id, effective_date, id);

CREATE INDEX cash_movement_statement_idx
    ON actionfinance.cash_movement (tenant_id, company_id, account_id, effective_date, recorded_at, id);

CREATE INDEX financial_account_history_recent_idx
    ON actionfinance.financial_account_history (tenant_id, company_id, account_id, occurred_at, id);
