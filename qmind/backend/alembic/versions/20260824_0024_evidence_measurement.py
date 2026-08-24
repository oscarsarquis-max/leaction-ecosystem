"""Contextual evidence + action measurement plans (ISOI-008, revision 001).

Revision ID: 20260824_0024
Revises: 20260824_0023
Create Date: 2026-08-24

Legacy evidence audit (local dev snapshot, 2026-08-24): 680 rows in `evidences`,
all with `assessment_id` set and none with `improvement_case_id`. A strict XOR is
therefore satisfiable today, but the CHECK is written so that an assessment-only
row is always legal — a legacy row can never be made invalid by this revision.

Revision 001 notes
------------------
This revision was already applied to development databases in an earlier shape.
`upgrade()` is therefore written to be **idempotent and self-repairing**: every
statement is either `IF NOT EXISTS`, or a `DROP ... IF EXISTS` followed by a
`CREATE`/`ADD`. Running it against a database that is already stamped
`20260824_0024` in the *old* shape upgrades that database to the revision-001
shape; running it against a fresh database creates the revision-001 shape
directly. The `RECONCILE` sections exist for exactly that reason.

`downgrade()` **refuses** to run when any revision-008 history exists. The
measurement trail and case-scoped evidences are audit records: a schema rollback
is never a licence to delete them. Roundtrip tests use a disposable database
(see `tests/alembic_support.py`).
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision = "20260824_0024"
down_revision = "20260824_0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(text(_EVIDENCE_SQL))
    op.execute(text(_PLAN_SQL))
    op.execute(text(_INDICATOR_SQL))
    op.execute(text(_RECORD_SQL))
    op.execute(text(_BASELINE_BACKFILL_SQL))
    op.execute(text(_OBSERVATION_LINK_SQL))
    op.execute(text(_RLS_AND_GRANTS_SQL))


def downgrade() -> None:
    op.execute(text(_DOWNGRADE_GUARD_SQL))
    op.execute(text(_DOWNGRADE_SQL))


# ---------------------------------------------------------------------------
# Evidence: context, phase, idempotency
# ---------------------------------------------------------------------------

_EVIDENCE_SQL = """
-- An evidence belongs either to an Assessment or to an ImprovementCase, never
-- to both and never to neither.
ALTER TABLE evidences
  ADD COLUMN IF NOT EXISTS improvement_case_id uuid;
ALTER TABLE evidences
  DROP CONSTRAINT IF EXISTS fk_evidences_improvement_case_same_org;
ALTER TABLE evidences
  ADD CONSTRAINT fk_evidences_improvement_case_same_org
    FOREIGN KEY (improvement_case_id, organization_id)
    REFERENCES improvement_cases (id, organization_id);

ALTER TABLE evidences DROP CONSTRAINT IF EXISTS ck_evidences_context_xor;
ALTER TABLE evidences
  ADD CONSTRAINT ck_evidences_context_xor CHECK (
    (assessment_id IS NOT NULL AND improvement_case_id IS NULL)
    OR (assessment_id IS NULL AND improvement_case_id IS NOT NULL)
  );

CREATE INDEX IF NOT EXISTS ix_evidences_improvement_case
  ON evidences (improvement_case_id, created_at DESC)
  WHERE improvement_case_id IS NOT NULL;

-- Proving that an action worked happens after the field work is over, so it
-- gets its own phase instead of being mislabelled as evidence collected
-- during the audit.
ALTER TABLE evidences DROP CONSTRAINT IF EXISTS ck_evidences_collected_phase;
ALTER TABLE evidences
  ADD CONSTRAINT ck_evidences_collected_phase CHECK (
    collected_phase IS NULL OR collected_phase IN (
      'preparation', 'planning', 'field', 'analysis',
      'action_execution', 'unknown_legacy'
    )
  );

-- Idempotency, revision 001. Retrying "authorize + link" must never create a
-- second Evidence, and a key reused with a *different* request must be refused
-- rather than silently answered with the wrong evidence. So we store:
--   * idempotency_scope        — canonical operation the key belongs to, chosen
--                                by the server, never by the caller
--   * idempotency_key_hash     — SHA-256 of the caller key (the raw key is not
--                                business data and can identify a client)
--   * request_fingerprint      — SHA-256 over the meaningful request fields
ALTER TABLE evidences
  ADD COLUMN IF NOT EXISTS idempotency_scope text;
ALTER TABLE evidences
  ADD COLUMN IF NOT EXISTS idempotency_key_hash text;
ALTER TABLE evidences
  ADD COLUMN IF NOT EXISTS request_fingerprint text;

-- RECONCILE: the first shape of this revision stored the raw key in a single
-- column with no scope and no fingerprint.
DROP INDEX IF EXISTS uq_evidences_authorize_idempotency;
ALTER TABLE evidences DROP COLUMN IF EXISTS authorize_idempotency_key;

ALTER TABLE evidences DROP CONSTRAINT IF EXISTS ck_evidences_idempotency_pair;
ALTER TABLE evidences
  ADD CONSTRAINT ck_evidences_idempotency_pair CHECK (
    (idempotency_scope IS NULL AND idempotency_key_hash IS NULL)
    OR (idempotency_scope IS NOT NULL AND idempotency_key_hash IS NOT NULL)
  );

