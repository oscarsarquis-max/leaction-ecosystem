"""Add commercial sale basis to practiced prices (nullable for legacy).

Revision ID: 0023_practiced_sale_basis
Revises: 0022_fiscal_inbound
Create Date: 2026-09-01
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0023_practiced_sale_basis"
down_revision: Union[str, Sequence[str], None] = "0022_fiscal_inbound"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "practiced_price",
        sa.Column("sale_basis_quantity", sa.Numeric(18, 6), nullable=True),
    )
    op.add_column(
        "practiced_price",
        sa.Column("sale_basis_unit_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_practiced_price_sale_basis_unit",
        "practiced_price",
        "measurement_unit",
        ["sale_basis_unit_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_check_constraint(
        "ck_practiced_price_sale_basis_qty",
        "practiced_price",
        "sale_basis_quantity IS NULL OR sale_basis_quantity > 0",
    )
    op.create_check_constraint(
        "ck_practiced_price_sale_basis_pair",
        "practiced_price",
        "(sale_basis_quantity IS NULL) = (sale_basis_unit_id IS NULL)",
    )
    # Legacy rows stay NULL: readable history, not comparable.


def downgrade() -> None:
    op.drop_constraint("ck_practiced_price_sale_basis_pair", "practiced_price", type_="check")
    op.drop_constraint("ck_practiced_price_sale_basis_qty", "practiced_price", type_="check")
    op.drop_constraint("fk_practiced_price_sale_basis_unit", "practiced_price", type_="foreignkey")
    op.drop_column("practiced_price", "sale_basis_unit_id")
    op.drop_column("practiced_price", "sale_basis_quantity")
