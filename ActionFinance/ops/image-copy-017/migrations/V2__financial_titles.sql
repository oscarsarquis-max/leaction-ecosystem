-- Títulos a receber/pagar, cadastros de apoio, isolamento tenant/empresa.
-- Sem seed. Sem DDL futuro de tesouraria/integração.

COMMENT ON SCHEMA actionfinance IS
    'ActionFinance local schema. Manual title tracking; no payment execution.';

CREATE TABLE actionfinance.tenant (
    id UUID PRIMARY KEY,
    code VARCHAR(40) NOT NULL,
    name VARCHAR(160) NOT NULL,
    active BOOLEAN NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    version BIGINT NOT NULL,
    CONSTRAINT tenant_code_unique UNIQUE (code),
    CONSTRAINT tenant_version_nonneg CHECK (version >= 0)
);

CREATE TABLE actionfinance.company (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES actionfinance.tenant (id) ON DELETE RESTRICT,
    code VARCHAR(40) NOT NULL,
    name VARCHAR(160) NOT NULL,
    active BOOLEAN NOT NULL,
    is_demo BOOLEAN NOT NULL DEFAULT FALSE,
    business_timezone VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    version BIGINT NOT NULL,
    CONSTRAINT company_tenant_id_unique UNIQUE (tenant_id, id),
    CONSTRAINT company_tenant_code_unique UNIQUE (tenant_id, code),
    CONSTRAINT company_version_nonneg CHECK (version >= 0)
);

CREATE TABLE actionfinance.counterparty (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    company_id UUID NOT NULL,
    code VARCHAR(40) NOT NULL,
    name VARCHAR(160) NOT NULL,
    role VARCHAR(16) NOT NULL,
    active BOOLEAN NOT NULL,
    version BIGINT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    created_by UUID NOT NULL,
    updated_by UUID NOT NULL,
    CONSTRAINT counterparty_role_chk CHECK (role IN ('CUSTOMER', 'SUPPLIER', 'BOTH')),
    CONSTRAINT counterparty_scope_unique UNIQUE (tenant_id, company_id, id),
    CONSTRAINT counterparty_code_unique UNIQUE (tenant_id, company_id, code),
    CONSTRAINT counterparty_company_fk FOREIGN KEY (tenant_id, company_id)
        REFERENCES actionfinance.company (tenant_id, id) ON DELETE RESTRICT,
    CONSTRAINT counterparty_version_nonneg CHECK (version >= 0)
);

CREATE TABLE actionfinance.financial_category (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    company_id UUID NOT NULL,
    code VARCHAR(40) NOT NULL,
    name VARCHAR(100) NOT NULL,
    direction VARCHAR(16) NOT NULL,
    active BOOLEAN NOT NULL,
    version BIGINT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    created_by UUID NOT NULL,
    updated_by UUID NOT NULL,
    CONSTRAINT financial_category_direction_chk CHECK (direction IN ('RECEIVABLE', 'PAYABLE', 'BOTH')),
    CONSTRAINT financial_category_scope_unique UNIQUE (tenant_id, company_id, id),
    CONSTRAINT financial_category_code_unique UNIQUE (tenant_id, company_id, code),
    CONSTRAINT financial_category_company_fk FOREIGN KEY (tenant_id, company_id)
        REFERENCES actionfinance.company (tenant_id, id) ON DELETE RESTRICT,
    CONSTRAINT financial_category_version_nonneg CHECK (version >= 0)
);

