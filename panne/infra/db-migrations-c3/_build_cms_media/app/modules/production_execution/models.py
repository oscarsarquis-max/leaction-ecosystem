"""Persistência da execução de produção. Sem estoque, custo ou HTTP."""

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


class ProductionExecutionPolicy(Base):
    __tablename__ = "production_execution_policy"
    __table_args__ = (
        Index("uq_production_execution_policy_order", "production_order_id", unique=True),
        Index("uq_production_execution_policy_id_org", "id", "organization_id", unique=True),
        ForeignKeyConstraint(
            ["production_order_id", "organization_id"],
            ["production_order.id", "production_order.organization_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["establishment_id", "organization_id"],
            ["establishment.id", "establishment.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    establishment_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    production_order_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    weighing_policy: Mapped[str] = mapped_column(Text, nullable=False)
    verification_policy: Mapped[str] = mapped_column(Text, nullable=False)
    absolute_tolerance: Mapped[Decimal | None] = mapped_column(Numeric(14, 6))
    percent_tolerance: Mapped[Decimal | None] = mapped_column(Numeric(14, 6))
    completion_tolerance: Mapped[Decimal] = mapped_column(Numeric(14, 6), nullable=False)
    allow_short_close: Mapped[bool] = mapped_column(Boolean, nullable=False)
    require_manual_lot: Mapped[bool] = mapped_column(Boolean, nullable=False)
    algorithm_code: Mapped[str] = mapped_column(Text, nullable=False)
    algorithm_version: Mapped[str] = mapped_column(Text, nullable=False)
    created_by_user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("app_user.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = _created_at()
    frozen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    frozen_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("app_user.id", ondelete="RESTRICT")
    )
    policy_hash: Mapped[str | None] = mapped_column(Text)


class ProductionWeighingSession(Base):
    __tablename__ = "production_weighing_session"
    __table_args__ = (
        Index("uq_production_weighing_session_id_org", "id", "organization_id", unique=True),
        Index(
            "uq_production_weighing_session_idem",
            "organization_id",
            "idempotency_key",
            unique=True,
        ),
        Index(
            "uq_production_weighing_session_open_batch",
            "production_batch_id",
            unique=True,
            postgresql_where=text("status = 'open'"),
        ),
        ForeignKeyConstraint(
            ["production_order_id", "organization_id"],
            ["production_order.id", "production_order.organization_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["production_batch_id", "organization_id"],
            ["production_batch.id", "production_batch.organization_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["establishment_id", "organization_id"],
            ["establishment.id", "establishment.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    establishment_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    production_order_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    production_batch_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'open'"))
    opened_by_user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("app_user.id", ondelete="RESTRICT"), nullable=False
    )
    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("app_user.id", ondelete="RESTRICT")
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("app_user.id", ondelete="RESTRICT")
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancel_reason: Mapped[str | None] = mapped_column(Text)
    idempotency_key: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))


class ProductionWeighingEntry(Base):
    __tablename__ = "production_weighing_entry"
    __table_args__ = (
        Index("uq_production_weighing_entry_id_org", "id", "organization_id", unique=True),
        Index(
            "uq_production_weighing_entry_idem",
            "organization_id",
            "idempotency_key",
            unique=True,
        ),
        ForeignKeyConstraint(
            ["session_id", "organization_id"],
            ["production_weighing_session.id", "production_weighing_session.organization_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["production_batch_material_id", "organization_id"],
            ["production_batch_material.id", "production_batch_material.organization_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["original_entry_id", "organization_id"],
            ["production_weighing_entry.id", "production_weighing_entry.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    session_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    production_batch_material_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    entry_type: Mapped[str] = mapped_column(Text, nullable=False)
    original_entry_id: Mapped[UUID | None] = mapped_column(Uuid)
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 6), nullable=False)
    measurement_unit_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("measurement_unit.id", ondelete="RESTRICT"), nullable=False
    )
    unit_code: Mapped[str] = mapped_column(Text, nullable=False)
    canonical_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 6), nullable=False)
    canonical_unit_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("measurement_unit.id", ondelete="RESTRICT"), nullable=False
    )
    canonical_unit_code: Mapped[str] = mapped_column(Text, nullable=False)
    conversion_factor: Mapped[Decimal] = mapped_column(Numeric(28, 10), nullable=False)
    conversion_source: Mapped[str] = mapped_column(Text, nullable=False)
    conversion_version: Mapped[str] = mapped_column(Text, nullable=False)
    planned_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 6), nullable=False)
    absolute_difference: Mapped[Decimal] = mapped_column(Numeric(14, 6), nullable=False)
    percent_difference: Mapped[Decimal] = mapped_column(Numeric(14, 6), nullable=False)
    within_tolerance: Mapped[bool] = mapped_column(Boolean, nullable=False)
    lot_code: Mapped[str | None] = mapped_column(Text)
    expires_on: Mapped[date | None] = mapped_column(Date)
    scale_reference: Mapped[str | None] = mapped_column(Text)
    operator_user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("app_user.id", ondelete="RESTRICT"), nullable=False
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("clock_timestamp()")
    )
    justification: Mapped[str | None] = mapped_column(Text)
    idempotency_key: Mapped[UUID] = mapped_column(Uuid, nullable=False)


