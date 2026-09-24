from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UuidPkMixin


class MediaAsset(UuidPkMixin, Base):
    __tablename__ = "media_assets"
    __table_args__ = (
        CheckConstraint("byte_size > 0", name="ck_media_assets_size"),
        CheckConstraint("width > 0 AND height > 0", name="ck_media_assets_dimensions"),
        CheckConstraint(
            "content_type IN ('image/jpeg','image/png','image/webp')",
            name="ck_media_assets_content_type",
        ),
        CheckConstraint(
            "storage_backend IN ('local','s3')",
            name="ck_media_assets_backend",
        ),
    )

    stored_name: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    object_key: Mapped[str] = mapped_column(String(240), nullable=False)
    storage_backend: Mapped[str] = mapped_column(String(16), nullable=False, default="local")
    content_type: Mapped[str] = mapped_column(String(32), nullable=False)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    created_by_ref: Mapped[str | None] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Product(UuidPkMixin, TimestampMixin, Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint(
            "editorial_status IN ('draft','published','archived')",
            name="ck_products_editorial_status",
        ),
        CheckConstraint("char_length(name) BETWEEN 1 AND 120", name="ck_products_name"),
        CheckConstraint("char_length(slug) BETWEEN 1 AND 80", name="ck_products_slug"),
        Index("ix_products_status_available", "editorial_status", "is_available"),
        Index("ix_products_sort_published", "sort_order", "published_at"),
    )

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    short_description: Mapped[str] = mapped_column(String(280), nullable=False, default="")
    long_description: Mapped[str | None] = mapped_column(Text)
    recipe_base_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("recipe_bases.id", ondelete="RESTRICT")
    )
    featured_image_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("media_assets.id", ondelete="RESTRICT")
    )
    featured_image_alt: Mapped[str] = mapped_column(String(160), nullable=False, default="")
    featured_image_caption: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    editorial_status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    is_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_by_ref: Mapped[str | None] = mapped_column(String(80))
    featured_image: Mapped[MediaAsset | None] = relationship()
    composition: Mapped[list["ProductIngredient"]] = relationship(
        order_by="ProductIngredient.sort_order"
    )
    variants: Mapped[list["ProductVariant"]] = relationship(
        order_by="ProductVariant.sort_order"
    )
    events: Mapped[list["ProductEvent"]] = relationship(
        order_by="ProductEvent.created_at"
    )


class ShowcaseSlot(Base):
    __tablename__ = "showcase_slots"
    __table_args__ = (
        CheckConstraint("position BETWEEN 1 AND 10", name="ck_showcase_slots_position"),
        UniqueConstraint("product_id", name="uq_showcase_slots_product"),
    )

    position: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), nullable=True
    )
    product: Mapped[Product | None] = relationship()


class ProductIngredient(UuidPkMixin, Base):
    __tablename__ = "product_ingredients"
    __table_args__ = (
        UniqueConstraint("product_id", "sort_order", name="uq_product_ingredient_order"),
        CheckConstraint("char_length(name) BETWEEN 1 AND 120", name="ck_product_ingredients_name"),
    )

    product_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    catalog_ingredient_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("ingredients.id", ondelete="SET NULL")
    )


class ProductVariant(UuidPkMixin, TimestampMixin, Base):
    __tablename__ = "product_variants"
    __table_args__ = (
        CheckConstraint(
            "presentation_type IN ('weight','pack')", name="ck_product_variants_presentation"
        ),
        CheckConstraint("currency = 'BRL'", name="ck_product_variants_currency"),
        CheckConstraint(
            "price_cents IS NULL OR price_cents > 0", name="ck_product_variants_price"
        ),
        CheckConstraint(
            "physical_units IS NULL OR physical_units > 0",
            name="ck_product_variants_physical_units",
        ),
        CheckConstraint(
            "(presentation_type = 'weight' AND net_weight_grams IS NOT NULL AND net_weight_grams > 0 "
            "AND units_per_pack IS NULL) OR "
            "(presentation_type = 'pack' AND units_per_pack IS NOT NULL AND units_per_pack > 0 "
            "AND net_weight_grams IS NULL)",
            name="ck_product_variants_measures",
        ),
        UniqueConstraint("product_id", "display_name", name="uq_product_variant_name"),
        Index(
            "uq_product_variant_weight",
            "product_id",
            "net_weight_grams",
            unique=True,
            postgresql_where=text("presentation_type = 'weight'"),
        ),
        Index(
            "uq_product_variant_pack",
            "product_id",
            "units_per_pack",
            unique=True,
            postgresql_where=text("presentation_type = 'pack'"),
        ),
    )

    product_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    display_name: Mapped[str] = mapped_column(String(80), nullable=False)
    presentation_type: Mapped[str] = mapped_column(String(20), nullable=False)
    net_weight_grams: Mapped[int | None] = mapped_column(Integer)
    units_per_pack: Mapped[int | None] = mapped_column(Integer)
    physical_units: Mapped[int | None] = mapped_column(Integer)
    price_cents: Mapped[int | None] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="BRL")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class ProductEvent(UuidPkMixin, Base):
    __tablename__ = "product_events"
    __table_args__ = (
        CheckConstraint(
            "action IN ('created','updated','published','unpublished','archived','availability','image')",
            name="ck_product_events_action",
        ),
        Index("ix_product_events_product_created", "product_id", "created_at"),
    )

    product_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_ref: Mapped[str | None] = mapped_column(String(80))
    detail: Mapped[str | None] = mapped_column(String(280))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
