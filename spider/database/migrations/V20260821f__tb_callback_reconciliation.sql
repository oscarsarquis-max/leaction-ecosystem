-- SPIDER-PROMPT-008 — Reconciliação de callback, confirmação e lease

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
