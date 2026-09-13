-- Harden notice/value/decision identity so SQL cannot cross snapshots or revisions.
-- V1–V9 unchanged. No CASCADE. No data repair. Conceptual rollback: drop V10
-- triggers/functions, consent_notice_decision, new FKs/uniques/columns.

DO $guard$
DECLARE
  crossed_value bigint;
  crossed_field bigint;
  missing_idempotency bigint;
  personal_fields bigint;
BEGIN
  SELECT COUNT(*) INTO crossed_value
  FROM segsense.context_instance_value v
  JOIN segsense.context_instance i ON v.instance_id = i.id
  WHERE v.snapshot_id IS DISTINCT FROM i.notice_snapshot_id
     OR EXISTS (
       SELECT 1
       FROM segsense.consent_notice_field f
       WHERE f.snapshot_id = v.snapshot_id
         AND f.field_key = v.field_key
         AND f.opportunity_revision_id IS DISTINCT FROM i.opportunity_revision_id
     );

  SELECT COUNT(*) INTO crossed_field
  FROM segsense.consent_notice_field f
  JOIN segsense.consent_notice_snapshot s ON f.snapshot_id = s.id
  JOIN segsense.consent_notice n ON s.notice_id = n.id
  WHERE f.opportunity_revision_id IS DISTINCT FROM n.opportunity_revision_id;

  SELECT COUNT(*) INTO missing_idempotency
  FROM segsense.context_instance
  WHERE idempotency_key_digest IS NULL
     OR octet_length(idempotency_key_digest) <> 32;

  SELECT COUNT(*) INTO personal_fields
  FROM segsense.contextual_opportunity_revision_field
  WHERE classification IS DISTINCT FROM 'NON_PERSONAL';

  IF crossed_value > 0 OR crossed_field > 0 OR missing_idempotency > 0 OR personal_fields > 0 THEN
    RAISE EXCEPTION
      'V10 aborted without mutation: crossed_value=%, crossed_field=%, missing_idempotency=%, personal_fields=%',
      crossed_value, crossed_field, missing_idempotency, personal_fields;
  END IF;
END $guard$;

ALTER TABLE segsense.consent_notice_snapshot
    ADD COLUMN opportunity_revision_id UUID;

UPDATE segsense.consent_notice_snapshot s
SET opportunity_revision_id = n.opportunity_revision_id
FROM segsense.consent_notice n
WHERE s.notice_id = n.id;

ALTER TABLE segsense.consent_notice_snapshot
    ALTER COLUMN opportunity_revision_id SET NOT NULL;

ALTER TABLE segsense.consent_notice_snapshot
    ADD CONSTRAINT consent_notice_snapshot_notice_revision_fk
        FOREIGN KEY (notice_id, opportunity_revision_id)
        REFERENCES segsense.consent_notice (id, opportunity_revision_id)
        ON DELETE NO ACTION ON UPDATE NO ACTION;

ALTER TABLE segsense.consent_notice_snapshot
    ADD CONSTRAINT consent_notice_snapshot_id_revision_unique
        UNIQUE (id, opportunity_revision_id);

ALTER TABLE segsense.consent_notice_snapshot
    ADD CONSTRAINT consent_notice_snapshot_proof_unique
        UNIQUE (notice_id, version_number, content_hash);

ALTER TABLE segsense.consent_notice_field
    ADD CONSTRAINT consent_notice_field_snapshot_revision_fk
        FOREIGN KEY (snapshot_id, opportunity_revision_id)
        REFERENCES segsense.consent_notice_snapshot (id, opportunity_revision_id)
        ON DELETE NO ACTION ON UPDATE NO ACTION;

ALTER TABLE segsense.context_instance
    ADD CONSTRAINT context_instance_id_snapshot_unique
        UNIQUE (id, notice_snapshot_id);

ALTER TABLE segsense.context_instance
    ADD CONSTRAINT context_instance_id_revision_unique
        UNIQUE (id, opportunity_revision_id);

ALTER TABLE segsense.context_instance
    ADD CONSTRAINT context_instance_id_notice_proof_unique
        UNIQUE (id, notice_version, notice_content_hash);

ALTER TABLE segsense.context_instance
    DROP CONSTRAINT context_instance_idempotency_len_chk;

ALTER TABLE segsense.context_instance
    ALTER COLUMN idempotency_key_digest SET NOT NULL;

ALTER TABLE segsense.context_instance
    ADD CONSTRAINT context_instance_idempotency_len_chk
        CHECK (octet_length(idempotency_key_digest) = 32);

ALTER TABLE segsense.context_instance_value
    ADD COLUMN opportunity_revision_id UUID;

UPDATE segsense.context_instance_value v
SET opportunity_revision_id = i.opportunity_revision_id
FROM segsense.context_instance i
WHERE v.instance_id = i.id;

ALTER TABLE segsense.context_instance_value
    ALTER COLUMN opportunity_revision_id SET NOT NULL;