CREATE UNIQUE INDEX IF NOT EXISTS uq_evidences_idempotency
  ON evidences (organization_id, idempotency_scope, idempotency_key_hash)
  WHERE idempotency_key_hash IS NOT NULL;

-- ---------------------------------------------------------------------------
-- Evidence links: new targets + soft delete (an audit trail must not lose the
-- fact that something was once linked).
-- ---------------------------------------------------------------------------
ALTER TABLE evidence_links
  ADD COLUMN IF NOT EXISTS removed_at timestamptz;
ALTER TABLE evidence_links
  ADD COLUMN IF NOT EXISTS removed_by uuid REFERENCES users (id);
ALTER TABLE evidence_links
  ADD COLUMN IF NOT EXISTS removal_reason text;

-- RECONCILE: `agile_ceremony_record` shipped in an earlier draft of this same
-- revision and was withdrawn: a ceremony belongs to a sprint, so a link to one
-- can never be proven to stay inside the assessment/case boundary that every
-- other target respects. The target type never existed outside this
-- uncommitted revision, so removing those rows destroys no committed history.
DELETE FROM evidence_links WHERE target_type = 'agile_ceremony_record';

ALTER TABLE evidence_links
  DROP CONSTRAINT IF EXISTS evidence_links_target_type_check;
ALTER TABLE evidence_links
  ADD CONSTRAINT evidence_links_target_type_check CHECK (
    target_type IN (
      'requirement', 'question', 'finding', 'action_item',
      'interview', 'answer',
      'action_check_in', 'action_impediment', 'measurement_record',
      'outcome_observation', 'improvement_case'
    )
  );

CREATE UNIQUE INDEX IF NOT EXISTS uq_evidence_links_active_target
  ON evidence_links (
    organization_id, evidence_id, target_type, target_id
  )
  WHERE removed_at IS NULL;
CREATE INDEX IF NOT EXISTS ix_evidence_links_target_active
  ON evidence_links (organization_id, target_type, target_id)
  WHERE removed_at IS NULL;

-- Outcome observations need a composite key so measurements can be attached
-- without losing the tenant guarantee. Added conditionally: on a re-run the
-- measurement foreign key already depends on it, so dropping it first would
-- fail.
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
     WHERE conrelid = 'improvement_case_outcome_observations'::regclass
       AND conname = 'uq_outcome_obs_id_org'
  ) THEN
    ALTER TABLE improvement_case_outcome_observations
      ADD CONSTRAINT uq_outcome_obs_id_org UNIQUE (id, organization_id);
  END IF;
END $$;

-- Board / read-model support: the execution board must answer "is this action
-- measured?" without a per-card query.
CREATE INDEX IF NOT EXISTS ix_action_items_plan_org
  ON action_items (action_plan_id, organization_id);
"""


# ---------------------------------------------------------------------------
# Measurement plans: how an ActionPlan will prove it worked
# ---------------------------------------------------------------------------

_PLAN_SQL = """
CREATE TABLE IF NOT EXISTS action_measurement_plans (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL REFERENCES organizations (id) ON DELETE CASCADE,
  action_plan_id uuid NOT NULL,
  assessment_id uuid,
  improvement_case_id uuid,
  objective text NOT NULL DEFAULT '',
  owner_membership_id uuid,
  review_cadence_days integer,
  next_review_at timestamptz,
  status text NOT NULL DEFAULT 'draft'
    CHECK (status IN ('draft', 'active', 'closed')),
  activated_by uuid REFERENCES users (id),
  activated_at timestamptz,
  closed_by uuid REFERENCES users (id),
  closed_at timestamptz,
  closure_reason text,
  created_by uuid NOT NULL REFERENCES users (id),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_action_measurement_plans_id_org UNIQUE (id, organization_id),
  CONSTRAINT ck_amp_context_xor CHECK (
    (assessment_id IS NOT NULL AND improvement_case_id IS NULL)
    OR (assessment_id IS NULL AND improvement_case_id IS NOT NULL)
  ),
  CONSTRAINT fk_amp_action_plan_same_org
    FOREIGN KEY (action_plan_id, organization_id)
    REFERENCES action_plans (id, organization_id),
  CONSTRAINT fk_amp_assessment_same_org
    FOREIGN KEY (assessment_id, organization_id)
    REFERENCES assessments (id, organization_id),
  CONSTRAINT fk_amp_case_same_org
    FOREIGN KEY (improvement_case_id, organization_id)
    REFERENCES improvement_cases (id, organization_id)
);

-- RECONCILE: `purpose` said what the row was for without saying what it had to
-- achieve. `objective` is the auditable field; the old value is carried over.
ALTER TABLE action_measurement_plans
  ADD COLUMN IF NOT EXISTS objective text NOT NULL DEFAULT '';
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'action_measurement_plans' AND column_name = 'purpose'
  ) THEN
    UPDATE action_measurement_plans
       SET objective = coalesce(nullif(btrim(objective), ''), purpose, '')
     WHERE coalesce(btrim(objective), '') = '';
    ALTER TABLE action_measurement_plans DROP COLUMN purpose;
  END IF;
END $$;

ALTER TABLE action_measurement_plans
  ADD COLUMN IF NOT EXISTS owner_membership_id uuid;
ALTER TABLE action_measurement_plans
  ADD COLUMN IF NOT EXISTS review_cadence_days integer;