class ProductionWeighingVerification(Base):
    __tablename__ = "production_weighing_verification"
    __table_args__ = (
        Index("uq_production_weighing_verification_id_org", "id", "organization_id", unique=True),
        Index(
            "uq_production_weighing_verification_idem",
            "organization_id",
            "idempotency_key",
            unique=True,
        ),
        ForeignKeyConstraint(
            ["entry_id", "organization_id"],
            ["production_weighing_entry.id", "production_weighing_entry.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    entry_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    decision: Mapped[str] = mapped_column(Text, nullable=False)
    verifier_user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("app_user.id", ondelete="RESTRICT"), nullable=False
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("clock_timestamp()")
    )
    justification: Mapped[str | None] = mapped_column(Text)
    idempotency_key: Mapped[UUID] = mapped_column(Uuid, nullable=False)


class ProductionMaterialConsumption(Base):
    __tablename__ = "production_material_consumption"
    __table_args__ = (
        Index("uq_production_material_consumption_id_org", "id", "organization_id", unique=True),
        Index(
            "uq_production_material_consumption_idem",
            "organization_id",
            "idempotency_key",
            unique=True,
        ),
        ForeignKeyConstraint(
            ["production_order_id", "organization_id"],
            ["production_order.id", "production_order.organization_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["production_batch_id", "organization_id"],
            ["production_batch.id", "production_batch.organization_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["production_batch_material_id", "organization_id"],
            ["production_batch_material.id", "production_batch_material.organization_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["weighing_entry_id", "organization_id"],
            ["production_weighing_entry.id", "production_weighing_entry.organization_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["corrects_id", "organization_id"],
            [
                "production_material_consumption.id",
                "production_material_consumption.organization_id",
            ],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    production_order_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    production_batch_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    production_batch_material_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    consumption_type: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 6), nullable=False)
    measurement_unit_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("measurement_unit.id", ondelete="RESTRICT"), nullable=False
    )
    unit_code: Mapped[str] = mapped_column(Text, nullable=False)
    canonical_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 6), nullable=False)
    canonical_unit_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("measurement_unit.id", ondelete="RESTRICT"), nullable=False
    )
    canonical_unit_code: Mapped[str] = mapped_column(Text, nullable=False)
    conversion_factor: Mapped[Decimal] = mapped_column(Numeric(28, 10), nullable=False)
    conversion_source: Mapped[str] = mapped_column(Text, nullable=False)
    conversion_version: Mapped[str] = mapped_column(Text, nullable=False)
    weighing_entry_id: Mapped[UUID | None] = mapped_column(Uuid)
    lot_code: Mapped[str | None] = mapped_column(Text)
    actor_user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("app_user.id", ondelete="RESTRICT"), nullable=False
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("clock_timestamp()")
    )
    reason: Mapped[str | None] = mapped_column(Text)
    corrects_id: Mapped[UUID | None] = mapped_column(Uuid)
    idempotency_key: Mapped[UUID] = mapped_column(Uuid, nullable=False)


class ProductionStepExecution(Base):
    __tablename__ = "production_step_execution"
    __table_args__ = (
        Index("uq_production_step_execution_id_org", "id", "organization_id", unique=True),
        Index(
            "uq_production_step_execution_batch_step",
            "production_batch_id",
            "production_order_step_id",
            unique=True,
        ),
        ForeignKeyConstraint(
            ["production_order_id", "organization_id"],
            ["production_order.id", "production_order.organization_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["production_batch_id", "organization_id"],
            ["production_batch.id", "production_batch.organization_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["production_order_step_id", "organization_id"],
            ["production_order_step.id", "production_order_step.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    production_order_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    production_batch_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    production_order_step_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'pending'"))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    operator_user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("app_user.id", ondelete="RESTRICT")
    )
    measured_duration_seconds: Mapped[int | None] = mapped_column(Integer)
    measured_temperature: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    measured_time_seconds: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))


class ProductionStepExecutionEvent(Base):
    __tablename__ = "production_step_execution_event"
    __table_args__ = (
        Index("uq_production_step_execution_event_id_org", "id", "organization_id", unique=True),
        ForeignKeyConstraint(
            ["execution_id", "organization_id"],
            ["production_step_execution.id", "production_step_execution.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    execution_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    from_status: Mapped[str] = mapped_column(Text, nullable=False)
    to_status: Mapped[str] = mapped_column(Text, nullable=False)
    actor_user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("app_user.id", ondelete="RESTRICT"), nullable=False
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("clock_timestamp()")
    )
    notes: Mapped[str | None] = mapped_column(Text)


class ProductionYieldMeasurement(Base):
    __tablename__ = "production_yield_measurement"
    __table_args__ = (
        Index("uq_production_yield_measurement_id_org", "id", "organization_id", unique=True),
        Index(
            "uq_production_yield_measurement_idem",
            "organization_id",
            "idempotency_key",
            unique=True,
        ),
        ForeignKeyConstraint(
            ["production_order_id", "organization_id"],
            ["production_order.id", "production_order.organization_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["production_batch_id", "organization_id"],
            ["production_batch.id", "production_batch.organization_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["reverses_id", "organization_id"],
            ["production_yield_measurement.id", "production_yield_measurement.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    production_order_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    production_batch_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    measurement_type: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 6), nullable=False)
    measurement_unit_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("measurement_unit.id", ondelete="RESTRICT"), nullable=False
    )
    unit_code: Mapped[str] = mapped_column(Text, nullable=False)
    actor_user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("app_user.id", ondelete="RESTRICT"), nullable=False
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("clock_timestamp()")
    )
    notes: Mapped[str | None] = mapped_column(Text)
    reverses_id: Mapped[UUID | None] = mapped_column(Uuid)
    idempotency_key: Mapped[UUID] = mapped_column(Uuid, nullable=False)


class ProductionOccurrence(Base):
    __tablename__ = "production_occurrence"
    __table_args__ = (
        Index("uq_production_occurrence_id_org", "id", "organization_id", unique=True),
        ForeignKeyConstraint(
            ["production_order_id", "organization_id"],
            ["production_order.id", "production_order.organization_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["production_batch_id", "organization_id"],
            ["production_batch.id", "production_batch.organization_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["production_order_step_id", "organization_id"],
            ["production_order_step.id", "production_order_step.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    production_order_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    production_batch_id: Mapped[UUID | None] = mapped_column(Uuid)
    production_order_step_id: Mapped[UUID | None] = mapped_column(Uuid)
    category: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    is_blocking: Mapped[bool] = mapped_column(Boolean, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'open'"))
    opened_by_user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("app_user.id", ondelete="RESTRICT"), nullable=False
    )
    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("clock_timestamp()")
    )
    evidence_refs: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )


class ProductionOccurrenceEvent(Base):
    __tablename__ = "production_occurrence_event"
    __table_args__ = (
        Index("uq_production_occurrence_event_id_org", "id", "organization_id", unique=True),
        ForeignKeyConstraint(
            ["occurrence_id", "organization_id"],
            ["production_occurrence.id", "production_occurrence.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    occurrence_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    actor_user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("app_user.id", ondelete="RESTRICT"), nullable=False
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("clock_timestamp()")
    )
    notes: Mapped[str | None] = mapped_column(Text)


class ProductionDependencyOverride(Base):
    __tablename__ = "production_dependency_override"
    __table_args__ = (
        Index("uq_production_dependency_override_id_org", "id", "organization_id", unique=True),
        Index(
            "uq_production_dependency_override_idem",
            "organization_id",
            "idempotency_key",
            unique=True,
        ),
        ForeignKeyConstraint(
            ["dependency_id", "organization_id"],
            ["production_order_dependency.id", "production_order_dependency.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    dependency_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    predecessor_status: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    actor_user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("app_user.id", ondelete="RESTRICT"), nullable=False
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("clock_timestamp()")
    )
    idempotency_key: Mapped[UUID] = mapped_column(Uuid, nullable=False)


class ProductionSheetIssue(Base):
    __tablename__ = "production_sheet_issue"
    __table_args__ = (
        Index("uq_production_sheet_issue_id_org", "id", "organization_id", unique=True),
        Index("uq_production_sheet_issue_number", "organization_id", "issue_number", unique=True),
        Index(
            "uq_production_sheet_issue_idem",
            "organization_id",
            "idempotency_key",
            unique=True,
        ),
        ForeignKeyConstraint(
            ["production_order_id", "organization_id"],
            ["production_order.id", "production_order.organization_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["production_batch_id", "organization_id"],
            ["production_batch.id", "production_batch.organization_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["establishment_id", "organization_id"],
            ["establishment.id", "establishment.organization_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["previous_issue_id", "organization_id"],
            ["production_sheet_issue.id", "production_sheet_issue.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    establishment_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    production_order_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    production_batch_id: Mapped[UUID | None] = mapped_column(Uuid)
    issue_number: Mapped[int] = mapped_column(Integer, nullable=False)
    template_version: Mapped[str] = mapped_column(Text, nullable=False)
    canonical_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    payload_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    issued_by_user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("app_user.id", ondelete="RESTRICT"), nullable=False
    )
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("clock_timestamp()")
    )
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    order_status_at_issue: Mapped[str] = mapped_column(Text, nullable=False)
    previous_issue_id: Mapped[UUID | None] = mapped_column(Uuid)
    idempotency_key: Mapped[UUID] = mapped_column(Uuid, nullable=False)
