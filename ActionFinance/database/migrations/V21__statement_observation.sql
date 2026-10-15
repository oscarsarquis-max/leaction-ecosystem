-- Observação de extrato. Não cria título, baixa, movimento de caixa nem saldo.
-- Sugestão de vínculo não é conciliação. Retirada lógica não apaga o fato externo.

CREATE TABLE actionfinance.external_account_link (
    id UUID NOT NULL,
    tenant_id UUID NOT NULL,
    company_id UUID NOT NULL,
    account_id UUID NOT NULL,
    origin_system VARCHAR(32) NOT NULL,
    external_ref VARCHAR(80) NOT NULL,
    provenance VARCHAR(500) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    created_by UUID NOT NULL,
    CONSTRAINT external_account_link_pk PRIMARY KEY (id),
    CONSTRAINT external_account_link_scope_id UNIQUE (tenant_id, company_id, id),
    CONSTRAINT external_account_link_account UNIQUE (tenant_id, company_id, account_id, origin_system),
    CONSTRAINT external_account_link_ref UNIQUE (tenant_id, company_id, origin_system, external_ref),
    CONSTRAINT external_account_link_company_fk FOREIGN KEY (tenant_id, company_id)
        REFERENCES actionfinance.company (tenant_id, id) ON DELETE RESTRICT,
    CONSTRAINT external_account_link_account_fk FOREIGN KEY (tenant_id, company_id, account_id)
        REFERENCES actionfinance.financial_account (tenant_id, company_id, id) ON DELETE RESTRICT,
    CONSTRAINT external_account_link_origin_chk CHECK (origin_system = 'MERCADOPAGO'),
    CONSTRAINT external_account_link_ref_chk CHECK (char_length(btrim(external_ref)) BETWEEN 3 AND 80),
    CONSTRAINT external_account_link_provenance_chk CHECK (char_length(btrim(provenance)) BETWEEN 3 AND 500)
);

