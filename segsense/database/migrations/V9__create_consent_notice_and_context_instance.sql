-- ConsentNotice versioned on the approved opportunity revision, ContextInstance,
-- typed collected values and append-only consent_decision ledger.
-- V1–V8 unchanged. No CASCADE. No data repair. No business triggers that mutate rows.
-- Conceptual rollback: drop decision trigger/function, value, instance, notice field,
-- snapshot, notice, then the new candidate keys on link and revision field.

DO $guard$
DECLARE
  personal_fields bigint;
  missing_classification bigint;
BEGIN
  SELECT COUNT(*) INTO personal_fields
  FROM segsense.contextual_opportunity_revision_field
  WHERE classification IS DISTINCT FROM 'NON_PERSONAL';

  SELECT COUNT(*) INTO missing_classification
  FROM segsense.contextual_opportunity_revision_field
  WHERE classification IS NULL;

  IF personal_fields > 0 OR missing_classification > 0 THEN
    RAISE EXCEPTION
      'V9 aborted without mutation: personal_fields=%, missing_classification=%',
      personal_fields, missing_classification;
  END IF;
END $guard$;

ALTER TABLE segsense.contextual_opportunity_revision_field
    ADD CONSTRAINT opportunity_revision_field_full_definition_unique
        UNIQUE (opportunity_revision_id, field_key, type, source, classification);

ALTER TABLE segsense.published_context_link
    ADD CONSTRAINT published_context_link_identity_unique
        UNIQUE (
            id,
            publisher_id,
            channel_id,
            environment_id,
            opportunity_id,
            revision_number,
            opportunity_revision_id
        );

CREATE TABLE segsense.consent_notice (
    id UUID PRIMARY KEY,
    publisher_id UUID NOT NULL,
    channel_id UUID NOT NULL,
    environment_id UUID NOT NULL,
    opportunity_id UUID NOT NULL,
    revision_number INTEGER NOT NULL,
    opportunity_revision_id UUID NOT NULL,
    current_version INTEGER NOT NULL,
    approved_version INTEGER,
    status VARCHAR(16) NOT NULL,
    version BIGINT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    created_by VARCHAR(128) NOT NULL,
    updated_by VARCHAR(128) NOT NULL,
    CONSTRAINT consent_notice_revision_unique UNIQUE (opportunity_revision_id),
    CONSTRAINT consent_notice_id_revision_unique UNIQUE (id, opportunity_revision_id),
    CONSTRAINT consent_notice_id_version_unique UNIQUE (id, current_version),
    CONSTRAINT consent_notice_scope_fk
        FOREIGN KEY (opportunity_id, publisher_id, channel_id, environment_id)
        REFERENCES segsense.contextual_opportunity (id, publisher_id, channel_id, environment_id)
        ON DELETE NO ACTION ON UPDATE NO ACTION,
    CONSTRAINT consent_notice_approved_revision_fk
        FOREIGN KEY (opportunity_id, revision_number)
        REFERENCES segsense.contextual_opportunity (id, approved_revision)
        ON DELETE NO ACTION ON UPDATE NO ACTION,
    CONSTRAINT consent_notice_revision_identity_fk
        FOREIGN KEY (opportunity_revision_id, opportunity_id, revision_number)
        REFERENCES segsense.contextual_opportunity_revision (id, opportunity_id, revision_number)
        ON DELETE NO ACTION ON UPDATE NO ACTION,
    CONSTRAINT consent_notice_status_chk CHECK (status IN ('DRAFT', 'APPROVED', 'RETIRED')),
    CONSTRAINT consent_notice_version_positive_chk CHECK (current_version >= 1),
    CONSTRAINT consent_notice_optimistic_chk CHECK (version >= 0),
    CONSTRAINT consent_notice_status_consistency_chk CHECK (
        (status = 'DRAFT' AND approved_version IS NULL)
        OR (status = 'APPROVED' AND approved_version = current_version)
        OR (status = 'RETIRED' AND approved_version IS NOT NULL)
    )
);

