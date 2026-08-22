"""Snapshot de cálculo nutricional técnico. Sem rótulo e sem conformidade."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Numeric,
    Text,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def _uuid_pk():
    return mapped_column(Uuid, primary_key=True, server_default=text("gen_random_uuid()"))


def _created_at():
    return mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class NutritionCalculation(Base):
    __tablename__ = "nutrition_calculation"
    __table_args__ = (
        Index("uq_nutrition_calculation_id_org", "id", "organization_id", unique=True),
        Index("ix_nutrition_calculation_version", "organization_id", "formulation_version_id"),
        ForeignKeyConstraint(
            ["formulation_version_id", "organization_id"],
            ["formulation_version.id", "formulation_version.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    formulation_version_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    calculation_basis: Mapped[str] = mapped_column(Text, nullable=False)
    formulation_version_status: Mapped[str] = mapped_column(Text, nullable=False)
    is_simulation: Mapped[bool] = mapped_column(Boolean, nullable=False)
    formula_net_mass_g: Mapped[Decimal] = mapped_column(Numeric(14, 6), nullable=False)
    expected_final_mass_g: Mapped[Decimal | None] = mapped_column(Numeric(14, 6))
    portion_mass_g: Mapped[Decimal | None] = mapped_column(Numeric(14, 6))
    algorithm_name: Mapped[str] = mapped_column(Text, nullable=False)
    algorithm_version: Mapped[str] = mapped_column(Text, nullable=False)
    rounding_policy: Mapped[str] = mapped_column(Text, nullable=False)
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("clock_timestamp()")
    )
    calculated_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("app_user.id", ondelete="RESTRICT")
    )
    warnings: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    assumptions: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    expectation_profile_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("nutrition_expectation_profile.id", ondelete="RESTRICT")
    )


class NutritionCalculationItem(Base):
    __tablename__ = "nutrition_calculation_item"
    __table_args__ = (
        Index(
            "uq_nutrition_calculation_item_nutrient",
            "nutrition_calculation_id",
            "nutrient_definition_id",
            unique=True,
        ),
        Index("uq_nutrition_calculation_item_id_org", "id", "organization_id", unique=True),
        ForeignKeyConstraint(
            ["nutrition_calculation_id", "organization_id"],
            ["nutrition_calculation.id", "nutrition_calculation.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    nutrition_calculation_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    nutrient_definition_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("nutrient_definition.id", ondelete="RESTRICT"), nullable=False
    )
    measurement_unit_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("measurement_unit.id", ondelete="RESTRICT"), nullable=False
    )
    whole_formula_amount: Mapped[Decimal] = mapped_column(Numeric(14, 6), nullable=False)
    per_100g_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 6))
    technical_portion_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 6))
    completeness_status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = _created_at()


class CalculationEvidence(Base):
    __tablename__ = "calculation_evidence"
    __table_args__ = (
        Index("ix_calculation_evidence_calc", "nutrition_calculation_id", "created_at"),
        ForeignKeyConstraint(
            ["nutrition_calculation_id", "organization_id"],
            ["nutrition_calculation.id", "nutrition_calculation.organization_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["nutrition_calculation_item_id", "organization_id"],
            ["nutrition_calculation_item.id", "nutrition_calculation_item.organization_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["formulation_item_id", "organization_id"],
            ["formulation_item.id", "formulation_item.organization_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["ingredient_version_id", "organization_id"],
            ["ingredient_version.id", "ingredient_version.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    nutrition_calculation_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    nutrition_calculation_item_id: Mapped[UUID | None] = mapped_column(Uuid)
    formulation_item_id: Mapped[UUID | None] = mapped_column(Uuid)
    ingredient_version_id: Mapped[UUID | None] = mapped_column(Uuid)
    ingredient_nutrient_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("ingredient_nutrient.id", ondelete="RESTRICT")
    )
    data_source_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("data_source.id", ondelete="RESTRICT")
    )
    evidence_type: Mapped[str] = mapped_column(Text, nullable=False)
    ingredient_quantity_g: Mapped[Decimal | None] = mapped_column(Numeric(14, 6))
    source_nutrient_value: Mapped[Decimal | None] = mapped_column(Numeric(14, 6))
    source_basis: Mapped[str | None] = mapped_column(Text)
    contribution_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 6))
    status: Mapped[str] = mapped_column(Text, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = _created_at()
