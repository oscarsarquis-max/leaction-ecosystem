-- Confiabilidade da consulta. Não altera V1–V9.
-- last_attempt_* é o resultado da tentativa; external_status é a última observação financeira válida.

ALTER TABLE actionfinance.external_operation
    DROP CONSTRAINT external_operation_external_status_chk;

ALTER TABLE actionfinance.external_operation
    ADD CONSTRAINT external_operation_external_status_chk CHECK (external_status IN (
        'AWAITING_SEND', 'ACCEPTED', 'IN_PROGRESS', 'CONFIRMED', 'REFUSED', 'REFUNDED', 'UNKNOWN', 'REVIEW_REQUIRED'
    ));

ALTER TABLE actionfinance.external_operation
    ADD COLUMN last_attempt_outcome VARCHAR(32),
    ADD COLUMN last_attempt_at TIMESTAMPTZ;

ALTER TABLE actionfinance.external_operation
    ADD CONSTRAINT external_operation_attempt_outcome_chk CHECK (
        last_attempt_outcome IS NULL
        OR last_attempt_outcome IN ('STARTED', 'DELIVERED', 'UNAVAILABLE', 'REJECTED', 'INVALID', 'CONFLICT')
    );

CREATE TABLE actionfinance.lookup_attempt (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    company_id UUID NOT NULL,
    operation_id UUID NOT NULL,
    correlation_id VARCHAR(80) NOT NULL,
    outcome VARCHAR(24) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT lookup_attempt_outcome_chk CHECK (outcome IN (
        'STARTED', 'DELIVERED', 'UNAVAILABLE', 'REJECTED', 'INVALID', 'CONFLICT'
    )),
    CONSTRAINT lookup_attempt_scope_unique UNIQUE (tenant_id, company_id, id),
    CONSTRAINT lookup_attempt_operation_fk FOREIGN KEY (tenant_id, company_id, operation_id)
        REFERENCES actionfinance.external_operation (tenant_id, company_id, id) ON DELETE RESTRICT
);

CREATE INDEX lookup_attempt_operation_idx
    ON actionfinance.lookup_attempt (tenant_id, company_id, operation_id, created_at);

COMMENT ON TABLE actionfinance.lookup_attempt IS
    'Log de tentativas de consulta. Não é fila outbox nem despacho garantido.';
COMMENT ON TABLE actionfinance.integration_message IS
    'Rótulos OUTBOX/INBOX herdados. Nesta fatia de consulta o log efetivo é lookup_attempt.';
COMMENT ON COLUMN actionfinance.external_operation.external_status IS
    'Última observação financeira válida. Falha de transporte não a apaga.';
COMMENT ON COLUMN actionfinance.external_operation.last_attempt_outcome IS
    'Resultado da última tentativa de consulta, distinto da observação financeira.';

GRANT SELECT, INSERT ON TABLE actionfinance.lookup_attempt TO actionfinance_runtime;
REVOKE UPDATE, DELETE ON TABLE actionfinance.lookup_attempt FROM actionfinance_runtime;
GRANT SELECT, INSERT, UPDATE ON TABLE actionfinance.external_operation TO actionfinance_runtime;
