"""Jobs worker lease, attempts, next_run_at, output_ref

Revision ID: 20260804_0006
Revises: 20260803_0005
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision = "20260804_0006"
down_revision = "20260803_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        text(
            """
            ALTER TABLE jobs
              ADD COLUMN IF NOT EXISTS attempt_count integer NOT NULL DEFAULT 0,
              ADD COLUMN IF NOT EXISTS max_attempts integer NOT NULL DEFAULT 5,
              ADD COLUMN IF NOT EXISTS locked_at timestamptz,
              ADD COLUMN IF NOT EXISTS locked_by text,
              ADD COLUMN IF NOT EXISTS next_run_at timestamptz,
              ADD COLUMN IF NOT EXISTS output_ref jsonb NOT NULL DEFAULT '{}'::jsonb;

            ALTER TABLE jobs
              DROP CONSTRAINT IF EXISTS jobs_attempt_count_check;
            ALTER TABLE jobs
              ADD CONSTRAINT jobs_attempt_count_check
              CHECK (attempt_count >= 0);

            ALTER TABLE jobs
              DROP CONSTRAINT IF EXISTS jobs_max_attempts_check;
            ALTER TABLE jobs
              ADD CONSTRAINT jobs_max_attempts_check
              CHECK (max_attempts >= 1 AND max_attempts <= 50);

            CREATE INDEX IF NOT EXISTS ix_jobs_claim_queue
              ON jobs (job_type, status, created_at)
              WHERE status = 'queued';

            CREATE INDEX IF NOT EXISTS ix_jobs_running_lease
              ON jobs (status, locked_at)
              WHERE status = 'running';
            """
        )
    )


def downgrade() -> None:
    op.execute(
        text(
            """
            DROP INDEX IF EXISTS ix_jobs_running_lease;
            DROP INDEX IF EXISTS ix_jobs_claim_queue;
            ALTER TABLE jobs DROP CONSTRAINT IF EXISTS jobs_max_attempts_check;
            ALTER TABLE jobs DROP CONSTRAINT IF EXISTS jobs_attempt_count_check;
            ALTER TABLE jobs
              DROP COLUMN IF EXISTS output_ref,
              DROP COLUMN IF EXISTS next_run_at,
              DROP COLUMN IF EXISTS locked_by,
              DROP COLUMN IF EXISTS locked_at,
              DROP COLUMN IF EXISTS max_attempts,
              DROP COLUMN IF EXISTS attempt_count;
            """
        )
    )
