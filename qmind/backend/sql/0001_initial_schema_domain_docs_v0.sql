-- QMind DDL v0
-- Freeze reference: git tag domain-docs-v0 (commit docs package 2026-08-03)
-- Sources: 001_Data_Dictionary.md, 002_ER_Logical.md, 001_State_Machines.md,
--          003_Maturity_Model.md, 002_Roles_and_Permissions.md
-- Engine: PostgreSQL, database name: qmind
-- Notes / amendments: architecture/04_Docs/007_Domain_Docs_Amendment_001.md

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE SCHEMA IF NOT EXISTS qmind_app;

-- ---------------------------------------------------------------------------
-- Helpers
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION qmind_app.set_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.updated_at := now();
  RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION qmind_app.current_organization_id()
RETURNS uuid
LANGUAGE sql
STABLE
AS $$
  SELECT NULLIF(current_setting('app.organization_id', true), '')::uuid;
$$;

COMMENT ON FUNCTION qmind_app.current_organization_id() IS
  'RLS helper. SET LOCAL app.organization_id = ''<uuid>''; before queries as qmind_app.';

-- ---------------------------------------------------------------------------
-- Global identity / catalog (no organization_id)
-- ---------------------------------------------------------------------------
CREATE TABLE users (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  idp_sub text NOT NULL,
  email text NOT NULL,
  display_name text,
  status text NOT NULL DEFAULT 'active'
    CHECK (status IN ('active', 'disabled')),
  last_login_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_users_idp_sub UNIQUE (idp_sub),
  CONSTRAINT uq_users_email UNIQUE (email)
);

CREATE TABLE platform_admin_grants (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users (id),
  status text NOT NULL DEFAULT 'active'
    CHECK (status IN ('active', 'revoked')),
  granted_at timestamptz NOT NULL DEFAULT now(),
  revoked_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE standards (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code text NOT NULL,
  title text NOT NULL,
  status text NOT NULL DEFAULT 'active'
    CHECK (status IN ('active', 'retired')),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_standards_code UNIQUE (code)
);

CREATE TABLE standard_versions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  standard_id uuid NOT NULL REFERENCES standards (id),
  version_label text NOT NULL,
  status text NOT NULL DEFAULT 'active'
    CHECK (status IN ('draft', 'active', 'retired')),
  effective_from date,
  effective_to date,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_standard_versions UNIQUE (standard_id, version_label)
);

CREATE TABLE requirements (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  standard_version_id uuid NOT NULL REFERENCES standard_versions (id),
  parent_id uuid REFERENCES requirements (id),
  code text NOT NULL,
  title_authorized text NOT NULL,
  sort_order int NOT NULL DEFAULT 0,
  status text NOT NULL DEFAULT 'active'
    CHECK (status IN ('active', 'retired')),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_requirements_code UNIQUE (standard_version_id, code)
);

CREATE TABLE assessment_models (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code text NOT NULL,
  version_label text NOT NULL,
  title text NOT NULL,
  status text NOT NULL DEFAULT 'active'
    CHECK (status IN ('draft', 'active', 'retired')),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_assessment_models UNIQUE (code, version_label)
);

CREATE TABLE criteria (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  assessment_model_id uuid NOT NULL REFERENCES assessment_models (id),
  code text NOT NULL,
  title text NOT NULL,
  sort_order int NOT NULL DEFAULT 0,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_criteria_code UNIQUE (assessment_model_id, code)
);

CREATE TABLE questions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  assessment_model_id uuid NOT NULL REFERENCES assessment_models (id),
  criterion_id uuid REFERENCES criteria (id),
  code text NOT NULL,
  prompt_text text NOT NULL,
  sort_order int NOT NULL DEFAULT 0,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_questions_code UNIQUE (assessment_model_id, code)
);

CREATE TABLE assessment_model_requirements (
  assessment_model_id uuid NOT NULL REFERENCES assessment_models (id),
  requirement_id uuid NOT NULL REFERENCES requirements (id),
  PRIMARY KEY (assessment_model_id, requirement_id)
);

CREATE TABLE maturity_models (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  model_code text NOT NULL,
  model_version text NOT NULL,
  status text NOT NULL DEFAULT 'active'
    CHECK (status IN ('draft', 'active', 'retired')),
  rounding_mode text NOT NULL DEFAULT 'half_up'
    CHECK (rounding_mode IN ('half_up')),
  decimal_places int NOT NULL DEFAULT 2 CHECK (decimal_places = 2),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_maturity_models UNIQUE (model_code, model_version)
);

CREATE TABLE maturity_dimensions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  maturity_model_id uuid NOT NULL REFERENCES maturity_models (id),
  code text NOT NULL,
  title text NOT NULL,
  sort_order int NOT NULL DEFAULT 0,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_maturity_dimensions UNIQUE (maturity_model_id, code)
);

