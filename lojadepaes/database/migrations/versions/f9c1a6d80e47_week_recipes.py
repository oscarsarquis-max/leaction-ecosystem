"""Prompt 47: receitas da semana editoriais.

Revision ID: f9c1a6d80e47
Revises: e8f4b2c70a46
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f9c1a6d80e47"
down_revision: Union[str, Sequence[str], None] = "e8f4b2c70a46"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "week_recipes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False, server_default=""),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("summary", sa.String(length=280), nullable=False, server_default=""),
        sa.Column("featured_image_id", sa.Uuid(), nullable=True),
        sa.Column("featured_image_alt", sa.String(length=160), nullable=False, server_default=""),
        sa.Column("featured_image_caption", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("image_focus_x", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("image_focus_y", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("prep_time_text", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("yield_text", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("editorial_status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("is_featured", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_by_ref", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["featured_image_id"], ["media_assets.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
        sa.CheckConstraint(
            "editorial_status IN ('draft','published','archived')",
            name="ck_week_recipes_editorial_status",
        ),
        sa.CheckConstraint(
            "image_focus_x BETWEEN 0 AND 100 AND image_focus_y BETWEEN 0 AND 100",
            name="ck_week_recipes_image_focus",
        ),
    )
    op.create_index(
        "uq_week_recipes_one_featured",
        "week_recipes",
        ["is_featured"],
        unique=True,
        postgresql_where=sa.text("is_featured IS TRUE"),
    )
    op.create_table(
        "week_recipe_ingredients",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("recipe_id", sa.Uuid(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("body", sa.String(length=280), nullable=False),
        sa.ForeignKeyConstraint(["recipe_id"], ["week_recipes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("recipe_id", "sort_order", name="uq_week_recipe_ingredient_order"),
    )
    op.create_index("ix_week_recipe_ingredients_recipe_id", "week_recipe_ingredients", ["recipe_id"])
    op.create_table(
        "week_recipe_steps",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("recipe_id", sa.Uuid(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("body", sa.String(length=2000), nullable=False),
        sa.ForeignKeyConstraint(["recipe_id"], ["week_recipes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("recipe_id", "sort_order", name="uq_week_recipe_step_order"),
    )
    op.create_index("ix_week_recipe_steps_recipe_id", "week_recipe_steps", ["recipe_id"])
    op.create_table(
        "week_recipe_breads",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("recipe_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("name_snapshot", sa.String(length=120), nullable=False),
        sa.ForeignKeyConstraint(["recipe_id"], ["week_recipes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("recipe_id", "sort_order", name="uq_week_recipe_bread_order"),
        sa.UniqueConstraint("recipe_id", "product_id", name="uq_week_recipe_bread_product"),
    )
    op.create_index("ix_week_recipe_breads_recipe_id", "week_recipe_breads", ["recipe_id"])


def downgrade() -> None:
    op.drop_table("week_recipe_breads")
    op.drop_table("week_recipe_steps")
    op.drop_table("week_recipe_ingredients")
    op.drop_index("uq_week_recipes_one_featured", table_name="week_recipes")
    op.drop_table("week_recipes")
