from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UuidPkMixin


class ProductionBatch(UuidPkMixin, TimestampMixin, Base):
    __tablename__ = "production_batches"
    __table_args__ = (
        CheckConstraint("capacity_units > 0", name="ck_production_batches_capacity"),
        CheckConstraint(
            "planned_start_at < breads_available_at",
            name="ck_production_batches_start_before_available",
        ),
        CheckConstraint(
            "order_deadline_at <= breads_available_at",
            name="ck_production_batches_deadline",
        ),
        CheckConstraint(
            "status IN ('planned', 'open', 'closed', 'cancelled')",
            name="ck_production_batches_status",
        ),
    )

    code: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    planned_start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    breads_available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    order_deadline_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    capacity_units: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="planned")


class ProductionBatchDoughLimit(UuidPkMixin, Base):
    __tablename__ = "production_batch_dough_limits"
    __table_args__ = (
        UniqueConstraint("production_batch_id", "dough_type_id", name="uq_batch_dough_limit"),
        CheckConstraint("capacity_units > 0", name="ck_batch_dough_limit_capacity"),
    )

    production_batch_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("production_batches.id", ondelete="RESTRICT"),
        nullable=False,
    )
    dough_type_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("dough_types.id", ondelete="RESTRICT"), nullable=False
    )
    capacity_units: Mapped[int] = mapped_column(Integer, nullable=False)


class FulfillmentSlot(UuidPkMixin, TimestampMixin, Base):
    __tablename__ = "fulfillment_slots"
    __table_args__ = (
        CheckConstraint("capacity_units > 0", name="ck_fulfillment_slots_capacity"),
        CheckConstraint("starts_at < ends_at", name="ck_fulfillment_slots_window"),
        CheckConstraint("modality IN ('pickup', 'delivery')", name="ck_fulfillment_slots_modality"),
    )

    production_batch_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("production_batches.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    capacity_units: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    modality: Mapped[str] = mapped_column(String(20), nullable=False)
