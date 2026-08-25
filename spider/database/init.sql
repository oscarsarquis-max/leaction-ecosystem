-- Spider technical store
-- Business payloads are NOT the system of record here.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ---------------------------------------------------------------------------
-- Product routes (JPA: ProductRoute -> tb_product_routes)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tb_product_routes (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  product_code    varchar(100) NOT NULL,
  name            varchar(200) NOT NULL,
  description     varchar(1000) NOT NULL DEFAULT '',
  enabled         boolean NOT NULL DEFAULT true,
  definition_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  version         integer NOT NULL DEFAULT 1,
  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_tb_product_routes_code_version UNIQUE (product_code, version)
);

CREATE INDEX IF NOT EXISTS ix_tb_product_routes_code
  ON tb_product_routes (product_code)
  WHERE enabled;

-- ---------------------------------------------------------------------------
-- Audit / orchestration trace (JPA: AuditTrace -> tb_audit_trace)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tb_audit_trace (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  correlation_id    uuid NOT NULL,
  product_code      varchar(100) NOT NULL,
  idempotency_key   varchar(200),
  status            varchar(40) NOT NULL DEFAULT 'started',
  started_at        timestamptz NOT NULL DEFAULT now(),
  finished_at       timestamptz,
  error_summary     varchar(2000),
  metadata          jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS ix_tb_audit_trace_correlation
  ON tb_audit_trace (correlation_id);

CREATE INDEX IF NOT EXISTS ix_tb_audit_trace_started
  ON tb_audit_trace (started_at DESC);

-- Seed
INSERT INTO tb_product_routes (product_code, name, description, definition_json)
SELECT
  'CONTA_DIGITAL_ONBOARDING',
  'Onboarding Conta Digital',
  'Cadastro + anùlise de crùdito (mock local)',
  '{
     "legacyEndpoint": "http://localhost:8082/api/legado/processar",
     "steps": [
       {"name": "processar_legado", "system": "legado-financeiro", "mode": "sync"}
     ]
   }'::jsonb
WHERE NOT EXISTS (
  SELECT 1 FROM tb_product_routes
  WHERE product_code = 'CONTA_DIGITAL_ONBOARDING' AND version = 1
);
-- SPIDER-PROMPT-003 ù Persistùncia tùcnica canùnica (aditiva)
-- Nùo altera tb_product_routes / tb_audit_trace

CREATE TABLE IF NOT EXISTS tb_execution_control (
  execution_id          varchar(120) PRIMARY KEY,
  context_id            varchar(120) NOT NULL,
  correlation_id        varchar(200) NOT NULL,
  plan_id               varchar(120),
  route_code            varchar(120),
  route_version         varchar(40),
  state                 varchar(40) NOT NULL,
  state_version         bigint NOT NULL DEFAULT 0,
  technical_status      varchar(40),
  started_at            timestamptz,
  completed_at          timestamptz,
  last_updated_at       timestamptz NOT NULL DEFAULT now(),
  active_wait_type      varchar(80),
  retention_class_ref   varchar(120) NOT NULL DEFAULT 'retention:technical-default@1'
);

CREATE INDEX IF NOT EXISTS ix_tb_execution_control_state_updated
  ON tb_execution_control (state, last_updated_at);

CREATE INDEX IF NOT EXISTS ix_tb_execution_control_correlation
  ON tb_execution_control (correlation_id);

CREATE TABLE IF NOT EXISTS tb_execution_plan (
  plan_id                         varchar(120) PRIMARY KEY,
  execution_id                    varchar(120) NOT NULL,
  route_code                      varchar(120) NOT NULL,
  route_version                   varchar(40) NOT NULL,
  journey_ref                     varchar(120) NOT NULL,
  created_at                      timestamptz NOT NULL,
  integrity_ref                   varchar(200) NOT NULL,
  schema_version                  varchar(20) NOT NULL DEFAULT '1.0',
  canonical_plan_representation   text NOT NULL,
  CONSTRAINT uq_tb_execution_plan_execution UNIQUE (execution_id)
);