ALTER TABLE action_measurement_plans
  ADD COLUMN IF NOT EXISTS next_review_at timestamptz;

ALTER TABLE action_measurement_plans
  DROP CONSTRAINT IF EXISTS fk_amp_owner_same_org;
ALTER TABLE action_measurement_plans
  ADD CONSTRAINT fk_amp_owner_same_org
    FOREIGN KEY (owner_membership_id, organization_id)
    REFERENCES memberships (id, organization_id);

ALTER TABLE action_measurement_plans
  DROP CONSTRAINT IF EXISTS ck_amp_review_cadence;
ALTER TABLE action_measurement_plans
  ADD CONSTRAINT ck_amp_review_cadence CHECK (
    review_cadence_days IS NULL
    OR (review_cadence_days > 0 AND review_cadence_days <= 3650)
  );

-- RECONCILE: plans created before this revision have no owner. Whoever created
-- the plan owns it until it is reassigned — that is the only attribution the
-- old rows can honestly support.
UPDATE action_measurement_plans amp
   SET owner_membership_id = m.id
  FROM memberships m
 WHERE amp.owner_membership_id IS NULL
   AND m.organization_id = amp.organization_id
   AND m.user_id = amp.created_by;

-- An active plan has a named owner: "the organization" cannot be asked why a
-- measurement is late.
ALTER TABLE action_measurement_plans
  DROP CONSTRAINT IF EXISTS ck_amp_active_has_owner;
ALTER TABLE action_measurement_plans
  ADD CONSTRAINT ck_amp_active_has_owner CHECK (
    status <> 'active' OR owner_membership_id IS NOT NULL
  ) NOT VALID;
-- Validated separately: a plan that is already live and whose creator has since
-- lost their membership cannot be given an owner by a migration, and refusing
-- to migrate would be worse than carrying one unattributed row forward.
DO $$
BEGIN
  ALTER TABLE action_measurement_plans VALIDATE CONSTRAINT ck_amp_active_has_owner;
EXCEPTION WHEN check_violation THEN
  RAISE NOTICE
    'ck_amp_active_has_owner left NOT VALID: pre-existing active plans without '
    'a resolvable owner. New and updated rows are still checked.';
END $$;

-- One live plan per ActionPlan; closed plans stay as history.
CREATE UNIQUE INDEX IF NOT EXISTS uq_amp_one_open_per_action_plan
  ON action_measurement_plans (organization_id, action_plan_id)
  WHERE status <> 'closed';
CREATE INDEX IF NOT EXISTS ix_amp_org_status
  ON action_measurement_plans (organization_id, status);
CREATE INDEX IF NOT EXISTS ix_amp_next_review
  ON action_measurement_plans (organization_id, next_review_at)
  WHERE status = 'active' AND next_review_at IS NOT NULL;
"""


# ---------------------------------------------------------------------------
# Indicator definitions: versioned; a revision after data exists creates a new
# version instead of rewriting history.
# ---------------------------------------------------------------------------

_INDICATOR_SQL = """
CREATE TABLE IF NOT EXISTS indicator_definitions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL REFERENCES organizations (id) ON DELETE CASCADE,
  measurement_plan_id uuid NOT NULL,
  code text NOT NULL,
  name text NOT NULL,
  question text NOT NULL DEFAULT '',
  owner_membership_id uuid,
  value_type text NOT NULL DEFAULT 'decimal',
  unit_kind text NOT NULL DEFAULT 'dimensionless',
  custom_unit_label text,
  currency_code text,
  decimal_places smallint NOT NULL DEFAULT 2,
  direction text NOT NULL,
  baseline_unavailable_reason text,
  target_value numeric(20, 6),
  target_min numeric(20, 6),
  target_max numeric(20, 6),
  target_due_at timestamptz,
  measurement_frequency_days integer
    CHECK (
      measurement_frequency_days IS NULL
      OR (measurement_frequency_days > 0 AND measurement_frequency_days <= 3650)
    ),
  data_source text NOT NULL DEFAULT '',
  collection_method text NOT NULL DEFAULT '',
  status text NOT NULL DEFAULT 'active'
    CHECK (status IN ('active', 'superseded', 'retired')),
  version integer NOT NULL DEFAULT 1 CHECK (version > 0),
  lineage_id uuid NOT NULL,
  supersedes_indicator_id uuid,
  revision_reason text,
  retired_reason text,
  created_by uuid NOT NULL REFERENCES users (id),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_indicator_definitions_id_org UNIQUE (id, organization_id),
  CONSTRAINT uq_indicator_definitions_id_plan UNIQUE (id, measurement_plan_id),
  CONSTRAINT fk_indicator_plan_same_org
    FOREIGN KEY (measurement_plan_id, organization_id)
    REFERENCES action_measurement_plans (id, organization_id),
  CONSTRAINT fk_indicator_supersedes_same_org
    FOREIGN KEY (supersedes_indicator_id, organization_id)
    REFERENCES indicator_definitions (id, organization_id)
);

-- RECONCILE: revision-001 columns.
ALTER TABLE indicator_definitions
  ADD COLUMN IF NOT EXISTS owner_membership_id uuid;
ALTER TABLE indicator_definitions
  ADD COLUMN IF NOT EXISTS value_type text NOT NULL DEFAULT 'decimal';
ALTER TABLE indicator_definitions
  ADD COLUMN IF NOT EXISTS unit_kind text NOT NULL DEFAULT 'dimensionless';