CREATE TABLE maturity_criteria (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  maturity_dimension_id uuid NOT NULL REFERENCES maturity_dimensions (id),
  code text NOT NULL,
  title text NOT NULL,
  anchor_l3 text,
  min_evidence_rule text,
  sort_order int NOT NULL DEFAULT 0,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_maturity_criteria UNIQUE (maturity_dimension_id, code)
);

-- ---------------------------------------------------------------------------
-- Tenant root
-- ---------------------------------------------------------------------------
CREATE TABLE organizations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,
  status text NOT NULL DEFAULT 'active'
    CHECK (status IN ('active', 'suspended', 'closed')),
  timezone text NOT NULL DEFAULT 'America/Sao_Paulo',
  data_residency_note text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE units (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL REFERENCES organizations (id),
  name text NOT NULL,
  unit_type text,
  parent_unit_id uuid,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_units_id_org UNIQUE (id, organization_id)
);

ALTER TABLE units
  ADD CONSTRAINT fk_units_parent_same_org
  FOREIGN KEY (parent_unit_id, organization_id)
  REFERENCES units (id, organization_id);

CREATE TABLE memberships (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL REFERENCES organizations (id),
  user_id uuid NOT NULL REFERENCES users (id),
  roles text[] NOT NULL,
  status text NOT NULL DEFAULT 'active'
    CHECK (status IN ('invited', 'active', 'revoked', 'expired')),
  valid_from timestamptz NOT NULL DEFAULT now(),
  valid_to timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_memberships_id_org UNIQUE (id, organization_id),
  CONSTRAINT uq_memberships_org_user UNIQUE (organization_id, user_id),
  CONSTRAINT ck_memberships_roles_nonempty CHECK (cardinality(roles) >= 1),
  CONSTRAINT ck_memberships_roles_known CHECK (
    roles <@ ARRAY[
      'platform_admin',
      'org_admin',
      'consultant_auditor',
      'quality_manager',
      'process_owner',
      'action_owner',
      'reader'
    ]::text[]
  )
);

CREATE INDEX ix_memberships_org_status ON memberships (organization_id, status);

CREATE TABLE person_contacts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL REFERENCES organizations (id),
  unit_id uuid,
  name text NOT NULL,
  email text,
  phone text,
  linked_user_id uuid REFERENCES users (id),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_person_contacts_id_org UNIQUE (id, organization_id),
  CONSTRAINT fk_person_contacts_unit_same_org
    FOREIGN KEY (unit_id, organization_id) REFERENCES units (id, organization_id)
);

CREATE TABLE org_processes (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL REFERENCES organizations (id),
  unit_id uuid,
  name text NOT NULL,
  owner_membership_id uuid,
  status text NOT NULL DEFAULT 'active'
    CHECK (status IN ('active', 'inactive')),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_org_processes_id_org UNIQUE (id, organization_id),
  CONSTRAINT fk_org_processes_unit_same_org
    FOREIGN KEY (unit_id, organization_id) REFERENCES units (id, organization_id),
  CONSTRAINT fk_org_processes_owner_same_org
    FOREIGN KEY (owner_membership_id, organization_id)
    REFERENCES memberships (id, organization_id)
);

CREATE INDEX ix_org_processes_org_status ON org_processes (organization_id, status, updated_at DESC);

-- ---------------------------------------------------------------------------
-- Assessments & collection
-- ---------------------------------------------------------------------------
CREATE TABLE assessments (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL REFERENCES organizations (id),
  assessment_model_id uuid NOT NULL REFERENCES assessment_models (id),
  standard_version_id uuid NOT NULL REFERENCES standard_versions (id),
  maturity_model_id uuid REFERENCES maturity_models (id),
  type text NOT NULL
    CHECK (type IN ('diagnosis', 'internal_audit', 'other')),
  status text NOT NULL DEFAULT 'draft'
    CHECK (status IN (
      'draft', 'planned', 'in_progress', 'analysis',
      'actions', 'report', 'closed', 'cancelled'
    )),
  planned_start timestamptz,
  planned_end timestamptz,
  started_at timestamptz,
  closed_at timestamptz,
  lead_membership_id uuid,
  no_findings_declared boolean NOT NULL DEFAULT false,
  close_waiver_reason text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  created_by uuid,
  updated_by uuid,
  CONSTRAINT uq_assessments_id_org UNIQUE (id, organization_id),
  CONSTRAINT fk_assessments_lead_same_org
    FOREIGN KEY (lead_membership_id, organization_id)
    REFERENCES memberships (id, organization_id)
);

CREATE INDEX ix_assessments_org_status ON assessments (organization_id, status, updated_at DESC);

