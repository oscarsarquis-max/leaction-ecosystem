-- Acompanhamento de consulta externa via Spider. Sem baixa automática.
-- Mapeamento empresa↔Pay é explícito; não inferido por nome.

CREATE TABLE actionfinance.pay_company_mapping (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    company_id UUID NOT NULL,
    pay_app_id VARCHAR(80) NOT NULL,
    environment VARCHAR(16) NOT NULL,
    authorized BOOLEAN NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT pay_company_mapping_env_chk CHECK (environment IN ('HOMOLOG', 'SANDBOX')),
    CONSTRAINT pay_company_mapping_scope_unique UNIQUE (tenant_id, company_id),
    CONSTRAINT pay_company_mapping_company_fk FOREIGN KEY (tenant_id, company_id)
        REFERENCES actionfinance.company (tenant_id, id) ON DELETE RESTRICT
);

CREATE TABLE actionfinance.external_operation (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    company_id UUID NOT NULL,
    title_id UUID,
    capability VARCHAR(40) NOT NULL,
    origin_system VARCHAR(32) NOT NULL,
    origin_kind VARCHAR(24) NOT NULL,
    external_reference VARCHAR(80) NOT NULL,
    amount_minor NUMERIC(19, 0),
    currency CHAR(3),
    external_status VARCHAR(32) NOT NULL,
    delivery_status VARCHAR(32) NOT NULL,
    idempotency_key VARCHAR(80) NOT NULL,
    semantic_fingerprint VARCHAR(64) NOT NULL,
    correlation_id VARCHAR(80) NOT NULL,
    spider_decision_id VARCHAR(80),
    provider_reference VARCHAR(80),
    provider_origin VARCHAR(40),
    last_error VARCHAR(200),
    observed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    version BIGINT NOT NULL,
    CONSTRAINT external_operation_capability_chk CHECK (capability IN ('LOOKUP_ACTIONHUB_PAYMENT')),
    CONSTRAINT external_operation_origin_chk CHECK (origin_system = 'ACTIONHUB_PAY'),
    CONSTRAINT external_operation_origin_kind_chk CHECK (origin_kind IN ('TITLE', 'STANDALONE')),
    CONSTRAINT external_operation_external_status_chk CHECK (external_status IN (
        'AWAITING_SEND', 'ACCEPTED', 'IN_PROGRESS', 'CONFIRMED', 'REFUSED', 'UNKNOWN', 'REVIEW_REQUIRED'
    )),
    CONSTRAINT external_operation_delivery_chk CHECK (delivery_status IN (
        'PENDING', 'DELIVERED', 'LOST_RESPONSE', 'CONFLICT', 'UNAVAILABLE'
    )),
    CONSTRAINT external_operation_currency_chk CHECK (currency IS NULL OR currency = 'BRL'),
    CONSTRAINT external_operation_scope_unique UNIQUE (tenant_id, company_id, id),
    CONSTRAINT external_operation_idem_unique UNIQUE (tenant_id, company_id, idempotency_key),
    CONSTRAINT external_operation_ext_ref_unique UNIQUE (tenant_id, company_id, origin_system, external_reference),
    CONSTRAINT external_operation_company_fk FOREIGN KEY (tenant_id, company_id)
        REFERENCES actionfinance.company (tenant_id, id) ON DELETE RESTRICT,
    CONSTRAINT external_operation_title_fk FOREIGN KEY (tenant_id, company_id, title_id)
        REFERENCES actionfinance.financial_title (tenant_id, company_id, id) ON DELETE RESTRICT,
    CONSTRAINT external_operation_version_nonneg CHECK (version >= 0)
);

CREATE TABLE actionfinance.integration_message (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    company_id UUID NOT NULL,
    operation_id UUID NOT NULL,
    direction VARCHAR(8) NOT NULL,
    message_id VARCHAR(80) NOT NULL,
    correlation_id VARCHAR(80) NOT NULL,
    idempotency_key VARCHAR(80) NOT NULL,
    kind VARCHAR(32) NOT NULL,
    outcome VARCHAR(24) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT integration_message_dir_chk CHECK (direction IN ('OUTBOX', 'INBOX')),
    CONSTRAINT integration_message_kind_chk CHECK (kind IN ('LOOKUP_REQUEST', 'LOOKUP_RESPONSE')),
    CONSTRAINT integration_message_outcome_chk CHECK (outcome IN ('SENT', 'RECEIVED', 'CONFLICT', 'FAILED')),
    CONSTRAINT integration_message_scope_unique UNIQUE (tenant_id, company_id, id),
    CONSTRAINT integration_message_dedup UNIQUE (tenant_id, company_id, direction, message_id),
    CONSTRAINT integration_message_operation_fk FOREIGN KEY (tenant_id, company_id, operation_id)
        REFERENCES actionfinance.external_operation (tenant_id, company_id, id) ON DELETE RESTRICT
);

CREATE INDEX external_operation_title_idx
    ON actionfinance.external_operation (tenant_id, company_id, title_id)
    WHERE title_id IS NOT NULL;

COMMENT ON TABLE actionfinance.pay_company_mapping IS
    'Vínculo explícito empresa local → aplicativo Pay. Sem inferência por nome.';
COMMENT ON TABLE actionfinance.external_operation IS
    'Consulta externa via Spider. Resultado não liquida título neste recorte.';
COMMENT ON TABLE actionfinance.integration_message IS
    'Outbox/inbox durável da fatia de consulta. Sem tokens.';