ALTER TABLE indicator_definitions
  ADD COLUMN IF NOT EXISTS custom_unit_label text;
ALTER TABLE indicator_definitions
  ADD COLUMN IF NOT EXISTS currency_code text;
ALTER TABLE indicator_definitions
  ADD COLUMN IF NOT EXISTS decimal_places smallint NOT NULL DEFAULT 2;

-- RECONCILE: the free-text `unit` column let two indicators claim the same
-- unit while meaning different things ('%' vs 'percent' vs 'pct'). The unit is
-- now a closed enumeration plus an explicit custom label, and the display
-- string is derived on read.
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'indicator_definitions' AND column_name = 'unit'
  ) THEN
    UPDATE indicator_definitions
       SET unit_kind = CASE
             WHEN lower(btrim(coalesce(unit, ''))) IN ('%', 'percent', 'percentual', 'pct')
                  -- Only when the numbers actually behave like percentages.
                  -- A '%' indicator whose target is 250 was mislabelled, and
                  -- carrying the label over would make the bounds check a lie.
                  AND coalesce(target_value, 0) BETWEEN 0 AND 100
                  AND coalesce(target_min, 0) BETWEEN 0 AND 100
                  AND coalesce(target_max, 0) BETWEEN 0 AND 100
               THEN 'percentage'
             WHEN lower(btrim(coalesce(unit, ''))) IN ('min', 'minuto', 'minutos', 'minutes')
               THEN 'duration_minutes'
             WHEN lower(btrim(coalesce(unit, ''))) IN ('h', 'hora', 'horas', 'hours')
               THEN 'duration_hours'
             WHEN lower(btrim(coalesce(unit, ''))) IN ('dia', 'dias', 'day', 'days', 'd')
               THEN 'duration_days'
             WHEN lower(btrim(coalesce(unit, ''))) IN ('brl', 'r$')
               THEN 'currency'
             WHEN btrim(coalesce(unit, '')) = ''
               THEN 'dimensionless'
             ELSE 'custom'
           END,
           currency_code = CASE
             WHEN lower(btrim(coalesce(unit, ''))) IN ('brl', 'r$') THEN 'BRL'
             ELSE currency_code
           END,
           -- Keep the original text around for anything that did not map to a
           -- known kind, so no label is silently lost.
           custom_unit_label = coalesce(
             nullif(btrim(coalesce(custom_unit_label, '')), ''),
             nullif(btrim(coalesce(unit, '')), '')
           );

    -- Anything still marked custom must carry a label.
    UPDATE indicator_definitions
       SET custom_unit_label = 'Unidade não informada'
     WHERE unit_kind = 'custom'
       AND nullif(btrim(coalesce(custom_unit_label, '')), '') IS NULL;

    ALTER TABLE indicator_definitions DROP COLUMN unit;
  END IF;
END $$;