CREATE TABLE assessment_scopes (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL,
  assessment_id uuid NOT NULL,
  org_process_id uuid,
  requirement_id uuid REFERENCES requirements (id),
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_assessment_scopes_id_org UNIQUE (id, organization_id),
  CONSTRAINT fk_assessment_scopes_assessment_same_org
    FOREIGN KEY (assessment_id, organization_id)
    REFERENCES assessments (id, organization_id),
  CONSTRAINT fk_assessment_scopes_process_same_org
    FOREIGN KEY (org_process_id, organization_id)
    REFERENCES org_processes (id, organization_id),
  CONSTRAINT ck_assessment_scopes_target CHECK (
    org_process_id IS NOT NULL OR requirement_id IS NOT NULL
  )
);

CREATE TABLE assessment_team_members (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL,
  assessment_id uuid NOT NULL,
  membership_id uuid NOT NULL,
  team_role text,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_assessment_team UNIQUE (assessment_id, membership_id),
  CONSTRAINT fk_assessment_team_assessment_same_org
    FOREIGN KEY (assessment_id, organization_id)
    REFERENCES assessments (id, organization_id),
  CONSTRAINT fk_assessment_team_membership_same_org
    FOREIGN KEY (membership_id, organization_id)
    REFERENCES memberships (id, organization_id)
);

CREATE TABLE interviews (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL,
  assessment_id uuid NOT NULL,
  conducted_at timestamptz,
  mode text CHECK (mode IS NULL OR mode IN ('onsite', 'remote', 'hybrid')),
  status text NOT NULL DEFAULT 'planned'
    CHECK (status IN ('planned', 'completed', 'cancelled')),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_interviews_id_org UNIQUE (id, organization_id),
  CONSTRAINT fk_interviews_assessment_same_org
    FOREIGN KEY (assessment_id, organization_id)
    REFERENCES assessments (id, organization_id)
);

CREATE TABLE answers (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL,
  interview_id uuid NOT NULL,
  question_id uuid REFERENCES questions (id),
  criterion_id uuid REFERENCES criteria (id),
  body text NOT NULL,
  author_membership_id uuid,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_answers_id_org UNIQUE (id, organization_id),
  CONSTRAINT fk_answers_interview_same_org
    FOREIGN KEY (interview_id, organization_id)
    REFERENCES interviews (id, organization_id),
  CONSTRAINT fk_answers_author_same_org
    FOREIGN KEY (author_membership_id, organization_id)
    REFERENCES memberships (id, organization_id)
);

-- ---------------------------------------------------------------------------
-- Evidence (legal_hold = flag, not status)
-- ---------------------------------------------------------------------------
CREATE TABLE evidences (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL REFERENCES organizations (id),
  assessment_id uuid,
  status text NOT NULL DEFAULT 'upload_pending'
    CHECK (status IN (
      'upload_pending', 'quarantined', 'rejected', 'approved',
      'superseded', 'pending_disposal', 'disposed'
    )),
  classification text NOT NULL DEFAULT 'confidential'
    CHECK (classification IN ('public', 'internal', 'confidential', 'restricted')),
  content_type text,
  byte_size bigint,
  content_hash text,
  storage_key text,
  version_no int NOT NULL DEFAULT 1,
  lineage_id uuid,
  supersedes_evidence_id uuid,
  retention_until date,
  legal_hold boolean NOT NULL DEFAULT false,
  legal_hold_reason text,
  legal_hold_at timestamptz,
  legal_hold_by uuid,
  uploaded_by uuid,
  upload_expires_at timestamptz,
  disposed_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_evidences_id_org UNIQUE (id, organization_id),
  CONSTRAINT fk_evidences_assessment_same_org
    FOREIGN KEY (assessment_id, organization_id)
    REFERENCES assessments (id, organization_id),
  CONSTRAINT fk_evidences_supersedes_same_org
    FOREIGN KEY (supersedes_evidence_id, organization_id)
    REFERENCES evidences (id, organization_id),
  CONSTRAINT ck_evidences_legal_hold_reason CHECK (
    (NOT legal_hold AND legal_hold_reason IS NULL)
    OR (legal_hold AND legal_hold_reason IS NOT NULL)
  )
);

CREATE INDEX ix_evidences_org_assessment_status
  ON evidences (organization_id, assessment_id, status);
CREATE INDEX ix_evidences_org_status ON evidences (organization_id, status, updated_at DESC);

CREATE TABLE evidence_links (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL,
  evidence_id uuid NOT NULL,
  target_type text NOT NULL
    CHECK (target_type IN (
      'requirement', 'question', 'finding', 'action_item', 'interview', 'answer'
    )),
  target_id uuid NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_evidence_links_id_org UNIQUE (id, organization_id),
  CONSTRAINT fk_evidence_links_evidence_same_org
    FOREIGN KEY (evidence_id, organization_id)
    REFERENCES evidences (id, organization_id)
);

