"""Finding discarded/rework lineage + ActionItem withdraw signal

Revision ID: 20260803_0003
Revises: 20260803_0002
Freeze reference: domain-docs-v0 §4 / §5
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision = "20260803_0003"
down_revision = "20260803_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        text(
            """
            ALTER TABLE findings DROP CONSTRAINT IF EXISTS findings_status_check;
            ALTER TABLE findings
              ADD CONSTRAINT findings_status_check
              CHECK (status IN (
                'draft', 'in_review', 'approved', 'rejected', 'withdrawn', 'discarded'
              ));

            ALTER TABLE findings
              ADD COLUMN IF NOT EXISTS discard_reason text,
              ADD COLUMN IF NOT EXISTS rework_of_finding_id uuid;

            DO $$
            BEGIN
              IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'fk_findings_rework_of_same_org'
              ) THEN
                ALTER TABLE findings
                  ADD CONSTRAINT fk_findings_rework_of_same_org
                  FOREIGN KEY (rework_of_finding_id, organization_id)
                  REFERENCES findings (id, organization_id);
              END IF;
            END $$;

            ALTER TABLE action_items
              ADD COLUMN IF NOT EXISTS source_finding_withdrawn boolean NOT NULL DEFAULT false,
              ADD COLUMN IF NOT EXISTS cancel_reason text,
              ADD COLUMN IF NOT EXISTS reject_reason text,
              ADD COLUMN IF NOT EXISTS efficacy_fail_reason text;
            """
        )
    )


def downgrade() -> None:
    op.execute(
        text(
            """
            ALTER TABLE action_items
              DROP COLUMN IF EXISTS efficacy_fail_reason,
              DROP COLUMN IF EXISTS reject_reason,
              DROP COLUMN IF EXISTS cancel_reason,
              DROP COLUMN IF EXISTS source_finding_withdrawn;

            ALTER TABLE findings DROP CONSTRAINT IF EXISTS fk_findings_rework_of_same_org;
            ALTER TABLE findings
              DROP COLUMN IF EXISTS rework_of_finding_id,
              DROP COLUMN IF EXISTS discard_reason;

            -- Cannot downgrade status check if discarded rows exist
            UPDATE findings SET status = 'draft' WHERE status = 'discarded';
            ALTER TABLE findings DROP CONSTRAINT IF EXISTS findings_status_check;
            ALTER TABLE findings
              ADD CONSTRAINT findings_status_check
              CHECK (status IN (
                'draft', 'in_review', 'approved', 'rejected', 'withdrawn'
              ));
            """
        )
    )