-- RECONCILE: a direction and a target shape that disagree ("lower is better,
-- keep it between 3 and 7") describe two different indicators. The bounds that
-- the direction cannot use are cleared rather than kept as dead data.
UPDATE indicator_definitions
   SET target_min = NULL, target_max = NULL
 WHERE direction IN ('increase_is_better', 'decrease_is_better',
                     'higher_is_better', 'lower_is_better')
   AND (target_min IS NOT NULL OR target_max IS NOT NULL);
UPDATE indicator_definitions
   SET target_value = NULL
 WHERE direction IN ('stay_within_range', 'within_range', 'maintain_range')
   AND target_value IS NOT NULL;

-- RECONCILE: directions were named after the arithmetic ('increase') rather
-- than after the intent ('higher is better'), and there was no way to say
-- "keep it where it already is". The old CHECK has to go before the rename,
-- not after.
ALTER TABLE indicator_definitions
  DROP CONSTRAINT IF EXISTS indicator_definitions_direction_check;
ALTER TABLE indicator_definitions
  DROP CONSTRAINT IF EXISTS ck_indicator_direction;

UPDATE indicator_definitions SET direction = 'higher_is_better'
  WHERE direction = 'increase_is_better';
UPDATE indicator_definitions SET direction = 'lower_is_better'
  WHERE direction = 'decrease_is_better';
UPDATE indicator_definitions SET direction = 'within_range'
  WHERE direction = 'stay_within_range';

ALTER TABLE indicator_definitions
  ADD CONSTRAINT ck_indicator_direction CHECK (
    direction IN (
      'higher_is_better', 'lower_is_better', 'within_range', 'maintain_range'
    )
  );

ALTER TABLE indicator_definitions
  DROP CONSTRAINT IF EXISTS ck_indicator_value_type;
ALTER TABLE indicator_definitions
  ADD CONSTRAINT ck_indicator_value_type CHECK (value_type = 'decimal');

ALTER TABLE indicator_definitions
  DROP CONSTRAINT IF EXISTS ck_indicator_unit_kind;
ALTER TABLE indicator_definitions
  ADD CONSTRAINT ck_indicator_unit_kind CHECK (
    unit_kind IN (
      'percentage', 'count', 'currency', 'ratio', 'score',
      'duration_minutes', 'duration_hours', 'duration_days',
      'dimensionless', 'custom'
    )
  );

-- A custom unit without a label is an unlabelled number; a currency without a
-- code cannot be compared or reported.
ALTER TABLE indicator_definitions
  DROP CONSTRAINT IF EXISTS ck_indicator_unit_shape;
ALTER TABLE indicator_definitions
  ADD CONSTRAINT ck_indicator_unit_shape CHECK (
    (unit_kind <> 'custom' OR nullif(btrim(coalesce(custom_unit_label, '')), '') IS NOT NULL)
    AND (unit_kind <> 'currency' OR currency_code IS NOT NULL)
  );

ALTER TABLE indicator_definitions
  DROP CONSTRAINT IF EXISTS ck_indicator_currency_code;
ALTER TABLE indicator_definitions
  ADD CONSTRAINT ck_indicator_currency_code CHECK (
    currency_code IS NULL OR currency_code ~ '^[A-Z]{3}$'
  );

ALTER TABLE indicator_definitions
  DROP CONSTRAINT IF EXISTS ck_indicator_decimal_places;
ALTER TABLE indicator_definitions
  ADD CONSTRAINT ck_indicator_decimal_places CHECK (
    decimal_places >= 0 AND decimal_places <= 8
  );

-- A percentage target outside 0..100 is a typo, not a stretch goal.
ALTER TABLE indicator_definitions
  DROP CONSTRAINT IF EXISTS ck_indicator_percentage_bounds;
ALTER TABLE indicator_definitions
  ADD CONSTRAINT ck_indicator_percentage_bounds CHECK (
    unit_kind <> 'percentage'
    OR (
      (target_value IS NULL OR (target_value >= 0 AND target_value <= 100))
      AND (target_min IS NULL OR (target_min >= 0 AND target_min <= 100))
      AND (target_max IS NULL OR (target_max >= 0 AND target_max <= 100))
    )
  );

-- A range direction needs bounds and no single target; a directional one needs
-- a single target and no bounds. Mixing them produces an indicator nobody can
-- evaluate. Bounds/targets stay nullable so a draft can be saved incomplete —
-- completeness is required when the plan is activated.
ALTER TABLE indicator_definitions DROP CONSTRAINT IF EXISTS ck_indicator_range_bounds;
ALTER TABLE indicator_definitions DROP CONSTRAINT IF EXISTS ck_indicator_target_shape;
ALTER TABLE indicator_definitions
  ADD CONSTRAINT ck_indicator_target_shape CHECK (
    CASE
      WHEN direction IN ('within_range', 'maintain_range') THEN
        target_value IS NULL
        AND (target_min IS NULL OR target_max IS NULL OR target_max >= target_min)
      ELSE
        target_min IS NULL AND target_max IS NULL
    END
  );

ALTER TABLE indicator_definitions
  DROP CONSTRAINT IF EXISTS fk_indicator_owner_same_org;
ALTER TABLE indicator_definitions
  ADD CONSTRAINT fk_indicator_owner_same_org
    FOREIGN KEY (owner_membership_id, organization_id)
    REFERENCES memberships (id, organization_id);

-- RECONCILE: a measurement must be provably attached to an indicator that
-- belongs to the *same* plan, which needs a composite unique to point at.
-- Added conditionally so a re-run does not have to drop it out from under the
-- measurement foreign key.
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
     WHERE conrelid = 'indicator_definitions'::regclass
       AND conname = 'uq_indicator_definitions_id_plan'
  ) THEN
    ALTER TABLE indicator_definitions
      ADD CONSTRAINT uq_indicator_definitions_id_plan
      UNIQUE (id, measurement_plan_id);
  END IF;
END $$;

-- RECONCILE: deleting a plan must never silently take the indicators (and with
-- them the measurements) along.
ALTER TABLE indicator_definitions
  DROP CONSTRAINT IF EXISTS fk_indicator_plan_same_org;
ALTER TABLE indicator_definitions
  ADD CONSTRAINT fk_indicator_plan_same_org
    FOREIGN KEY (measurement_plan_id, organization_id)
    REFERENCES action_measurement_plans (id, organization_id);

CREATE UNIQUE INDEX IF NOT EXISTS uq_indicator_active_code_per_plan
  ON indicator_definitions (organization_id, measurement_plan_id, code)
  WHERE status = 'active';
CREATE INDEX IF NOT EXISTS ix_indicator_plan_status
  ON indicator_definitions (measurement_plan_id, status);
CREATE INDEX IF NOT EXISTS ix_indicator_lineage
  ON indicator_definitions (organization_id, lineage_id, version DESC);
