-- SPIDER-PROMPT-013: Inbox application lease + signal definition refs (additive)
ALTER TABLE tb_inbox_message ADD COLUMN IF NOT EXISTS wait_id VARCHAR(120);
ALTER TABLE tb_inbox_message ADD COLUMN IF NOT EXISTS signal_definition_ref VARCHAR(200);
ALTER TABLE tb_inbox_message ADD COLUMN IF NOT EXISTS payload_digest VARCHAR(128);
ALTER TABLE tb_inbox_message ADD COLUMN IF NOT EXISTS application_attempt_count INTEGER DEFAULT 0;
ALTER TABLE tb_inbox_message ADD COLUMN IF NOT EXISTS next_attempt_at TIMESTAMPTZ;
ALTER TABLE tb_inbox_message ADD COLUMN IF NOT EXISTS lease_owner VARCHAR(120);
ALTER TABLE tb_inbox_message ADD COLUMN IF NOT EXISTS lease_until TIMESTAMPTZ;
ALTER TABLE tb_inbox_message ADD COLUMN IF NOT EXISTS optimistic_version BIGINT DEFAULT 0;
ALTER TABLE tb_inbox_message ADD COLUMN IF NOT EXISTS verified_at TIMESTAMPTZ;
ALTER TABLE tb_inbox_message ADD COLUMN IF NOT EXISTS applied_at TIMESTAMPTZ;

ALTER TABLE tb_execution_wait ADD COLUMN IF NOT EXISTS signal_definition_ref VARCHAR(200);
ALTER TABLE tb_execution_wait ADD COLUMN IF NOT EXISTS integrity_profile_ref VARCHAR(200);

CREATE INDEX IF NOT EXISTS ix_tb_inbox_message_apply_due
  ON tb_inbox_message (processing_state, next_attempt_at);

CREATE INDEX IF NOT EXISTS ix_tb_inbox_message_lease
  ON tb_inbox_message (lease_until);

CREATE INDEX IF NOT EXISTS ix_tb_inbox_message_wait
  ON tb_inbox_message (wait_id);

CREATE INDEX IF NOT EXISTS ix_tb_inbox_message_execution
  ON tb_inbox_message (execution_id);
