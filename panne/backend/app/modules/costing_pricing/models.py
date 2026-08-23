"""Persistência de custeio e preços. Cálculos e decisões append-only."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
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


class CostingPolicy(Base):
    __tablename__ = "costing_policy"
    __table_args__ = (
        Index("uq_costing_policy_id_org", "id", "organization_id", unique=True),
        Index("uq_costing_policy_org_code", "organization_id", "code", unique=True),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    code: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="draft")
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    created_by_user_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    created_at: Mapped[datetime] = _created_at()


class CostingPolicyVersion(Base):
    __tablename__ = "costing_policy_version"
    __table_args__ = (
        Index("uq_costing_policy_version_id_org", "id", "organization_id", unique=True),
        Index(
            "uq_costing_policy_version_number",
            "costing_policy_id",
            "version_number",
            unique=True,
        ),
        ForeignKeyConstraint(
            ["costing_policy_id", "organization_id"],
            ["costing_policy.id", "costing_policy.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    costing_policy_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="draft")
    currency: Mapped[str] = mapped_column(Text, nullable=False, server_default="BRL")
    timezone: Mapped[str] = mapped_column(Text, nullable=False, server_default="America/Sao_Paulo")
    price_criterion: Mapped[str] = mapped_column(Text, nullable=False)
    use_gross_quantity: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    include_return: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    include_waste: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    include_leftover: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    include_scrap: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    use_sellable_yield: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    enabled_categories: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    allocation_notes: Mapped[str | None] = mapped_column(Text)
    presentation_decimals: Mapped[int] = mapped_column(Integer, nullable=False, server_default="2")
    justification: Mapped[str | None] = mapped_column(Text)
    algorithm_name: Mapped[str] = mapped_column(Text, nullable=False)
    algorithm_version: Mapped[str] = mapped_column(Text, nullable=False)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by_user_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    created_at: Mapped[datetime] = _created_at()


class CostingAssumption(Base):
    __tablename__ = "costing_assumption"
    __table_args__ = (
        Index("uq_costing_assumption_id_org", "id", "organization_id", unique=True),
        ForeignKeyConstraint(
            ["costing_policy_version_id", "organization_id"],
            ["costing_policy_version.id", "costing_policy_version.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    costing_policy_version_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    category: Mapped[str] = mapped_column(Text, nullable=False)
    code: Mapped[str] = mapped_column(Text, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    unit_code: Mapped[str] = mapped_column(Text, nullable=False)
    currency: Mapped[str] = mapped_column(Text, nullable=False)
    channel: Mapped[str | None] = mapped_column(Text)
    nature: Mapped[str] = mapped_column(Text, nullable=False)
    behavior: Mapped[str] = mapped_column(Text, nullable=False)
    quality: Mapped[str] = mapped_column(Text, nullable=False, server_default="manual_assumption")
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by_user_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    created_at: Mapped[datetime] = _created_at()


class CostingCalculation(Base):
    __tablename__ = "costing_calculation"
    __table_args__ = (
        Index("uq_costing_calculation_id_org", "id", "organization_id", unique=True),
        ForeignKeyConstraint(
            ["costing_policy_version_id", "organization_id"],
            ["costing_policy_version.id", "costing_policy_version.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    establishment_id: Mapped[UUID | None] = mapped_column(Uuid)
    costing_policy_version_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    completeness: Mapped[str] = mapped_column(Text, nullable=False)
    technical_product_id: Mapped[UUID | None] = mapped_column(Uuid)
    formulation_id: Mapped[UUID | None] = mapped_column(Uuid)
    formulation_version_id: Mapped[UUID | None] = mapped_column(Uuid)
    scale_calculation_id: Mapped[UUID | None] = mapped_column(Uuid)
    production_order_id: Mapped[UUID | None] = mapped_column(Uuid)
    production_batch_id: Mapped[UUID | None] = mapped_column(Uuid)
    valuation_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    currency: Mapped[str] = mapped_column(Text, nullable=False)
    total_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    batch_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    mass_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    produced_unit_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    sellable_unit_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    produced_quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    sellable_quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    content_hash: Mapped[str] = mapped_column(Text, nullable=False)
    algorithm_name: Mapped[str] = mapped_column(Text, nullable=False)
    algorithm_version: Mapped[str] = mapped_column(Text, nullable=False)
    created_by_user_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    created_at: Mapped[datetime] = _created_at()


class CostingComponent(Base):
    __tablename__ = "costing_component"
    __table_args__ = (
        Index("uq_costing_component_id_org", "id", "organization_id", unique=True),
        Index(
            "uq_costing_component_origin",
            "costing_calculation_id",
            "origin_type",
            "origin_id",
            unique=True,
        ),
        ForeignKeyConstraint(
            ["costing_calculation_id", "organization_id"],
            ["costing_calculation.id", "costing_calculation.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    costing_calculation_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    category: Mapped[str] = mapped_column(Text, nullable=False)
    origin_type: Mapped[str] = mapped_column(Text, nullable=False)
    origin_id: Mapped[str] = mapped_column(Text, nullable=False)
    nature: Mapped[str] = mapped_column(Text, nullable=False)
    behavior: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    unit_code: Mapped[str | None] = mapped_column(Text)
    rate: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    quality: Mapped[str] = mapped_column(Text, nullable=False)
    allocation_rule: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = _created_at()


class CostingEvidence(Base):
    __tablename__ = "costing_evidence"
    __table_args__ = (
        Index("uq_costing_evidence_id_org", "id", "organization_id", unique=True),
        ForeignKeyConstraint(
            ["costing_component_id", "organization_id"],
            ["costing_component.id", "costing_component.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    costing_component_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    created_at: Mapped[datetime] = _created_at()


class CostingGap(Base):
    __tablename__ = "costing_gap"
    __table_args__ = (
        Index("uq_costing_gap_id_org", "id", "organization_id", unique=True),
        ForeignKeyConstraint(
            ["costing_calculation_id", "organization_id"],
            ["costing_calculation.id", "costing_calculation.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    costing_calculation_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    code: Mapped[str] = mapped_column(Text, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = _created_at()


class CostingInvalidation(Base):
    __tablename__ = "costing_invalidation"
    __table_args__ = (
        Index("uq_costing_invalidation_id_org", "id", "organization_id", unique=True),
        ForeignKeyConstraint(
            ["costing_calculation_id", "organization_id"],
            ["costing_calculation.id", "costing_calculation.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    costing_calculation_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_by_user_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    created_at: Mapped[datetime] = _created_at()


class PricingSimulation(Base):
    __tablename__ = "pricing_simulation"
    __table_args__ = (
        Index("uq_pricing_simulation_id_org", "id", "organization_id", unique=True),
        ForeignKeyConstraint(
            ["costing_calculation_id", "organization_id"],
            ["costing_calculation.id", "costing_calculation.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    costing_calculation_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    channel: Mapped[str] = mapped_column(Text, nullable=False)
    suggested_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    warning: Mapped[str | None] = mapped_column(Text)
    snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    content_hash: Mapped[str] = mapped_column(Text, nullable=False)
    created_by_user_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    created_at: Mapped[datetime] = _created_at()


class PricingSimulationComponent(Base):
    __tablename__ = "pricing_simulation_component"
    __table_args__ = (
        Index("uq_pricing_sim_component_id_org", "id", "organization_id", unique=True),
        ForeignKeyConstraint(
            ["pricing_simulation_id", "organization_id"],
            ["pricing_simulation.id", "pricing_simulation.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    pricing_simulation_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    code: Mapped[str] = mapped_column(Text, nullable=False)
    amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    rate: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = _created_at()


class PricingDecision(Base):
    __tablename__ = "pricing_decision"
    __table_args__ = (
        Index("uq_pricing_decision_id_org", "id", "organization_id", unique=True),
        ForeignKeyConstraint(
            ["practiced_price_id", "organization_id"],
            ["practiced_price.id", "practiced_price.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    practiced_price_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    decision: Mapped[str] = mapped_column(Text, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    created_by_user_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    created_at: Mapped[datetime] = _created_at()


class PracticedPrice(Base):
    __tablename__ = "practiced_price"
    __table_args__ = (
        Index("uq_practiced_price_id_org", "id", "organization_id", unique=True),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    establishment_id: Mapped[UUID | None] = mapped_column(Uuid)
    technical_product_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    channel: Mapped[str] = mapped_column(Text, nullable=False)
    currency: Mapped[str] = mapped_column(Text, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    pricing_simulation_id: Mapped[UUID | None] = mapped_column(Uuid)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="draft")
    justification: Mapped[str | None] = mapped_column(Text)
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    created_by_user_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    created_at: Mapped[datetime] = _created_at()


class CostingCommand(Base):
    __tablename__ = "costing_command"
    __table_args__ = (
        Index("uq_costing_command_id_org", "id", "organization_id", unique=True),
        Index(
            "uq_costing_command_idempotency",
            "organization_id",
            "idempotency_key",
            unique=True,
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    idempotency_key: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    command: Mapped[str] = mapped_column(Text, nullable=False)
    payload_digest: Mapped[str] = mapped_column(Text, nullable=False)
    resource_type: Mapped[str] = mapped_column(Text, nullable=False)
    resource_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    actor_user_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    created_at: Mapped[datetime] = _created_at()