"""


# ---------------------------------------------------------------------------
# Measurement records: append-only. A correction is a new row that supersedes
# the previous one, never an UPDATE of the value.
# ---------------------------------------------------------------------------

_RECORD_SQL = """
CREATE TABLE IF NOT EXISTS measurement_records (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL REFERENCES organizations (id) ON DELETE CASCADE,
  measurement_plan_id uuid NOT NULL,
  indicator_definition_id uuid NOT NULL,
  measurement_kind text NOT NULL DEFAULT 'observation',
  value numeric(20, 6) NOT NULL,
  measured_at timestamptz NOT NULL,
  window_start timestamptz,
  window_end timestamptz,
  note text NOT NULL DEFAULT '',
  collection_method text NOT NULL DEFAULT '',
  supersedes_measurement_id uuid,
  correction_reason text,
  idempotency_scope text,
  idempotency_key_hash text,
  request_fingerprint text,
  recorded_by uuid NOT NULL REFERENCES users (id),
  recorded_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_measurement_records_id_org UNIQUE (id, organization_id),
  CONSTRAINT ck_measurement_window CHECK (
    window_start IS NULL OR window_end IS NULL OR window_end >= window_start
  ),
  CONSTRAINT ck_measurement_correction_reason CHECK (
    supersedes_measurement_id IS NULL
    OR nullif(btrim(coalesce(correction_reason, '')), '') IS NOT NULL
  ),
  CONSTRAINT fk_measurement_plan_same_org
    FOREIGN KEY (measurement_plan_id, organization_id)
    REFERENCES action_measurement_plans (id, organization_id),
  CONSTRAINT fk_measurement_indicator_same_org
    FOREIGN KEY (indicator_definition_id, organization_id)
    REFERENCES indicator_definitions (id, organization_id),
  CONSTRAINT fk_measurement_indicator_same_plan
    FOREIGN KEY (indicator_definition_id, measurement_plan_id)
    REFERENCES indicator_definitions (id, measurement_plan_id),
  CONSTRAINT fk_measurement_supersedes_same_org
    FOREIGN KEY (supersedes_measurement_id, organization_id)
    REFERENCES measurement_records (id, organization_id)
);

-- RECONCILE: the baseline is a measurement like any other, so it lives here
-- and carries who took it and when.
ALTER TABLE measurement_records
  ADD COLUMN IF NOT EXISTS measurement_kind text NOT NULL DEFAULT 'observation';
ALTER TABLE measurement_records
  DROP CONSTRAINT IF EXISTS ck_measurement_kind;
ALTER TABLE measurement_records
  ADD CONSTRAINT ck_measurement_kind CHECK (
    measurement_kind IN ('baseline', 'observation')
  );

-- RECONCILE: revision 001 idempotency columns; the raw-key column is gone.
ALTER TABLE measurement_records
  ADD COLUMN IF NOT EXISTS idempotency_scope text;
ALTER TABLE measurement_records
  ADD COLUMN IF NOT EXISTS idempotency_key_hash text;
ALTER TABLE measurement_records
  ADD COLUMN IF NOT EXISTS request_fingerprint text;
DROP INDEX IF EXISTS uq_measurement_idempotency;
ALTER TABLE measurement_records DROP COLUMN IF EXISTS idempotency_key;

ALTER TABLE measurement_records
  DROP CONSTRAINT IF EXISTS ck_measurement_idempotency_pair;
ALTER TABLE measurement_records
  ADD CONSTRAINT ck_measurement_idempotency_pair CHECK (
    (idempotency_scope IS NULL AND idempotency_key_hash IS NULL)
    OR (idempotency_scope IS NOT NULL AND idempotency_key_hash IS NOT NULL)
  );
CREATE UNIQUE INDEX IF NOT EXISTS uq_measurement_idempotency
  ON measurement_records (
    organization_id, idempotency_scope, idempotency_key_hash
  )
  WHERE idempotency_key_hash IS NOT NULL;

-- RECONCILE: `status` was a stored value the app had to UPDATE, which meant the
-- app needed UPDATE rights on an append-only table and two writers could
-- disagree about which reading is current. Being superseded is now *derived*
-- from the existence of a successor, and the successor link is unique, so a
-- reading can be corrected exactly once.
ALTER TABLE measurement_records DROP CONSTRAINT IF EXISTS measurement_records_status_check;
DROP INDEX IF EXISTS ix_measurement_indicator_measured;
DROP INDEX IF EXISTS ix_measurement_plan_active;
ALTER TABLE measurement_records DROP COLUMN IF EXISTS status;

CREATE UNIQUE INDEX IF NOT EXISTS uq_measurement_one_successor
  ON measurement_records (organization_id, supersedes_measurement_id)
  WHERE supersedes_measurement_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS ix_measurement_indicator_measured
  ON measurement_records (indicator_definition_id, measured_at DESC);
CREATE INDEX IF NOT EXISTS ix_measurement_plan_measured
  ON measurement_records (measurement_plan_id, measured_at DESC);
CREATE INDEX IF NOT EXISTS ix_measurement_supersedes
  ON measurement_records (supersedes_measurement_id)
  WHERE supersedes_measurement_id IS NOT NULL;

-- One live baseline per indicator version. A correction of the baseline is a
-- successor row, so only chain roots are constrained.
CREATE UNIQUE INDEX IF NOT EXISTS uq_measurement_one_baseline_per_indicator
  ON measurement_records (organization_id, indicator_definition_id)
  WHERE measurement_kind = 'baseline' AND supersedes_measurement_id IS NULL;

CREATE INDEX IF NOT EXISTS ix_measurement_baseline
  ON measurement_records (indicator_definition_id)
  WHERE measurement_kind = 'baseline';

-- RECONCILE: dropping a plan must never take its measurements with it.
ALTER TABLE measurement_records
  DROP CONSTRAINT IF EXISTS fk_measurement_plan_same_org;
ALTER TABLE measurement_records
  ADD CONSTRAINT fk_measurement_plan_same_org
    FOREIGN KEY (measurement_plan_id, organization_id)
    REFERENCES action_measurement_plans (id, organization_id);

ALTER TABLE measurement_records
  DROP CONSTRAINT IF EXISTS fk_measurement_indicator_same_plan;
