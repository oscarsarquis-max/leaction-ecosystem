"""Optional visible caption for featured product photos

Revision ID: e2c9b4a81d05
Revises: c3a9f0b18d22
Create Date: 2026-09-21
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e2c9b4a81d05"
down_revision: Union[str, Sequence[str], None] = "c3a9f0b18d22"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "products",
        sa.Column(
            "featured_image_caption",
            sa.String(length=200),
            nullable=False,
            server_default="",
        ),
    )
    op.alter_column("products", "featured_image_caption", server_default=None)


def downgrade() -> None:
    op.drop_column("products", "featured_image_caption")
