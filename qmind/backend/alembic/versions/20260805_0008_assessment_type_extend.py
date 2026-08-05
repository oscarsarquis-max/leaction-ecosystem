"""Extend assessment types for journey UI labels

Revision ID: 20260805_0008
Revises: 20260804_0007
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision = "20260805_0008"
down_revision = "20260804_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        text(
            """
            ALTER TABLE assessments DROP CONSTRAINT IF EXISTS assessments_type_check;
            ALTER TABLE assessments ADD CONSTRAINT assessments_type_check
              CHECK (type IN (
                'diagnosis',
                'internal_audit',
                'external_audit',
                'certification_prep',
                'other'
              ));
            """
        )
    )


def downgrade() -> None:
    op.execute(
        text(
            """
            UPDATE assessments
              SET type = 'other'
              WHERE type IN ('external_audit', 'certification_prep');
            ALTER TABLE assessments DROP CONSTRAINT IF EXISTS assessments_type_check;
            ALTER TABLE assessments ADD CONSTRAINT assessments_type_check
              CHECK (type IN ('diagnosis', 'internal_audit', 'other'));
            """
        )
    )
