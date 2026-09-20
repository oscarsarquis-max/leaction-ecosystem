"""standard bakery products, variants, composition and media

Revision ID: c8f3a1b27d09
Revises: b4e8d2a91c70
Create Date: 2026-09-16
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c8f3a1b27d09"
down_revision: Union[str, Sequence[str], None] = "b4e8d2a91c70"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "media_assets",
        sa.Column("stored_name", sa.String(length=80), nullable=False),
        sa.Column("content_type", sa.String(length=32), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("created_by_ref", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint("byte_size > 0", name="ck_media_assets_size"),
        sa.CheckConstraint("width > 0 AND height > 0", name="ck_media_assets_dimensions"),
        sa.CheckConstraint(
            "content_type IN ('image/jpeg','image/png','image/webp')",
            name="ck_media_assets_content_type",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stored_name"),
    )
    op.create_table(
        "products",
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("short_description", sa.String(length=280), nullable=False, server_default=""),
        sa.Column("long_description", sa.Text(), nullable=True),
        sa.Column("featured_image_id", sa.Uuid(), nullable=True),
        sa.Column("featured_image_alt", sa.String(length=160), nullable=False, server_default=""),
        sa.Column("editorial_status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("is_available", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_by_ref", sa.String(length=80), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "editorial_status IN ('draft','published','archived')",
            name="ck_products_editorial_status",
        ),
        sa.CheckConstraint("char_length(name) BETWEEN 1 AND 120", name="ck_products_name"),
        sa.CheckConstraint("char_length(slug) BETWEEN 1 AND 80", name="ck_products_slug"),
        sa.ForeignKeyConstraint(["featured_image_id"], ["media_assets.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_products_status_available", "products", ["editorial_status", "is_available"])
    op.create_index("ix_products_sort_published", "products", ["sort_order", "published_at"])
    op.create_table(
        "product_ingredients",
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("catalog_ingredient_id", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "char_length(name) BETWEEN 1 AND 120", name="ck_product_ingredients_name"
        ),
        sa.ForeignKeyConstraint(["catalog_ingredient_id"], ["ingredients.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("product_id", "sort_order", name="uq_product_ingredient_order"),
    )
    op.create_index(op.f("ix_product_ingredients_product_id"), "product_ingredients", ["product_id"])
    op.create_table(
        "product_variants",
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("display_name", sa.String(length=80), nullable=False),
        sa.Column("presentation_type", sa.String(length=20), nullable=False),
        sa.Column("net_weight_grams", sa.Integer(), nullable=True),
        sa.Column("units_per_pack", sa.Integer(), nullable=True),
        sa.Column("price_cents", sa.Integer(), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="BRL"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "presentation_type IN ('weight','pack')", name="ck_product_variants_presentation"
        ),
        sa.CheckConstraint("currency = 'BRL'", name="ck_product_variants_currency"),
        sa.CheckConstraint("price_cents IS NULL OR price_cents > 0", name="ck_product_variants_price"),
        sa.CheckConstraint(
            "(presentation_type = 'weight' AND net_weight_grams IS NOT NULL AND net_weight_grams > 0 "
            "AND units_per_pack IS NULL) OR "
            "(presentation_type = 'pack' AND units_per_pack IS NOT NULL AND units_per_pack > 0 "
            "AND net_weight_grams IS NULL)",
            name="ck_product_variants_measures",
        ),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("product_id", "display_name", name="uq_product_variant_name"),
    )
    op.create_index(op.f("ix_product_variants_product_id"), "product_variants", ["product_id"])
    op.create_index(
        "uq_product_variant_weight",
        "product_variants",
        ["product_id", "net_weight_grams"],
        unique=True,
        postgresql_where=sa.text("presentation_type = 'weight'"),
    )
    op.create_index(
        "uq_product_variant_pack",
        "product_variants",
        ["product_id", "units_per_pack"],
        unique=True,
        postgresql_where=sa.text("presentation_type = 'pack'"),
    )
    op.create_table(
        "product_events",
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("actor_ref", sa.String(length=80), nullable=True),
        sa.Column("detail", sa.String(length=280), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "action IN ('created','updated','published','unpublished','archived','availability','image')",
            name="ck_product_events_action",
        ),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_product_events_product_created",
        "product_events",
        ["product_id", "created_at"],
    )
    for table in ("products", "product_variants"):
        op.execute(
            f"CREATE TRIGGER trg_{table}_updated_at "
            f"BEFORE UPDATE ON {table} "
            f"FOR EACH ROW EXECUTE FUNCTION set_updated_at();"
        )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_product_variants_updated_at ON product_variants")
    op.execute("DROP TRIGGER IF EXISTS trg_products_updated_at ON products")
    op.drop_index("ix_product_events_product_created", table_name="product_events")
    op.drop_table("product_events")
    op.drop_index("uq_product_variant_pack", table_name="product_variants")
    op.drop_index("uq_product_variant_weight", table_name="product_variants")
    op.drop_index(op.f("ix_product_variants_product_id"), table_name="product_variants")
    op.drop_table("product_variants")
    op.drop_index(op.f("ix_product_ingredients_product_id"), table_name="product_ingredients")
    op.drop_table("product_ingredients")
    op.drop_index("ix_products_sort_published", table_name="products")
    op.drop_index("ix_products_status_available", table_name="products")
    op.drop_table("products")
    op.drop_table("media_assets")