CREATE TABLE actionfinance.statement_batch (
    id UUID NOT NULL,
    tenant_id UUID NOT NULL,
    company_id UUID NOT NULL,
    account_id UUID NOT NULL,
    profile_id VARCHAR(40) NOT NULL,
    parser_version VARCHAR(16) NOT NULL,
    file_sha256 CHAR(64) NOT NULL,
    file_name VARCHAR(200) NOT NULL,
    status VARCHAR(16) NOT NULL,
    preview_token CHAR(64) NOT NULL,
    file_account_ref VARCHAR(80),
    account_evidence VARCHAR(500),
    period_from DATE,
    period_to DATE,
    preview_json TEXT NOT NULL,
    result_json TEXT,
    confirm_idempotency_key VARCHAR(80),
    selection_sha256 CHAR(64),
    created_count INTEGER NOT NULL DEFAULT 0,
    enriched_count INTEGER NOT NULL DEFAULT 0,
    unchanged_count INTEGER NOT NULL DEFAULT 0,
    rejected_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL,
    created_by UUID NOT NULL,
    confirmed_at TIMESTAMPTZ,
    confirmed_by UUID,
    withdrawn_at TIMESTAMPTZ,
    withdrawn_by UUID,
    withdraw_reason VARCHAR(500),
    CONSTRAINT statement_batch_pk PRIMARY KEY (id),
    CONSTRAINT statement_batch_scope_id UNIQUE (tenant_id, company_id, id),
    CONSTRAINT statement_batch_company_fk FOREIGN KEY (tenant_id, company_id)
        REFERENCES actionfinance.company (tenant_id, id) ON DELETE RESTRICT,
    CONSTRAINT statement_batch_account_fk FOREIGN KEY (tenant_id, company_id, account_id)
        REFERENCES actionfinance.financial_account (tenant_id, company_id, id) ON DELETE RESTRICT,
    CONSTRAINT statement_batch_status_chk CHECK (status IN ('PREVIEW', 'CONFIRMED', 'WITHDRAWN')),
    CONSTRAINT statement_batch_profile_chk CHECK (profile_id = 'mp-account-money-csv-1'),
    CONSTRAINT statement_batch_sha_chk CHECK (file_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT statement_batch_token_chk CHECK (preview_token ~ '^[0-9a-f]{64}$')
);

CREATE UNIQUE INDEX statement_batch_confirm_key_uidx
    ON actionfinance.statement_batch (tenant_id, company_id, confirm_idempotency_key)
    WHERE confirm_idempotency_key IS NOT NULL;

CREATE TABLE actionfinance.statement_line (
    id UUID NOT NULL,
    tenant_id UUID NOT NULL,
    company_id UUID NOT NULL,
    account_id UUID NOT NULL,
    batch_id UUID NOT NULL,
    event_key VARCHAR(220) NOT NULL,
    content_hash CHAR(64) NOT NULL,
    source_id VARCHAR(80) NOT NULL,
    record_type VARCHAR(24) NOT NULL,
    external_reference VARCHAR(80),
    description VARCHAR(300),
    effective_on DATE,
    direction VARCHAR(8) NOT NULL,
    event_kind VARCHAR(24) NOT NULL,
    balance_effect VARCHAR(24) NOT NULL,
    gross_minor NUMERIC(19, 0),
    gross_absent BOOLEAN NOT NULL,
    fee_minor NUMERIC(19, 0),
    fee_absent BOOLEAN NOT NULL,
    net_minor NUMERIC(19, 0),
    net_absent BOOLEAN NOT NULL,
    currency CHAR(3) NOT NULL,
    currency_assumed BOOLEAN NOT NULL,
    classification_state VARCHAR(16) NOT NULL,
    initiative_state VARCHAR(16) NOT NULL,
    import_status VARCHAR(16) NOT NULL,
    source_line_number INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT statement_line_pk PRIMARY KEY (id),
    CONSTRAINT statement_line_scope_id UNIQUE (tenant_id, company_id, id),
    CONSTRAINT statement_line_event_uidx UNIQUE (tenant_id, company_id, account_id, event_key),
    CONSTRAINT statement_line_company_fk FOREIGN KEY (tenant_id, company_id)
        REFERENCES actionfinance.company (tenant_id, id) ON DELETE RESTRICT,
    CONSTRAINT statement_line_account_fk FOREIGN KEY (tenant_id, company_id, account_id)
        REFERENCES actionfinance.financial_account (tenant_id, company_id, id) ON DELETE RESTRICT,
    CONSTRAINT statement_line_batch_fk FOREIGN KEY (tenant_id, company_id, batch_id)
        REFERENCES actionfinance.statement_batch (tenant_id, company_id, id) ON DELETE RESTRICT,
    CONSTRAINT statement_line_direction_chk CHECK (direction IN ('IN', 'OUT', 'NONE')),
    CONSTRAINT statement_line_effect_chk CHECK (balance_effect IN ('AFFECTS', 'AVAILABILITY_ONLY', 'UNKNOWN')),
    CONSTRAINT statement_line_currency_chk CHECK (currency = 'BRL'),
    CONSTRAINT statement_line_class_chk CHECK (classification_state = 'UNCLASSIFIED'),
    CONSTRAINT statement_line_initiative_chk CHECK (initiative_state = 'UNASSIGNED'),
    CONSTRAINT statement_line_import_chk CHECK (import_status IN ('ACTIVE', 'WITHDRAWN')),
    CONSTRAINT statement_line_gross_chk CHECK (
        (gross_minor IS NULL AND gross_absent) OR (gross_minor IS NOT NULL AND NOT gross_absent AND gross_minor >= 0)),
    CONSTRAINT statement_line_fee_chk CHECK (
        (fee_minor IS NULL AND fee_absent) OR (fee_minor IS NOT NULL AND NOT fee_absent AND fee_minor >= 0)),
    CONSTRAINT statement_line_net_chk CHECK (
        (net_minor IS NULL AND net_absent) OR (net_minor IS NOT NULL AND NOT net_absent AND net_minor >= 0))
);

CREATE INDEX statement_line_list_idx
    ON actionfinance.statement_line (tenant_id, company_id, account_id, effective_on DESC, id DESC);

CREATE TABLE actionfinance.statement_original_row (
    id UUID NOT NULL,
    tenant_id UUID NOT NULL,
    company_id UUID NOT NULL,
    line_id UUID NOT NULL,
    batch_id UUID NOT NULL,
    source_line_number INTEGER NOT NULL,
    raw_text VARCHAR(2000) NOT NULL,
    truncated BOOLEAN NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT statement_original_row_pk PRIMARY KEY (id),
    CONSTRAINT statement_original_row_company_fk FOREIGN KEY (tenant_id, company_id)
        REFERENCES actionfinance.company (tenant_id, id) ON DELETE RESTRICT,
    CONSTRAINT statement_original_row_line_fk FOREIGN KEY (tenant_id, company_id, line_id)
        REFERENCES actionfinance.statement_line (tenant_id, company_id, id) ON DELETE RESTRICT
);

COMMENT ON TABLE actionfinance.statement_original_row IS
    'Texto da linha do arquivo, restrito à empresa. Sem URL pública. Retirada do lote não apaga esta evidência.';

GRANT SELECT, INSERT, UPDATE ON TABLE actionfinance.external_account_link TO actionfinance_runtime;
GRANT SELECT, INSERT, UPDATE ON TABLE actionfinance.statement_batch TO actionfinance_runtime;
GRANT SELECT, INSERT, UPDATE ON TABLE actionfinance.statement_line TO actionfinance_runtime;
GRANT SELECT, INSERT ON TABLE actionfinance.statement_original_row TO actionfinance_runtime;

REVOKE DELETE ON TABLE actionfinance.external_account_link FROM actionfinance_runtime;
REVOKE DELETE ON TABLE actionfinance.statement_batch FROM actionfinance_runtime;
REVOKE DELETE ON TABLE actionfinance.statement_line FROM actionfinance_runtime;
REVOKE UPDATE, DELETE ON TABLE actionfinance.statement_original_row FROM actionfinance_runtime;