CREATE UNIQUE INDEX consent_notice_one_approved_per_revision_idx
    ON segsense.consent_notice (opportunity_revision_id)
    WHERE status = 'APPROVED';

CREATE TABLE segsense.consent_notice_snapshot (
    id UUID PRIMARY KEY,
    notice_id UUID NOT NULL,
    version_number INTEGER NOT NULL,
    purpose_title VARCHAR(140) NOT NULL,
    purpose_description VARCHAR(2000) NOT NULL,
    transparency_text VARCHAR(4000) NOT NULL,
    no_external_sharing_text VARCHAR(500) NOT NULL,
    content_hash CHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    created_by VARCHAR(128) NOT NULL,
    CONSTRAINT consent_notice_snapshot_unique UNIQUE (notice_id, version_number),
    CONSTRAINT consent_notice_snapshot_identity_unique UNIQUE (id, notice_id, version_number),
    CONSTRAINT consent_notice_snapshot_notice_fk FOREIGN KEY (notice_id)
        REFERENCES segsense.consent_notice (id)
        ON DELETE NO ACTION ON UPDATE NO ACTION,
    CONSTRAINT consent_notice_snapshot_version_chk CHECK (version_number >= 1),
    CONSTRAINT consent_notice_snapshot_title_len_chk
        CHECK (char_length(purpose_title) BETWEEN 5 AND 140),
    CONSTRAINT consent_notice_snapshot_description_len_chk
        CHECK (char_length(purpose_description) BETWEEN 20 AND 2000),
    CONSTRAINT consent_notice_snapshot_transparency_len_chk
        CHECK (char_length(transparency_text) BETWEEN 20 AND 4000),
    CONSTRAINT consent_notice_snapshot_sharing_len_chk
        CHECK (char_length(no_external_sharing_text) BETWEEN 10 AND 500),
    CONSTRAINT consent_notice_snapshot_hash_chk CHECK (content_hash ~ '^[a-f0-9]{64}$')
);

ALTER TABLE segsense.consent_notice
    ADD CONSTRAINT consent_notice_current_snapshot_fk
        FOREIGN KEY (id, current_version)
        REFERENCES segsense.consent_notice_snapshot (notice_id, version_number)
        ON DELETE NO ACTION ON UPDATE NO ACTION
        DEFERRABLE INITIALLY DEFERRED;

CREATE TABLE segsense.consent_notice_field (
    id UUID PRIMARY KEY,
    snapshot_id UUID NOT NULL,
    opportunity_revision_id UUID NOT NULL,
    field_key VARCHAR(40) NOT NULL,
    field_label VARCHAR(80) NOT NULL,
    field_type VARCHAR(16) NOT NULL,
    field_source VARCHAR(16) NOT NULL,
    classification VARCHAR(16) NOT NULL,
    required BOOLEAN NOT NULL,
    position INTEGER NOT NULL,
    allowed_values TEXT[],
    CONSTRAINT consent_notice_field_snapshot_fk FOREIGN KEY (snapshot_id)
        REFERENCES segsense.consent_notice_snapshot (id)
        ON DELETE NO ACTION ON UPDATE NO ACTION,
    CONSTRAINT consent_notice_field_definition_fk
        FOREIGN KEY (opportunity_revision_id, field_key, field_type, field_source, classification)
        REFERENCES segsense.contextual_opportunity_revision_field
            (opportunity_revision_id, field_key, type, source, classification)
        ON DELETE NO ACTION ON UPDATE NO ACTION,
    CONSTRAINT consent_notice_field_key_unique UNIQUE (snapshot_id, field_key),
    CONSTRAINT consent_notice_field_position_unique UNIQUE (snapshot_id, position),
    CONSTRAINT consent_notice_field_definition_unique
        UNIQUE (snapshot_id, field_key, field_type, field_source, classification),
    CONSTRAINT consent_notice_field_label_len_chk CHECK (char_length(field_label) BETWEEN 3 AND 80),
    CONSTRAINT consent_notice_field_source_chk CHECK (field_source IN ('USER', 'EITHER')),
    CONSTRAINT consent_notice_field_classification_chk CHECK (classification = 'NON_PERSONAL'),
    CONSTRAINT consent_notice_field_type_chk
        CHECK (field_type IN ('TEXT', 'NUMBER', 'BOOLEAN', 'DATE', 'ENUM')),
    CONSTRAINT consent_notice_field_position_chk CHECK (position >= 0 AND position < 20)
);