-- ---------------------------------------------------------------------------
-- Findings
-- ---------------------------------------------------------------------------
CREATE TABLE findings (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL,
  assessment_id uuid NOT NULL,
  finding_type text NOT NULL
    CHECK (finding_type IN (
      'conformity', 'nonconformity', 'opportunity', 'observation'
    )),
  severity text,
  status text NOT NULL DEFAULT 'draft'
    CHECK (status IN (
      'draft', 'in_review', 'approved', 'rejected', 'withdrawn', 'discarded'
    )),
  title text NOT NULL,
  body text NOT NULL,
  insufficient_evidence boolean NOT NULL DEFAULT false,
  insufficient_evidence_rationale text,
  author_membership_id uuid NOT NULL,
  submitted_at timestamptz,
  approved_at timestamptz,
  approved_by uuid,
  withdrawn_reason text,
  discard_reason text,
  rework_of_finding_id uuid,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_findings_id_org UNIQUE (id, organization_id),
  CONSTRAINT fk_findings_assessment_same_org
    FOREIGN KEY (assessment_id, organization_id)
    REFERENCES assessments (id, organization_id),
  CONSTRAINT fk_findings_author_same_org
    FOREIGN KEY (author_membership_id, organization_id)
    REFERENCES memberships (id, organization_id),
  CONSTRAINT fk_findings_approver_same_org
    FOREIGN KEY (approved_by, organization_id)
    REFERENCES memberships (id, organization_id),
  CONSTRAINT fk_findings_rework_of_same_org
    FOREIGN KEY (rework_of_finding_id, organization_id)
    REFERENCES findings (id, organization_id),
  CONSTRAINT ck_findings_insufficient_by_type CHECK (
    (
      finding_type IN ('conformity', 'opportunity')
      AND insufficient_evidence = false
      AND insufficient_evidence_rationale IS NULL
    )
    OR (
      finding_type IN ('nonconformity', 'observation')
      AND (
        insufficient_evidence = false
        OR (insufficient_evidence = true AND insufficient_evidence_rationale IS NOT NULL)
      )
    )
  ),
  -- Segregation of duties: approver ≠ author when approved
  CONSTRAINT ck_findings_sod_approve CHECK (
    status <> 'approved'
    OR (
      approved_by IS NOT NULL
      AND approved_by IS DISTINCT FROM author_membership_id
    )
  )
);

CREATE INDEX ix_findings_org_status ON findings (organization_id, status, updated_at DESC);

CREATE TABLE finding_requirements (
  organization_id uuid NOT NULL,
  finding_id uuid NOT NULL,
  requirement_id uuid NOT NULL REFERENCES requirements (id),
  PRIMARY KEY (finding_id, requirement_id),
  CONSTRAINT fk_finding_requirements_finding_same_org
    FOREIGN KEY (finding_id, organization_id)
    REFERENCES findings (id, organization_id)
);

CREATE TABLE finding_evidences (
  organization_id uuid NOT NULL,
  finding_id uuid NOT NULL,
  evidence_id uuid NOT NULL,
  PRIMARY KEY (finding_id, evidence_id),
  CONSTRAINT fk_finding_evidences_finding_same_org
    FOREIGN KEY (finding_id, organization_id)
    REFERENCES findings (id, organization_id),
  CONSTRAINT fk_finding_evidences_evidence_same_org
    FOREIGN KEY (evidence_id, organization_id)
    REFERENCES evidences (id, organization_id)
);

-- ---------------------------------------------------------------------------
-- Maturity (versioned package)
-- ---------------------------------------------------------------------------
CREATE TABLE maturity_assessments (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL,
  assessment_id uuid NOT NULL,
  version_no int NOT NULL,
  supersedes_id uuid,
  maturity_model_id uuid NOT NULL REFERENCES maturity_models (id),
  status text NOT NULL DEFAULT 'draft'
    CHECK (status IN (
      'draft', 'in_review', 'approved', 'rejected', 'superseded', 'discarded'
    )),
  global_score numeric(5, 2),
  author_membership_id uuid NOT NULL,
  approved_by uuid,
  discard_reason text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_maturity_assessments_id_org UNIQUE (id, organization_id),
  CONSTRAINT uq_maturity_assessments_version UNIQUE (assessment_id, version_no),
  CONSTRAINT fk_maturity_assessments_assessment_same_org
    FOREIGN KEY (assessment_id, organization_id)
    REFERENCES assessments (id, organization_id),
  CONSTRAINT fk_maturity_assessments_author_same_org
    FOREIGN KEY (author_membership_id, organization_id)
    REFERENCES memberships (id, organization_id),
  CONSTRAINT fk_maturity_assessments_approver_same_org
    FOREIGN KEY (approved_by, organization_id)
    REFERENCES memberships (id, organization_id),
  CONSTRAINT fk_maturity_assessments_supersedes_same_org
    FOREIGN KEY (supersedes_id, organization_id)
    REFERENCES maturity_assessments (id, organization_id),
  CONSTRAINT ck_maturity_assessments_sod CHECK (
    status <> 'approved'
    OR (
      approved_by IS NOT NULL
      AND approved_by IS DISTINCT FROM author_membership_id
    )
  )
);