CREATE TABLE IF NOT EXISTS tb_execution_transition (
  transition_id   varchar(120) PRIMARY KEY,
  execution_id    varchar(120) NOT NULL,
  sequence_no     bigint NOT NULL,
  previous_state  varchar(40),
  new_state       varchar(40) NOT NULL,
  reason_code     varchar(80) NOT NULL,
  occurred_at     timestamptz NOT NULL,
  attempt_id      varchar(120),
  CONSTRAINT uq_tb_execution_transition_seq UNIQUE (execution_id, sequence_no)
);

CREATE INDEX IF NOT EXISTS ix_tb_execution_transition_execution
  ON tb_execution_transition (execution_id);

CREATE TABLE IF NOT EXISTS tb_execution_result (
  result_ref              varchar(120) PRIMARY KEY,
  execution_id            varchar(120) NOT NULL,
  contract_version        varchar(40) NOT NULL,
  state                   varchar(40) NOT NULL,
  technical_status        varchar(40) NOT NULL,
  result_representation   text NOT NULL,
  content_digest          varchar(200) NOT NULL,
  created_at              timestamptz NOT NULL,
  expires_at              timestamptz NOT NULL,
  CONSTRAINT uq_tb_execution_result_execution UNIQUE (execution_id)
);

CREATE TABLE IF NOT EXISTS tb_idempotency_record (
  idempotency_record_id   varchar(120) PRIMARY KEY,
  scope_hash              varchar(128) NOT NULL,
  idempotency_key_hash    varchar(128) NOT NULL,
  request_fingerprint     varchar(128) NOT NULL,
  fingerprint_version     varchar(20) NOT NULL,
  execution_id            varchar(120) NOT NULL,
  state                   varchar(40) NOT NULL,
  result_ref              varchar(120),
  created_at              timestamptz NOT NULL,
  updated_at              timestamptz NOT NULL,
  expires_at              timestamptz NOT NULL,
  record_version          bigint NOT NULL DEFAULT 0,
  CONSTRAINT uq_tb_idempotency_scope_key UNIQUE (scope_hash, idempotency_key_hash)
);

CREATE INDEX IF NOT EXISTS ix_tb_idempotency_execution
  ON tb_idempotency_record (execution_id);
-- SPIDER-PROMPT-004 ù Steps e Attempts (aditiva)

CREATE TABLE IF NOT EXISTS tb_execution_step (
  execution_id          varchar(120) NOT NULL,
  step_id               varchar(120) NOT NULL,
  ordered_position      integer NOT NULL,
  state                 varchar(40) NOT NULL,
  state_version         bigint NOT NULL DEFAULT 0,
  active_attempt_id     varchar(120),
  output_result_ref     varchar(120),
  terminal_error_code   varchar(80),
  started_at            timestamptz,
  completed_at          timestamptz,
  last_updated_at       timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (execution_id, step_id)
);

CREATE INDEX IF NOT EXISTS ix_tb_execution_step_state
  ON tb_execution_step (execution_id, state);

CREATE TABLE IF NOT EXISTS tb_step_attempt (
  attempt_id            varchar(120) PRIMARY KEY,
  execution_id          varchar(120) NOT NULL,
  step_id               varchar(120) NOT NULL,
  attempt_number        integer NOT NULL,
  invocation_id         varchar(120) NOT NULL,
  adapter_binding_ref   varchar(200) NOT NULL,
  started_at            timestamptz NOT NULL,
  deadline              timestamptz NOT NULL,
  completed_at          timestamptz,
  state                 varchar(40) NOT NULL,
  error_category        varchar(40),
  error_code            varchar(80),
  retryable             boolean,
  certainty             varchar(40),
  evidence_refs_json    text NOT NULL DEFAULT '[]',
  CONSTRAINT uq_tb_step_attempt_number UNIQUE (execution_id, step_id, attempt_number)
);

CREATE INDEX IF NOT EXISTS ix_tb_step_attempt_execution_step
  ON tb_step_attempt (execution_id, step_id);
-- SPIDER-PROMPT-005 ù Wait e Inbox (aditiva)

