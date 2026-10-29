"""Persistência do planejamento de produção. Sem execução real, custo ou HTTP."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
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


class ProductionCodeCounter(Base):
    __tablename__ = "production_code_counter"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "kind", "period", name="uq_production_code_counter_period"
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("organization.id", ondelete="RESTRICT"), nullable=False
    )
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    period: Mapped[str] = mapped_column(Text, nullable=False)
    last_value: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    created_at: Mapped[datetime] = _created_at()
    updated_at: Mapped[datetime] = _updated_at()


class ProductionPlan(Base):
    __tablename__ = "production_plan"
    __table_args__ = (
        Index("uq_production_plan_org_code", "organization_id", "public_code", unique=True),
        Index("uq_production_plan_id_org", "id", "organization_id", unique=True),
        ForeignKeyConstraint(
            ["establishment_id", "organization_id"],
            ["establishment.id", "establishment.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    establishment_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    public_code: Mapped[str] = mapped_column(Text, nullable=False)
    operational_date: Mapped[date] = mapped_column(Date, nullable=False)
    shift: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'draft'"))
    notes: Mapped[str | None] = mapped_column(Text)
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    created_by_user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("app_user.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = _created_at()
    updated_at: Mapped[datetime] = _updated_at()
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ProductionPlanItem(Base):
    __tablename__ = "production_plan_item"
    __table_args__ = (
        Index("uq_production_plan_item_sort", "production_plan_id", "sort_order", unique=True),
        Index("uq_production_plan_item_id_org", "id", "organization_id", unique=True),
        ForeignKeyConstraint(
            ["production_plan_id", "organization_id"],
            ["production_plan.id", "production_plan.organization_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["technical_product_id", "organization_id"],
            ["technical_product.id", "technical_product.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    production_plan_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    technical_product_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    target_mode: Mapped[str] = mapped_column(Text, nullable=False)
    target_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 6), nullable=False)
    unit_weight_g: Mapped[Decimal | None] = mapped_column(Numeric(14, 6))
    priority: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("50"))
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    desired_window_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    desired_window_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = _created_at()
    updated_at: Mapped[datetime] = _updated_at()


class ProductionOrder(Base):
    __tablename__ = "production_order"
    __table_args__ = (
        Index("uq_production_order_org_code", "organization_id", "public_code", unique=True),
        Index("uq_production_order_id_org", "id", "organization_id", unique=True),
        Index(
            "uq_production_order_active_item",
            "plan_item_id",
            unique=True,
            postgresql_where=text("plan_item_id IS NOT NULL AND status <> 'cancelled'"),
        ),
        ForeignKeyConstraint(
            ["establishment_id", "organization_id"],
            ["establishment.id", "establishment.organization_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["plan_id", "organization_id"],
            ["production_plan.id", "production_plan.organization_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["plan_item_id", "organization_id"],
            ["production_plan_item.id", "production_plan_item.organization_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["technical_product_id", "organization_id"],
            ["technical_product.id", "technical_product.organization_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["formulation_version_id", "organization_id"],
            ["formulation_version.id", "formulation_version.organization_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["scale_calculation_id", "organization_id"],
            ["scale_calculation.id", "scale_calculation.organization_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["superseded_order_id", "organization_id"],
            ["production_order.id", "production_order.organization_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["successor_order_id", "organization_id"],
            ["production_order.id", "production_order.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    establishment_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    public_code: Mapped[str] = mapped_column(Text, nullable=False)
    plan_id: Mapped[UUID | None] = mapped_column(Uuid)
    plan_item_id: Mapped[UUID | None] = mapped_column(Uuid)
    technical_product_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    formulation_version_id: Mapped[UUID | None] = mapped_column(Uuid)
    scale_calculation_id: Mapped[UUID | None] = mapped_column(Uuid)
    target_mode: Mapped[str] = mapped_column(Text, nullable=False)
    target_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 6), nullable=False)
    unit_weight_g: Mapped[Decimal | None] = mapped_column(Numeric(14, 6))
    priority: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("50"))
    planned_start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    planned_end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'draft'"))
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    assigned_user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("app_user.id", ondelete="RESTRICT")
    )
    created_by_user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("app_user.id", ondelete="RESTRICT"), nullable=False
    )
    scheduled_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("app_user.id", ondelete="RESTRICT")
    )
    released_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("app_user.id", ondelete="RESTRICT")
    )
    cancelled_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("app_user.id", ondelete="RESTRICT")
    )
    created_at: Mapped[datetime] = _created_at()
    updated_at: Mapped[datetime] = _updated_at()
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    held_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancel_reason: Mapped[str | None] = mapped_column(Text)
    hold_reason: Mapped[str | None] = mapped_column(Text)
    superseded_order_id: Mapped[UUID | None] = mapped_column(Uuid)
    successor_order_id: Mapped[UUID | None] = mapped_column(Uuid)
    materials_hash: Mapped[str | None] = mapped_column(Text)
    steps_hash: Mapped[str | None] = mapped_column(Text)
    snapshot_hash: Mapped[str | None] = mapped_column(Text)
    held_from_status: Mapped[str | None] = mapped_column(Text)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("app_user.id", ondelete="RESTRICT")
    )
    short_closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    short_closed_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("app_user.id", ondelete="RESTRICT")
    )
    short_close_reason: Mapped[str | None] = mapped_column(Text)


class ProductionOrderDependency(Base):
    __tablename__ = "production_order_dependency"
    __table_args__ = (
        Index(
            "uq_production_order_dependency_pair",
            "dependent_order_id",
            "predecessor_order_id",
            unique=True,
        ),
        Index("uq_production_order_dependency_id_org", "id", "organization_id", unique=True),
        ForeignKeyConstraint(
            ["dependent_order_id", "organization_id"],
            ["production_order.id", "production_order.organization_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["predecessor_order_id", "organization_id"],
            ["production_order.id", "production_order.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    dependent_order_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    predecessor_order_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    dependency_type: Mapped[str] = mapped_column(Text, nullable=False)
    relation_note: Mapped[str | None] = mapped_column(Text)
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(14, 6))
    created_at: Mapped[datetime] = _created_at()


class ProductionBatch(Base):
    __tablename__ = "production_batch"
    __table_args__ = (
        Index("uq_production_batch_sequence", "production_order_id", "sequence", unique=True),
        Index("uq_production_batch_id_org", "id", "organization_id", unique=True),
        ForeignKeyConstraint(
            ["production_order_id", "organization_id"],
            ["production_order.id", "production_order.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    production_order_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    operational_code: Mapped[str] = mapped_column(Text, nullable=False)
    target_mode: Mapped[str] = mapped_column(Text, nullable=False)
    target_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 6), nullable=False)
    split_factor: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    remainder_applied: Mapped[Decimal] = mapped_column(
        Numeric(14, 6), nullable=False, server_default=text("0")
    )
    split_memory: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    planned_start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    planned_end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'pending'"))
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    held_from_status: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    short_closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = _created_at()
    updated_at: Mapped[datetime] = _updated_at()


class ProductionOrderMaterial(Base):
    __tablename__ = "production_order_material"
    __table_args__ = (
        Index(
            "uq_production_order_material_seq",
            "production_order_id",
            "presentation_sequence",
            unique=True,
        ),
        Index("uq_production_order_material_id_org", "id", "organization_id", unique=True),
        ForeignKeyConstraint(
            ["production_order_id", "organization_id"],
            ["production_order.id", "production_order.organization_id"],
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
    production_order_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    formulation_item_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    ingredient_version_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    operational_name: Mapped[str] = mapped_column(Text, nullable=False)
    measurement_unit_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("measurement_unit.id", ondelete="RESTRICT"), nullable=False
    )
    unit_code: Mapped[str] = mapped_column(Text, nullable=False)
    unit_name: Mapped[str] = mapped_column(Text, nullable=False)
    net_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 6), nullable=False)
    correction_factor: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    gross_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 6), nullable=False)
    bakers_percentage: Mapped[Decimal | None] = mapped_column(Numeric(14, 6))
    is_flour_basis: Mapped[bool] = mapped_column(Boolean, nullable=False)
    presentation_sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    algorithm_code: Mapped[str] = mapped_column(Text, nullable=False)
    algorithm_version: Mapped[str] = mapped_column(Text, nullable=False)
    rounding_mode: Mapped[str] = mapped_column(Text, nullable=False)
    presentation_decimal_places: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = _created_at()


class ProductionOrderStep(Base):
    __tablename__ = "production_order_step"
    __table_args__ = (
        Index("uq_production_order_step_seq", "production_order_id", "sequence", unique=True),
        Index("uq_production_order_step_id_org", "id", "organization_id", unique=True),
        ForeignKeyConstraint(
            ["production_order_id", "organization_id"],
            ["production_order.id", "production_order.organization_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["process_step_id", "organization_id"],
            ["process_step.id", "process_step.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    production_order_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    process_step_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    instructions: Mapped[str] = mapped_column(Text, nullable=False)
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    temperature_value: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    temperature_unit: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    control_points: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    created_at: Mapped[datetime] = _created_at()


class ProductionBatchMaterial(Base):
    __tablename__ = "production_batch_material"
    __table_args__ = (
        Index(
            "uq_production_batch_material_line",
            "production_batch_id",
            "production_order_material_id",
            unique=True,
        ),
        ForeignKeyConstraint(
            ["production_batch_id", "organization_id"],
            ["production_batch.id", "production_batch.organization_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["production_order_material_id", "organization_id"],
            ["production_order_material.id", "production_order_material.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    production_batch_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    production_order_material_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    planned_net_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 6), nullable=False)
    planned_gross_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 6), nullable=False)
    remainder_applied: Mapped[Decimal] = mapped_column(
        Numeric(14, 6), nullable=False, server_default=text("0")
    )
    created_at: Mapped[datetime] = _created_at()


class ProductionEvent(Base):
    __tablename__ = "production_event"
    __table_args__ = (
        Index(
            "uq_production_event_idempotency",
            "organization_id",
            "idempotency_key",
            unique=True,
        ),
        Index("ix_production_event_stable_order", "organization_id", "sequence_no"),
        ForeignKeyConstraint(
            ["plan_id", "organization_id"],
            ["production_plan.id", "production_plan.organization_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["order_id", "organization_id"],
            ["production_order.id", "production_order.organization_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["batch_id", "organization_id"],
            ["production_batch.id", "production_batch.organization_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["causation_event_id"],
            ["production_event.id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    establishment_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("establishment.id", ondelete="RESTRICT"), nullable=False
    )
    plan_id: Mapped[UUID | None] = mapped_column(Uuid)
    order_id: Mapped[UUID | None] = mapped_column(Uuid)
    batch_id: Mapped[UUID | None] = mapped_column(Uuid)
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    command: Mapped[str] = mapped_column(Text, nullable=False)
    actor_user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("app_user.id", ondelete="RESTRICT"), nullable=False
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("clock_timestamp()")
    )
    correlation_id: Mapped[UUID | None] = mapped_column(Uuid)
    causation_event_id: Mapped[UUID | None] = mapped_column(Uuid)
    idempotency_key: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    payload_digest: Mapped[str] = mapped_column(Text, nullable=False)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    sequence_no: Mapped[int] = mapped_column(
        BigInteger, nullable=False, server_default=text("nextval('production_event_seq')")
    )
