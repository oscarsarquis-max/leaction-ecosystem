-- Identidade de aplicação, vínculos por empresa e sessões JDBC (Spring Session 3.4).
-- Sem seed. Sem FK de fatos financeiros para app_user (autoria demo/legado permanece UUID opaco).

CREATE TABLE actionfinance.app_user (
    id UUID PRIMARY KEY,
    display_name VARCHAR(160) NOT NULL,
    status VARCHAR(16) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    version BIGINT NOT NULL,
    CONSTRAINT app_user_status_chk CHECK (status IN ('ACTIVE', 'BLOCKED')),
    CONSTRAINT app_user_version_nonneg CHECK (version >= 0),
    CONSTRAINT app_user_display_name_chk CHECK (char_length(btrim(display_name)) >= 1)
);

CREATE TABLE actionfinance.external_identity (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES actionfinance.app_user (id) ON DELETE RESTRICT,
    issuer VARCHAR(512) NOT NULL,
    subject VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT external_identity_issuer_subject_unique UNIQUE (issuer, subject),
    CONSTRAINT external_identity_issuer_chk CHECK (char_length(btrim(issuer)) >= 1),
    CONSTRAINT external_identity_subject_chk CHECK (char_length(btrim(subject)) >= 1)
);

CREATE INDEX external_identity_user_idx ON actionfinance.external_identity (user_id);

CREATE TABLE actionfinance.company_membership (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES actionfinance.app_user (id) ON DELETE RESTRICT,
    tenant_id UUID NOT NULL,
    company_id UUID NOT NULL,
    role VARCHAR(16) NOT NULL,
    status VARCHAR(16) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    version BIGINT NOT NULL,
    CONSTRAINT company_membership_role_chk CHECK (role IN ('VIEWER', 'OPERATOR')),
    CONSTRAINT company_membership_status_chk CHECK (status IN ('ACTIVE', 'REVOKED')),
    CONSTRAINT company_membership_version_nonneg CHECK (version >= 0),
    CONSTRAINT company_membership_user_company_unique UNIQUE (user_id, tenant_id, company_id),
    CONSTRAINT company_membership_company_fk FOREIGN KEY (tenant_id, company_id)
        REFERENCES actionfinance.company (tenant_id, id) ON DELETE RESTRICT
);

CREATE INDEX company_membership_company_idx ON actionfinance.company_membership (tenant_id, company_id, status);
CREATE INDEX company_membership_user_status_idx ON actionfinance.company_membership (user_id, status);

CREATE TABLE actionfinance.access_admin_audit (
    id UUID PRIMARY KEY,
    occurred_at TIMESTAMPTZ NOT NULL,
    executor_kind VARCHAR(32) NOT NULL,
    executor_label VARCHAR(160) NOT NULL,
    target_kind VARCHAR(32) NOT NULL,
    target_id UUID,
    action VARCHAR(40) NOT NULL,
    reason VARCHAR(500) NOT NULL,
    correlation_id VARCHAR(80),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    CONSTRAINT access_admin_audit_executor_kind_chk CHECK (executor_kind IN ('ADMIN_CLI', 'SYSTEM')),
    CONSTRAINT access_admin_audit_target_kind_chk CHECK (target_kind IN ('USER', 'IDENTITY', 'MEMBERSHIP')),
    CONSTRAINT access_admin_audit_action_chk CHECK (action IN (
        'PROVISION_USER',
        'LINK_IDENTITY',
        'GRANT_MEMBERSHIP',
        'REVOKE_MEMBERSHIP',
        'BLOCK_USER',
        'UNBLOCK_USER')),
    CONSTRAINT access_admin_audit_reason_chk CHECK (char_length(btrim(reason)) >= 3)
);

CREATE INDEX access_admin_audit_occurred_idx ON actionfinance.access_admin_audit (occurred_at DESC, id);
CREATE INDEX access_admin_audit_target_idx ON actionfinance.access_admin_audit (target_kind, target_id);

-- Schema oficial Spring Session 3.4 (PostgreSQL), no schema do produto.
CREATE TABLE actionfinance.SPRING_SESSION (
    PRIMARY_ID CHAR(36) NOT NULL,
    SESSION_ID CHAR(36) NOT NULL,
    CREATION_TIME BIGINT NOT NULL,
    LAST_ACCESS_TIME BIGINT NOT NULL,
    MAX_INACTIVE_INTERVAL INT NOT NULL,
    EXPIRY_TIME BIGINT NOT NULL,
    PRINCIPAL_NAME VARCHAR(100),
    CONSTRAINT SPRING_SESSION_PK PRIMARY KEY (PRIMARY_ID)
);

CREATE UNIQUE INDEX SPRING_SESSION_IX1 ON actionfinance.SPRING_SESSION (SESSION_ID);
CREATE INDEX SPRING_SESSION_IX2 ON actionfinance.SPRING_SESSION (EXPIRY_TIME);
CREATE INDEX SPRING_SESSION_IX3 ON actionfinance.SPRING_SESSION (PRINCIPAL_NAME);

CREATE TABLE actionfinance.SPRING_SESSION_ATTRIBUTES (
    SESSION_PRIMARY_ID CHAR(36) NOT NULL,
    ATTRIBUTE_NAME VARCHAR(200) NOT NULL,
    ATTRIBUTE_BYTES BYTEA NOT NULL,
    CONSTRAINT SPRING_SESSION_ATTRIBUTES_PK PRIMARY KEY (SESSION_PRIMARY_ID, ATTRIBUTE_NAME),
    CONSTRAINT SPRING_SESSION_ATTRIBUTES_FK FOREIGN KEY (SESSION_PRIMARY_ID)
        REFERENCES actionfinance.SPRING_SESSION (PRIMARY_ID) ON DELETE CASCADE
);

CREATE INDEX SPRING_SESSION_ATTRIBUTES_IX1 ON actionfinance.SPRING_SESSION_ATTRIBUTES (SESSION_PRIMARY_ID);

COMMENT ON TABLE actionfinance.app_user IS
    'Ator estável do ActionFinance. Não é identidade OIDC e não recebe senha.';
COMMENT ON TABLE actionfinance.external_identity IS
    'Vínculo issuer+subject. Email não é chave.';
COMMENT ON TABLE actionfinance.company_membership IS
    'Autorização e papel por empresa. Claims externos não gravam aqui.';
COMMENT ON TABLE actionfinance.access_admin_audit IS
    'Append-only de provisionamento administrativo. Sem segredos.';
COMMENT ON TABLE actionfinance.SPRING_SESSION IS
    'Spring Session JDBC 3.4. Runtime pode apagar linhas expiradas.';
