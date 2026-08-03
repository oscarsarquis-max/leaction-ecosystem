"""One current published Report per Assessment

Revision ID: 20260803_0005
Revises: 20260803_0004
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision = "20260803_0005"
down_revision = "20260803_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        text(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_reports_one_published_per_assessment
              ON reports (assessment_id)
              WHERE status = 'published';
            """
        )
    )


def downgrade() -> None:
    op.execute(text("DROP INDEX IF EXISTS uq_reports_one_published_per_assessment"))
