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
