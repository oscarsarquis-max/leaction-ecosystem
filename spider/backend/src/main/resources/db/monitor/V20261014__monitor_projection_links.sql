ALTER TABLE tb_monitor_projection ADD COLUMN IF NOT EXISTS credit_state varchar(80);
ALTER TABLE tb_monitor_projection ADD COLUMN IF NOT EXISTS sync_run_id varchar(80);
ALTER TABLE tb_monitor_projection ADD COLUMN IF NOT EXISTS related_sync_id varchar(200);
ALTER TABLE tb_monitor_projection ADD COLUMN IF NOT EXISTS related_payment_id varchar(200);
ALTER TABLE tb_monitor_projection ADD COLUMN IF NOT EXISTS related_interaction_id varchar(200);
ALTER TABLE tb_monitor_projection ADD COLUMN IF NOT EXISTS pages_consulted integer;
ALTER TABLE tb_monitor_projection ADD COLUMN IF NOT EXISTS found_count integer;
ALTER TABLE tb_monitor_projection ADD COLUMN IF NOT EXISTS new_count integer;
ALTER TABLE tb_monitor_projection ADD COLUMN IF NOT EXISTS updated_count integer;
ALTER TABLE tb_monitor_projection ADD COLUMN IF NOT EXISTS ignored_count integer;
ALTER TABLE tb_monitor_projection ADD COLUMN IF NOT EXISTS failed_count integer;

CREATE INDEX IF NOT EXISTS idx_monitor_projection_sync
  ON tb_monitor_projection (sync_run_id);
