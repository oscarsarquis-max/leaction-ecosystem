-- Cadastro operacional de clientes e fornecedores.
-- Incremental: reaproveita actionfinance.counterparty e seus IDs.
-- Sem DELETE físico da contraparte. Sem seed. Sem conector Panne.
-- Documento só é único quando informado; matriz/filiais são unidades da mesma pessoa.

ALTER TABLE actionfinance.counterparty
    ADD COLUMN person_kind VARCHAR(16) NOT NULL DEFAULT 'UNSPECIFIED',
    ADD COLUMN trade_name VARCHAR(160),
    ADD COLUMN document_country CHAR(2),
    ADD COLUMN document_type VARCHAR(16),
    ADD COLUMN document_number VARCHAR(32),
    ADD COLUMN document_number_normalized VARCHAR(32),
    ADD COLUMN document_pending BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN origin_kind VARCHAR(16) NOT NULL DEFAULT 'MANUAL',
    ADD COLUMN notes VARCHAR(500);

ALTER TABLE actionfinance.counterparty
    ADD CONSTRAINT counterparty_person_kind_chk
        CHECK (person_kind IN ('LEGAL', 'NATURAL', 'UNSPECIFIED')),
    ADD CONSTRAINT counterparty_document_type_chk
        CHECK (document_type IS NULL OR document_type IN ('CNPJ', 'CPF', 'OTHER')),
    ADD CONSTRAINT counterparty_origin_kind_chk
        CHECK (origin_kind IN ('MANUAL', 'FILE', 'SYSTEM')),
    ADD CONSTRAINT counterparty_document_shape_chk
        CHECK (
            (document_number_normalized IS NULL
                AND document_number IS NULL
                AND document_type IS NULL
                AND document_country IS NULL
                AND document_pending)
            OR (
                document_number_normalized IS NOT NULL
                AND document_number IS NOT NULL
                AND document_type IS NOT NULL
                AND document_country IS NOT NULL
                AND NOT document_pending
            )
        );

-- Decisão explícita: o documento da pessoa é chave forte no escopo empresa+tipo+país.
-- Unidades (filiais) podem ter documento próprio, em índice separado.
-- Ausência de documento permanece permitida; registros legados ficam pendentes.
CREATE UNIQUE INDEX counterparty_document_unique
    ON actionfinance.counterparty (
        tenant_id, company_id, document_country, document_type, document_number_normalized)
    WHERE document_number_normalized IS NOT NULL;

CREATE INDEX counterparty_search_name_idx
    ON actionfinance.counterparty (tenant_id, company_id, name);

CREATE INDEX counterparty_search_trade_idx
    ON actionfinance.counterparty (tenant_id, company_id, trade_name);

CREATE TABLE actionfinance.counterparty_unit (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    company_id UUID NOT NULL,
    counterparty_id UUID NOT NULL,
    name VARCHAR(160) NOT NULL,
    unit_kind VARCHAR(24) NOT NULL,
    is_primary BOOLEAN NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    document_country CHAR(2),
    document_type VARCHAR(16),
    document_number VARCHAR(32),
    document_number_normalized VARCHAR(32),
    version BIGINT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    created_by UUID NOT NULL,
    updated_by UUID NOT NULL,
    CONSTRAINT counterparty_unit_kind_chk
        CHECK (unit_kind IN ('STORE', 'DEPOT', 'WAREHOUSE', 'LOCAL_PRODUCER', 'OFFICE', 'OTHER')),
    CONSTRAINT counterparty_unit_document_type_chk
        CHECK (document_type IS NULL OR document_type IN ('CNPJ', 'CPF', 'OTHER')),
    CONSTRAINT counterparty_unit_document_shape_chk
        CHECK (
            (document_number_normalized IS NULL AND document_number IS NULL AND document_type IS NULL AND document_country IS NULL)
            OR (
                document_number_normalized IS NOT NULL
                AND document_number IS NOT NULL
                AND document_type IS NOT NULL
                AND document_country IS NOT NULL
            )
        ),
    CONSTRAINT counterparty_unit_scope_unique UNIQUE (tenant_id, company_id, id),
    CONSTRAINT counterparty_unit_party_fk FOREIGN KEY (tenant_id, company_id, counterparty_id)
        REFERENCES actionfinance.counterparty (tenant_id, company_id, id) ON DELETE RESTRICT,
    CONSTRAINT counterparty_unit_version_nonneg CHECK (version >= 0)
);

