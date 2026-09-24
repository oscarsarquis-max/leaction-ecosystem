from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UuidPkMixin


class DoughType(UuidPkMixin, TimestampMixin, Base):
    __tablename__ = "dough_types"
    __table_args__ = (
        CheckConstraint(
            "base_price_cents IS NULL OR base_price_cents >= 0",
            name="ck_dough_types_base_price_cents",
        ),
        CheckConstraint(
            "fermentation_hours IS NULL OR fermentation_hours > 0",
            name="ck_dough_types_fermentation_hours",
        ),
    )

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    short_description: Mapped[str] = mapped_column(String(280), nullable=False)
    story: Mapped[str | None] = mapped_column(Text)
    fermentation_hours: Mapped[int | None] = mapped_column(Integer)
    image_ref: Mapped[str | None] = mapped_column(String(500))
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    base_price_cents: Mapped[int | None] = mapped_column(Integer)
    recipe_base_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("recipe_bases.id", ondelete="RESTRICT")
    )


class Ingredient(UuidPkMixin, TimestampMixin, Base):
    __tablename__ = "ingredients"
    __table_args__ = (
        CheckConstraint(
            "surcharge_cents IS NULL OR surcharge_cents >= 0",
            name="ck_ingredients_surcharge_cents",
        ),
    )

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(String(280), nullable=False)
    image_ref: Mapped[str | None] = mapped_column(String(500))
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    surcharge_cents: Mapped[int | None] = mapped_column(Integer)


class BreadShape(UuidPkMixin, TimestampMixin, Base):
    __tablename__ = "bread_shapes"

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(String(280), nullable=False)
    crust_crumb_notes: Mapped[str] = mapped_column(Text, nullable=False)
    image_ref: Mapped[str | None] = mapped_column(String(500))
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class DoughIngredientCompatibility(UuidPkMixin, Base):
    __tablename__ = "dough_ingredient_compatibilities"
    __table_args__ = (
        UniqueConstraint("dough_type_id", "ingredient_id", name="uq_dough_ingredient_compat"),
    )

    dough_type_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("dough_types.id", ondelete="RESTRICT"), nullable=False
    )
    ingredient_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("ingredients.id", ondelete="RESTRICT"), nullable=False
    )


class DoughShapeCompatibility(UuidPkMixin, Base):
    __tablename__ = "dough_shape_compatibilities"
    __table_args__ = (
        UniqueConstraint("dough_type_id", "bread_shape_id", name="uq_dough_shape_compat"),
    )

    dough_type_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("dough_types.id", ondelete="RESTRICT"), nullable=False
    )
    bread_shape_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("bread_shapes.id", ondelete="RESTRICT"), nullable=False
    )


class PairingTip(UuidPkMixin, TimestampMixin, Base):
    __tablename__ = "pairing_tips"
    __table_args__ = (
        CheckConstraint(
            "paired_ingredient_id IS NULL OR ingredient_id <> paired_ingredient_id",
            name="ck_pairing_tips_not_self",
        ),
        CheckConstraint(
            "paired_ingredient_id IS NULL OR ingredient_id < paired_ingredient_id",
            name="ck_pairing_tips_canonical_order",
        ),
        Index(
            "uq_pairing_tips_single",
            "ingredient_id",
            unique=True,
            postgresql_where=text("paired_ingredient_id IS NULL"),
        ),
        Index(
            "uq_pairing_tips_pair",
            "ingredient_id",
            "paired_ingredient_id",
            unique=True,
            postgresql_where=text("paired_ingredient_id IS NOT NULL"),
        ),
    )

    ingredient_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("ingredients.id", ondelete="RESTRICT"), nullable=False
    )
    paired_ingredient_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("ingredients.id", ondelete="RESTRICT")
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Allergen(UuidPkMixin, TimestampMixin, Base):
    __tablename__ = "allergens"

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)


class DoughAllergen(UuidPkMixin, Base):
    __tablename__ = "dough_allergens"
    __table_args__ = (
        UniqueConstraint(
            "dough_type_id", "allergen_id", "presence", name="uq_dough_allergen_presence"
        ),
        CheckConstraint(
            "presence IN ('contains', 'may_contain')", name="ck_dough_allergens_presence"
        ),
    )

    dough_type_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("dough_types.id", ondelete="RESTRICT"), nullable=False
    )
    allergen_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("allergens.id", ondelete="RESTRICT"), nullable=False
    )
    presence: Mapped[str] = mapped_column(String(20), nullable=False)
    is_reviewed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class IngredientAllergen(UuidPkMixin, Base):
    __tablename__ = "ingredient_allergens"
    __table_args__ = (
        UniqueConstraint(
            "ingredient_id", "allergen_id", "presence", name="uq_ingredient_allergen_presence"
        ),
        CheckConstraint(
            "presence IN ('contains', 'may_contain')", name="ck_ingredient_allergens_presence"
        ),
    )

    ingredient_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("ingredients.id", ondelete="RESTRICT"), nullable=False
    )
    allergen_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("allergens.id", ondelete="RESTRICT"), nullable=False
    )
    presence: Mapped[str] = mapped_column(String(20), nullable=False)
    is_reviewed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


__all__ = [
    "Allergen",
    "BreadShape",
    "DoughAllergen",
    "DoughIngredientCompatibility",
    "DoughShapeCompatibility",
    "DoughType",
    "Ingredient",
    "IngredientAllergen",
    "PairingTip",
]
