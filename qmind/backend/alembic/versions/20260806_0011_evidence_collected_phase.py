"""Evidence collection origin (phase/at/by) derived from assessment status

Revision ID: 20260806_0011
Revises: 20260806_0010
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision = "20260806_0011"
down_revision = "20260806_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        text(
            """
            ALTER TABLE evidences
              ADD COLUMN IF NOT EXISTS collected_phase text,
              ADD COLUMN IF NOT EXISTS collected_at timestamptz,
              ADD COLUMN IF NOT EXISTS collected_by uuid;

            ALTER TABLE evidences
              DROP CONSTRAINT IF EXISTS ck_evidences_collected_phase;
            ALTER TABLE evidences
              ADD CONSTRAINT ck_evidences_collected_phase CHECK (
                collected_phase IS NULL OR collected_phase IN (
                  'preparation', 'planning', 'field', 'analysis', 'unknown_legacy'
                )
              );

            -- Historical rows: phase at upload time is unknown — do not invent.
            UPDATE evidences
            SET collected_phase = 'unknown_legacy'
            WHERE collected_phase IS NULL;
            """
        )
    )


def downgrade() -> None:
    op.execute(
        text(
            """
            ALTER TABLE evidences
              DROP CONSTRAINT IF EXISTS ck_evidences_collected_phase;
            ALTER TABLE evidences
              DROP COLUMN IF EXISTS collected_phase,
              DROP COLUMN IF EXISTS collected_at,
              DROP COLUMN IF EXISTS collected_by;
            """
        )
    )
