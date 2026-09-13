-- Isolated demo protection journey (PRM_013). V1–V12 unchanged.
-- Not a Satellite Contract table. No PII columns. No CASCADE.

CREATE TABLE segsense.demo_protection_journey (
    id UUID PRIMARY KEY,
    scenario_key VARCHAR(80) NOT NULL,
    declared_objective VARCHAR(80) NOT NULL,
    status VARCHAR(32) NOT NULL,
    correlation_id VARCHAR(36) NOT NULL,
    idempotency_key_hash CHAR(64) NOT NULL,
    spider_decision_id VARCHAR(80),
    mock_result_id VARCHAR(80),
    failure_kind VARCHAR(16),
    projection_json TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT demo_protection_journey_status_chk CHECK (
        status IN (
            'SUBMITTED',
            'SPIDER_DECISION',
            'PRE_PROPOSAL_AVAILABLE',
            'REJECTED',
            'SPIDER_UNAVAILABLE',
            'MOCK_UNAVAILABLE'
        )
    ),
    CONSTRAINT demo_protection_journey_failure_chk CHECK (
        failure_kind IS NULL OR failure_kind IN ('SPIDER', 'MOCK', 'VALIDATION')
    ),
    CONSTRAINT demo_protection_journey_idempotency_unique UNIQUE (idempotency_key_hash)
);

CREATE INDEX demo_protection_journey_correlation_idx
    ON segsense.demo_protection_journey (correlation_id);
