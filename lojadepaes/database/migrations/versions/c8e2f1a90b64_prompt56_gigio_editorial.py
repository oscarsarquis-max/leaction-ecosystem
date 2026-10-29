"""Prompt 56: base editorial do Gigio.

Revision ID: c8e2f1a90b64
Revises: b3f7a1c82e09
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c8e2f1a90b64"
down_revision: Union[str, Sequence[str], None] = "b3f7a1c82e09"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "gigio_editorial_notes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("topic_key", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("editorial_status", sa.String(length=16), nullable=False, server_default="draft"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.CheckConstraint(
            "editorial_status IN ('draft','published')",
            name="ck_gigio_editorial_status",
        ),
        sa.CheckConstraint("char_length(topic_key) BETWEEN 1 AND 80", name="ck_gigio_editorial_topic"),
        sa.CheckConstraint("char_length(title) BETWEEN 1 AND 160", name="ck_gigio_editorial_title"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("topic_key", name="uq_gigio_editorial_topic"),
    )


def downgrade() -> None:
    op.drop_table("gigio_editorial_notes")