CREATE TABLE segsense.context_instance (
    id UUID PRIMARY KEY,
    link_id UUID NOT NULL,
    publisher_id UUID NOT NULL,
    channel_id UUID NOT NULL,
    environment_id UUID NOT NULL,
    opportunity_id UUID NOT NULL,
    revision_number INTEGER NOT NULL,
    opportunity_revision_id UUID NOT NULL,
    notice_id UUID NOT NULL,
    notice_version INTEGER NOT NULL,
    notice_snapshot_id UUID NOT NULL,
    notice_content_hash CHAR(64) NOT NULL,
    credential_digest BYTEA NOT NULL,
    credential_hint VARCHAR(8) NOT NULL,
    idempotency_key_digest BYTEA,
    status VARCHAR(32) NOT NULL,
    values_unavailable BOOLEAN NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    version BIGINT NOT NULL,
    created_correlation_id UUID NOT NULL,
    CONSTRAINT context_instance_credential_unique UNIQUE (credential_digest),
    CONSTRAINT context_instance_idempotency_unique UNIQUE (idempotency_key_digest),
    CONSTRAINT context_instance_link_identity_fk
        FOREIGN KEY (
            link_id,
            publisher_id,
            channel_id,
            environment_id,
            opportunity_id,
            revision_number,
            opportunity_revision_id
        )
        REFERENCES segsense.published_context_link (
            id,
            publisher_id,
            channel_id,
            environment_id,
            opportunity_id,
            revision_number,
            opportunity_revision_id
        )
        ON DELETE NO ACTION ON UPDATE NO ACTION,
    CONSTRAINT context_instance_notice_fk FOREIGN KEY (notice_id)
        REFERENCES segsense.consent_notice (id)
        ON DELETE NO ACTION ON UPDATE NO ACTION,
    CONSTRAINT context_instance_notice_snapshot_fk
        FOREIGN KEY (notice_snapshot_id, notice_id, notice_version)
        REFERENCES segsense.consent_notice_snapshot (id, notice_id, version_number)
        ON DELETE NO ACTION ON UPDATE NO ACTION,
    CONSTRAINT context_instance_notice_revision_fk
        FOREIGN KEY (notice_id, opportunity_revision_id)
        REFERENCES segsense.consent_notice (id, opportunity_revision_id)
        ON DELETE NO ACTION ON UPDATE NO ACTION,
    CONSTRAINT context_instance_status_chk CHECK (
        status IN (
            'AWAITING_INPUT',
            'AWAITING_DECISION',
            'AUTHORIZED',
            'AUTHORIZATION_WITHDRAWN',
            'EXPIRED'
        )
    ),
    CONSTRAINT context_instance_digest_len_chk CHECK (octet_length(credential_digest) = 32),
    CONSTRAINT context_instance_hint_len_chk CHECK (char_length(credential_hint) BETWEEN 1 AND 8),
    CONSTRAINT context_instance_idempotency_len_chk CHECK (
        idempotency_key_digest IS NULL OR octet_length(idempotency_key_digest) = 32
    ),
    CONSTRAINT context_instance_hash_chk CHECK (notice_content_hash ~ '^[a-f0-9]{64}$'),
    CONSTRAINT context_instance_version_chk CHECK (version >= 0),
    CONSTRAINT context_instance_withdrawn_values_chk CHECK (
        (status = 'AUTHORIZATION_WITHDRAWN' AND values_unavailable = TRUE)
        OR (status <> 'AUTHORIZATION_WITHDRAWN')
    )
);

