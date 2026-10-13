CREATE TABLE IF NOT EXISTS tb_monitor_journey_stage (
  record_id           varchar(200) NOT NULL,
  stage_id            varchar(80)  NOT NULL,
  stage_type          varchar(80)  NOT NULL,
  sort_order          integer      NOT NULL,
  state               varchar(40)  NOT NULL,
  component           varchar(80),
  executor            varchar(80),
  occurred_at         timestamp    NOT NULL,
  completed_at        timestamp,
  title               varchar(160) NOT NULL,
  definition_key      varchar(80)  NOT NULL,
  decision            varchar(200),
  event_type          varchar(80),
  evidence_json       varchar(4000),
  attempt             integer,
  projection_version  integer      NOT NULL DEFAULT 2,
  PRIMARY KEY (record_id, stage_id),
  CONSTRAINT fk_monitor_journey_record
    FOREIGN KEY (record_id) REFERENCES tb_monitor_projection (record_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_monitor_journey_record_order
  ON tb_monitor_journey_stage (record_id, sort_order);

CREATE INDEX IF NOT EXISTS idx_monitor_journey_occurred
  ON tb_monitor_journey_stage (record_id, occurred_at);
