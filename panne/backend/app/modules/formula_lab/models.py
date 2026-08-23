"""Núcleo de produto técnico e formulações. Sem CRUD HTTP, nutrição ou custo."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
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


def _updated_at():
    return mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class TechnicalProduct(Base):
    __tablename__ = "technical_product"
    __table_args__ = (
        Index("uq_technical_product_org_code", "organization_id", "code", unique=True),
        Index("uq_technical_product_id_org", "id", "organization_id", unique=True),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("organization.id", ondelete="RESTRICT"), nullable=False
    )
    code: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'development'"))
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    created_at: Mapped[datetime] = _created_at()
    updated_at: Mapped[datetime] = _updated_at()


class RecipeReference(Base):
    __tablename__ = "recipe_reference"
    __table_args__ = (Index("uq_recipe_reference_id_org", "id", "organization_id", unique=True),)

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("organization.id", ondelete="RESTRICT"), nullable=False
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text)
    author: Mapped[str | None] = mapped_column(Text)
    license_or_usage_notes: Mapped[str | None] = mapped_column(Text)
    accessed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    created_at: Mapped[datetime] = _created_at()
    created_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("app_user.id", ondelete="RESTRICT")
    )


class Formulation(Base):
    __tablename__ = "formulation"
    __table_args__ = (
        Index("uq_formulation_org_code", "organization_id", "code", unique=True),
        Index("uq_formulation_id_org", "id", "organization_id", unique=True),
        ForeignKeyConstraint(
            ["technical_product_id", "organization_id"],
            ["technical_product.id", "technical_product.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    technical_product_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    code: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'development'"))
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    created_at: Mapped[datetime] = _created_at()
    updated_at: Mapped[datetime] = _updated_at()


class FormulationRecipeReference(Base):
    __tablename__ = "formulation_recipe_reference"
    __table_args__ = (
        Index(
            "uq_formulation_recipe_reference",
            "formulation_id",
            "recipe_reference_id",
            unique=True,
        ),
        ForeignKeyConstraint(
            ["formulation_id", "organization_id"],
            ["formulation.id", "formulation.organization_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["recipe_reference_id", "organization_id"],
            ["recipe_reference.id", "recipe_reference.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    formulation_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    recipe_reference_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    role: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = _created_at()


class FormulationVersion(Base):
    __tablename__ = "formulation_version"
    __table_args__ = (
        Index("uq_formulation_version_number", "formulation_id", "version_number", unique=True),
        Index("uq_formulation_version_id_org", "id", "organization_id", unique=True),
        Index(
            "uq_formulation_version_published",
            "formulation_id",
            unique=True,
            postgresql_where=text("status = 'published'"),
        ),
        ForeignKeyConstraint(
            ["formulation_id", "organization_id"],
            ["formulation.id", "formulation.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    formulation_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'draft'"))
    yield_units: Mapped[int | None] = mapped_column(Integer)
    target_unit_weight_g: Mapped[Decimal | None] = mapped_column(Numeric(14, 6))
    expected_bake_loss_rate: Mapped[Decimal | None] = mapped_column(Numeric(20, 10))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = _created_at()
    created_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("app_user.id", ondelete="RESTRICT")
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))


class FormulationVersionRecipeReference(Base):
    __tablename__ = "formulation_version_recipe_reference"
    __table_args__ = (
        Index(
            "uq_formulation_version_recipe_reference",
            "formulation_version_id",
            "recipe_reference_id",
            unique=True,
            postgresql_where=text("recipe_reference_id IS NOT NULL"),
        ),
        Index(
            "uq_formulation_version_fragment_ref",
            "formulation_version_id",
            "knowledge_fragment_id",
            unique=True,
            postgresql_where=text("knowledge_fragment_id IS NOT NULL"),
        ),
        Index(
            "uq_formulation_version_ref_id_org",
            "id",
            "organization_id",
            unique=True,
        ),
        ForeignKeyConstraint(
            ["formulation_version_id", "organization_id"],
            ["formulation_version.id", "formulation_version.organization_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["recipe_reference_id", "organization_id"],
            ["recipe_reference.id", "recipe_reference.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    formulation_version_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    recipe_reference_id: Mapped[UUID | None] = mapped_column(Uuid)
    knowledge_source_version_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("knowledge_source_version.id", ondelete="RESTRICT")
    )
    knowledge_fragment_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("knowledge_fragment.id", ondelete="RESTRICT")
    )
    role: Mapped[str] = mapped_column(Text, nullable=False)
    source_version_label: Mapped[str | None] = mapped_column(Text)
    locator_type: Mapped[str | None] = mapped_column(Text)
    locator_value: Mapped[str | None] = mapped_column(Text)
    content_hash: Mapped[str | None] = mapped_column(Text)
    accessed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    snapshot: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    copied_from_version_id: Mapped[UUID | None] = mapped_column(Uuid)
    created_at: Mapped[datetime] = _created_at()


class FormulationItem(Base):
    __tablename__ = "formulation_item"
    __table_args__ = (
        Index("uq_formulation_item_sequence", "formulation_version_id", "sequence", unique=True),
        Index("uq_formulation_item_id_org", "id", "organization_id", unique=True),
        ForeignKeyConstraint(
            ["formulation_version_id", "organization_id"],
            ["formulation_version.id", "formulation_version.organization_id"],
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
    formulation_version_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    ingredient_version_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    net_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 6), nullable=False)
    measurement_unit_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("measurement_unit.id", ondelete="RESTRICT"), nullable=False
    )
    correction_factor: Mapped[Decimal] = mapped_column(
        Numeric(20, 10), nullable=False, server_default=text("1")
    )
    is_flour_basis: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    role: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'ingredient'"))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = _created_at()


class ProcessStep(Base):
    __tablename__ = "process_step"
    __table_args__ = (
        Index("uq_process_step_sequence", "formulation_version_id", "sequence", unique=True),
        Index("uq_process_step_id_org", "id", "organization_id", unique=True),
        ForeignKeyConstraint(
            ["formulation_version_id", "organization_id"],
            ["formulation_version.id", "formulation_version.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    formulation_version_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    instructions: Mapped[str] = mapped_column(Text, nullable=False)
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    temperature_celsius: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    created_at: Mapped[datetime] = _created_at()


class ScaleCalculation(Base):
    __tablename__ = "scale_calculation"
    __table_args__ = (
        Index("uq_scale_calculation_id_org", "id", "organization_id", unique=True),
        ForeignKeyConstraint(
            ["formulation_version_id", "organization_id"],
            ["formulation_version.id", "formulation_version.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    formulation_version_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    calculation_mode: Mapped[str] = mapped_column(Text, nullable=False)
    input_target_total_dough_mass: Mapped[Decimal | None] = mapped_column(Numeric(14, 6))
    input_unit_count: Mapped[int | None] = mapped_column(Integer)
    input_final_unit_weight_g: Mapped[Decimal | None] = mapped_column(Numeric(14, 6))
    input_bake_loss_rate: Mapped[Decimal | None] = mapped_column(Numeric(20, 10))
    base_total_net_mass: Mapped[Decimal] = mapped_column(Numeric(14, 6), nullable=False)
    scale_factor: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    required_pre_bake_mass: Mapped[Decimal] = mapped_column(Numeric(14, 6), nullable=False)
    algorithm_code: Mapped[str] = mapped_column(Text, nullable=False)
    algorithm_version: Mapped[str] = mapped_column(Text, nullable=False)
    rounding_mode: Mapped[str] = mapped_column(Text, nullable=False)
    presentation_decimal_places: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = _created_at()
    created_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("app_user.id", ondelete="RESTRICT")
    )


class ScaleCalculationItem(Base):
    __tablename__ = "scale_calculation_item"
    __table_args__ = (
        Index(
            "uq_scale_calculation_item_sequence",
            "scale_calculation_id",
            "sequence",
            unique=True,
        ),
        ForeignKeyConstraint(
            ["scale_calculation_id", "organization_id"],
            ["scale_calculation.id", "scale_calculation.organization_id"],
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
    scale_calculation_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    formulation_item_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    ingredient_version_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    scaled_net_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 6), nullable=False)
    scaled_gross_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 6), nullable=False)
    bakers_percentage: Mapped[Decimal | None] = mapped_column(Numeric(14, 6))
    measurement_unit_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("measurement_unit.id", ondelete="RESTRICT"), nullable=False
    )
    base_net_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 6), nullable=False)
    base_correction_factor: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    created_at: Mapped[datetime] = _created_at()


class Trial(Base):
    __tablename__ = "trial"
    __table_args__ = (
        Index("uq_trial_org_code", "organization_id", "code", unique=True),
        Index("uq_trial_id_org", "id", "organization_id", unique=True),
        ForeignKeyConstraint(
            ["formulation_version_id", "organization_id"],
            ["formulation_version.id", "formulation_version.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    formulation_version_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    code: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'planned'"))
    planned_on: Mapped[date | None] = mapped_column(Date)
    executed_on: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = _created_at()
    created_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("app_user.id", ondelete="RESTRICT")
    )


class TrialMeasurement(Base):
    __tablename__ = "trial_measurement"
    __table_args__ = (
        ForeignKeyConstraint(
            ["trial_id", "organization_id"],
            ["trial.id", "trial.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    trial_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    measurement_type: Mapped[str] = mapped_column(Text, nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric(14, 6), nullable=False)
    measurement_unit_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("measurement_unit.id", ondelete="RESTRICT")
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    notes: Mapped[str | None] = mapped_column(Text)


class Approval(Base):
    __tablename__ = "approval"
    __table_args__ = (
        Index("ix_approval_version_occurred", "formulation_version_id", "occurred_at"),
        ForeignKeyConstraint(
            ["formulation_version_id", "organization_id"],
            ["formulation_version.id", "formulation_version.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    formulation_version_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    actor_user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("app_user.id", ondelete="RESTRICT"), nullable=False
    )
    decision: Mapped[str] = mapped_column(Text, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("clock_timestamp()")
    )
    notes: Mapped[str | None] = mapped_column(Text)
    correlation_id: Mapped[UUID | None] = mapped_column(Uuid)


class FormulationCommand(Base):
    __tablename__ = "formulation_command"
    __table_args__ = (
        Index(
            "uq_formulation_command_idempotency",
            "organization_id",
            "idempotency_key",
            unique=True,
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("organization.id", ondelete="RESTRICT"), nullable=False
    )
    idempotency_key: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    command: Mapped[str] = mapped_column(Text, nullable=False)
    payload_digest: Mapped[str] = mapped_column(Text, nullable=False)
    resource_type: Mapped[str] = mapped_column(Text, nullable=False)
    resource_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    actor_user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("app_user.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = _created_at()
