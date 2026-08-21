-- SPIDER-PROMPT-010 — Control Plane (artefatos, bundles, snapshots, ativação)

CREATE TABLE IF NOT EXISTS tb_governance_artifact (
  artifact_id            varchar(120) PRIMARY KEY,
  artifact_type          varchar(80)  NOT NULL,
  artifact_code          varchar(120) NOT NULL,
  artifact_version       varchar(40)  NOT NULL,
  schema_version         varchar(40)  NOT NULL,
  canonical_content      text         NOT NULL,
  content_digest         varchar(128) NOT NULL,
  lifecycle_state        varchar(40)  NOT NULL,
  created_by_principal   varchar(200) NOT NULL,
  created_at             timestamptz  NOT NULL,
  validated_at           timestamptz,
  published_at           timestamptz,
  deprecated_at          timestamptz,
  retired_at             timestamptz,
  revoked_at             timestamptz,
  lifecycle_reason_code  varchar(80),
  version                bigint       NOT NULL DEFAULT 0,
  CONSTRAINT uq_tb_governance_artifact_ref UNIQUE (artifact_type, artifact_code, artifact_version)
);

CREATE TABLE IF NOT EXISTS tb_governance_bundle (
  bundle_id              varchar(120) PRIMARY KEY,
  bundle_code            varchar(120) NOT NULL,
  bundle_version         varchar(40)  NOT NULL,
  governance_scope       varchar(64)  NOT NULL,
  bundle_digest          varchar(128) NOT NULL,
  lifecycle_state        varchar(40)  NOT NULL,
  validation_report_ref  varchar(120),
  created_by_principal   varchar(200) NOT NULL,
  created_at             timestamptz  NOT NULL,
  validated_at           timestamptz,
  published_at           timestamptz,
  deprecated_at          timestamptz,
  retired_at             timestamptz,
  revoked_at             timestamptz,
  reason_code            varchar(80),
  version                bigint       NOT NULL DEFAULT 0,
  CONSTRAINT uq_tb_governance_bundle_ref UNIQUE (bundle_code, bundle_version, governance_scope)
);

CREATE TABLE IF NOT EXISTS tb_governance_bundle_artifact (
  bundle_id        varchar(120) NOT NULL,
  artifact_type    varchar(80)  NOT NULL,
  artifact_code    varchar(120) NOT NULL,
  artifact_version varchar(40)  NOT NULL,
  ordinal_pos      integer      NOT NULL,
  CONSTRAINT uq_tb_governance_bundle_artifact UNIQUE (bundle_id, artifact_type, artifact_code, artifact_version)
);

CREATE TABLE IF NOT EXISTS tb_governance_validation_report (
  report_id              varchar(120) PRIMARY KEY,
  bundle_id              varchar(120) NOT NULL,
  validator_version      varchar(40)  NOT NULL,
  passed                 boolean      NOT NULL,
  error_count            integer      NOT NULL,
  warning_count          integer      NOT NULL,
  info_count             integer      NOT NULL,
  findings_json          text,
  created_at             timestamptz  NOT NULL,
  created_by_principal   varchar(200) NOT NULL
);

CREATE TABLE IF NOT EXISTS tb_governance_snapshot (
  snapshot_id            varchar(120) PRIMARY KEY,
  bundle_ref             varchar(200) NOT NULL,
  bundle_digest          varchar(128) NOT NULL,
  governance_scope       varchar(64)  NOT NULL,
  snapshot_digest        varchar(128) NOT NULL,
  compiled_at            timestamptz  NOT NULL,
  snapshot_json          text,
  CONSTRAINT uq_tb_governance_snapshot_bundle UNIQUE (bundle_ref, bundle_digest)
);

CREATE TABLE IF NOT EXISTS tb_governance_activation (
  governance_scope         varchar(64)  PRIMARY KEY,
  active_snapshot_id       varchar(120) NOT NULL,
  previous_snapshot_id     varchar(120),
  activation_sequence      bigint       NOT NULL,
  activated_at             timestamptz  NOT NULL,
  activated_by_principal   varchar(200) NOT NULL,
  reason_code              varchar(80)  NOT NULL,
  version                  bigint       NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS tb_governance_audit_event (
  event_id                 varchar(120) PRIMARY KEY,
  command_type             varchar(80)  NOT NULL,
  target_type              varchar(80),
  target_ref               varchar(200),
  actor_principal_ref      varchar(200) NOT NULL,
  outcome                  varchar(40)  NOT NULL,
  reason_code              varchar(80),
  previous_lifecycle_state varchar(40),
  new_lifecycle_state      varchar(40),
  occurred_at              timestamptz  NOT NULL,
  correlation_id           varchar(200)
);

CREATE TABLE IF NOT EXISTS tb_execution_governance_fixation (
  execution_id                   varchar(120) PRIMARY KEY,
  governance_snapshot_id         varchar(120) NOT NULL,
  governance_bundle_ref          varchar(200) NOT NULL,
  governance_bundle_digest       varchar(128) NOT NULL,
  governance_activation_sequence bigint       NOT NULL,
  fixed_at                       timestamptz  NOT NULL
);
