"""Catálogo técnico de ingredientes. Sem ficha, CRUD ou API de negócio."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def _uuid_pk():
    return mapped_column(Uuid, primary_key=True, server_default=text("gen_random_uuid()"))


def _created_at():
    return mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


def _updated_at():
    return mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class MeasurementUnit(Base):
    __tablename__ = "measurement_unit"

    id: Mapped[UUID] = _uuid_pk()
    code: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    plural_name: Mapped[str | None] = mapped_column(Text)
    dimension: Mapped[str] = mapped_column(Text, nullable=False)
    si_factor: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    symbol: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'active'"))
    created_at: Mapped[datetime] = _created_at()
    updated_at: Mapped[datetime] = _updated_at()


class UnitConversion(Base):
    __tablename__ = "unit_conversion"
    __table_args__ = (
        Index(
            "uq_unit_conversion_pair_ctx",
            "from_unit_id",
            "to_unit_id",
            "context",
            unique=True,
            postgresql_where=text("context IS NOT NULL"),
        ),
        Index(
            "uq_unit_conversion_pair",
            "from_unit_id",
            "to_unit_id",
            unique=True,
            postgresql_where=text("context IS NULL"),
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    from_unit_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("measurement_unit.id", ondelete="RESTRICT"), nullable=False
    )
    to_unit_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("measurement_unit.id", ondelete="RESTRICT"), nullable=False
    )
    factor: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    context: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'active'"))
    created_at: Mapped[datetime] = _created_at()
    updated_at: Mapped[datetime] = _updated_at()


class NutrientDefinition(Base):
    __tablename__ = "nutrient_definition"

    id: Mapped[UUID] = _uuid_pk()
    code: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    unit_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("measurement_unit.id", ondelete="RESTRICT"), nullable=False
    )
    group_code: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'active'"))
    created_at: Mapped[datetime] = _created_at()
    updated_at: Mapped[datetime] = _updated_at()


class Allergen(Base):
    __tablename__ = "allergen"

    id: Mapped[UUID] = _uuid_pk()
    code: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'active'"))
    created_at: Mapped[datetime] = _created_at()
    updated_at: Mapped[datetime] = _updated_at()


class DataSource(Base):
    __tablename__ = "data_source"

    id: Mapped[UUID] = _uuid_pk()
    source_type: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    external_ref: Mapped[str | None] = mapped_column(Text)
    version_label: Mapped[str | None] = mapped_column(Text)
    valid_from: Mapped[date | None] = mapped_column(Date)
    valid_to: Mapped[date | None] = mapped_column(Date)
    uri: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'active'"))
    created_at: Mapped[datetime] = _created_at()
    updated_at: Mapped[datetime] = _updated_at()


class Ingredient(Base):
    __tablename__ = "ingredient"
    __table_args__ = (
        Index("uq_ingredient_org_code", "organization_id", "code", unique=True),
        Index("uq_ingredient_id_org", "id", "organization_id", unique=True),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("organization.id", ondelete="RESTRICT"), nullable=False
    )
    code: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    ingredient_type: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'active'"))
    created_at: Mapped[datetime] = _created_at()
    updated_at: Mapped[datetime] = _updated_at()


class IngredientVersion(Base):
    __tablename__ = "ingredient_version"
    __table_args__ = (
        Index("uq_ingredient_version_number", "ingredient_id", "version_number", unique=True),
        Index("uq_ingredient_version_id_org", "id", "organization_id", unique=True),
        Index(
            "uq_ingredient_version_published",
            "ingredient_id",
            unique=True,
            postgresql_where=text("status = 'published'"),
        ),
        ForeignKeyConstraint(
            ["ingredient_id", "organization_id"],
            ["ingredient.id", "ingredient.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    ingredient_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'draft'"))
    data_source_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("data_source.id", ondelete="RESTRICT")
    )
    nutrition_basis_type: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'per_100g'")
    )
    nutrition_basis_quantity: Mapped[Decimal] = mapped_column(
        Numeric(14, 6), nullable=False, server_default=text("100")
    )
    nutrition_basis_unit_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("measurement_unit.id", ondelete="RESTRICT"), nullable=False
    )
    valid_from: Mapped[date | None] = mapped_column(Date)
    valid_to: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = _created_at()
    created_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("app_user.id", ondelete="RESTRICT")
    )
    updated_at: Mapped[datetime] = _updated_at()


class IngredientComposition(Base):
    __tablename__ = "ingredient_composition"
    __table_args__ = (
        Index(
            "uq_ingredient_composition_pair",
            "parent_ingredient_version_id",
            "component_ingredient_version_id",
            unique=True,
        ),
        Index(
            "uq_ingredient_composition_sequence",
            "parent_ingredient_version_id",
            "sequence",
            unique=True,
        ),
        ForeignKeyConstraint(
            ["parent_ingredient_version_id", "organization_id"],
            ["ingredient_version.id", "ingredient_version.organization_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["component_ingredient_version_id", "organization_id"],
            ["ingredient_version.id", "ingredient_version.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    parent_ingredient_version_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    component_ingredient_version_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    component_type: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 6), nullable=False)
    measurement_unit_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("measurement_unit.id", ondelete="RESTRICT"), nullable=False
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = _created_at()


class IngredientNutrient(Base):
    __tablename__ = "ingredient_nutrient"
    __table_args__ = (
        Index(
            "uq_ingredient_nutrient",
            "ingredient_version_id",
            "nutrient_id",
            unique=True,
        ),
        ForeignKeyConstraint(
            ["ingredient_version_id", "organization_id"],
            ["ingredient_version.id", "ingredient_version.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    ingredient_version_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    nutrient_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("nutrient_definition.id", ondelete="RESTRICT"), nullable=False
    )
    value: Mapped[Decimal | None] = mapped_column(Numeric(14, 6))
    value_status: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'measured'")
    )
    limit_of_quantification: Mapped[Decimal | None] = mapped_column(Numeric(14, 6))
    loq_unit_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("measurement_unit.id", ondelete="RESTRICT")
    )
    method_or_source: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = _created_at()


class IngredientAllergen(Base):
    __tablename__ = "ingredient_allergen"
    __table_args__ = (
        Index("uq_ingredient_allergen", "ingredient_version_id", "allergen_id", unique=True),
        ForeignKeyConstraint(
            ["ingredient_version_id", "organization_id"],
            ["ingredient_version.id", "ingredient_version.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    ingredient_version_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    allergen_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("allergen.id", ondelete="RESTRICT"), nullable=False
    )
    presence: Mapped[str] = mapped_column(Text, nullable=False)
    data_source_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("data_source.id", ondelete="RESTRICT")
    )
    evidence_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = _created_at()


class Supplier(Base):
    __tablename__ = "supplier"
    __table_args__ = (
        Index("uq_supplier_org_code", "organization_id", "code", unique=True),
        Index("uq_supplier_id_org", "id", "organization_id", unique=True),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("organization.id", ondelete="RESTRICT"), nullable=False
    )
    code: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'active'"))
    created_at: Mapped[datetime] = _created_at()
    updated_at: Mapped[datetime] = _updated_at()


class SupplierItem(Base):
    __tablename__ = "supplier_item"
    __table_args__ = (
        Index("uq_supplier_item_sku", "supplier_id", "supplier_sku", unique=True),
        ForeignKeyConstraint(
            ["supplier_id", "organization_id"],
            ["supplier.id", "supplier.organization_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["ingredient_id", "organization_id"],
            ["ingredient.id", "ingredient.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    supplier_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    ingredient_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    supplier_sku: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    package_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 6), nullable=False)
    measurement_unit_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("measurement_unit.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'active'"))
    created_at: Mapped[datetime] = _created_at()
    updated_at: Mapped[datetime] = _updated_at()


class SupplierItemPrice(Base):
    __tablename__ = "supplier_item_price"

    id: Mapped[UUID] = _uuid_pk()
    supplier_item_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("supplier_item.id", ondelete="RESTRICT"), nullable=False
    )
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = _created_at()
