-- Unique target for opportunity composite FKs, then opportunity + immutable revisions.
-- V1–V3 unchanged. No CASCADE. Conceptual rollback: drop field, revision, opportunity, then unique.

ALTER TABLE segsense.contextual_environment
    ADD CONSTRAINT environment_id_scope_unique UNIQUE (id, channel_id, publisher_id);

CREATE TABLE segsense.contextual_opportunity (
    id UUID PRIMARY KEY,
    publisher_id UUID NOT NULL,
    channel_id UUID NOT NULL,
    environment_id UUID NOT NULL,
    key VARCHAR(50) NOT NULL,
    status VARCHAR(16) NOT NULL,
    current_revision INTEGER NOT NULL,
    version BIGINT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    created_by VARCHAR(128) NOT NULL,
    updated_by VARCHAR(128) NOT NULL,
    CONSTRAINT opportunity_key_unique UNIQUE (environment_id, key),
    CONSTRAINT opportunity_key_format_chk CHECK (key ~ '^[a-z][a-z0-9-]{2,49}$'),
    CONSTRAINT opportunity_status_chk CHECK (status = 'DRAFT'),
    CONSTRAINT opportunity_revision_positive_chk CHECK (current_revision >= 1),
    CONSTRAINT opportunity_version_chk CHECK (version >= 0),
    CONSTRAINT opportunity_publisher_fk FOREIGN KEY (publisher_id)
        REFERENCES segsense.publisher (id) ON DELETE NO ACTION ON UPDATE NO ACTION,
    CONSTRAINT opportunity_channel_scope_fk FOREIGN KEY (channel_id, publisher_id)
        REFERENCES segsense.channel (id, publisher_id) ON DELETE NO ACTION ON UPDATE NO ACTION,
    CONSTRAINT opportunity_environment_scope_fk
        FOREIGN KEY (environment_id, channel_id, publisher_id)
        REFERENCES segsense.contextual_environment (id, channel_id, publisher_id)
        ON DELETE NO ACTION ON UPDATE NO ACTION
);

CREATE INDEX opportunity_environment_created_cursor_idx
    ON segsense.contextual_opportunity (environment_id, created_at, id);
CREATE INDEX opportunity_environment_status_idx
    ON segsense.contextual_opportunity (environment_id, status);

CREATE TABLE segsense.contextual_opportunity_revision (
    id UUID PRIMARY KEY,
    opportunity_id UUID NOT NULL,
    revision_number INTEGER NOT NULL,
    title VARCHAR(140) NOT NULL,
    context_mode VARCHAR(16) NOT NULL,
    context_summary_template VARCHAR(1000) NOT NULL,
    objective_template VARCHAR(1000) NOT NULL,
    call_to_action_label VARCHAR(80) NOT NULL,
    valid_from TIMESTAMPTZ,
    valid_until TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL,
    created_by VARCHAR(128) NOT NULL,
    CONSTRAINT opportunity_revision_unique UNIQUE (opportunity_id, revision_number),
    CONSTRAINT opportunity_revision_fk FOREIGN KEY (opportunity_id)
        REFERENCES segsense.contextual_opportunity (id)
        ON DELETE NO ACTION ON UPDATE NO ACTION,
    CONSTRAINT opportunity_revision_number_chk CHECK (revision_number >= 1),
    CONSTRAINT opportunity_revision_title_len_chk CHECK (char_length(title) BETWEEN 5 AND 140),
    CONSTRAINT opportunity_revision_summary_len_chk
        CHECK (char_length(context_summary_template) BETWEEN 10 AND 1000),
    CONSTRAINT opportunity_revision_objective_len_chk
        CHECK (char_length(objective_template) BETWEEN 10 AND 1000),
    CONSTRAINT opportunity_revision_cta_len_chk
        CHECK (char_length(call_to_action_label) BETWEEN 3 AND 80),
    CONSTRAINT opportunity_revision_mode_chk
        CHECK (context_mode IN ('STATIC', 'DYNAMIC', 'HYBRID')),
    CONSTRAINT opportunity_revision_validity_chk CHECK (
        valid_from IS NULL
        OR valid_until IS NULL
        OR valid_until > valid_from
    )
);

CREATE INDEX opportunity_revision_history_idx
    ON segsense.contextual_opportunity_revision (opportunity_id, revision_number);

CREATE TABLE segsense.contextual_opportunity_revision_field (
    id UUID PRIMARY KEY,
    opportunity_revision_id UUID NOT NULL,
    field_key VARCHAR(40) NOT NULL,
    label VARCHAR(80) NOT NULL,
    type VARCHAR(16) NOT NULL,
    required BOOLEAN NOT NULL,
    source VARCHAR(16) NOT NULL,
    classification VARCHAR(16) NOT NULL,
    position INTEGER NOT NULL,
    allowed_values TEXT[],
    CONSTRAINT opportunity_revision_field_fk FOREIGN KEY (opportunity_revision_id)
        REFERENCES segsense.contextual_opportunity_revision (id)
        ON DELETE NO ACTION ON UPDATE NO ACTION,
    CONSTRAINT opportunity_revision_field_key_unique UNIQUE (opportunity_revision_id, field_key),
    CONSTRAINT opportunity_revision_field_position_unique UNIQUE (opportunity_revision_id, position),
    CONSTRAINT opportunity_revision_field_key_format_chk
        CHECK (field_key ~ '^[a-z][a-zA-Z0-9]{1,39}$'),
    CONSTRAINT opportunity_revision_field_label_len_chk CHECK (char_length(label) BETWEEN 3 AND 80),
    CONSTRAINT opportunity_revision_field_type_chk
        CHECK (type IN ('TEXT', 'NUMBER', 'BOOLEAN', 'DATE', 'ENUM')),
    CONSTRAINT opportunity_revision_field_source_chk
        CHECK (source IN ('PUBLISHER', 'USER', 'EITHER')),
    CONSTRAINT opportunity_revision_field_classification_chk CHECK (classification = 'NON_PERSONAL'),
    CONSTRAINT opportunity_revision_field_position_chk CHECK (position >= 0 AND position < 20),
    CONSTRAINT opportunity_revision_field_enum_values_chk CHECK (
        (type <> 'ENUM' AND allowed_values IS NULL)
        OR (type = 'ENUM' AND cardinality(allowed_values) BETWEEN 1 AND 50)
    )
);