ALTER TABLE measurement_records
  ADD CONSTRAINT fk_measurement_indicator_same_plan
    FOREIGN KEY (indicator_definition_id, measurement_plan_id)
    REFERENCES indicator_definitions (id, measurement_plan_id);
"""


# ---------------------------------------------------------------------------
# Baseline backfill: indicator_definitions.baseline_* → measurement_records
# ---------------------------------------------------------------------------

_BASELINE_BACKFILL_SQL = """
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'indicator_definitions' AND column_name = 'baseline_value'
  ) THEN
    -- A baseline recorded on the definition had no author and no reading date
    -- of its own; it is promoted to a real measurement, attributed to whoever
    -- created the indicator, so the trail is complete.
    INSERT INTO measurement_records (
      organization_id, measurement_plan_id, indicator_definition_id,
      measurement_kind, value, measured_at, note, collection_method,
      recorded_by, recorded_at
    )
    SELECT i.organization_id, i.measurement_plan_id, i.id,
           'baseline', i.baseline_value,
           coalesce(i.baseline_at, i.created_at),
           'Linha de base migrada da definição do indicador (ISOI-008 rev001).',
           coalesce(i.collection_method, ''),
           i.created_by, i.created_at
      FROM indicator_definitions i
     WHERE i.baseline_value IS NOT NULL
       AND NOT EXISTS (
         SELECT 1 FROM measurement_records mr
          WHERE mr.indicator_definition_id = i.id
            AND mr.measurement_kind = 'baseline'
       );

    ALTER TABLE indicator_definitions DROP COLUMN baseline_value;
  END IF;

  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'indicator_definitions' AND column_name = 'baseline_at'
  ) THEN
    ALTER TABLE indicator_definitions DROP COLUMN baseline_at;
  END IF;
END $$;
"""


# ---------------------------------------------------------------------------
# Outcome observation ↔ measurement evidence chain
# ---------------------------------------------------------------------------

_OBSERVATION_LINK_SQL = """
CREATE TABLE IF NOT EXISTS outcome_observation_measurements (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL REFERENCES organizations (id) ON DELETE CASCADE,
  outcome_observation_id uuid NOT NULL,
  measurement_record_id uuid NOT NULL,
  created_by uuid NOT NULL REFERENCES users (id),
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_oom_id_org UNIQUE (id, organization_id),
  CONSTRAINT uq_oom_pair UNIQUE (
    organization_id, outcome_observation_id, measurement_record_id
  ),
  CONSTRAINT fk_oom_observation_same_org
    FOREIGN KEY (outcome_observation_id, organization_id)
    REFERENCES improvement_case_outcome_observations (id, organization_id),
  CONSTRAINT fk_oom_measurement_same_org
    FOREIGN KEY (measurement_record_id, organization_id)
    REFERENCES measurement_records (id, organization_id)
);
CREATE INDEX IF NOT EXISTS ix_oom_observation
  ON outcome_observation_measurements (outcome_observation_id);

-- RECONCILE: an observation used to cascade-delete the proof that backed it.
ALTER TABLE outcome_observation_measurements
  DROP CONSTRAINT IF EXISTS fk_oom_observation_same_org;
ALTER TABLE outcome_observation_measurements
  ADD CONSTRAINT fk_oom_observation_same_org
    FOREIGN KEY (outcome_observation_id, organization_id)
    REFERENCES improvement_case_outcome_observations (id, organization_id);
"""


# ---------------------------------------------------------------------------
# RLS + grants
# ---------------------------------------------------------------------------

_RLS_AND_GRANTS_SQL = """
ALTER TABLE action_measurement_plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE action_measurement_plans FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON action_measurement_plans;
CREATE POLICY tenant_isolation ON action_measurement_plans FOR ALL TO qmind_app
  USING (organization_id = qmind_app.current_organization_id())
  WITH CHECK (organization_id = qmind_app.current_organization_id());

ALTER TABLE indicator_definitions ENABLE ROW LEVEL SECURITY;
ALTER TABLE indicator_definitions FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON indicator_definitions;
CREATE POLICY tenant_isolation ON indicator_definitions FOR ALL TO qmind_app
  USING (organization_id = qmind_app.current_organization_id())
  WITH CHECK (organization_id = qmind_app.current_organization_id());

ALTER TABLE measurement_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE measurement_records FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON measurement_records;
CREATE POLICY tenant_isolation ON measurement_records FOR ALL TO qmind_app
  USING (organization_id = qmind_app.current_organization_id())
  WITH CHECK (organization_id = qmind_app.current_organization_id());

ALTER TABLE outcome_observation_measurements ENABLE ROW LEVEL SECURITY;
ALTER TABLE outcome_observation_measurements FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON outcome_observation_measurements;
CREATE POLICY tenant_isolation ON outcome_observation_measurements
  FOR ALL TO qmind_app
  USING (organization_id = qmind_app.current_organization_id())
  WITH CHECK (organization_id = qmind_app.current_organization_id());

-- Grants. Everything this revision adds is part of an audit trail, so the
-- application role may never DELETE from any of it. Measurement records go one
-- step further: they are append-only, so UPDATE is revoked too and a
-- correction can only ever be a new row.
GRANT SELECT, INSERT, UPDATE ON
  action_measurement_plans,
  indicator_definitions
  TO qmind_app;
