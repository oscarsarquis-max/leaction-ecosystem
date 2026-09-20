-- PRM_020: URL capture snapshots and honest NO_COMPATIBLE_CAPABILITY. V1–V16 unchanged.

CREATE TABLE segsense.demo_url_capture (
    id UUID PRIMARY KEY,
    requested_url VARCHAR(2048) NOT NULL,
    final_url VARCHAR(2048),
    final_host VARCHAR(253),
    captured_at TIMESTAMPTZ NOT NULL,
    http_status INTEGER,
    content_type VARCHAR(200),
    title VARCHAR(300),
    detected_language VARCHAR(16),
    excerpt VARCHAR(2000),
    normalized_text TEXT,
    bytes_sha256 CHAR(64),
    text_sha256 CHAR(64),
    extractor_version VARCHAR(40) NOT NULL,
    result_code VARCHAR(40) NOT NULL,
    extracted_elements_json TEXT,
    correlation_id VARCHAR(80),
    created_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT demo_url_capture_result_chk CHECK (
        result_code IN (
            'FETCHED',
            'UNSUPPORTED_CONTENT',
            'TOO_LARGE',
            'TIMEOUT',
            'DNS_BLOCKED',
            'REDIRECT_BLOCKED',
            'HTTP_ERROR',
            'NO_MEANINGFUL_TEXT',
            'INVALID_URL'
        )
    )
);

CREATE INDEX demo_url_capture_created_idx
    ON segsense.demo_url_capture (created_at);

CREATE TABLE segsense.demo_url_capture_confirmation (
    id UUID PRIMARY KEY,
    capture_id UUID NOT NULL,
    confirmed_at TIMESTAMPTZ NOT NULL,
    confirmed_elements_json TEXT NOT NULL,
    corrections_json TEXT,
    correlation_id VARCHAR(80),
    CONSTRAINT demo_url_capture_confirmation_capture_fk
        FOREIGN KEY (capture_id) REFERENCES segsense.demo_url_capture (id)
);

CREATE INDEX demo_url_capture_confirmation_capture_idx
    ON segsense.demo_url_capture_confirmation (capture_id);

ALTER TABLE segsense.demo_protection_journey
    DROP CONSTRAINT demo_protection_journey_status_chk;

ALTER TABLE segsense.demo_protection_journey
    ADD CONSTRAINT demo_protection_journey_status_chk CHECK (
        status IN (
            'SUBMITTED',
            'SPIDER_DECISION',
            'PRE_PROPOSAL_AVAILABLE',
            'SIMULATED_QUOTE_AVAILABLE',
            'REJECTED',
            'SPIDER_UNAVAILABLE',
            'MOCK_UNAVAILABLE',
            'INCOMPLETE_CANONICAL',
            'MISSING_CONTEXT',
            'AMBIGUOUS',
            'NO_COMPATIBLE_CAPABILITY'
        )
    );
