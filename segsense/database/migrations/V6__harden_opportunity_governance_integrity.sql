-- Harden opportunity governance integrity without rewriting V1–V5.
-- No data repair. No CASCADE. No business triggers.
-- If existing rows violate the intended identity, abort before any DDL change.

DO $guard$
DECLARE
  cross_open bigint;
  missing_open bigint;
  open_revision_mismatch bigint;
  decision_mismatch bigint;
  missing_decision_submission bigint;
  duplicate_decision bigint;
  missing_submission_revision bigint;
  missing_decision_revision bigint;
BEGIN
  SELECT COUNT(*) INTO cross_open
  FROM segsense.contextual_opportunity o
  JOIN segsense.opportunity_submission s ON s.id = o.open_submission_id
  WHERE s.opportunity_id <> o.id;

  SELECT COUNT(*) INTO missing_open
  FROM segsense.contextual_opportunity o
  WHERE o.open_submission_id IS NOT NULL
    AND NOT EXISTS (
      SELECT 1
      FROM segsense.opportunity_submission s
      WHERE s.id = o.open_submission_id
    );

  SELECT COUNT(*) INTO open_revision_mismatch
  FROM segsense.contextual_opportunity o
  JOIN segsense.opportunity_submission s ON s.id = o.open_submission_id
  WHERE o.submitted_revision IS DISTINCT FROM s.revision_number
     OR s.opportunity_id <> o.id;

  SELECT COUNT(*) INTO decision_mismatch
  FROM segsense.opportunity_decision d
  JOIN segsense.opportunity_submission s ON s.id = d.submission_id
  WHERE d.opportunity_id <> s.opportunity_id
     OR d.revision_number <> s.revision_number;

  SELECT COUNT(*) INTO missing_decision_submission
  FROM segsense.opportunity_decision d
  WHERE NOT EXISTS (
    SELECT 1
    FROM segsense.opportunity_submission s
    WHERE s.id = d.submission_id
  );

  SELECT COUNT(*) INTO duplicate_decision
  FROM (
    SELECT submission_id
    FROM segsense.opportunity_decision
    GROUP BY submission_id
    HAVING COUNT(*) > 1
  ) duplicated;

  SELECT COUNT(*) INTO missing_submission_revision
  FROM segsense.opportunity_submission s
  WHERE NOT EXISTS (
    SELECT 1
    FROM segsense.contextual_opportunity_revision r
    WHERE r.opportunity_id = s.opportunity_id
      AND r.revision_number = s.revision_number
  );

  SELECT COUNT(*) INTO missing_decision_revision
  FROM segsense.opportunity_decision d
  WHERE NOT EXISTS (
    SELECT 1
    FROM segsense.contextual_opportunity_revision r
    WHERE r.opportunity_id = d.opportunity_id
      AND r.revision_number = d.revision_number
  );

  IF cross_open > 0 THEN
    RAISE EXCEPTION
      'V6 abort: open_submission_id references a submission of another opportunity (% rows)',
      cross_open;
  END IF;
  IF missing_open > 0 THEN
    RAISE EXCEPTION
      'V6 abort: open_submission_id references a missing submission (% rows)',
      missing_open;
  END IF;
  IF open_revision_mismatch > 0 THEN
    RAISE EXCEPTION
      'V6 abort: open submission identity does not match opportunity/revision (% rows)',
      open_revision_mismatch;
  END IF;
  IF decision_mismatch > 0 THEN
    RAISE EXCEPTION
      'V6 abort: decision identity does not match its submission (% rows)',
      decision_mismatch;
  END IF;
  IF missing_decision_submission > 0 THEN
    RAISE EXCEPTION
      'V6 abort: decision references a missing submission (% rows)',
      missing_decision_submission;
  END IF;
  IF duplicate_decision > 0 THEN
    RAISE EXCEPTION
      'V6 abort: more than one decision exists for the same submission (% groups)',
      duplicate_decision;
  END IF;
  IF missing_submission_revision > 0 THEN
    RAISE EXCEPTION
      'V6 abort: submission references a missing revision (% rows)',
      missing_submission_revision;
  END IF;
  IF missing_decision_revision > 0 THEN
    RAISE EXCEPTION
      'V6 abort: decision references a missing revision (% rows)',
      missing_decision_revision;
  END IF;
END
$guard$;

ALTER TABLE segsense.opportunity_submission
    ADD CONSTRAINT opportunity_submission_identity_unique
        UNIQUE (id, opportunity_id, revision_number);

ALTER TABLE segsense.contextual_opportunity
    DROP CONSTRAINT opportunity_open_submission_fk;

ALTER TABLE segsense.contextual_opportunity
    ADD CONSTRAINT opportunity_open_submission_identity_chk
        CHECK (open_submission_id IS NULL OR submitted_revision IS NOT NULL);

ALTER TABLE segsense.contextual_opportunity
    ADD CONSTRAINT opportunity_open_submission_identity_fk
        FOREIGN KEY (open_submission_id, id, submitted_revision)
        REFERENCES segsense.opportunity_submission (id, opportunity_id, revision_number)
        ON DELETE NO ACTION
        ON UPDATE NO ACTION;

ALTER TABLE segsense.opportunity_decision
    DROP CONSTRAINT opportunity_decision_submission_fk;

ALTER TABLE segsense.opportunity_decision
    DROP CONSTRAINT opportunity_decision_revision_fk;

ALTER TABLE segsense.opportunity_decision
    ADD CONSTRAINT opportunity_decision_submission_identity_fk
        FOREIGN KEY (submission_id, opportunity_id, revision_number)
        REFERENCES segsense.opportunity_submission (id, opportunity_id, revision_number)
        ON DELETE NO ACTION
        ON UPDATE NO ACTION;

DROP INDEX segsense.opportunity_open_submission_unique;

CREATE INDEX opportunity_open_submission_lookup_idx
    ON segsense.contextual_opportunity (open_submission_id)
    WHERE open_submission_id IS NOT NULL;

COMMENT ON COLUMN segsense.opportunity_submission.status IS
    'Deprecated historical marker (OPEN/DECIDED). Openness is derived from contextual_opportunity.open_submission_id and the absence of opportunity_decision. The application must not update this column.';

COMMENT ON CONSTRAINT opportunity_submission_identity_unique ON segsense.opportunity_submission IS
    'Candidate key for composite identity FKs (id, opportunity_id, revision_number).';

COMMENT ON CONSTRAINT opportunity_open_submission_identity_fk ON segsense.contextual_opportunity IS
    'Open pointer must reference a submission of the same opportunity and submitted revision.';

COMMENT ON CONSTRAINT opportunity_decision_submission_identity_fk ON segsense.opportunity_decision IS
    'A decision must name the same opportunity and revision as its submission row.';
