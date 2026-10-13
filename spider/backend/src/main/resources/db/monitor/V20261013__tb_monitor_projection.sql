CREATE TABLE IF NOT EXISTS tb_monitor_projection (
  record_id           varchar(200) PRIMARY KEY,
  kind                varchar(40)  NOT NULL,
  satellite_id        varchar(80),
  satellite_role      varchar(40),
  origin              varchar(80),
  message_id          varchar(120),
  correlation_id      varchar(200),
  execution_id        varchar(120),
  external_ref        varchar(120),
  capability          varchar(80),
  contract_version    varchar(20),
  company_id          varchar(80),
  environment         varchar(40),
  technical_state     varchar(80),
  commercial_state    varchar(80),
  financial_state     varchar(80),
  credit_state        varchar(80),
  current_component   varchar(80),
  objective           varchar(120),
  created_at          timestamp    NOT NULL,
  updated_at          timestamp    NOT NULL,
  last_synced_at      timestamp,
  discovery_origin    varchar(40),
  event_key           varchar(200),
  projection_version  integer      NOT NULL,
  retention_until     timestamp    NOT NULL,
  sync_run_id         varchar(80),
  related_sync_id     varchar(200),
  related_payment_id  varchar(200),
  related_interaction_id varchar(200),
  pages_consulted     integer,
  found_count         integer,
  new_count           integer,
  updated_count       integer,
  ignored_count       integer,
  failed_count        integer
);

CREATE INDEX IF NOT EXISTS idx_monitor_projection_updated
  ON tb_monitor_projection (updated_at, record_id);

CREATE INDEX IF NOT EXISTS idx_monitor_projection_origin
  ON tb_monitor_projection (origin, kind);

CREATE INDEX IF NOT EXISTS idx_monitor_projection_company
  ON tb_monitor_projection (company_id, updated_at);

CREATE INDEX IF NOT EXISTS idx_monitor_projection_external
  ON tb_monitor_projection (external_ref);

CREATE INDEX IF NOT EXISTS idx_monitor_projection_retention
  ON tb_monitor_projection (retention_until);

CREATE INDEX IF NOT EXISTS idx_monitor_projection_sync
  ON tb_monitor_projection (sync_run_id);
