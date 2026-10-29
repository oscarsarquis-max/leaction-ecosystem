"""Persistência de estoque e compras. Movimentos e contagens são append-only."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Boolean,
    Date,
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


class InventoryPolicy(Base):
    __tablename__ = "inventory_policy"
    __table_args__ = (
        Index("uq_inventory_policy_id_org", "id", "organization_id", unique=True),
        Index("uq_inventory_policy_org_code", "organization_id", "code", unique=True),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    establishment_id: Mapped[UUID | None] = mapped_column(Uuid)
    code: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="draft")
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    created_by_user_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    created_at: Mapped[datetime] = _created_at()


class InventoryPolicyVersion(Base):
    __tablename__ = "inventory_policy_version"
    __table_args__ = (
        Index("uq_inventory_policy_version_id_org", "id", "organization_id", unique=True),
        Index(
            "uq_inventory_policy_version_number",
            "inventory_policy_id",
            "version_number",
            unique=True,
        ),
        ForeignKeyConstraint(
            ["inventory_policy_id", "organization_id"],
            ["inventory_policy.id", "inventory_policy.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    inventory_policy_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="draft")
    allow_negative_balance: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    lot_mode: Mapped[str] = mapped_column(Text, nullable=False, server_default="optional")
    expiry_required: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    lot_consumption: Mapped[str] = mapped_column(Text, nullable=False, server_default="fefo_suggest")
    receipt_tolerance_percent: Mapped[Decimal] = mapped_column(
        Numeric(8, 4), nullable=False, server_default="0"
    )
    count_tolerance_percent: Mapped[Decimal] = mapped_column(
        Numeric(8, 4), nullable=False, server_default="0"
    )
    reserve_on_release: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    cancelled_order_treatment: Mapped[str] = mapped_column(
        Text, nullable=False, server_default="release_reservation"
    )
    return_restores_available: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    waste_reduces_physical: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    adjust_requires_approval: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    lock_location_on_count: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    expiry_alert_days: Mapped[int] = mapped_column(Integer, nullable=False, server_default="7")
    justification: Mapped[str | None] = mapped_column(Text)
    algorithm_name: Mapped[str] = mapped_column(Text, nullable=False)
    algorithm_version: Mapped[str] = mapped_column(Text, nullable=False)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by_user_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    created_at: Mapped[datetime] = _created_at()


class InventoryLocation(Base):
    __tablename__ = "inventory_location"
    __table_args__ = (
        Index("uq_inventory_location_id_org", "id", "organization_id", unique=True),
        Index("uq_inventory_location_org_code", "organization_id", "code", unique=True),
        ForeignKeyConstraint(
            ["establishment_id", "organization_id"],
            ["establishment.id", "establishment.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    establishment_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    code: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="active")
    responsible_user_id: Mapped[UUID | None] = mapped_column(Uuid)
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    created_by_user_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    created_at: Mapped[datetime] = _created_at()


class InventoryItem(Base):
    __tablename__ = "inventory_item"
    __table_args__ = (
        Index("uq_inventory_item_id_org", "id", "organization_id", unique=True),
        Index("uq_inventory_item_ingredient", "organization_id", "ingredient_id", unique=True),
        ForeignKeyConstraint(
            ["ingredient_id", "organization_id"],
            ["ingredient.id", "ingredient.organization_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["preferred_supplier_id", "organization_id"],
            ["supplier.id", "supplier.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    ingredient_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    unit_code: Mapped[str] = mapped_column(Text, nullable=False)
    lot_control: Mapped[str] = mapped_column(Text, nullable=False, server_default="optional")
    expiry_control: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    reorder_point: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    safety_stock: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    target_quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    preferred_supplier_id: Mapped[UUID | None] = mapped_column(Uuid)
    preferred_supplier_item_id: Mapped[UUID | None] = mapped_column(Uuid)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="active")
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    created_by_user_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    created_at: Mapped[datetime] = _created_at()


class InventoryLot(Base):
    __tablename__ = "inventory_lot"
    __table_args__ = (
        Index("uq_inventory_lot_id_org", "id", "organization_id", unique=True),
        Index("uq_inventory_lot_internal", "organization_id", "internal_lot_code", unique=True),
        Index("ix_inventory_lot_expiry", "organization_id", "expires_on", "status"),
        ForeignKeyConstraint(
            ["inventory_item_id", "organization_id"],
            ["inventory_item.id", "inventory_item.organization_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["inventory_location_id", "organization_id"],
            ["inventory_location.id", "inventory_location.organization_id"],
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
    inventory_item_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    inventory_location_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    internal_lot_code: Mapped[str] = mapped_column(Text, nullable=False)
    supplier_lot_code: Mapped[str | None] = mapped_column(Text)
    supplier_id: Mapped[UUID | None] = mapped_column(Uuid)
    supplier_item_id: Mapped[UUID | None] = mapped_column(Uuid)
    manufactured_on: Mapped[date | None] = mapped_column(Date)
    expires_on: Mapped[date | None] = mapped_column(Date)
    procurement_receipt_id: Mapped[UUID | None] = mapped_column(Uuid)
    unit_code: Mapped[str] = mapped_column(Text, nullable=False)
    received_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="available")
    block_reason: Mapped[str | None] = mapped_column(Text)
    blocked_by_user_id: Mapped[UUID | None] = mapped_column(Uuid)
    blocked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    content_hash: Mapped[str] = mapped_column(Text, nullable=False)
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    created_by_user_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    created_at: Mapped[datetime] = _created_at()


class InventoryMovement(Base):
    __tablename__ = "inventory_movement"
    __table_args__ = (
        Index("uq_inventory_movement_id_org", "id", "organization_id", unique=True),
        Index("ix_inventory_movement_item", "organization_id", "inventory_item_id", "created_at"),
        Index("ix_inventory_movement_lot", "organization_id", "inventory_lot_id"),
        ForeignKeyConstraint(
            ["inventory_item_id", "organization_id"],
            ["inventory_item.id", "inventory_item.organization_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["inventory_policy_version_id", "organization_id"],
            ["inventory_policy_version.id", "inventory_policy_version.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    inventory_item_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    inventory_lot_id: Mapped[UUID | None] = mapped_column(Uuid)
    from_location_id: Mapped[UUID | None] = mapped_column(Uuid)
    to_location_id: Mapped[UUID | None] = mapped_column(Uuid)
    movement_type: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    unit_code: Mapped[str] = mapped_column(Text, nullable=False)
    canonical_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    conversion_factor: Mapped[Decimal] = mapped_column(Numeric(28, 10), nullable=False)
    sign: Mapped[int] = mapped_column(Integer, nullable=False)
    nature: Mapped[str] = mapped_column(Text, nullable=False)
    origin_type: Mapped[str] = mapped_column(Text, nullable=False)
    origin_id: Mapped[UUID | None] = mapped_column(Uuid)
    production_order_id: Mapped[UUID | None] = mapped_column(Uuid)
    production_batch_id: Mapped[UUID | None] = mapped_column(Uuid)
    production_material_consumption_id: Mapped[UUID | None] = mapped_column(Uuid)
    procurement_receipt_id: Mapped[UUID | None] = mapped_column(Uuid)
    inventory_count_session_id: Mapped[UUID | None] = mapped_column(Uuid)
    inventory_policy_version_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    actor_user_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    effective_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    correlation_id: Mapped[UUID | None] = mapped_column(Uuid)
    causation_id: Mapped[UUID | None] = mapped_column(Uuid)
    reverses_id: Mapped[UUID | None] = mapped_column(Uuid)
    content_hash: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = _created_at()


class InventoryBalance(Base):
    __tablename__ = "inventory_balance"
    __table_args__ = (
        Index("uq_inventory_balance_id_org", "id", "organization_id", unique=True),
        Index(
            "uq_inventory_balance_grain",
            "organization_id",
            "inventory_location_id",
            "inventory_item_id",
            "inventory_lot_id",
            unique=True,
        ),
        Index("ix_inventory_balance_item", "organization_id", "inventory_item_id"),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    establishment_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    inventory_location_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    inventory_item_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    inventory_lot_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    unit_code: Mapped[str] = mapped_column(Text, nullable=False)
    physical_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False, server_default="0")
    reserved_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False, server_default="0")
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_at: Mapped[datetime] = _created_at()


class InventoryReservation(Base):
    __tablename__ = "inventory_reservation"
    __table_args__ = (
        Index("uq_inventory_reservation_id_org", "id", "organization_id", unique=True),
        Index(
            "ix_inventory_reservation_order",
            "organization_id",
            "production_order_id",
            "status",
        ),
        ForeignKeyConstraint(
            ["inventory_item_id", "organization_id"],
            ["inventory_item.id", "inventory_item.organization_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["production_order_id", "organization_id"],
            ["production_order.id", "production_order.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    production_order_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    production_batch_id: Mapped[UUID | None] = mapped_column(Uuid)
    inventory_item_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    required_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    reserved_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False, server_default="0")
    unit_code: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    adopted: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    shortage_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False, server_default="0")
    reason: Mapped[str | None] = mapped_column(Text)
    inventory_policy_version_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    created_by_user_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    created_at: Mapped[datetime] = _created_at()


class InventoryReservationAllocation(Base):
    __tablename__ = "inventory_reservation_allocation"
    __table_args__ = (
        Index("uq_inventory_res_alloc_id_org", "id", "organization_id", unique=True),
        ForeignKeyConstraint(
            ["inventory_reservation_id", "organization_id"],
            ["inventory_reservation.id", "inventory_reservation.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    inventory_reservation_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    inventory_lot_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    inventory_location_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    created_at: Mapped[datetime] = _created_at()


class InventoryPick(Base):
    __tablename__ = "inventory_pick"
    __table_args__ = (
        Index("uq_inventory_pick_id_org", "id", "organization_id", unique=True),
        Index("uq_inventory_pick_code", "organization_id", "public_code", unique=True),
        ForeignKeyConstraint(
            ["production_order_id", "organization_id"],
            ["production_order.id", "production_order.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    public_code: Mapped[str] = mapped_column(Text, nullable=False)
    production_order_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    production_batch_id: Mapped[UUID | None] = mapped_column(Uuid)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="draft")
    inventory_policy_version_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    created_by_user_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    created_at: Mapped[datetime] = _created_at()


class InventoryPickLine(Base):
    __tablename__ = "inventory_pick_line"
    __table_args__ = (
        Index("uq_inventory_pick_line_id_org", "id", "organization_id", unique=True),
        ForeignKeyConstraint(
            ["inventory_pick_id", "organization_id"],
            ["inventory_pick.id", "inventory_pick.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    inventory_pick_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    inventory_item_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    inventory_lot_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    inventory_location_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    suggested: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    substituted: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = _created_at()


class InventoryConsumptionPosting(Base):
    __tablename__ = "inventory_consumption_posting"
    __table_args__ = (
        Index("uq_inventory_cons_post_id_org", "id", "organization_id", unique=True),
        Index(
            "uq_inventory_cons_post_origin",
            "organization_id",
            "production_material_consumption_id",
            unique=True,
        ),
        ForeignKeyConstraint(
            ["production_material_consumption_id", "organization_id"],
            [
                "production_material_consumption.id",
                "production_material_consumption.organization_id",
            ],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    production_material_consumption_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    inventory_movement_id: Mapped[UUID | None] = mapped_column(Uuid)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text)
    created_by_user_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    created_at: Mapped[datetime] = _created_at()


class InventoryCountSession(Base):
    __tablename__ = "inventory_count_session"
    __table_args__ = (
        Index("uq_inventory_count_id_org", "id", "organization_id", unique=True),
        Index("uq_inventory_count_code", "organization_id", "public_code", unique=True),
        ForeignKeyConstraint(
            ["inventory_location_id", "organization_id"],
            ["inventory_location.id", "inventory_location.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    public_code: Mapped[str] = mapped_column(Text, nullable=False)
    inventory_location_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    cutoff_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="draft")
    require_second_count: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    lock_location: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    inventory_policy_version_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    created_by_user_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    created_at: Mapped[datetime] = _created_at()


class InventoryCountScope(Base):
    __tablename__ = "inventory_count_scope"
    __table_args__ = (
        Index("uq_inventory_count_scope_id_org", "id", "organization_id", unique=True),
        ForeignKeyConstraint(
            ["inventory_count_session_id", "organization_id"],
            ["inventory_count_session.id", "inventory_count_session.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    inventory_count_session_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    inventory_item_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    inventory_lot_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    expected_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    created_at: Mapped[datetime] = _created_at()


class InventoryCountEntry(Base):
    __tablename__ = "inventory_count_entry"
    __table_args__ = (
        Index("uq_inventory_count_entry_id_org", "id", "organization_id", unique=True),
        ForeignKeyConstraint(
            ["inventory_count_session_id", "organization_id"],
            ["inventory_count_session.id", "inventory_count_session.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    inventory_count_session_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    inventory_count_scope_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    pass_number: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    actor_user_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    created_at: Mapped[datetime] = _created_at()


class InventoryCountReview(Base):
    __tablename__ = "inventory_count_review"
    __table_args__ = (
        Index("uq_inventory_count_review_id_org", "id", "organization_id", unique=True),
        ForeignKeyConstraint(
            ["inventory_count_session_id", "organization_id"],
            ["inventory_count_session.id", "inventory_count_session.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    inventory_count_session_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    decision: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    actor_user_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    created_at: Mapped[datetime] = _created_at()


class InventoryReplenishmentSuggestion(Base):
    __tablename__ = "inventory_replenishment_suggestion"
    __table_args__ = (
        Index("uq_inventory_replenish_id_org", "id", "organization_id", unique=True),
        Index("uq_inventory_replenish_code", "organization_id", "public_code", unique=True),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    public_code: Mapped[str] = mapped_column(Text, nullable=False)
    horizon_days: Mapped[int] = mapped_column(Integer, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    inventory_policy_version_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    created_by_user_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    created_at: Mapped[datetime] = _created_at()


class InventoryReplenishmentItem(Base):
    __tablename__ = "inventory_replenishment_item"
    __table_args__ = (
        Index("uq_inventory_replenish_item_id_org", "id", "organization_id", unique=True),
        ForeignKeyConstraint(
            ["inventory_replenishment_suggestion_id", "organization_id"],
            [
                "inventory_replenishment_suggestion.id",
                "inventory_replenishment_suggestion.organization_id",
            ],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    inventory_replenishment_suggestion_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    inventory_item_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    physical_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    reserved_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    available_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    in_transit_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    planned_demand: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    suggested_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    formula: Mapped[dict] = mapped_column(JSONB, nullable=False)
    gaps: Mapped[list] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    created_at: Mapped[datetime] = _created_at()


class ProcurementRequisition(Base):
    __tablename__ = "procurement_requisition"
    __table_args__ = (
        Index("uq_procurement_req_id_org", "id", "organization_id", unique=True),
        Index("uq_procurement_req_code", "organization_id", "public_code", unique=True),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    public_code: Mapped[str] = mapped_column(Text, nullable=False)
    establishment_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    inventory_location_id: Mapped[UUID | None] = mapped_column(Uuid)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="draft")
    needed_by: Mapped[date | None] = mapped_column(Date)
    justification: Mapped[str] = mapped_column(Text, nullable=False)
    origin_type: Mapped[str] = mapped_column(Text, nullable=False)
    origin_id: Mapped[UUID | None] = mapped_column(Uuid)
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    created_by_user_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    created_at: Mapped[datetime] = _created_at()


class ProcurementRequisitionItem(Base):
    __tablename__ = "procurement_requisition_item"
    __table_args__ = (
        Index("uq_procurement_req_item_id_org", "id", "organization_id", unique=True),
        ForeignKeyConstraint(
            ["procurement_requisition_id", "organization_id"],
            ["procurement_requisition.id", "procurement_requisition.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    procurement_requisition_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    inventory_item_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    unit_code: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = _created_at()


class ProcurementQuotation(Base):
    __tablename__ = "procurement_quotation"
    __table_args__ = (
        Index("uq_procurement_quote_id_org", "id", "organization_id", unique=True),
        ForeignKeyConstraint(
            ["supplier_id", "organization_id"],
            ["supplier.id", "supplier.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    supplier_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    valid_until: Mapped[date | None] = mapped_column(Date)
    lead_time_days: Mapped[int | None] = mapped_column(Integer)
    conditions: Mapped[str | None] = mapped_column(Text)
    evidence_ref: Mapped[str | None] = mapped_column(Text)
    currency: Mapped[str] = mapped_column(Text, nullable=False, server_default="BRL")
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    created_by_user_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    created_at: Mapped[datetime] = _created_at()


class ProcurementQuotationItem(Base):
    __tablename__ = "procurement_quotation_item"
    __table_args__ = (
        Index("uq_procurement_quote_item_id_org", "id", "organization_id", unique=True),
        ForeignKeyConstraint(
            ["procurement_quotation_id", "organization_id"],
            ["procurement_quotation.id", "procurement_quotation.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    procurement_quotation_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    inventory_item_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    supplier_item_id: Mapped[UUID | None] = mapped_column(Uuid)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    package_quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    unit_code: Mapped[str] = mapped_column(Text, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    currency: Mapped[str] = mapped_column(Text, nullable=False, server_default="BRL")
    created_at: Mapped[datetime] = _created_at()


class ProcurementOrder(Base):
    __tablename__ = "procurement_order"
    __table_args__ = (
        Index("uq_procurement_order_id_org", "id", "organization_id", unique=True),
        Index("uq_procurement_order_code", "organization_id", "public_code", unique=True),
        ForeignKeyConstraint(
            ["supplier_id", "organization_id"],
            ["supplier.id", "supplier.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    public_code: Mapped[str] = mapped_column(Text, nullable=False)
    establishment_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    supplier_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    inventory_location_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="draft")
    currency: Mapped[str] = mapped_column(Text, nullable=False, server_default="BRL")
    expected_at: Mapped[date | None] = mapped_column(Date)
    current_revision: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    created_by_user_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    created_at: Mapped[datetime] = _created_at()


class ProcurementOrderRevision(Base):
    __tablename__ = "procurement_order_revision"
    __table_args__ = (
        Index("uq_procurement_order_rev_id_org", "id", "organization_id", unique=True),
        Index(
            "uq_procurement_order_rev_number",
            "procurement_order_id",
            "revision_number",
            unique=True,
        ),
        ForeignKeyConstraint(
            ["procurement_order_id", "organization_id"],
            ["procurement_order.id", "procurement_order.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    procurement_order_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    created_by_user_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    created_at: Mapped[datetime] = _created_at()


class ProcurementOrderItem(Base):
    __tablename__ = "procurement_order_item"
    __table_args__ = (
        Index("uq_procurement_order_item_id_org", "id", "organization_id", unique=True),
        ForeignKeyConstraint(
            ["procurement_order_id", "organization_id"],
            ["procurement_order.id", "procurement_order.organization_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["procurement_order_revision_id", "organization_id"],
            ["procurement_order_revision.id", "procurement_order_revision.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    procurement_order_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    procurement_order_revision_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    inventory_item_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    supplier_item_id: Mapped[UUID | None] = mapped_column(Uuid)
    procurement_requisition_item_id: Mapped[UUID | None] = mapped_column(Uuid)
    procurement_quotation_item_id: Mapped[UUID | None] = mapped_column(Uuid)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    package_quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    unit_code: Mapped[str] = mapped_column(Text, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    currency: Mapped[str] = mapped_column(Text, nullable=False, server_default="BRL")
    created_at: Mapped[datetime] = _created_at()


class ProcurementReceipt(Base):
    __tablename__ = "procurement_receipt"
    __table_args__ = (
        Index("uq_procurement_receipt_id_org", "id", "organization_id", unique=True),
        Index("uq_procurement_receipt_code", "organization_id", "public_code", unique=True),
        ForeignKeyConstraint(
            ["procurement_order_id", "organization_id"],
            ["procurement_order.id", "procurement_order.organization_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["fiscal_inbound_document_id", "organization_id"],
            ["fiscal_inbound_document.id", "fiscal_inbound_document.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    public_code: Mapped[str] = mapped_column(Text, nullable=False)
    procurement_order_id: Mapped[UUID | None] = mapped_column(Uuid)
    fiscal_inbound_document_id: Mapped[UUID | None] = mapped_column(Uuid)
    source: Mapped[str] = mapped_column(Text, nullable=False, server_default="order")
    inventory_location_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="draft")
    evidence_ref: Mapped[str | None] = mapped_column(Text)
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    created_by_user_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    created_at: Mapped[datetime] = _created_at()


class ProcurementReceiptItem(Base):
    __tablename__ = "procurement_receipt_item"
    __table_args__ = (
        Index("uq_procurement_receipt_item_id_org", "id", "organization_id", unique=True),
        ForeignKeyConstraint(
            ["procurement_receipt_id", "organization_id"],
            ["procurement_receipt.id", "procurement_receipt.organization_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["fiscal_inbound_item_id", "organization_id"],
            ["fiscal_inbound_item.id", "fiscal_inbound_item.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    procurement_receipt_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    procurement_order_item_id: Mapped[UUID | None] = mapped_column(Uuid)
    fiscal_inbound_item_id: Mapped[UUID | None] = mapped_column(Uuid)
    inventory_item_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    unit_code: Mapped[str] = mapped_column(Text, nullable=False)
    supplier_lot_code: Mapped[str | None] = mapped_column(Text)
    manufactured_on: Mapped[date | None] = mapped_column(Date)
    expires_on: Mapped[date | None] = mapped_column(Date)
    observed_unit_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    currency: Mapped[str] = mapped_column(Text, nullable=False, server_default="BRL")
    inventory_lot_id: Mapped[UUID | None] = mapped_column(Uuid)
    divergence: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    created_at: Mapped[datetime] = _created_at()


class ProcurementReturn(Base):
    __tablename__ = "procurement_return"
    __table_args__ = (
        Index("uq_procurement_return_id_org", "id", "organization_id", unique=True),
        Index("uq_procurement_return_code", "organization_id", "public_code", unique=True),
        ForeignKeyConstraint(
            ["procurement_receipt_id", "organization_id"],
            ["procurement_receipt.id", "procurement_receipt.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    public_code: Mapped[str] = mapped_column(Text, nullable=False)
    procurement_receipt_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    inventory_lot_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    inventory_movement_id: Mapped[UUID | None] = mapped_column(Uuid)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="posted")
    created_by_user_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    created_at: Mapped[datetime] = _created_at()


class InventoryCommand(Base):
    __tablename__ = "inventory_command"
    __table_args__ = (
        Index("uq_inventory_command_id_org", "id", "organization_id", unique=True),
        Index("uq_inventory_command_idempotency", "organization_id", "idempotency_key", unique=True),
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


class InventoryCodeCounter(Base):
    __tablename__ = "inventory_code_counter"
    __table_args__ = (
        Index("uq_inventory_code_counter_id_org", "id", "organization_id", unique=True),
        Index("uq_inventory_code_counter_kind", "organization_id", "kind", unique=True),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    last_value: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    created_at: Mapped[datetime] = _created_at()