ALTER TABLE segsense.context_instance_value
    ADD CONSTRAINT context_instance_value_instance_snapshot_fk
        FOREIGN KEY (instance_id, snapshot_id)
        REFERENCES segsense.context_instance (id, notice_snapshot_id)
        ON DELETE NO ACTION ON UPDATE NO ACTION;

ALTER TABLE segsense.context_instance_value
    ADD CONSTRAINT context_instance_value_instance_revision_fk
        FOREIGN KEY (instance_id, opportunity_revision_id)
        REFERENCES segsense.context_instance (id, opportunity_revision_id)
        ON DELETE NO ACTION ON UPDATE NO ACTION;

ALTER TABLE segsense.consent_decision
    ADD CONSTRAINT consent_decision_instance_notice_fk
        FOREIGN KEY (instance_id, notice_version, notice_content_hash)
        REFERENCES segsense.context_instance (id, notice_version, notice_content_hash)
        ON DELETE NO ACTION ON UPDATE NO ACTION;

CREATE TABLE segsense.consent_notice_decision (
    id UUID PRIMARY KEY,
    notice_id UUID NOT NULL,
    notice_version INTEGER NOT NULL,
    content_hash CHAR(64) NOT NULL,
    decision_type VARCHAR(16) NOT NULL,
    justification VARCHAR(500) NOT NULL,
    actor VARCHAR(128) NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT consent_notice_decision_snapshot_fk
        FOREIGN KEY (notice_id, notice_version, content_hash)
        REFERENCES segsense.consent_notice_snapshot (notice_id, version_number, content_hash)
        ON DELETE NO ACTION ON UPDATE NO ACTION,
    CONSTRAINT consent_notice_decision_type_chk CHECK (decision_type IN ('APPROVED', 'RETIRED')),
    CONSTRAINT consent_notice_decision_justification_len_chk
        CHECK (char_length(justification) BETWEEN 10 AND 500),
    CONSTRAINT consent_notice_decision_hash_chk CHECK (content_hash ~ '^[a-f0-9]{64}$')
);

CREATE UNIQUE INDEX consent_notice_decision_one_approved_idx
    ON segsense.consent_notice_decision (notice_id)
    WHERE decision_type = 'APPROVED';

CREATE FUNCTION segsense.reject_consent_snapshot_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  RAISE EXCEPTION 'consent_notice_snapshot is append-only';
END;
$$;

CREATE TRIGGER consent_notice_snapshot_no_update
    BEFORE UPDATE ON segsense.consent_notice_snapshot
    FOR EACH ROW
    EXECUTE FUNCTION segsense.reject_consent_snapshot_mutation();

CREATE TRIGGER consent_notice_snapshot_no_delete
    BEFORE DELETE ON segsense.consent_notice_snapshot
    FOR EACH ROW
    EXECUTE FUNCTION segsense.reject_consent_snapshot_mutation();

CREATE FUNCTION segsense.reject_consent_notice_field_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  RAISE EXCEPTION 'consent_notice_field is append-only';
END;
$$;

CREATE TRIGGER consent_notice_field_no_update
    BEFORE UPDATE ON segsense.consent_notice_field
    FOR EACH ROW
    EXECUTE FUNCTION segsense.reject_consent_notice_field_mutation();

CREATE TRIGGER consent_notice_field_no_delete
    BEFORE DELETE ON segsense.consent_notice_field
    FOR EACH ROW
    EXECUTE FUNCTION segsense.reject_consent_notice_field_mutation();

CREATE FUNCTION segsense.reject_consent_notice_decision_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  RAISE EXCEPTION 'consent_notice_decision is append-only';
END;
$$;

CREATE TRIGGER consent_notice_decision_no_update
    BEFORE UPDATE ON segsense.consent_notice_decision
    FOR EACH ROW
    EXECUTE FUNCTION segsense.reject_consent_notice_decision_mutation();

CREATE TRIGGER consent_notice_decision_no_delete
    BEFORE DELETE ON segsense.consent_notice_decision
    FOR EACH ROW
    EXECUTE FUNCTION segsense.reject_consent_notice_decision_mutation();

CREATE FUNCTION segsense.reject_context_instance_identity_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  IF NEW.link_id IS DISTINCT FROM OLD.link_id
     OR NEW.opportunity_revision_id IS DISTINCT FROM OLD.opportunity_revision_id
     OR NEW.notice_id IS DISTINCT FROM OLD.notice_id
     OR NEW.notice_version IS DISTINCT FROM OLD.notice_version
     OR NEW.notice_snapshot_id IS DISTINCT FROM OLD.notice_snapshot_id
     OR NEW.notice_content_hash IS DISTINCT FROM OLD.notice_content_hash
     OR NEW.credential_digest IS DISTINCT FROM OLD.credential_digest
     OR NEW.idempotency_key_digest IS DISTINCT FROM OLD.idempotency_key_digest THEN
    RAISE EXCEPTION 'context_instance identity is immutable';
  END IF;
  RETURN NEW;
END;
$$;

CREATE TRIGGER context_instance_identity_no_update
    BEFORE UPDATE ON segsense.context_instance
    FOR EACH ROW
    EXECUTE FUNCTION segsense.reject_context_instance_identity_mutation();
