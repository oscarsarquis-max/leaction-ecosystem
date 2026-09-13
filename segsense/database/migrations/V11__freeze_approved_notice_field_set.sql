-- Freeze the field set of an approved/retired notice snapshot.
-- V1–V10 unchanged. No CASCADE. No data repair.
-- Conceptual rollback: drop V11 triggers/functions.

DO $guard$
DECLARE
  personal_fields bigint;
BEGIN
  SELECT COUNT(*) INTO personal_fields
  FROM segsense.contextual_opportunity_revision_field
  WHERE classification IS DISTINCT FROM 'NON_PERSONAL';

  IF personal_fields > 0 THEN
    RAISE EXCEPTION
      'V11 aborted without mutation: personal_fields=%',
      personal_fields;
  END IF;
END $guard$;

CREATE FUNCTION segsense.reject_consent_notice_field_insert()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
  notice_status varchar(16);
  snapshot_age integer;
BEGIN
  SELECT n.status, age(s.xmin)
    INTO notice_status, snapshot_age
  FROM segsense.consent_notice_snapshot s
  JOIN segsense.consent_notice n ON n.id = s.notice_id
  WHERE s.id = NEW.snapshot_id;

  IF notice_status IS NULL THEN
    RAISE EXCEPTION 'consent_notice_field requires an existing snapshot';
  END IF;
  IF notice_status IN ('APPROVED', 'RETIRED') THEN
    RAISE EXCEPTION 'cannot add fields to an approved or retired notice snapshot';
  END IF;
  IF snapshot_age IS DISTINCT FROM 0 THEN
    RAISE EXCEPTION 'cannot add fields to a committed notice snapshot';
  END IF;
  RETURN NEW;
END;
$$;

CREATE TRIGGER consent_notice_field_no_insert_after_commit
    BEFORE INSERT ON segsense.consent_notice_field
    FOR EACH ROW
    EXECUTE FUNCTION segsense.reject_consent_notice_field_insert();

CREATE FUNCTION segsense.reject_consent_notice_snapshot_insert()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
  notice_status varchar(16);
BEGIN
  SELECT status INTO notice_status
  FROM segsense.consent_notice
  WHERE id = NEW.notice_id;

  IF notice_status IS NULL THEN
    RAISE EXCEPTION 'consent_notice_snapshot requires an existing notice';
  END IF;
  IF notice_status IN ('APPROVED', 'RETIRED') THEN
    RAISE EXCEPTION 'cannot add snapshots to an approved or retired notice';
  END IF;
  RETURN NEW;
END;
$$;

CREATE TRIGGER consent_notice_snapshot_no_insert_when_effective
    BEFORE INSERT ON segsense.consent_notice_snapshot
    FOR EACH ROW
    EXECUTE FUNCTION segsense.reject_consent_notice_snapshot_insert();

CREATE FUNCTION segsense.reject_effective_notice_identity_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  IF OLD.status IN ('APPROVED', 'RETIRED') THEN
    IF NEW.current_version IS DISTINCT FROM OLD.current_version
       OR NEW.approved_version IS DISTINCT FROM OLD.approved_version
       OR NEW.opportunity_revision_id IS DISTINCT FROM OLD.opportunity_revision_id
       OR NEW.opportunity_id IS DISTINCT FROM OLD.opportunity_id THEN
      RAISE EXCEPTION 'approved notice identity is immutable';
    END IF;
    IF OLD.status = 'RETIRED' AND NEW.status IS DISTINCT FROM 'RETIRED' THEN
      RAISE EXCEPTION 'retired notice status is immutable';
    END IF;
    IF OLD.status = 'APPROVED' AND NEW.status NOT IN ('APPROVED', 'RETIRED') THEN
      RAISE EXCEPTION 'approved notice status is immutable';
    END IF;
  END IF;
  RETURN NEW;
END;
$$;

CREATE TRIGGER consent_notice_identity_no_update
    BEFORE UPDATE ON segsense.consent_notice
    FOR EACH ROW
    EXECUTE FUNCTION segsense.reject_effective_notice_identity_mutation();