CREATE TABLE maturity_scores (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL,
  maturity_assessment_id uuid NOT NULL,
  criterion_id uuid NOT NULL REFERENCES maturity_criteria (id),
  applicability text NOT NULL
    CHECK (applicability IN ('applicable', 'not_applicable', 'insufficient_info')),
  na_rationale text,
  level int,
  rationale text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_maturity_scores_id_org UNIQUE (id, organization_id),
  CONSTRAINT uq_maturity_scores_criterion UNIQUE (maturity_assessment_id, criterion_id),
  CONSTRAINT fk_maturity_scores_package_same_org
    FOREIGN KEY (maturity_assessment_id, organization_id)
    REFERENCES maturity_assessments (id, organization_id),
  CONSTRAINT ck_maturity_scores_applicability CHECK (
    (
      applicability = 'applicable'
      AND level BETWEEN 1 AND 5
      AND na_rationale IS NULL
    )
    OR (
      applicability = 'not_applicable'
      AND level IS NULL
      AND na_rationale IS NOT NULL
    )
    OR (
      applicability = 'insufficient_info'
      AND level IS NULL
    )
  )
);

CREATE TABLE maturity_dimension_scores (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL,
  maturity_assessment_id uuid NOT NULL,
  dimension_id uuid NOT NULL REFERENCES maturity_dimensions (id),
  score numeric(5, 2) NOT NULL,
  applicable_count int NOT NULL CHECK (applicable_count >= 0),
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_maturity_dimension_scores UNIQUE (maturity_assessment_id, dimension_id),
  CONSTRAINT fk_maturity_dimension_scores_package_same_org
    FOREIGN KEY (maturity_assessment_id, organization_id)
    REFERENCES maturity_assessments (id, organization_id)
);

CREATE TABLE maturity_score_evidence_links (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL,
  maturity_score_id uuid NOT NULL,
  evidence_id uuid,
  answer_id uuid,
  finding_id uuid,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT fk_mse_score_same_org
    FOREIGN KEY (maturity_score_id, organization_id)
    REFERENCES maturity_scores (id, organization_id),
  CONSTRAINT fk_mse_evidence_same_org
    FOREIGN KEY (evidence_id, organization_id)
    REFERENCES evidences (id, organization_id),
  CONSTRAINT fk_mse_answer_same_org
    FOREIGN KEY (answer_id, organization_id)
    REFERENCES answers (id, organization_id),
  CONSTRAINT fk_mse_finding_same_org
    FOREIGN KEY (finding_id, organization_id)
    REFERENCES findings (id, organization_id),
  CONSTRAINT ck_mse_one_target CHECK (
    (evidence_id IS NOT NULL)::int
    + (answer_id IS NOT NULL)::int
    + (finding_id IS NOT NULL)::int = 1
  )
);

-- ---------------------------------------------------------------------------
-- Actions & reports
-- ---------------------------------------------------------------------------
CREATE TABLE action_plans (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL,
  assessment_id uuid NOT NULL,
  status text NOT NULL DEFAULT 'draft'
    CHECK (status IN ('draft', 'active', 'completed', 'cancelled')),
  empty_plan_rationale text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_action_plans_id_org UNIQUE (id, organization_id),
  CONSTRAINT fk_action_plans_assessment_same_org
    FOREIGN KEY (assessment_id, organization_id)
    REFERENCES assessments (id, organization_id)
);

CREATE TABLE action_items (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL,
  action_plan_id uuid NOT NULL,
  finding_id uuid,
  action_kind text NOT NULL
    CHECK (action_kind IN ('correction', 'corrective_action', 'improvement')),
  description text NOT NULL,
  owner_membership_id uuid NOT NULL,
  due_at timestamptz NOT NULL,
  status text NOT NULL DEFAULT 'open'
    CHECK (status IN (
      'open', 'in_progress', 'implemented', 'validated', 'done',
      'cancelled', 'ineffective', 'ineffective_closed'
    )),
  is_overdue boolean NOT NULL DEFAULT false,
  efficacy_required boolean NOT NULL DEFAULT false,
  source_finding_withdrawn boolean NOT NULL DEFAULT false,
  validated_by uuid,
  efficacy_confirmed_by uuid,
  cancel_reason text,
  reject_reason text,
  efficacy_fail_reason text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_action_items_id_org UNIQUE (id, organization_id),
  CONSTRAINT fk_action_items_plan_same_org
    FOREIGN KEY (action_plan_id, organization_id)
    REFERENCES action_plans (id, organization_id),
  CONSTRAINT fk_action_items_finding_same_org
    FOREIGN KEY (finding_id, organization_id)
    REFERENCES findings (id, organization_id),
  CONSTRAINT fk_action_items_owner_same_org
    FOREIGN KEY (owner_membership_id, organization_id)
    REFERENCES memberships (id, organization_id),
  CONSTRAINT fk_action_items_validator_same_org
    FOREIGN KEY (validated_by, organization_id)
    REFERENCES memberships (id, organization_id),
  CONSTRAINT fk_action_items_efficacy_same_org
    FOREIGN KEY (efficacy_confirmed_by, organization_id)
    REFERENCES memberships (id, organization_id),
  CONSTRAINT ck_action_items_sod_validate CHECK (
    validated_by IS NULL OR validated_by IS DISTINCT FROM owner_membership_id
  )
);

