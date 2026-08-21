-- SPIDER-PROMPT-003 — Persistência técnica canônica (aditiva)
-- Não altera tb_product_routes / tb_audit_trace

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
