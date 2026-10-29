"""Prompt 73: curadoria aditiva de complementos.

Revision ID: b8e4c1d93f50
Revises: a7d3b8e02c41
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b8e4c1d93f50"
down_revision: Union[str, Sequence[str], None] = "a7d3b8e02c41"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "accompaniment_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("hub_offer_id", sa.String(length=80), nullable=False),
        sa.Column("hub_source", sa.String(length=40), nullable=False, server_default="mercadolivre"),
        sa.Column("snapshot_title", sa.String(length=240), nullable=False, server_default=""),
        sa.Column("snapshot_description", sa.Text(), nullable=False, server_default=""),
        sa.Column("snapshot_image_url", sa.String(length=500), nullable=True),
        sa.Column("snapshot_price_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("snapshot_price_currency", sa.String(length=8), nullable=False, server_default="BRL"),
        sa.Column("snapshot_link", sa.Text(), nullable=True),
        sa.Column("snapshot_fetched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("occasion", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("story_title", sa.String(length=160), nullable=False, server_default=""),
        sa.Column("story_lead", sa.Text(), nullable=False, server_default=""),
        sa.Column("why_pairs", sa.Text(), nullable=False, server_default=""),
        sa.Column("serving_tip", sa.Text(), nullable=False, server_default=""),
        sa.Column("related_product_slugs", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("related_recipe_slugs", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("published", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("hub_offer_id", name="uq_accompaniment_hub_offer"),
        sa.CheckConstraint("char_length(hub_offer_id) BETWEEN 1 AND 80", name="ck_accompaniment_hub_id"),
        sa.CheckConstraint("sort_order >= 0", name="ck_accompaniment_sort"),
    )
    op.create_index("ix_accompaniment_published_sort", "accompaniment_items", ["published", "sort_order"])


def downgrade() -> None:
    op.drop_index("ix_accompaniment_published_sort", table_name="accompaniment_items")
    op.drop_table("accompaniment_items")
