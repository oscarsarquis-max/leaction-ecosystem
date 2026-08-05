-- Jobs worker lease / retry columns (mirror of alembic 20260804_0006)
ALTER TABLE jobs
  ADD COLUMN IF NOT EXISTS attempt_count integer NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS max_attempts integer NOT NULL DEFAULT 5,
  ADD COLUMN IF NOT EXISTS locked_at timestamptz,
  ADD COLUMN IF NOT EXISTS locked_by text,
  ADD COLUMN IF NOT EXISTS next_run_at timestamptz,
  ADD COLUMN IF NOT EXISTS output_ref jsonb NOT NULL DEFAULT '{}'::jsonb;

ALTER TABLE jobs DROP CONSTRAINT IF EXISTS jobs_attempt_count_check;
ALTER TABLE jobs ADD CONSTRAINT jobs_attempt_count_check CHECK (attempt_count >= 0);

ALTER TABLE jobs DROP CONSTRAINT IF EXISTS jobs_max_attempts_check;
ALTER TABLE jobs ADD CONSTRAINT jobs_max_attempts_check
  CHECK (max_attempts >= 1 AND max_attempts <= 50);

CREATE INDEX IF NOT EXISTS ix_jobs_claim_queue
  ON jobs (job_type, status, created_at)
  WHERE status = 'queued';

CREATE INDEX IF NOT EXISTS ix_jobs_running_lease
  ON jobs (status, locked_at)
  WHERE status = 'running';
