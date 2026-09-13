-- Candidate key so published_context_link can FK the full opportunity scope.
-- V1–V6 unchanged. No CASCADE. Conceptual rollback: drop event, binding, link, then unique.

ALTER TABLE segsense.contextual_opportunity
    ADD CONSTRAINT opportunity_id_scope_unique
        UNIQUE (id, publisher_id, channel_id, environment_id);

CREATE TABLE segsense.published_context_link (
    id UUID PRIMARY KEY,
    publisher_id UUID NOT NULL,
    channel_id UUID NOT NULL,
    environment_id UUID NOT NULL,
    opportunity_id UUID NOT NULL,
    revision_number INTEGER NOT NULL,
    placement_key VARCHAR(80) NOT NULL,
    label VARCHAR(120) NOT NULL,
    token_digest BYTEA NOT NULL,
    token_hint VARCHAR(8) NOT NULL,
    status VARCHAR(16) NOT NULL,
    issued_at TIMESTAMPTZ NOT NULL,
    issued_by VARCHAR(128) NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    revoked_by VARCHAR(128),
    revocation_reason VARCHAR(500),
    version BIGINT NOT NULL,
    issued_correlation_id UUID NOT NULL,
    revoked_correlation_id UUID,
    CONSTRAINT published_context_link_digest_unique UNIQUE (token_digest),
    CONSTRAINT published_context_link_placement_unique
        UNIQUE (opportunity_id, revision_number, placement_key),
    CONSTRAINT published_context_link_scope_fk
        FOREIGN KEY (opportunity_id, publisher_id, channel_id, environment_id)
        REFERENCES segsense.contextual_opportunity (id, publisher_id, channel_id, environment_id)
        ON DELETE NO ACTION ON UPDATE NO ACTION,
    CONSTRAINT published_context_link_revision_fk
        FOREIGN KEY (opportunity_id, revision_number)
        REFERENCES segsense.contextual_opportunity_revision (opportunity_id, revision_number)
        ON DELETE NO ACTION ON UPDATE NO ACTION,
    CONSTRAINT published_context_link_status_chk CHECK (status IN ('ACTIVE', 'REVOKED')),
    CONSTRAINT published_context_link_placement_chk
        CHECK (placement_key ~ '^[a-z][a-z0-9-]{2,79}$'),
    CONSTRAINT published_context_link_label_len_chk
        CHECK (char_length(label) BETWEEN 5 AND 120),
    CONSTRAINT published_context_link_digest_len_chk
        CHECK (octet_length(token_digest) = 32),
    CONSTRAINT published_context_link_hint_len_chk
        CHECK (char_length(token_hint) BETWEEN 1 AND 8),
    CONSTRAINT published_context_link_expires_after_issued_chk CHECK (expires_at > issued_at),
    CONSTRAINT published_context_link_revoked_consistency_chk CHECK (
        (status = 'ACTIVE'
            AND revoked_at IS NULL
            AND revoked_by IS NULL
            AND revocation_reason IS NULL
            AND revoked_correlation_id IS NULL)
        OR (status = 'REVOKED'
            AND revoked_at IS NOT NULL
            AND revoked_by IS NOT NULL
            AND char_length(revocation_reason) BETWEEN 10 AND 500
            AND revoked_correlation_id IS NOT NULL)
    ),
    CONSTRAINT published_context_link_version_chk CHECK (version >= 0)
);

CREATE INDEX published_context_link_opportunity_cursor_idx
    ON segsense.published_context_link (opportunity_id, issued_at DESC, id);
CREATE INDEX published_context_link_expiry_idx
    ON segsense.published_context_link (status, expires_at);

CREATE TABLE segsense.published_context_link_binding (
    id UUID PRIMARY KEY,
    link_id UUID NOT NULL,
    field_key VARCHAR(40) NOT NULL,
    field_type VARCHAR(16) NOT NULL,
    text_value VARCHAR(200),
    number_value NUMERIC,
    boolean_value BOOLEAN,
    date_value DATE,
    CONSTRAINT published_context_link_binding_fk FOREIGN KEY (link_id)
        REFERENCES segsense.published_context_link (id)
        ON DELETE NO ACTION ON UPDATE NO ACTION,
    CONSTRAINT published_context_link_binding_key_unique UNIQUE (link_id, field_key),
    CONSTRAINT published_context_link_binding_key_format_chk
        CHECK (field_key ~ '^[a-z][a-zA-Z0-9]{1,39}$'),
    CONSTRAINT published_context_link_binding_type_chk
        CHECK (field_type IN ('TEXT', 'NUMBER', 'BOOLEAN', 'DATE', 'ENUM')),
    CONSTRAINT published_context_link_binding_value_chk CHECK (
        (field_type IN ('TEXT', 'ENUM')
            AND text_value IS NOT NULL
            AND number_value IS NULL
            AND boolean_value IS NULL
            AND date_value IS NULL
            AND char_length(text_value) BETWEEN 1 AND 200)
        OR (field_type = 'NUMBER'
            AND number_value IS NOT NULL
            AND text_value IS NULL
            AND boolean_value IS NULL
            AND date_value IS NULL)
        OR (field_type = 'BOOLEAN'
            AND boolean_value IS NOT NULL
            AND text_value IS NULL
            AND number_value IS NULL
            AND date_value IS NULL)
        OR (field_type = 'DATE'
            AND date_value IS NOT NULL
            AND text_value IS NULL
            AND number_value IS NULL
            AND boolean_value IS NULL)
    )
);

CREATE TABLE segsense.published_context_link_event (
    id UUID PRIMARY KEY,
    link_id UUID NOT NULL,
    event_type VARCHAR(16) NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL,
    actor_subject VARCHAR(128) NOT NULL,
    correlation_id UUID NOT NULL,
    CONSTRAINT published_context_link_event_fk FOREIGN KEY (link_id)
        REFERENCES segsense.published_context_link (id)
        ON DELETE NO ACTION ON UPDATE NO ACTION,
    CONSTRAINT published_context_link_event_type_chk CHECK (event_type IN ('ISSUED', 'REVOKED'))
);

CREATE INDEX published_context_link_event_cursor_idx
    ON segsense.published_context_link_event (link_id, occurred_at, id);
