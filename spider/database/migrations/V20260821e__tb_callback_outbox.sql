-- SPIDER-PROMPT-007 — Callback context, Outbox e delivery attempts

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