CREATE UNIQUE INDEX counterparty_unit_document_unique
    ON actionfinance.counterparty_unit (
        tenant_id, company_id, document_country, document_type, document_number_normalized)
    WHERE document_number_normalized IS NOT NULL AND active;

CREATE TABLE actionfinance.counterparty_address (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    company_id UUID NOT NULL,
    counterparty_id UUID NOT NULL,
    unit_id UUID,
    country CHAR(2) NOT NULL DEFAULT 'BR',
    postal_code VARCHAR(16),
    street VARCHAR(200),
    number VARCHAR(20),
    no_number BOOLEAN NOT NULL DEFAULT FALSE,
    complement VARCHAR(120),
    district VARCHAR(120),
    municipality VARCHAR(120),
    region VARCHAR(40),
    usage VARCHAR(24) NOT NULL DEFAULT 'MAIN',
    incomplete BOOLEAN NOT NULL DEFAULT TRUE,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    version BIGINT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    created_by UUID NOT NULL,
    updated_by UUID NOT NULL,
    CONSTRAINT counterparty_address_usage_chk
        CHECK (usage IN ('MAIN', 'BILLING', 'SHIPPING', 'OTHER')),
    CONSTRAINT counterparty_address_number_chk
        CHECK (NOT no_number OR number IS NULL),
    CONSTRAINT counterparty_address_scope_unique UNIQUE (tenant_id, company_id, id),
    CONSTRAINT counterparty_address_party_fk FOREIGN KEY (tenant_id, company_id, counterparty_id)
        REFERENCES actionfinance.counterparty (tenant_id, company_id, id) ON DELETE RESTRICT,
    CONSTRAINT counterparty_address_unit_fk FOREIGN KEY (tenant_id, company_id, unit_id)
        REFERENCES actionfinance.counterparty_unit (tenant_id, company_id, id) ON DELETE RESTRICT,
    CONSTRAINT counterparty_address_version_nonneg CHECK (version >= 0)
);

CREATE TABLE actionfinance.counterparty_contact (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    company_id UUID NOT NULL,
    counterparty_id UUID NOT NULL,
    name VARCHAR(160) NOT NULL,
    role_title VARCHAR(80),
    email VARCHAR(254),
    phone VARCHAR(40),
    is_primary BOOLEAN NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    version BIGINT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    created_by UUID NOT NULL,
    updated_by UUID NOT NULL,
    CONSTRAINT counterparty_contact_scope_unique UNIQUE (tenant_id, company_id, id),
    CONSTRAINT counterparty_contact_party_fk FOREIGN KEY (tenant_id, company_id, counterparty_id)
        REFERENCES actionfinance.counterparty (tenant_id, company_id, id) ON DELETE RESTRICT,
    CONSTRAINT counterparty_contact_version_nonneg CHECK (version >= 0)
);

CREATE TABLE actionfinance.counterparty_supply (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    company_id UUID NOT NULL,
    counterparty_id UUID NOT NULL,
    description VARCHAR(200) NOT NULL,
    supply_category VARCHAR(80),
    notes VARCHAR(500),
    active BOOLEAN NOT NULL DEFAULT TRUE,
    version BIGINT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    created_by UUID NOT NULL,
    updated_by UUID NOT NULL,
    CONSTRAINT counterparty_supply_scope_unique UNIQUE (tenant_id, company_id, id),
    CONSTRAINT counterparty_supply_party_fk FOREIGN KEY (tenant_id, company_id, counterparty_id)
        REFERENCES actionfinance.counterparty (tenant_id, company_id, id) ON DELETE RESTRICT,
    CONSTRAINT counterparty_supply_version_nonneg CHECK (version >= 0)
);

CREATE TABLE actionfinance.counterparty_external_identity (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    company_id UUID NOT NULL,
    counterparty_id UUID NOT NULL,
    origin_system VARCHAR(40) NOT NULL,
    connection_key VARCHAR(80),
    external_id VARCHAR(120) NOT NULL,
    observed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL,
    created_by UUID NOT NULL,
    CONSTRAINT counterparty_external_origin_chk
        CHECK (origin_system IN ('PANNE', 'FILE', 'OTHER')),
    CONSTRAINT counterparty_external_scope_unique UNIQUE (tenant_id, company_id, id),
    CONSTRAINT counterparty_external_identity_unique
        UNIQUE (tenant_id, company_id, origin_system, connection_key, external_id),
    CONSTRAINT counterparty_external_party_fk FOREIGN KEY (tenant_id, company_id, counterparty_id)
        REFERENCES actionfinance.counterparty (tenant_id, company_id, id) ON DELETE RESTRICT
);

