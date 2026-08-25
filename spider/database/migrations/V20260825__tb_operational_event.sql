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
