-- SPIDER-PROMPT-014: continuation token fingerprint + protected signal envelope
ALTER TABLE tb_execution_wait ADD COLUMN IF NOT EXISTS continuation_token_fingerprint VARCHAR(128);
ALTER TABLE tb_execution_wait ADD COLUMN IF NOT EXISTS continuation_token_fp_version VARCHAR(40);
ALTER TABLE tb_execution_wait ADD COLUMN IF NOT EXISTS continuation_token_key_ref VARCHAR(200);
ALTER TABLE tb_execution_wait ADD COLUMN IF NOT EXISTS continuation_token_key_version VARCHAR(40);
ALTER TABLE tb_execution_wait ADD COLUMN IF NOT EXISTS continuation_token_expires_at TIMESTAMPTZ;
ALTER TABLE tb_execution_wait ADD COLUMN IF NOT EXISTS data_protection_profile_ref VARCHAR(200);

CREATE UNIQUE INDEX IF NOT EXISTS uq_tb_execution_wait_token_fp
  ON tb_execution_wait (continuation_token_fingerprint)
  WHERE continuation_token_fingerprint IS NOT NULL;

CREATE TABLE IF NOT EXISTS tb_protected_signal_envelope (
  protected_envelope_id VARCHAR(120) PRIMARY KEY,
  inbox_logical_key VARCHAR(200) NOT NULL,
  data_protection_profile_ref VARCHAR(200) NOT NULL,
  algorithm VARCHAR(40) NOT NULL,
  key_ref VARCHAR(200) NOT NULL,
  key_version VARCHAR(40) NOT NULL,
  aad_version VARCHAR(20) NOT NULL,
  iv_b64 VARCHAR(64) NOT NULL,
  ciphertext_and_tag_b64 TEXT NOT NULL,
  plaintext_digest VARCHAR(128),
  ciphertext_digest VARCHAR(128),
  plaintext_size INTEGER NOT NULL,
  state VARCHAR(40) NOT NULL,
  created_at TIMESTAMPTZ NOT NULL,
  consumed_at TIMESTAMPTZ,
  eligible_for_deletion_at TIMESTAMPTZ,
  lease_owner VARCHAR(120),
  lease_until TIMESTAMPTZ,
  optimistic_version BIGINT NOT NULL DEFAULT 0,
  CONSTRAINT uq_tb_protected_signal_envelope_inbox UNIQUE (inbox_logical_key)
);

CREATE INDEX IF NOT EXISTS ix_tb_protected_signal_envelope_state
  ON tb_protected_signal_envelope (state);
