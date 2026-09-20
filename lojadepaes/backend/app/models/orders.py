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
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UuidPkMixin

ORDER_STATUSES = (
    "draft",
    "confirmed",
    "in_production",
    "ready",
    "completed",
    "cancelled",
)


class Order(UuidPkMixin, TimestampMixin, Base):
    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft','confirmed','in_production','ready','completed','cancelled')",
            name="ck_orders_status",
        ),
        CheckConstraint(
            "fulfillment_modality IS NULL OR fulfillment_modality IN ('pickup','delivery')",
            name="ck_orders_modality",
        ),
        CheckConstraint("currency = 'BRL'", name="ck_orders_currency"),
        CheckConstraint(
            "subtotal_cents IS NULL OR subtotal_cents >= 0", name="ck_orders_subtotal"
        ),
        CheckConstraint(
            "delivery_fee_cents IS NULL OR delivery_fee_cents >= 0",
            name="ck_orders_delivery_fee",
        ),
        CheckConstraint(
            "discount_cents IS NULL OR discount_cents >= 0", name="ck_orders_discount"
        ),
        CheckConstraint("total_cents IS NULL OR total_cents >= 0", name="ck_orders_total"),
        CheckConstraint("char_length(customer_note) <= 2000", name="ck_orders_customer_note"),
        Index("ix_orders_status_confirmed_at", "status", "confirmed_at"),
        Index("ix_orders_batch_status", "production_batch_id", "status"),
        Index("ix_orders_slot_status", "fulfillment_slot_id", "status"),
        Index("ix_orders_created_at", "created_at"),
        Index(
            "ix_orders_batch_holds_capacity",
            "production_batch_id",
            postgresql_where=text("holds_capacity"),
        ),
        Index(
            "ix_orders_slot_holds_capacity",
            "fulfillment_slot_id",
            postgresql_where=text("holds_capacity"),
        ),
    )

    public_reference: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    fulfillment_modality: Mapped[str | None] = mapped_column(String(20))
    fulfillment_slot_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("fulfillment_slots.id", ondelete="RESTRICT")
    )
    production_batch_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("production_batches.id", ondelete="RESTRICT")
    )
    identity_subject_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True))
    customer_name: Mapped[str | None] = mapped_column(String(160))
    customer_email: Mapped[str | None] = mapped_column(String(254))
    customer_phone: Mapped[str | None] = mapped_column(String(40))
    delivery_street: Mapped[str | None] = mapped_column(String(160))
    delivery_number: Mapped[str | None] = mapped_column(String(20))
    delivery_complement: Mapped[str | None] = mapped_column(String(80))
    delivery_district: Mapped[str | None] = mapped_column(String(80))
    delivery_city: Mapped[str | None] = mapped_column(String(80))
    delivery_state: Mapped[str | None] = mapped_column(String(2))
    delivery_postal_code: Mapped[str | None] = mapped_column(String(12))
    customer_note: Mapped[str] = mapped_column(String(2000), nullable=False, default="")
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="BRL")
    subtotal_cents: Mapped[int | None] = mapped_column(Integer)
    delivery_fee_cents: Mapped[int | None] = mapped_column(Integer)
    discount_cents: Mapped[int | None] = mapped_column(Integer)
    total_cents: Mapped[int | None] = mapped_column(Integer)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    production_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ready_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancellation_reason: Mapped[str | None] = mapped_column(String(280))
    holds_capacity: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class OrderItem(UuidPkMixin, TimestampMixin, Base):
    __tablename__ = "order_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_order_items_quantity"),
        CheckConstraint(
            "unit_price_cents IS NULL OR unit_price_cents >= 0",
            name="ck_order_items_unit_price",
        ),
        CheckConstraint(
            "line_total_cents IS NULL OR line_total_cents >= 0",
            name="ck_order_items_line_total",
        ),
    )

    order_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    dough_type_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("dough_types.id", ondelete="RESTRICT"), nullable=False
    )
    bread_shape_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("bread_shapes.id", ondelete="RESTRICT"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    dough_name_snapshot: Mapped[str | None] = mapped_column(String(120))
    shape_name_snapshot: Mapped[str | None] = mapped_column(String(120))
    unit_price_cents: Mapped[int | None] = mapped_column(Integer)
    line_total_cents: Mapped[int | None] = mapped_column(Integer)


class OrderItemIngredient(UuidPkMixin, Base):
    __tablename__ = "order_item_ingredients"
    __table_args__ = (
        UniqueConstraint("order_item_id", "ingredient_id", name="uq_order_item_ingredient"),
        CheckConstraint(
            "surcharge_cents IS NULL OR surcharge_cents >= 0",
            name="ck_order_item_ingredients_surcharge",
        ),
    )

    order_item_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("order_items.id", ondelete="CASCADE"), nullable=False
    )
    ingredient_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("ingredients.id", ondelete="RESTRICT"), nullable=False
    )
    name_snapshot: Mapped[str | None] = mapped_column(String(120))
    surcharge_cents: Mapped[int | None] = mapped_column(Integer)


class OrderStatusHistory(UuidPkMixin, Base):
    __tablename__ = "order_status_history"
    __table_args__ = (
        CheckConstraint(
            "from_status IS NULL OR from_status IN "
            "('draft','confirmed','in_production','ready','completed','cancelled')",
            name="ck_order_status_history_from",
        ),
        CheckConstraint(
            "to_status IN ('draft','confirmed','in_production','ready','completed','cancelled')",
            name="ck_order_status_history_to",
        ),
        Index("ix_order_status_history_order_created", "order_id", "created_at"),
    )

    order_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    from_status: Mapped[str | None] = mapped_column(String(20))
    to_status: Mapped[str] = mapped_column(String(20), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(280))
    actor_ref: Mapped[str | None] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class OrderInternalNote(UuidPkMixin, Base):
    __tablename__ = "order_internal_notes"
    __table_args__ = (
        CheckConstraint(
            "char_length(body) BETWEEN 1 AND 2000", name="ck_order_internal_notes_body"
        ),
    )

    order_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    author_ref: Mapped[str | None] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
