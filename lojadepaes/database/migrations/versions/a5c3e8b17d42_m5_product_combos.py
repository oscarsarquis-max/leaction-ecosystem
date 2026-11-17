"""Combinações pão da casa + produto do parceiro. Chaves só no schema marketplace.

Revision ID: a5c3e8b17d42
Revises: e1b8a4c27d09
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a5c3e8b17d42"
down_revision: Union[str, Sequence[str], None] = "e1b8a4c27d09"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_SCHEMA = "marketplace"


def upgrade() -> None:
    op.create_table(
        "product_combos",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("partner_id", sa.Uuid(), sa.ForeignKey("marketplace.partners.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "partner_product_id",
            sa.Uuid(),
            sa.ForeignKey("marketplace.partner_products.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("house_product_slug", sa.String(length=80), nullable=False),
        sa.Column("reason", sa.String(length=400), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("review_note", sa.String(length=2000), nullable=True),
        sa.Column("reviewer_ref", sa.String(length=120), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('pending','approved','returned','rejected','paused')",
            name="ck_mp_combos_status",
        ),
        sa.CheckConstraint("char_length(reason) BETWEEN 1 AND 400", name="ck_mp_combos_reason"),
        sa.CheckConstraint(
            "review_note IS NULL OR char_length(review_note) <= 2000",
            name="ck_mp_combos_note",
        ),
        schema=_SCHEMA,
    )
    op.create_index(
        "uq_mp_combos_open_pair",
        "product_combos",
        ["partner_product_id", "house_product_slug"],
        unique=True,
        schema=_SCHEMA,
        postgresql_where=sa.text("status IN ('pending','approved','returned')"),
    )


def downgrade() -> None:
    op.drop_table("product_combos", schema=_SCHEMA)
