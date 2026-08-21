-- SPIDER-PROMPT-004 — Steps e Attempts (aditiva)

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