CREATE INDEX context_instance_link_idx ON segsense.context_instance (link_id, created_at DESC, id);

CREATE TABLE segsense.context_instance_value (
    id UUID PRIMARY KEY,
    instance_id UUID NOT NULL,
    snapshot_id UUID NOT NULL,
    field_key VARCHAR(40) NOT NULL,
    field_type VARCHAR(16) NOT NULL,
    field_source VARCHAR(16) NOT NULL,
    classification VARCHAR(16) NOT NULL,
    text_value VARCHAR(200),
    number_value NUMERIC,
    boolean_value BOOLEAN,
    date_value DATE,
    CONSTRAINT context_instance_value_instance_fk FOREIGN KEY (instance_id)
        REFERENCES segsense.context_instance (id)
        ON DELETE NO ACTION ON UPDATE NO ACTION,
    CONSTRAINT context_instance_value_notice_field_fk
        FOREIGN KEY (snapshot_id, field_key, field_type, field_source, classification)
        REFERENCES segsense.consent_notice_field
            (snapshot_id, field_key, field_type, field_source, classification)
        ON DELETE NO ACTION ON UPDATE NO ACTION,
    CONSTRAINT context_instance_value_key_unique UNIQUE (instance_id, field_key),
    CONSTRAINT context_instance_value_source_chk CHECK (field_source IN ('USER', 'EITHER')),
    CONSTRAINT context_instance_value_classification_chk CHECK (classification = 'NON_PERSONAL'),
    CONSTRAINT context_instance_value_typed_chk CHECK (
        (field_type IN ('TEXT', 'ENUM')
            AND text_value IS NOT NULL
            AND number_value IS NULL
            AND boolean_value IS NULL
            AND date_value IS NULL)
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

CREATE TABLE segsense.consent_decision (
    id UUID PRIMARY KEY,
    instance_id UUID NOT NULL,
    decision_type VARCHAR(24) NOT NULL,
    notice_version INTEGER NOT NULL,
    notice_content_hash CHAR(64) NOT NULL,
    covered_fields_hash CHAR(64) NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL,
    correlation_id UUID NOT NULL,
    instance_version_before BIGINT NOT NULL,
    instance_version_after BIGINT NOT NULL,
    actor VARCHAR(32) NOT NULL,
    CONSTRAINT consent_decision_instance_fk FOREIGN KEY (instance_id)
        REFERENCES segsense.context_instance (id)
        ON DELETE NO ACTION ON UPDATE NO ACTION,
    CONSTRAINT consent_decision_type_chk CHECK (decision_type IN ('AUTHORIZED', 'WITHDRAWN')),
    CONSTRAINT consent_decision_hash_chk CHECK (
        notice_content_hash ~ '^[a-f0-9]{64}$'
        AND covered_fields_hash ~ '^[a-f0-9]{64}$'
    ),
    CONSTRAINT consent_decision_actor_chk CHECK (actor = 'PUBLIC_ANONYMOUS'),
    CONSTRAINT consent_decision_version_chk CHECK (instance_version_after = instance_version_before + 1)
);

CREATE UNIQUE INDEX consent_decision_one_authorized_per_instance_idx
    ON segsense.consent_decision (instance_id)
    WHERE decision_type = 'AUTHORIZED';

CREATE FUNCTION segsense.reject_consent_decision_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  RAISE EXCEPTION 'consent_decision is append-only';
END;
$$;

CREATE TRIGGER consent_decision_no_update
    BEFORE UPDATE ON segsense.consent_decision
    FOR EACH ROW
    EXECUTE FUNCTION segsense.reject_consent_decision_mutation();

CREATE TRIGGER consent_decision_no_delete
    BEFORE DELETE ON segsense.consent_decision
    FOR EACH ROW
    EXECUTE FUNCTION segsense.reject_consent_decision_mutation();