CREATE INDEX ix_action_items_org_status ON action_items (organization_id, status, updated_at DESC);

CREATE TABLE reports (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL,
  assessment_id uuid NOT NULL,
  version_no int NOT NULL,
  status text NOT NULL DEFAULT 'draft'
    CHECK (status IN (
      'draft', 'in_review', 'published', 'archived', 'superseded', 'discarded'
    )),
  structured_content jsonb NOT NULL DEFAULT '{}'::jsonb,
  maturity_assessment_id uuid,
  export_storage_key text,
  supersedes_report_id uuid,
  discard_reason text,
  published_at timestamptz,
  published_by uuid,
  author_membership_id uuid,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_reports_id_org UNIQUE (id, organization_id),
  CONSTRAINT uq_reports_version UNIQUE (assessment_id, version_no),
  CONSTRAINT fk_reports_assessment_same_org
    FOREIGN KEY (assessment_id, organization_id)
    REFERENCES assessments (id, organization_id),
  CONSTRAINT fk_reports_maturity_same_org
    FOREIGN KEY (maturity_assessment_id, organization_id)
    REFERENCES maturity_assessments (id, organization_id),
  CONSTRAINT fk_reports_supersedes_same_org
    FOREIGN KEY (supersedes_report_id, organization_id)
    REFERENCES reports (id, organization_id),
  CONSTRAINT fk_reports_publisher_same_org
    FOREIGN KEY (published_by, organization_id)
    REFERENCES memberships (id, organization_id),
  CONSTRAINT fk_reports_author_same_org
    FOREIGN KEY (author_membership_id, organization_id)
    REFERENCES memberships (id, organization_id),
  CONSTRAINT ck_reports_sod_publish CHECK (
    status <> 'published'
    OR (
      published_by IS NOT NULL
      AND (
        author_membership_id IS NULL
        OR published_by IS DISTINCT FROM author_membership_id
      )
    )
  )
);

CREATE INDEX ix_reports_org_status ON reports (organization_id, status, updated_at DESC);

-- ---------------------------------------------------------------------------
-- Jobs / AI / audit / break-glass
-- ---------------------------------------------------------------------------
CREATE TABLE jobs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL REFERENCES organizations (id),
  job_type text NOT NULL,
  status text NOT NULL DEFAULT 'queued'
    CHECK (status IN ('queued', 'running', 'succeeded', 'failed', 'cancelled')),
  requested_by uuid,
  idempotency_key text NOT NULL,
  input_ref jsonb NOT NULL DEFAULT '{}'::jsonb,
  error_code text,
  error_safe_message text,
  started_at timestamptz,
  finished_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_jobs_id_org UNIQUE (id, organization_id),
  CONSTRAINT uq_jobs_idempotency UNIQUE (organization_id, idempotency_key),
  CONSTRAINT fk_jobs_requested_by_same_org
    FOREIGN KEY (requested_by, organization_id)
    REFERENCES memberships (id, organization_id)
);

CREATE INDEX ix_jobs_org_status ON jobs (organization_id, status, created_at DESC);

CREATE TABLE ai_suggestions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL,
  job_id uuid NOT NULL,
  use_case text NOT NULL,
  status text NOT NULL DEFAULT 'suggested'
    CHECK (status IN ('suggested', 'accepted', 'edited', 'rejected')),
  target_type text NOT NULL,
  target_id uuid NOT NULL,
  suggestion_payload jsonb NOT NULL,
  provenance jsonb NOT NULL DEFAULT '{}'::jsonb,
  reviewed_by uuid,
  reviewed_at timestamptz,
  human_diff jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_ai_suggestions_id_org UNIQUE (id, organization_id),
  CONSTRAINT fk_ai_suggestions_job_same_org
    FOREIGN KEY (job_id, organization_id)
    REFERENCES jobs (id, organization_id),
  CONSTRAINT fk_ai_suggestions_reviewer_same_org
    FOREIGN KEY (reviewed_by, organization_id)
    REFERENCES memberships (id, organization_id)
);

