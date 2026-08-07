"""Allow agenda_events.status=waived + waiver_reason for opening meeting handoff.

Revision ID: 20260807_0014
Revises: 20260806_0013
Create Date: 2026-08-07
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision = "20260807_0014"
down_revision = "20260806_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        text(
            """
            ALTER TABLE agenda_events DROP CONSTRAINT IF EXISTS agenda_events_status_check;
            ALTER TABLE agenda_events DROP CONSTRAINT IF EXISTS ck_agenda_events_status;
            ALTER TABLE agenda_events
              ADD CONSTRAINT ck_agenda_events_status
              CHECK (status IN ('scheduled', 'completed', 'cancelled', 'waived'));

            ALTER TABLE agenda_events
              ADD COLUMN IF NOT EXISTS waiver_reason text NOT NULL DEFAULT '';
            """
        )
    )


def downgrade() -> None:
    op.execute(
        text(
            """
            UPDATE agenda_events SET status = 'cancelled' WHERE status = 'waived';
            ALTER TABLE agenda_events DROP COLUMN IF EXISTS waiver_reason;
            ALTER TABLE agenda_events DROP CONSTRAINT IF EXISTS ck_agenda_events_status;
            ALTER TABLE agenda_events
              ADD CONSTRAINT ck_agenda_events_status
              CHECK (status IN ('scheduled', 'completed', 'cancelled'));
            """
        )
    )