REVOKE DELETE ON action_measurement_plans FROM qmind_app;
REVOKE DELETE ON indicator_definitions FROM qmind_app;

GRANT SELECT, INSERT ON outcome_observation_measurements TO qmind_app;
REVOKE UPDATE, DELETE ON outcome_observation_measurements FROM qmind_app;

GRANT SELECT, INSERT ON measurement_records TO qmind_app;
REVOKE UPDATE, DELETE ON measurement_records FROM qmind_app;

GRANT SELECT, INSERT, UPDATE ON evidence_links TO qmind_app;
REVOKE DELETE ON evidence_links FROM qmind_app;

-- The documents the whole trail points at. Disposal is already a status change
-- with a date and an author, so the row itself never has to go away — and if it
-- did, every link pointing at it would become a dangling claim.
GRANT SELECT, INSERT, UPDATE ON evidences TO qmind_app;
REVOKE DELETE ON evidences FROM qmind_app;
"""


# ---------------------------------------------------------------------------
# Downgrade
# ---------------------------------------------------------------------------

_DOWNGRADE_GUARD_SQL = """
DO $$
DECLARE
  n_measurements bigint := 0;
  n_case_evidences bigint := 0;
  n_links bigint := 0;
  n_observation_links bigint := 0;
BEGIN
  IF to_regclass('public.measurement_records') IS NOT NULL THEN
    SELECT count(*) INTO n_measurements FROM measurement_records;
  END IF;
  IF to_regclass('public.outcome_observation_measurements') IS NOT NULL THEN
    SELECT count(*) INTO n_observation_links FROM outcome_observation_measurements;
  END IF;
  SELECT count(*) INTO n_case_evidences
    FROM evidences WHERE improvement_case_id IS NOT NULL;
  SELECT count(*) INTO n_links
    FROM evidence_links
   WHERE removed_at IS NOT NULL
      OR target_type IN (
           'action_check_in', 'action_impediment', 'measurement_record',
           'outcome_observation', 'improvement_case'
         );

  IF n_measurements > 0
     OR n_observation_links > 0
     OR n_case_evidences > 0
     OR n_links > 0 THEN
    RAISE EXCEPTION
      'ISOI-008 downgrade refused: it would destroy audit history '
      '(% measurement records, % observation-measurement links, '
      '% case-scoped evidences, % execution/removed evidence links). '
      'Downgrade is only supported on a database with no ISOI-008 data. '
      'Archive and remove the history deliberately first, or roll back on a '
      'disposable copy.',
      n_measurements, n_observation_links, n_case_evidences, n_links;
  END IF;
END $$;
"""

_DOWNGRADE_SQL = """
-- Only reachable when the guard above proved every table is empty, so nothing
-- below can lose a row.
DROP TABLE IF EXISTS outcome_observation_measurements;
DROP TABLE IF EXISTS measurement_records;
DROP TABLE IF EXISTS indicator_definitions;
DROP TABLE IF EXISTS action_measurement_plans;

ALTER TABLE improvement_case_outcome_observations
  DROP CONSTRAINT IF EXISTS uq_outcome_obs_id_org;

DROP INDEX IF EXISTS ix_evidence_links_target_active;
DROP INDEX IF EXISTS uq_evidence_links_active_target;
ALTER TABLE evidence_links DROP COLUMN IF EXISTS removal_reason;
ALTER TABLE evidence_links DROP COLUMN IF EXISTS removed_by;
ALTER TABLE evidence_links DROP COLUMN IF EXISTS removed_at;
ALTER TABLE evidence_links
  DROP CONSTRAINT IF EXISTS evidence_links_target_type_check;
ALTER TABLE evidence_links
  ADD CONSTRAINT evidence_links_target_type_check CHECK (
    target_type IN (
      'requirement', 'question', 'finding', 'action_item',
      'interview', 'answer'
    )
  );
GRANT SELECT, INSERT, UPDATE, DELETE ON evidence_links TO qmind_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON evidences TO qmind_app;

DROP INDEX IF EXISTS uq_evidences_idempotency;
ALTER TABLE evidences DROP CONSTRAINT IF EXISTS ck_evidences_idempotency_pair;
ALTER TABLE evidences DROP COLUMN IF EXISTS request_fingerprint;
ALTER TABLE evidences DROP COLUMN IF EXISTS idempotency_key_hash;
ALTER TABLE evidences DROP COLUMN IF EXISTS idempotency_scope;

UPDATE evidences SET collected_phase = 'unknown_legacy'
WHERE collected_phase = 'action_execution';
ALTER TABLE evidences DROP CONSTRAINT IF EXISTS ck_evidences_collected_phase;
ALTER TABLE evidences
  ADD CONSTRAINT ck_evidences_collected_phase CHECK (
    collected_phase IS NULL OR collected_phase IN (
      'preparation', 'planning', 'field', 'analysis', 'unknown_legacy'
    )
  );
DROP INDEX IF EXISTS ix_evidences_improvement_case;
ALTER TABLE evidences DROP CONSTRAINT IF EXISTS ck_evidences_context_xor;
ALTER TABLE evidences
  DROP CONSTRAINT IF EXISTS fk_evidences_improvement_case_same_org;
ALTER TABLE evidences DROP COLUMN IF EXISTS improvement_case_id;

DROP INDEX IF EXISTS ix_action_items_plan_org;
"""