CREATE TABLE platform_audit_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid REFERENCES organizations (id),
  actor_type text NOT NULL
    CHECK (actor_type IN ('user', 'service', 'system')),
  actor_user_id uuid REFERENCES users (id),
  actor_membership_id uuid,
  actor_service_id text,
  action text NOT NULL,
  resource_type text NOT NULL,
  resource_id uuid NOT NULL,
  from_status text,
  to_status text,
  correlation_id uuid NOT NULL,
  result text NOT NULL
    CHECK (result IN ('success', 'denied', 'error')),
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_audit_actor_identity CHECK (
    (
      actor_type = 'user'
      AND actor_user_id IS NOT NULL
      AND actor_service_id IS NULL
    )
    OR (
      actor_type = 'service'
      AND actor_service_id IS NOT NULL
      AND actor_user_id IS NULL
    )
    OR (
      actor_type = 'system'
      AND actor_user_id IS NULL
      AND actor_service_id IS NULL
    )
  )
);

CREATE INDEX ix_audit_org_created ON platform_audit_events (organization_id, created_at DESC);
CREATE INDEX ix_audit_correlation ON platform_audit_events (correlation_id);

CREATE TABLE break_glass_sessions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL REFERENCES organizations (id),
  platform_admin_user_id uuid NOT NULL REFERENCES users (id),
  reason text NOT NULL,
  ticket_id text NOT NULL,
  started_at timestamptz NOT NULL DEFAULT now(),
  expires_at timestamptz NOT NULL,
  ended_at timestamptz,
  scope_notes text,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_break_glass_window CHECK (expires_at > started_at)
);

-- ---------------------------------------------------------------------------
-- App role (not table owner; cannot bypass RLS) — before policies
-- ---------------------------------------------------------------------------
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'qmind_app') THEN
    CREATE ROLE qmind_app LOGIN PASSWORD 'qmind_app_dev';
  END IF;
END;
$$;

GRANT CONNECT ON DATABASE qmind TO qmind_app;
GRANT USAGE ON SCHEMA public TO qmind_app;
GRANT USAGE ON SCHEMA qmind_app TO qmind_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO qmind_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO qmind_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO qmind_app;

-- ---------------------------------------------------------------------------
-- RLS (defense in depth; app still authorizes)
-- organizations uses id as tenant key; other tenant tables use organization_id
-- ---------------------------------------------------------------------------
ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE organizations FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON organizations
  FOR ALL TO qmind_app
  USING (id = qmind_app.current_organization_id())
  WITH CHECK (id = qmind_app.current_organization_id());

ALTER TABLE units ENABLE ROW LEVEL SECURITY;
ALTER TABLE units FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON units FOR ALL TO qmind_app
  USING (organization_id = qmind_app.current_organization_id())
  WITH CHECK (organization_id = qmind_app.current_organization_id());

ALTER TABLE memberships ENABLE ROW LEVEL SECURITY;
ALTER TABLE memberships FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON memberships FOR ALL TO qmind_app
  USING (organization_id = qmind_app.current_organization_id())
  WITH CHECK (organization_id = qmind_app.current_organization_id());

ALTER TABLE person_contacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE person_contacts FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON person_contacts FOR ALL TO qmind_app
  USING (organization_id = qmind_app.current_organization_id())
  WITH CHECK (organization_id = qmind_app.current_organization_id());

ALTER TABLE org_processes ENABLE ROW LEVEL SECURITY;
ALTER TABLE org_processes FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON org_processes FOR ALL TO qmind_app
  USING (organization_id = qmind_app.current_organization_id())
  WITH CHECK (organization_id = qmind_app.current_organization_id());

ALTER TABLE assessments ENABLE ROW LEVEL SECURITY;
ALTER TABLE assessments FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON assessments FOR ALL TO qmind_app
  USING (organization_id = qmind_app.current_organization_id())
  WITH CHECK (organization_id = qmind_app.current_organization_id());

ALTER TABLE assessment_scopes ENABLE ROW LEVEL SECURITY;
ALTER TABLE assessment_scopes FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON assessment_scopes FOR ALL TO qmind_app
  USING (organization_id = qmind_app.current_organization_id())
  WITH CHECK (organization_id = qmind_app.current_organization_id());

ALTER TABLE assessment_team_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE assessment_team_members FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON assessment_team_members FOR ALL TO qmind_app
  USING (organization_id = qmind_app.current_organization_id())
  WITH CHECK (organization_id = qmind_app.current_organization_id());

ALTER TABLE interviews ENABLE ROW LEVEL SECURITY;
ALTER TABLE interviews FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON interviews FOR ALL TO qmind_app
  USING (organization_id = qmind_app.current_organization_id())
  WITH CHECK (organization_id = qmind_app.current_organization_id());

ALTER TABLE answers ENABLE ROW LEVEL SECURITY;
ALTER TABLE answers FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON answers FOR ALL TO qmind_app
  USING (organization_id = qmind_app.current_organization_id())
  WITH CHECK (organization_id = qmind_app.current_organization_id());

