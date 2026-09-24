"""recipe bases, bakery schedule and media backend

Revision ID: d1a7c4e90b12
Revises: c8f3a1b27d09
Create Date: 2026-09-20
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "d1a7c4e90b12"
down_revision: Union[str, Sequence[str], None] = "c8f3a1b27d09"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "recipe_bases",
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint("char_length(code) BETWEEN 1 AND 40", name="ck_recipe_bases_code"),
        sa.CheckConstraint("char_length(name) BETWEEN 1 AND 120", name="ck_recipe_bases_name"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_table(
        "schedule_settings",
        sa.Column("id", sa.SmallInteger(), nullable=False),
        sa.Column("production_weekdays", postgresql.ARRAY(sa.Integer()), nullable=False),
        sa.Column("daily_physical_limit", sa.Integer(), nullable=False),
        sa.Column("daily_base_limit", sa.Integer(), nullable=False),
        sa.Column("horizon_days", sa.Integer(), nullable=False),
        sa.Column("min_advance_hours", sa.Integer(), nullable=False),
        sa.Column("eligibility_mode", sa.String(length=16), nullable=False),
        sa.Column("occupancy_enabled", sa.Boolean(), nullable=False),
        sa.Column("reservation_policy", sa.String(length=20), nullable=False),
        sa.CheckConstraint("id = 1", name="ck_schedule_settings_singleton"),
        sa.CheckConstraint("daily_physical_limit > 0", name="ck_schedule_settings_physical"),
        sa.CheckConstraint("daily_base_limit > 0", name="ck_schedule_settings_bases"),
        sa.CheckConstraint("horizon_days > 0", name="ck_schedule_settings_horizon"),
        sa.CheckConstraint("min_advance_hours >= 0", name="ck_schedule_settings_advance"),
        sa.CheckConstraint(
            "eligibility_mode IN ('inherit','explicit')",
            name="ck_schedule_settings_eligibility",
        ),
        sa.CheckConstraint(
            "reservation_policy IN ('unset','request','admin_accept','payment')",
            name="ck_schedule_settings_policy",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(
        sa.text(
            "INSERT INTO schedule_settings ("
            "id, production_weekdays, daily_physical_limit, daily_base_limit, "
            "horizon_days, min_advance_hours, eligibility_mode, occupancy_enabled, "
            "reservation_policy"
            ") VALUES ("
            "1, ARRAY[3,6], 15, 5, 56, 0, 'inherit', false, 'unset'"
            ")"
        )
    )
    op.create_table(
        "schedule_week_overrides",
        sa.Column("week_start", sa.Date(), nullable=False),
        sa.Column("production_weekdays", postgresql.ARRAY(sa.Integer()), nullable=True),
        sa.Column("daily_physical_limit", sa.Integer(), nullable=True),
        sa.Column("daily_base_limit", sa.Integer(), nullable=True),
        sa.Column("eligibility_mode", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "daily_physical_limit IS NULL OR daily_physical_limit >= 0",
            name="ck_week_override_physical",
        ),
        sa.CheckConstraint(
            "daily_base_limit IS NULL OR daily_base_limit >= 0",
            name="ck_week_override_bases",
        ),
        sa.CheckConstraint(
            "eligibility_mode IN ('inherit','explicit')",
            name="ck_week_override_eligibility",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("week_start"),
    )
    op.create_table(
        "schedule_date_overrides",
        sa.Column("local_date", sa.Date(), nullable=False),
        sa.Column("open_state", sa.String(length=16), nullable=False),
        sa.Column("daily_physical_limit", sa.Integer(), nullable=True),
        sa.Column("daily_base_limit", sa.Integer(), nullable=True),
        sa.Column("eligibility_mode", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "open_state IN ('inherit','open','closed')",
            name="ck_date_override_open_state",
        ),
        sa.CheckConstraint(
            "daily_physical_limit IS NULL OR daily_physical_limit >= 0",
            name="ck_date_override_physical",
        ),
        sa.CheckConstraint(
            "daily_base_limit IS NULL OR daily_base_limit >= 0",
            name="ck_date_override_bases",
        ),
        sa.CheckConstraint(
            "eligibility_mode IN ('inherit','explicit')",
            name="ck_date_override_eligibility",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("local_date"),
    )
    op.create_table(
        "schedule_eligible_bases",
        sa.Column("scope_kind", sa.String(length=16), nullable=False),
        sa.Column("scope_id", sa.Uuid(), nullable=True),
        sa.Column("recipe_base_id", sa.Uuid(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "scope_kind IN ('default','week','date')",
            name="ck_schedule_eligible_scope",
        ),
        sa.CheckConstraint(
            "(scope_kind = 'default' AND scope_id IS NULL) OR "
            "(scope_kind <> 'default' AND scope_id IS NOT NULL)",
            name="ck_schedule_eligible_scope_id",
        ),
        sa.ForeignKeyConstraint(["recipe_base_id"], ["recipe_bases.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("scope_kind", "scope_id", "recipe_base_id", name="uq_schedule_eligible_base"),
    )
    op.add_column("dough_types", sa.Column("recipe_base_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_dough_types_recipe_base",
        "dough_types",
        "recipe_bases",
        ["recipe_base_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.add_column("products", sa.Column("recipe_base_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_products_recipe_base",
        "products",
        "recipe_bases",
        ["recipe_base_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.add_column("product_variants", sa.Column("physical_units", sa.Integer(), nullable=True))
    op.create_check_constraint(
        "ck_product_variants_physical_units",
        "product_variants",
        "physical_units IS NULL OR physical_units > 0",
    )
    op.add_column("media_assets", sa.Column("object_key", sa.String(length=240), nullable=True))
    op.add_column(
        "media_assets",
        sa.Column("storage_backend", sa.String(length=16), nullable=False, server_default="local"),
    )
    op.execute(sa.text("UPDATE media_assets SET object_key = stored_name WHERE object_key IS NULL"))
    op.alter_column("media_assets", "object_key", nullable=False)
    op.create_check_constraint(
        "ck_media_assets_backend",
        "media_assets",
        "storage_backend IN ('local','s3')",
    )
    op.add_column("orders", sa.Column("production_local_date", sa.Date(), nullable=True))
    op.alter_column("order_items", "dough_type_id", existing_type=sa.Uuid(), nullable=True)
    op.alter_column("order_items", "bread_shape_id", existing_type=sa.Uuid(), nullable=True)
    op.add_column("order_items", sa.Column("product_id", sa.Uuid(), nullable=True))
    op.add_column("order_items", sa.Column("product_variant_id", sa.Uuid(), nullable=True))
    op.add_column("order_items", sa.Column("recipe_base_id", sa.Uuid(), nullable=True))
    op.add_column("order_items", sa.Column("physical_units", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_order_items_product",
        "order_items",
        "products",
        ["product_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_order_items_variant",
        "order_items",
        "product_variants",
        ["product_variant_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_order_items_recipe_base",
        "order_items",
        "recipe_bases",
        ["recipe_base_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_check_constraint(
        "ck_order_items_physical_units",
        "order_items",
        "physical_units IS NULL OR physical_units > 0",
    )
    op.create_check_constraint(
        "ck_order_items_origin",
        "order_items",
        "("
        "dough_type_id IS NOT NULL AND bread_shape_id IS NOT NULL AND "
        "product_variant_id IS NULL"
        ") OR ("
        "product_id IS NOT NULL AND product_variant_id IS NOT NULL"
        ")",
    )


def downgrade() -> None:
    op.drop_constraint("ck_order_items_origin", "order_items", type_="check")
    op.drop_constraint("ck_order_items_physical_units", "order_items", type_="check")
    op.drop_constraint("fk_order_items_recipe_base", "order_items", type_="foreignkey")
    op.drop_constraint("fk_order_items_variant", "order_items", type_="foreignkey")
    op.drop_constraint("fk_order_items_product", "order_items", type_="foreignkey")
    op.drop_column("order_items", "physical_units")
    op.drop_column("order_items", "recipe_base_id")
    op.drop_column("order_items", "product_variant_id")
    op.drop_column("order_items", "product_id")
    op.alter_column("order_items", "bread_shape_id", existing_type=sa.Uuid(), nullable=False)
    op.alter_column("order_items", "dough_type_id", existing_type=sa.Uuid(), nullable=False)
    op.drop_column("orders", "production_local_date")
    op.drop_constraint("ck_media_assets_backend", "media_assets", type_="check")
    op.drop_column("media_assets", "storage_backend")
    op.drop_column("media_assets", "object_key")
    op.drop_constraint("ck_product_variants_physical_units", "product_variants", type_="check")
    op.drop_column("product_variants", "physical_units")
    op.drop_constraint("fk_products_recipe_base", "products", type_="foreignkey")
    op.drop_column("products", "recipe_base_id")
    op.drop_constraint("fk_dough_types_recipe_base", "dough_types", type_="foreignkey")
    op.drop_column("dough_types", "recipe_base_id")
    op.drop_table("schedule_eligible_bases")
    op.drop_table("schedule_date_overrides")
    op.drop_table("schedule_week_overrides")
    op.drop_table("schedule_settings")
    op.drop_table("recipe_bases")