CREATE TABLE IF NOT EXISTS tb_execution_wait (
  wait_id                       varchar(120) PRIMARY KEY,
  execution_id                  varchar(120) NOT NULL,
  step_id                       varchar(120) NOT NULL,
  attempt_id                    varchar(120) NOT NULL,
  wait_type                     varchar(60) NOT NULL,
  wait_policy_ref               varchar(200) NOT NULL,
  external_operation_ref        varchar(200),
  expected_signal_contract_ref  varchar(200),
  expected_source_ref           varchar(200),
  state                         varchar(40) NOT NULL,
  state_version                 bigint NOT NULL DEFAULT 0,
  created_at                    timestamptz NOT NULL,
  earliest_resume_at            timestamptz,
  expires_at                    timestamptz NOT NULL,
  received_message_id           varchar(120),
  resolved_at                   timestamptz,
  resolution_reason_code        varchar(80),
  signal_definition_ref         varchar(200),
  integrity_profile_ref         varchar(200),
  continuation_token_fingerprint varchar(128),
  continuation_token_fp_version  varchar(40),
  continuation_token_key_ref     varchar(200),
  continuation_token_key_version varchar(40),
  continuation_token_expires_at  timestamptz,
  data_protection_profile_ref    varchar(200)
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_tb_execution_wait_token_fp
  ON tb_execution_wait (continuation_token_fingerprint)
  WHERE continuation_token_fingerprint IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_tb_execution_wait_active
  ON tb_execution_wait (execution_id, step_id, attempt_id)
  WHERE state IN ('WAITING', 'SIGNALLED', 'EXPIRING', 'RESUMING');

CREATE INDEX IF NOT EXISTS ix_tb_execution_wait_expires
  ON tb_execution_wait (state, expires_at);

CREATE INDEX IF NOT EXISTS ix_tb_execution_wait_execution_step
  ON tb_execution_wait (execution_id, step_id);

CREATE TABLE IF NOT EXISTS tb_protected_signal_envelope (
  protected_envelope_id VARCHAR(120) PRIMARY KEY,
  inbox_logical_key VARCHAR(200) NOT NULL,
  data_protection_profile_ref VARCHAR(200) NOT NULL,
  algorithm VARCHAR(40) NOT NULL,
  key_ref VARCHAR(200) NOT NULL,
  key_version VARCHAR(40) NOT NULL,
  aad_version VARCHAR(20) NOT NULL,
  iv_b64 VARCHAR(64) NOT NULL,
  ciphertext_and_tag_b64 TEXT NOT NULL,
  plaintext_digest VARCHAR(128),
  ciphertext_digest VARCHAR(128),
  plaintext_size INTEGER NOT NULL,
  state VARCHAR(40) NOT NULL,
  created_at TIMESTAMPTZ NOT NULL,
  consumed_at TIMESTAMPTZ,
  eligible_for_deletion_at TIMESTAMPTZ,
  lease_owner VARCHAR(120),
  lease_until TIMESTAMPTZ,
  optimistic_version BIGINT NOT NULL DEFAULT 0,
  CONSTRAINT uq_tb_protected_signal_envelope_inbox UNIQUE (inbox_logical_key)
);

CREATE INDEX IF NOT EXISTS ix_tb_protected_signal_envelope_state
  ON tb_protected_signal_envelope (state);

CREATE TABLE IF NOT EXISTS tb_inbox_message (
  source_ref                    varchar(200) NOT NULL,
  message_id                    varchar(120) NOT NULL,
  binding_ref                   varchar(200) NOT NULL,
  contract_ref                  varchar(200) NOT NULL,
  deduplication_key_hash        varchar(128) NOT NULL,
  message_fingerprint           varchar(128) NOT NULL,
  fingerprint_version           varchar(20) NOT NULL,
  execution_id                  varchar(120),
  step_id                       varchar(120),
  external_operation_ref        varchar(200),
  received_at                   timestamptz NOT NULL,
  validation_state              varchar(40) NOT NULL,
  processing_state              varchar(40) NOT NULL,
  payload_ref                   varchar(120),
  error_code                    varchar(80),
  expires_at                    timestamptz NOT NULL,
  wait_id                       varchar(120),
  signal_definition_ref         varchar(200),
  payload_digest                varchar(128),
  application_attempt_count     integer DEFAULT 0,
  next_attempt_at               timestamptz,
  lease_owner                   varchar(120),
  lease_until                   timestamptz,
  optimistic_version            bigint DEFAULT 0,
  verified_at                   timestamptz,
  applied_at                    timestamptz,
  PRIMARY KEY (source_ref, message_id)
);

CREATE INDEX IF NOT EXISTS ix_tb_inbox_processing
  ON tb_inbox_message (processing_state, received_at);

CREATE INDEX IF NOT EXISTS ix_tb_inbox_message_apply_due
  ON tb_inbox_message (processing_state, next_attempt_at);

CREATE INDEX IF NOT EXISTS ix_tb_inbox_message_lease
  ON tb_inbox_message (lease_until);

CREATE INDEX IF NOT EXISTS ix_tb_inbox_message_wait
  ON tb_inbox_message (wait_id);

CREATE INDEX IF NOT EXISTS ix_tb_inbox_message_execution
  ON tb_inbox_message (execution_id);
-- SPIDER-PROMPT-006 ù ownership tùcnico de execuùùo (aditiva)

ALTER TABLE tb_execution_control
  ADD COLUMN IF NOT EXISTS owner_principal_ref varchar(200);

CREATE INDEX IF NOT EXISTS ix_tb_execution_control_owner
  ON tb_execution_control (owner_principal_ref)
  WHERE owner_principal_ref IS NOT NULL;
-- SPIDER-PROMPT-007 ù Callback context, Outbox e delivery attempts

CREATE TABLE IF NOT EXISTS tb_execution_callback_context (
  execution_id              varchar(120) PRIMARY KEY,
  callback_definition_ref   varchar(200) NOT NULL,
  binding_ref               varchar(200) NOT NULL,
  callback_contract_ref     varchar(200) NOT NULL,
  security_profile_ref      varchar(200) NOT NULL,
  delivery_policy_ref       varchar(200) NOT NULL,
  projection_ref            varchar(120) NOT NULL,
  authorized_originator_ref varchar(200) NOT NULL,
  integrity_ref             varchar(200) NOT NULL,
  fixed_at                  timestamptz  NOT NULL
);

CREATE TABLE IF NOT EXISTS tb_callback_outbox (
  outbox_id                     varchar(120) PRIMARY KEY,
  logical_callback_id           varchar(160) NOT NULL,
  execution_id                  varchar(120) NOT NULL,
  callback_definition_ref       varchar(200) NOT NULL,
  binding_ref                   varchar(200) NOT NULL,
  contract_ref                  varchar(200) NOT NULL,
  security_profile_ref          varchar(200) NOT NULL,
  projection_ref                varchar(120) NOT NULL,
  result_ref                    varchar(120) NOT NULL,
  logical_idempotency_key_hash  varchar(128) NOT NULL,
  state                         varchar(40)  NOT NULL,
  created_at                    timestamptz  NOT NULL,
  next_attempt_at               timestamptz  NOT NULL,
  expires_at                    timestamptz  NOT NULL,
  attempt_count                 integer      NOT NULL DEFAULT 0,
  state_version                 bigint       NOT NULL DEFAULT 0,
  last_error_code               varchar(80),
  CONSTRAINT uq_tb_callback_outbox_logical UNIQUE (logical_callback_id),
  CONSTRAINT uq_tb_callback_outbox_execution UNIQUE (execution_id)
);

CREATE INDEX IF NOT EXISTS ix_tb_callback_outbox_ready
  ON tb_callback_outbox (state, next_attempt_at);

CREATE TABLE IF NOT EXISTS tb_callback_delivery_attempt (
  delivery_id          varchar(120) PRIMARY KEY,
  outbox_id            varchar(120) NOT NULL,
  logical_callback_id  varchar(160) NOT NULL,
  attempt_number       integer      NOT NULL,
  binding_ref          varchar(200) NOT NULL,
  started_at           timestamptz  NOT NULL,
  deadline             timestamptz  NOT NULL,
  completed_at         timestamptz,
  state                varchar(40)  NOT NULL,
  certainty            varchar(40)  NOT NULL,
  error_category       varchar(40),
  error_code           varchar(80),
  retryable            boolean,
  CONSTRAINT uq_tb_callback_delivery_attempt UNIQUE (outbox_id, attempt_number)
);

CREATE INDEX IF NOT EXISTS ix_tb_callback_delivery_attempt_outbox
  ON tb_callback_delivery_attempt (outbox_id);

-- SPIDER-PROMPT-008 ù Reconciliaùùo de callback

ALTER TABLE tb_execution_callback_context
  ADD COLUMN IF NOT EXISTS confirmation_mode varchar(60) NOT NULL DEFAULT 'SYNCHRONOUS_ACK_IS_FINAL';

ALTER TABLE tb_execution_callback_context
  ADD COLUMN IF NOT EXISTS status_query_binding_ref varchar(200);

ALTER TABLE tb_execution_callback_context
  ADD COLUMN IF NOT EXISTS reconciliation_policy_ref varchar(200);

ALTER TABLE tb_execution_callback_context
  ADD COLUMN IF NOT EXISTS redelivery_safety varchar(60) NOT NULL DEFAULT 'NEVER_AUTOMATIC';

ALTER TABLE tb_execution_callback_context
  ADD COLUMN IF NOT EXISTS delivery_key_hash varchar(128) NOT NULL DEFAULT 'legacy';

ALTER TABLE tb_callback_outbox
  ADD COLUMN IF NOT EXISTS lease_owner varchar(120);

ALTER TABLE tb_callback_outbox
  ADD COLUMN IF NOT EXISTS lease_until timestamptz;

ALTER TABLE tb_callback_outbox
  ADD COLUMN IF NOT EXISTS confirmation_state varchar(60);

CREATE TABLE IF NOT EXISTS tb_callback_reconciliation (
  reconciliation_id      varchar(120) PRIMARY KEY,
  outbox_id              varchar(120) NOT NULL,
  execution_id           varchar(120) NOT NULL,
  delivery_key_hash      varchar(128) NOT NULL,
  policy_ref             varchar(200) NOT NULL,
  state                  varchar(40)  NOT NULL,
  query_count            integer      NOT NULL DEFAULT 0,
  next_query_at          timestamptz  NOT NULL,
  started_at             timestamptz  NOT NULL,
  expires_at             timestamptz  NOT NULL,
  last_disposition       varchar(60),
  external_delivery_ref  varchar(200),
  lease_owner            varchar(120),
  lease_until            timestamptz,
  version                bigint       NOT NULL DEFAULT 0,
  created_at             timestamptz  NOT NULL,
  updated_at             timestamptz  NOT NULL,
  CONSTRAINT uq_tb_callback_reconciliation_outbox UNIQUE (outbox_id)
);

CREATE INDEX IF NOT EXISTS ix_tb_callback_reconciliation_due
  ON tb_callback_reconciliation (state, next_query_at);

CREATE INDEX IF NOT EXISTS ix_tb_callback_reconciliation_lease
  ON tb_callback_reconciliation (lease_until);

CREATE INDEX IF NOT EXISTS ix_tb_callback_reconciliation_execution
  ON tb_callback_reconciliation (execution_id);

CREATE TABLE IF NOT EXISTS tb_callback_reconciliation_attempt (
  reconciliation_attempt_id varchar(120) PRIMARY KEY,
  reconciliation_id         varchar(120) NOT NULL,
  attempt_number            integer      NOT NULL,
  started_at                timestamptz  NOT NULL,
  completed_at              timestamptz,
  disposition               varchar(60),
  safe_status_code          varchar(40),
  error_code                varchar(80),
  error_category            varchar(40),
  next_query_at             timestamptz,
  evidence_ref              varchar(120),
  trace_correlation_id      varchar(200),
  CONSTRAINT uq_tb_callback_reconciliation_attempt UNIQUE (reconciliation_id, attempt_number)
);

CREATE INDEX IF NOT EXISTS ix_tb_callback_reconciliation_attempt_rec
  ON tb_callback_reconciliation_attempt (reconciliation_id, started_at);

-- SPIDER-PROMPT-009 ù Replay Guard e proof metadata

CREATE TABLE IF NOT EXISTS tb_security_replay_guard (
  reservation_id         varchar(120) PRIMARY KEY,
  replay_scope_hash      varchar(128) NOT NULL,
  nonce_hash             varchar(128) NOT NULL,
  message_fingerprint    varchar(200) NOT NULL,
  fingerprint_version    varchar(40)  NOT NULL,
  key_ref                varchar(200),
  key_version            varchar(40),
  integrity_profile_ref  varchar(200),
  first_seen_at          timestamptz  NOT NULL,
  expires_at             timestamptz  NOT NULL,
  status                 varchar(40)  NOT NULL,
  version                bigint       NOT NULL DEFAULT 0,
  created_at             timestamptz  NOT NULL,
  updated_at             timestamptz  NOT NULL,
  CONSTRAINT uq_tb_security_replay_guard_scope_nonce
    UNIQUE (replay_scope_hash, nonce_hash, fingerprint_version)
);

CREATE INDEX IF NOT EXISTS ix_tb_security_replay_guard_expiry
  ON tb_security_replay_guard (expires_at, status);

CREATE INDEX IF NOT EXISTS ix_tb_security_replay_guard_profile
  ON tb_security_replay_guard (integrity_profile_ref, key_version);

ALTER TABLE tb_callback_delivery_attempt
  ADD COLUMN IF NOT EXISTS proof_profile_ref varchar(200);

ALTER TABLE tb_callback_delivery_attempt
  ADD COLUMN IF NOT EXISTS proof_key_version varchar(40);

ALTER TABLE tb_callback_delivery_attempt
  ADD COLUMN IF NOT EXISTS proof_mac_fingerprint varchar(32);

ALTER TABLE tb_callback_reconciliation_attempt
  ADD COLUMN IF NOT EXISTS proof_profile_ref varchar(200);

ALTER TABLE tb_callback_reconciliation_attempt
  ADD COLUMN IF NOT EXISTS proof_key_version varchar(40);

ALTER TABLE tb_callback_reconciliation_attempt
  ADD COLUMN IF NOT EXISTS proof_mac_fingerprint varchar(32);

ALTER TABLE tb_execution_callback_context
  ADD COLUMN IF NOT EXISTS integrity_profile_ref varchar(200);
-- SPIDER-PROMPT-010 ù Control Plane (artefatos, bundles, snapshots, ativaùùo)

CREATE TABLE IF NOT EXISTS tb_governance_artifact (
  artifact_id            varchar(120) PRIMARY KEY,
  artifact_type          varchar(80)  NOT NULL,
  artifact_code          varchar(120) NOT NULL,
  artifact_version       varchar(40)  NOT NULL,
  schema_version         varchar(40)  NOT NULL,
  canonical_content      text         NOT NULL,
  content_digest         varchar(128) NOT NULL,
  lifecycle_state        varchar(40)  NOT NULL,
  created_by_principal   varchar(200) NOT NULL,
  created_at             timestamptz  NOT NULL,
  validated_at           timestamptz,
  published_at           timestamptz,
  deprecated_at          timestamptz,
  retired_at             timestamptz,
  revoked_at             timestamptz,
  lifecycle_reason_code  varchar(80),
  version                bigint       NOT NULL DEFAULT 0,
  CONSTRAINT uq_tb_governance_artifact_ref UNIQUE (artifact_type, artifact_code, artifact_version)
);

CREATE TABLE IF NOT EXISTS tb_governance_bundle (
  bundle_id              varchar(120) PRIMARY KEY,
  bundle_code            varchar(120) NOT NULL,
  bundle_version         varchar(40)  NOT NULL,
  governance_scope       varchar(64)  NOT NULL,
  bundle_digest          varchar(128) NOT NULL,
  lifecycle_state        varchar(40)  NOT NULL,
  validation_report_ref  varchar(120),
  created_by_principal   varchar(200) NOT NULL,
  created_at             timestamptz  NOT NULL,
  validated_at           timestamptz,
  published_at           timestamptz,
  deprecated_at          timestamptz,
  retired_at             timestamptz,
  revoked_at             timestamptz,
  reason_code            varchar(80),
  version                bigint       NOT NULL DEFAULT 0,
  CONSTRAINT uq_tb_governance_bundle_ref UNIQUE (bundle_code, bundle_version, governance_scope)
);

CREATE TABLE IF NOT EXISTS tb_governance_bundle_artifact (
  bundle_id        varchar(120) NOT NULL,
  artifact_type    varchar(80)  NOT NULL,
  artifact_code    varchar(120) NOT NULL,
  artifact_version varchar(40)  NOT NULL,
  ordinal_pos      integer      NOT NULL,
  CONSTRAINT uq_tb_governance_bundle_artifact UNIQUE (bundle_id, artifact_type, artifact_code, artifact_version)
);

CREATE TABLE IF NOT EXISTS tb_governance_validation_report (
  report_id              varchar(120) PRIMARY KEY,
  bundle_id              varchar(120) NOT NULL,
  validator_version      varchar(40)  NOT NULL,
  passed                 boolean      NOT NULL,
  error_count            integer      NOT NULL,
  warning_count          integer      NOT NULL,
  info_count             integer      NOT NULL,
  findings_json          text,
  created_at             timestamptz  NOT NULL,
  created_by_principal   varchar(200) NOT NULL
);

CREATE TABLE IF NOT EXISTS tb_governance_snapshot (
  snapshot_id            varchar(120) PRIMARY KEY,
  bundle_ref             varchar(200) NOT NULL,
  bundle_digest          varchar(128) NOT NULL,
  governance_scope       varchar(64)  NOT NULL,
  snapshot_digest        varchar(128) NOT NULL,
  compiled_at            timestamptz  NOT NULL,
  snapshot_json          text,
  CONSTRAINT uq_tb_governance_snapshot_bundle UNIQUE (bundle_ref, bundle_digest)
);

CREATE TABLE IF NOT EXISTS tb_governance_activation (
  governance_scope         varchar(64)  PRIMARY KEY,
  active_snapshot_id       varchar(120) NOT NULL,
  previous_snapshot_id     varchar(120),
  activation_sequence      bigint       NOT NULL,
  activated_at             timestamptz  NOT NULL,
  activated_by_principal   varchar(200) NOT NULL,
  reason_code              varchar(80)  NOT NULL,
  version                  bigint       NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS tb_governance_audit_event (
  event_id                 varchar(120) PRIMARY KEY,
  command_type             varchar(80)  NOT NULL,
  target_type              varchar(80),
  target_ref               varchar(200),
  actor_principal_ref      varchar(200) NOT NULL,
  outcome                  varchar(40)  NOT NULL,
  reason_code              varchar(80),
  previous_lifecycle_state varchar(40),
  new_lifecycle_state      varchar(40),
  occurred_at              timestamptz  NOT NULL,
  correlation_id           varchar(200)
);

CREATE TABLE IF NOT EXISTS tb_execution_governance_fixation (
  execution_id                   varchar(120) PRIMARY KEY,
  governance_snapshot_id         varchar(120) NOT NULL,
  governance_bundle_ref          varchar(200) NOT NULL,
  governance_bundle_digest       varchar(128) NOT NULL,
  governance_activation_sequence bigint       NOT NULL,
  fixed_at                       timestamptz  NOT NULL
);

-- SPIDER-PROMPT-010 ù JPA runtime persistence and activation history

CREATE TABLE IF NOT EXISTS tb_governance_activation_history (
  history_id               bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  governance_scope         varchar(64)  NOT NULL,
  activation_sequence      bigint       NOT NULL,
  active_snapshot_id       varchar(120) NOT NULL,
  previous_snapshot_id     varchar(120),
  activated_at             timestamptz  NOT NULL,
  activated_by_principal   varchar(200) NOT NULL,
  reason_code              varchar(80)  NOT NULL,
  CONSTRAINT uq_tb_governance_activation_history_scope_sequence
    UNIQUE (governance_scope, activation_sequence)
);

ALTER TABLE tb_execution_governance_fixation
  ADD COLUMN IF NOT EXISTS governance_mode varchar(40);

ALTER TABLE tb_execution_governance_fixation
  ADD COLUMN IF NOT EXISTS governance_scope varchar(64);

ALTER TABLE tb_execution_governance_fixation
  ADD COLUMN IF NOT EXISTS snapshot_id varchar(120);

ALTER TABLE tb_execution_governance_fixation
  ADD COLUMN IF NOT EXISTS bundle_code varchar(120);

ALTER TABLE tb_execution_governance_fixation
  ADD COLUMN IF NOT EXISTS bundle_version varchar(40);

ALTER TABLE tb_execution_governance_fixation
  ADD COLUMN IF NOT EXISTS bundle_digest varchar(128);

ALTER TABLE tb_execution_governance_fixation
  ADD COLUMN IF NOT EXISTS snapshot_digest varchar(128);

ALTER TABLE tb_execution_governance_fixation
  ADD COLUMN IF NOT EXISTS activation_sequence bigint;

UPDATE tb_execution_governance_fixation
SET governance_mode = 'CONTROL_PLANE'
WHERE governance_mode IS NULL;

UPDATE tb_execution_governance_fixation
SET governance_scope = 'DEFAULT'
WHERE governance_scope IS NULL;

UPDATE tb_execution_governance_fixation
SET snapshot_id = governance_snapshot_id
WHERE snapshot_id IS NULL;

UPDATE tb_execution_governance_fixation
SET bundle_digest = governance_bundle_digest
WHERE bundle_digest IS NULL;

UPDATE tb_execution_governance_fixation
SET activation_sequence = governance_activation_sequence
WHERE activation_sequence IS NULL;

-- Legacy columns remain for rollback compatibility, but cannot stay mandatory once JPA writes
-- the expanded representation.
ALTER TABLE tb_execution_governance_fixation
  ALTER COLUMN governance_snapshot_id DROP NOT NULL;

ALTER TABLE tb_execution_governance_fixation
  ALTER COLUMN governance_bundle_ref DROP NOT NULL;

ALTER TABLE tb_execution_governance_fixation
  ALTER COLUMN governance_bundle_digest DROP NOT NULL;

ALTER TABLE tb_execution_governance_fixation
  ALTER COLUMN governance_activation_sequence DROP NOT NULL;

-- SPIDER-PROMPT-016 - operational events
CREATE TABLE IF NOT EXISTS tb_operational_event (
  event_id       varchar(120) PRIMARY KEY,
  schema_version integer      NOT NULL,
  event_type     varchar(80)  NOT NULL,
  category       varchar(40)  NOT NULL,
  occurred_at    timestamptz  NOT NULL,
  execution_id   varchar(120) NOT NULL,
  interaction_id varchar(120),
  correlation_id varchar(200),
  source         varchar(120) NOT NULL,
  outcome        varchar(40),
  duration_ms    bigint,
  metadata_json  text         NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_operational_event_execution_time
  ON tb_operational_event (execution_id, occurred_at, event_id);

CREATE INDEX IF NOT EXISTS idx_operational_event_type
  ON tb_operational_event (event_type);

CREATE INDEX IF NOT EXISTS idx_operational_event_category
  ON tb_operational_event (category);

-- SPIDER-PROMPT-019 - durable worker runtime (schedule/claim/lease/fencing/heartbeat/drain)
-- Boundary: SIMULATED_INFRASTRUCTURE. Integrations remain MOCK_ONLY.
CREATE TABLE IF NOT EXISTS tb_runtime_worker_instance (
  worker_id           varchar(120) PRIMARY KEY,
  runtime_instance_id varchar(120) NOT NULL,
  worker_type         varchar(60)  NOT NULL,
  status              varchar(40)  NOT NULL,
  started_at          timestamptz,
  last_heartbeat_at   timestamptz,
  drain_requested_at  timestamptz,
  stopped_at          timestamptz,
  current_claims      integer      NOT NULL DEFAULT 0,
  processed_count     bigint       NOT NULL DEFAULT 0,
  failure_count       bigint       NOT NULL DEFAULT 0,
  version             bigint       NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_runtime_worker_instance_status
  ON tb_runtime_worker_instance (status);

CREATE INDEX IF NOT EXISTS idx_runtime_worker_instance_type_status
  ON tb_runtime_worker_instance (worker_type, status);

CREATE INDEX IF NOT EXISTS idx_runtime_worker_instance_heartbeat
  ON tb_runtime_worker_instance (last_heartbeat_at);

CREATE TABLE IF NOT EXISTS tb_runtime_schedule (
  schedule_code        varchar(160) PRIMARY KEY,
  schedule_def_version varchar(20)  NOT NULL,
  worker_type          varchar(60)  NOT NULL,
  enabled              boolean      NOT NULL,
  interval_seconds     bigint       NOT NULL,
  next_eligible_at     timestamptz  NOT NULL,
  last_started_at      timestamptz,
  last_completed_at    timestamptz,
  last_outcome         varchar(40),
  owner_worker_id      varchar(120),
  lease_until          timestamptz,
  fencing_token        bigint       NOT NULL DEFAULT 0,
  version              bigint       NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_runtime_schedule_eligible
  ON tb_runtime_schedule (enabled, next_eligible_at);

CREATE INDEX IF NOT EXISTS idx_runtime_schedule_owner
  ON tb_runtime_schedule (owner_worker_id);

CREATE INDEX IF NOT EXISTS idx_runtime_schedule_worker_type
  ON tb_runtime_schedule (worker_type);
