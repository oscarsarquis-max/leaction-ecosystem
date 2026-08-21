-- SPIDER-PROMPT-005 — Wait e Inbox (aditiva)

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
  resolution_reason_code        varchar(80)
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_tb_execution_wait_active
  ON tb_execution_wait (execution_id, step_id, attempt_id)
  WHERE state IN ('WAITING', 'SIGNALLED', 'EXPIRING', 'RESUMING');

CREATE INDEX IF NOT EXISTS ix_tb_execution_wait_expires
  ON tb_execution_wait (state, expires_at);

CREATE INDEX IF NOT EXISTS ix_tb_execution_wait_execution_step
  ON tb_execution_wait (execution_id, step_id);

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
  PRIMARY KEY (source_ref, message_id)
);

CREATE INDEX IF NOT EXISTS ix_tb_inbox_processing
  ON tb_inbox_message (processing_state, received_at);
