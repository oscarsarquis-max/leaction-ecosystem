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
  current_component   varchar(80),
  objective           varchar(120),
  created_at          timestamptz  NOT NULL,
  updated_at          timestamptz  NOT NULL,
  last_synced_at      timestamptz,
  discovery_origin    varchar(40),
  event_key           varchar(200),
  projection_version  integer      NOT NULL,
  retention_until     timestamptz  NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_monitor_projection_updated
  ON tb_monitor_projection (updated_at desc, record_id desc);

CREATE INDEX IF NOT EXISTS idx_monitor_projection_origin
  ON tb_monitor_projection (origin, kind);

CREATE INDEX IF NOT EXISTS idx_monitor_projection_company
  ON tb_monitor_projection (company_id, updated_at desc);

CREATE INDEX IF NOT EXISTS idx_monitor_projection_external
  ON tb_monitor_projection (external_ref);
