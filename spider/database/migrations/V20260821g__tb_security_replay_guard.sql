-- SPIDER-PROMPT-009 — Replay Guard e metadata de proof segura

CREATE TABLE IF NOT EXISTS tb_security_replay_guard (
  reservation_id         varchar(120) PRIMARY KEY,
  replay_scope_hash      varchar(128) NOT NULL,
  nonce_hash             varchar(128) NOT NULL,
  message_fingerprint    varchar(200) NOT NULL,
  fingerprint_version    varchar(40)  NOT NULL,
  key_ref                varchar(200),
  key_version            varchar(40),
  integrity_profile_ref  varchar(200),
  first_seen_at          timestamptz  NOT NULL,
  expires_at             timestamptz  NOT NULL,
  status                 varchar(40)  NOT NULL,
  version                bigint       NOT NULL DEFAULT 0,
  created_at             timestamptz  NOT NULL,
  updated_at             timestamptz  NOT NULL,
  CONSTRAINT uq_tb_security_replay_guard_scope_nonce
    UNIQUE (replay_scope_hash, nonce_hash, fingerprint_version)
);

CREATE INDEX IF NOT EXISTS ix_tb_security_replay_guard_expiry
  ON tb_security_replay_guard (expires_at, status);

CREATE INDEX IF NOT EXISTS ix_tb_security_replay_guard_profile
  ON tb_security_replay_guard (integrity_profile_ref, key_version);

ALTER TABLE tb_callback_delivery_attempt
  ADD COLUMN IF NOT EXISTS proof_profile_ref varchar(200);

ALTER TABLE tb_callback_delivery_attempt
  ADD COLUMN IF NOT EXISTS proof_key_version varchar(40);

ALTER TABLE tb_callback_delivery_attempt
  ADD COLUMN IF NOT EXISTS proof_mac_fingerprint varchar(32);

ALTER TABLE tb_callback_reconciliation_attempt
  ADD COLUMN IF NOT EXISTS proof_profile_ref varchar(200);

ALTER TABLE tb_callback_reconciliation_attempt
  ADD COLUMN IF NOT EXISTS proof_key_version varchar(40);

ALTER TABLE tb_callback_reconciliation_attempt
  ADD COLUMN IF NOT EXISTS proof_mac_fingerprint varchar(32);

ALTER TABLE tb_execution_callback_context
  ADD COLUMN IF NOT EXISTS integrity_profile_ref varchar(200);