ALTER TABLE evidences ENABLE ROW LEVEL SECURITY;
ALTER TABLE evidences FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON evidences FOR ALL TO qmind_app
  USING (organization_id = qmind_app.current_organization_id())
  WITH CHECK (organization_id = qmind_app.current_organization_id());

ALTER TABLE evidence_links ENABLE ROW LEVEL SECURITY;
ALTER TABLE evidence_links FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON evidence_links FOR ALL TO qmind_app
  USING (organization_id = qmind_app.current_organization_id())
  WITH CHECK (organization_id = qmind_app.current_organization_id());

ALTER TABLE findings ENABLE ROW LEVEL SECURITY;
ALTER TABLE findings FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON findings FOR ALL TO qmind_app
  USING (organization_id = qmind_app.current_organization_id())
  WITH CHECK (organization_id = qmind_app.current_organization_id());

ALTER TABLE finding_requirements ENABLE ROW LEVEL SECURITY;
ALTER TABLE finding_requirements FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON finding_requirements FOR ALL TO qmind_app
  USING (organization_id = qmind_app.current_organization_id())
  WITH CHECK (organization_id = qmind_app.current_organization_id());

ALTER TABLE finding_evidences ENABLE ROW LEVEL SECURITY;
ALTER TABLE finding_evidences FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON finding_evidences FOR ALL TO qmind_app
  USING (organization_id = qmind_app.current_organization_id())
  WITH CHECK (organization_id = qmind_app.current_organization_id());

ALTER TABLE maturity_assessments ENABLE ROW LEVEL SECURITY;
ALTER TABLE maturity_assessments FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON maturity_assessments FOR ALL TO qmind_app
  USING (organization_id = qmind_app.current_organization_id())
  WITH CHECK (organization_id = qmind_app.current_organization_id());

ALTER TABLE maturity_scores ENABLE ROW LEVEL SECURITY;
ALTER TABLE maturity_scores FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON maturity_scores FOR ALL TO qmind_app
  USING (organization_id = qmind_app.current_organization_id())
  WITH CHECK (organization_id = qmind_app.current_organization_id());

ALTER TABLE maturity_dimension_scores ENABLE ROW LEVEL SECURITY;
ALTER TABLE maturity_dimension_scores FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON maturity_dimension_scores FOR ALL TO qmind_app
  USING (organization_id = qmind_app.current_organization_id())
  WITH CHECK (organization_id = qmind_app.current_organization_id());

ALTER TABLE maturity_score_evidence_links ENABLE ROW LEVEL SECURITY;
ALTER TABLE maturity_score_evidence_links FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON maturity_score_evidence_links FOR ALL TO qmind_app
  USING (organization_id = qmind_app.current_organization_id())
  WITH CHECK (organization_id = qmind_app.current_organization_id());

ALTER TABLE action_plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE action_plans FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON action_plans FOR ALL TO qmind_app
  USING (organization_id = qmind_app.current_organization_id())
  WITH CHECK (organization_id = qmind_app.current_organization_id());

ALTER TABLE action_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE action_items FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON action_items FOR ALL TO qmind_app
  USING (organization_id = qmind_app.current_organization_id())
  WITH CHECK (organization_id = qmind_app.current_organization_id());

ALTER TABLE reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE reports FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON reports FOR ALL TO qmind_app
  USING (organization_id = qmind_app.current_organization_id())
  WITH CHECK (organization_id = qmind_app.current_organization_id());

ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE jobs FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON jobs FOR ALL TO qmind_app
  USING (organization_id = qmind_app.current_organization_id())
  WITH CHECK (organization_id = qmind_app.current_organization_id());

ALTER TABLE ai_suggestions ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_suggestions FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON ai_suggestions FOR ALL TO qmind_app
  USING (organization_id = qmind_app.current_organization_id())
  WITH CHECK (organization_id = qmind_app.current_organization_id());

ALTER TABLE break_glass_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE break_glass_sessions FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON break_glass_sessions FOR ALL TO qmind_app
  USING (organization_id = qmind_app.current_organization_id())
  WITH CHECK (organization_id = qmind_app.current_organization_id());

-- Audit: readable within org context; inserts allowed for app role
ALTER TABLE platform_audit_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE platform_audit_events FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_audit_select ON platform_audit_events
  FOR SELECT TO qmind_app
  USING (
    organization_id IS NULL
    OR organization_id = qmind_app.current_organization_id()
  );
CREATE POLICY tenant_audit_insert ON platform_audit_events
  FOR INSERT TO qmind_app
  WITH CHECK (
    organization_id IS NULL
    OR organization_id = qmind_app.current_organization_id()
  );

COMMENT ON SCHEMA qmind_app IS 'QMind helpers; DDL v0 freeze domain-docs-v0';
