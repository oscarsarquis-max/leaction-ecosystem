"""Ten numbered storefront slots

Revision ID: f1a8c6d23b90
Revises: c4d8a0b15e27
Create Date: 2026-09-20
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f1a8c6d23b90"
down_revision: Union[str, Sequence[str], None] = "c4d8a0b15e27"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "showcase_slots",
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=True),
        sa.CheckConstraint("position BETWEEN 1 AND 10", name="ck_showcase_slots_position"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("position"),
        sa.UniqueConstraint("product_id", name="uq_showcase_slots_product"),
    )
    op.execute("INSERT INTO showcase_slots (position) SELECT generate_series(1, 10)")


def downgrade() -> None:
    op.drop_table("showcase_slots")
