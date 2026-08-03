"""Evidence upload_expires_at for abandon/expire cleanup

Revision ID: 20260803_0002
Revises: 20260803_0001
Freeze reference: domain-docs-v0 (Evidence machine)
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision = "20260803_0002"
down_revision = "20260803_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        text(
            """
            ALTER TABLE evidences
              ADD COLUMN IF NOT EXISTS upload_expires_at timestamptz;
            CREATE INDEX IF NOT EXISTS ix_evidences_upload_pending_expires
              ON evidences (status, upload_expires_at)
              WHERE status = 'upload_pending';
            """
        )
    )


def downgrade() -> None:
    op.execute(text("DROP INDEX IF EXISTS ix_evidences_upload_pending_expires"))
    op.execute(text("ALTER TABLE evidences DROP COLUMN IF EXISTS upload_expires_at"))