CREATE TABLE actionfinance.financial_title (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    company_id UUID NOT NULL,
    reference VARCHAR(48) NOT NULL,
    direction VARCHAR(16) NOT NULL,
    status VARCHAR(16) NOT NULL,
    description VARCHAR(200) NOT NULL,
    counterparty_id UUID,
    category_id UUID,
    amount_minor NUMERIC(19, 0),
    currency CHAR(3) NOT NULL DEFAULT 'BRL',
    competence_date DATE,
    due_date DATE,
    origin_kind VARCHAR(16) NOT NULL,
    source_reference VARCHAR(100),
    version BIGINT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    created_by UUID NOT NULL,
    updated_by UUID NOT NULL,
    confirmed_at TIMESTAMPTZ,
    cancelled_at TIMESTAMPTZ,
    cancellation_reason VARCHAR(500),
    CONSTRAINT financial_title_direction_chk CHECK (direction IN ('RECEIVABLE', 'PAYABLE')),
    CONSTRAINT financial_title_status_chk CHECK (status IN ('DRAFT', 'OPEN', 'CANCELLED')),
    CONSTRAINT financial_title_origin_chk CHECK (origin_kind IN ('MANUAL')),
    CONSTRAINT financial_title_currency_chk CHECK (currency = 'BRL'),
    CONSTRAINT financial_title_amount_positive CHECK (amount_minor IS NULL OR amount_minor > 0),
    CONSTRAINT financial_title_description_present CHECK (length(btrim(description)) > 0),
    CONSTRAINT financial_title_open_complete CHECK (
        status <> 'OPEN'
        OR (
            counterparty_id IS NOT NULL
            AND category_id IS NOT NULL
            AND amount_minor IS NOT NULL
            AND competence_date IS NOT NULL
            AND due_date IS NOT NULL
            AND confirmed_at IS NOT NULL
            AND cancelled_at IS NULL
            AND cancellation_reason IS NULL
        )
    ),
    CONSTRAINT financial_title_cancelled_complete CHECK (
        status <> 'CANCELLED'
        OR (cancelled_at IS NOT NULL AND cancellation_reason IS NOT NULL)
    ),
    CONSTRAINT financial_title_draft_markers CHECK (
        status <> 'DRAFT'
        OR (confirmed_at IS NULL AND cancelled_at IS NULL AND cancellation_reason IS NULL)
    ),
    CONSTRAINT financial_title_scope_unique UNIQUE (tenant_id, company_id, id),
    CONSTRAINT financial_title_reference_unique UNIQUE (tenant_id, company_id, reference),
    CONSTRAINT financial_title_company_fk FOREIGN KEY (tenant_id, company_id)
        REFERENCES actionfinance.company (tenant_id, id) ON DELETE RESTRICT,
    CONSTRAINT financial_title_counterparty_fk FOREIGN KEY (tenant_id, company_id, counterparty_id)
        REFERENCES actionfinance.counterparty (tenant_id, company_id, id) ON DELETE RESTRICT,
    CONSTRAINT financial_title_category_fk FOREIGN KEY (tenant_id, company_id, category_id)
        REFERENCES actionfinance.financial_category (tenant_id, company_id, id) ON DELETE RESTRICT,
    CONSTRAINT financial_title_version_nonneg CHECK (version >= 0)
);

CREATE TABLE actionfinance.financial_title_history (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    company_id UUID NOT NULL,
    title_id UUID NOT NULL,
    title_version BIGINT NOT NULL,
    action VARCHAR(24) NOT NULL,
    actor_id UUID NOT NULL,
    actor_display_name VARCHAR(160) NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL,
    reason VARCHAR(500),
    changes JSONB NOT NULL,
    CONSTRAINT financial_title_history_action_chk CHECK (action IN ('CREATED', 'UPDATED', 'CONFIRMED', 'CANCELLED')),
    CONSTRAINT financial_title_history_version_unique UNIQUE (tenant_id, company_id, title_id, title_version),
    CONSTRAINT financial_title_history_title_fk FOREIGN KEY (tenant_id, company_id, title_id)
        REFERENCES actionfinance.financial_title (tenant_id, company_id, id) ON DELETE RESTRICT
);

CREATE TABLE actionfinance.request_idempotency (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    company_id UUID NOT NULL,
    actor_id UUID NOT NULL,
    operation VARCHAR(80) NOT NULL,
    idempotency_key VARCHAR(128) NOT NULL,
    request_hash CHAR(64) NOT NULL,
    resource_id UUID NOT NULL,
    response_status INTEGER NOT NULL,
    response_body JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT request_idempotency_scope_unique UNIQUE (tenant_id, company_id, actor_id, operation, idempotency_key),
    CONSTRAINT request_idempotency_company_fk FOREIGN KEY (tenant_id, company_id)
        REFERENCES actionfinance.company (tenant_id, id) ON DELETE RESTRICT
);

CREATE INDEX financial_title_list_idx
    ON actionfinance.financial_title (tenant_id, company_id, direction, status, due_date, id);

CREATE INDEX financial_title_counterparty_idx
    ON actionfinance.financial_title (tenant_id, company_id, counterparty_id);

CREATE INDEX financial_title_category_idx
    ON actionfinance.financial_title (tenant_id, company_id, category_id);

CREATE INDEX financial_title_history_recent_idx
    ON actionfinance.financial_title_history (tenant_id, company_id, title_id, occurred_at DESC, id);

CREATE INDEX counterparty_active_name_idx
    ON actionfinance.counterparty (tenant_id, company_id, active, name, id);

CREATE INDEX financial_category_active_name_idx
    ON actionfinance.financial_category (tenant_id, company_id, active, name, id);