CREATE TABLE actionfinance.counterparty_history (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    company_id UUID NOT NULL,
    counterparty_id UUID NOT NULL,
    counterparty_version BIGINT NOT NULL,
    action VARCHAR(24) NOT NULL,
    actor_id UUID NOT NULL,
    actor_display_name VARCHAR(160),
    occurred_at TIMESTAMPTZ NOT NULL,
    reason VARCHAR(500),
    changes JSONB,
    CONSTRAINT counterparty_history_action_chk
        CHECK (action IN ('CREATED', 'UPDATED', 'INACTIVATED', 'REACTIVATED', 'IMPORTED')),
    CONSTRAINT counterparty_history_party_fk FOREIGN KEY (tenant_id, company_id, counterparty_id)
        REFERENCES actionfinance.counterparty (tenant_id, company_id, id) ON DELETE RESTRICT
);

CREATE INDEX counterparty_history_party_idx
    ON actionfinance.counterparty_history (tenant_id, company_id, counterparty_id, occurred_at);

CREATE TABLE actionfinance.counterparty_import_batch (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    company_id UUID NOT NULL,
    filename VARCHAR(200) NOT NULL,
    content_sha256 CHAR(64) NOT NULL,
    status VARCHAR(20) NOT NULL,
    total_lines INT NOT NULL,
    column_map JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    created_by UUID NOT NULL,
    confirmed_at TIMESTAMPTZ,
    confirmed_by UUID,
    CONSTRAINT counterparty_import_status_chk
        CHECK (status IN ('PREVIEW', 'CONFIRMED', 'CANCELLED')),
    CONSTRAINT counterparty_import_scope_unique UNIQUE (tenant_id, company_id, id),
    CONSTRAINT counterparty_import_company_fk FOREIGN KEY (tenant_id, company_id)
        REFERENCES actionfinance.company (tenant_id, id) ON DELETE RESTRICT
);

CREATE UNIQUE INDEX counterparty_import_batch_resume_unique
    ON actionfinance.counterparty_import_batch (tenant_id, company_id, content_sha256)
    WHERE status = 'PREVIEW';

CREATE TABLE actionfinance.counterparty_import_line (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    company_id UUID NOT NULL,
    batch_id UUID NOT NULL,
    line_no INT NOT NULL,
    raw JSONB NOT NULL,
    classification VARCHAR(20) NOT NULL,
    selected BOOLEAN NOT NULL DEFAULT FALSE,
    match_counterparty_id UUID,
    preview_version BIGINT,
    result VARCHAR(20),
    error_message VARCHAR(400),
    idempotency_key VARCHAR(128) NOT NULL,
    CONSTRAINT counterparty_import_line_class_chk
        CHECK (classification IN ('NEW', 'DUPLICATE', 'CONFLICT', 'INVALID')),
    CONSTRAINT counterparty_import_line_result_chk
        CHECK (result IS NULL OR result IN ('CREATED', 'UPDATED', 'SKIPPED', 'REJECTED')),
    CONSTRAINT counterparty_import_line_scope_unique UNIQUE (tenant_id, company_id, id),
    CONSTRAINT counterparty_import_line_batch_unique UNIQUE (tenant_id, company_id, batch_id, line_no),
    CONSTRAINT counterparty_import_line_idem_unique UNIQUE (tenant_id, company_id, idempotency_key),
    CONSTRAINT counterparty_import_line_batch_fk FOREIGN KEY (tenant_id, company_id, batch_id)
        REFERENCES actionfinance.counterparty_import_batch (tenant_id, company_id, id) ON DELETE RESTRICT
);

CREATE INDEX counterparty_external_search_idx
    ON actionfinance.counterparty_external_identity (tenant_id, company_id, external_id);

COMMENT ON TABLE actionfinance.counterparty_supply IS
    'Produtos/serviços fornecidos informados no cadastro. Não é categoria financeira nem estoque.';
COMMENT ON TABLE actionfinance.counterparty_external_identity IS
    'Vínculo externo por empresa+sistema+ID. Preparação de contrato; sem conector ativo.';
COMMENT ON COLUMN actionfinance.counterparty.document_number IS
    'Texto informado. Não é inteiro. Zeros à esquerda são preservados.';
