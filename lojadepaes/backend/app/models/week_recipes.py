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
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UuidPkMixin
from app.models.products import MediaAsset, Product


class WeekRecipe(UuidPkMixin, TimestampMixin, Base):
    __tablename__ = "week_recipes"
    __table_args__ = (
        CheckConstraint(
            "editorial_status IN ('draft','published','archived')",
            name="ck_week_recipes_editorial_status",
        ),
        CheckConstraint("char_length(title) <= 160", name="ck_week_recipes_title"),
        CheckConstraint("char_length(slug) BETWEEN 1 AND 80", name="ck_week_recipes_slug"),
        CheckConstraint("char_length(summary) <= 280", name="ck_week_recipes_summary"),
        CheckConstraint(
            "image_focus_x BETWEEN 0 AND 100 AND image_focus_y BETWEEN 0 AND 100",
            name="ck_week_recipes_image_focus",
        ),
        Index(
            "uq_week_recipes_one_featured",
            "is_featured",
            unique=True,
            postgresql_where=text("is_featured IS TRUE"),
            sqlite_where=text("is_featured IS TRUE"),
        ),
    )

    title: Mapped[str] = mapped_column(String(160), nullable=False, default="")
    slug: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    summary: Mapped[str] = mapped_column(String(280), nullable=False, default="")
    featured_image_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("media_assets.id", ondelete="RESTRICT")
    )
    featured_image_alt: Mapped[str] = mapped_column(String(160), nullable=False, default="")
    featured_image_caption: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    image_focus_x: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    image_focus_y: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    prep_time_text: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    yield_text: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    method_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    editorial_status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    is_featured: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_by_ref: Mapped[str | None] = mapped_column(String(80))
    featured_image: Mapped[MediaAsset | None] = relationship()
    ingredients: Mapped[list["WeekRecipeIngredient"]] = relationship(
        order_by="WeekRecipeIngredient.sort_order", cascade="all, delete-orphan"
    )
    steps: Mapped[list["WeekRecipeStep"]] = relationship(
        order_by="WeekRecipeStep.sort_order", cascade="all, delete-orphan"
    )
    breads: Mapped[list["WeekRecipeBread"]] = relationship(
        order_by="WeekRecipeBread.sort_order", cascade="all, delete-orphan"
    )


class WeekRecipeIngredient(UuidPkMixin, Base):
    __tablename__ = "week_recipe_ingredients"
    __table_args__ = (
        UniqueConstraint("recipe_id", "sort_order", name="uq_week_recipe_ingredient_order"),
        CheckConstraint("char_length(body) BETWEEN 1 AND 280", name="ck_week_recipe_ingredient_body"),
    )

    recipe_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("week_recipes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    body: Mapped[str] = mapped_column(String(280), nullable=False)


class WeekRecipeStep(UuidPkMixin, Base):
    __tablename__ = "week_recipe_steps"
    __table_args__ = (
        UniqueConstraint("recipe_id", "sort_order", name="uq_week_recipe_step_order"),
        CheckConstraint("char_length(body) BETWEEN 1 AND 20000", name="ck_week_recipe_step_body"),
    )

    recipe_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("week_recipes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)


class WeekRecipeBread(UuidPkMixin, Base):
    __tablename__ = "week_recipe_breads"
    __table_args__ = (
        UniqueConstraint("recipe_id", "sort_order", name="uq_week_recipe_bread_order"),
        UniqueConstraint("recipe_id", "product_id", name="uq_week_recipe_bread_product"),
    )

    recipe_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("week_recipes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL")
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    name_snapshot: Mapped[str] = mapped_column(String(120), nullable=False)
    product: Mapped[Product | None] = relationship()
