"""Fotos enviadas pelo parceiro. A chave só aponta para marketplace.partners.

Revision ID: d4e7b1a90c63
Revises: c8d5f3b02a41
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d4e7b1a90c63"
down_revision: Union[str, Sequence[str], None] = "c8d5f3b02a41"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_SCHEMA = "marketplace"


def upgrade() -> None:
    op.create_table(
        "partner_media",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("partner_id", sa.Uuid(), sa.ForeignKey("marketplace.partners.id", ondelete="CASCADE"), nullable=False),
        sa.Column("stored_name", sa.String(length=80), nullable=False),
        sa.Column("storage_backend", sa.String(length=32), nullable=False),
        sa.Column("content_type", sa.String(length=40), nullable=False),
        sa.Column("bytes", sa.Integer(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        schema=_SCHEMA,
    )


def downgrade() -> None:
    op.drop_table("partner_media", schema=_SCHEMA)
