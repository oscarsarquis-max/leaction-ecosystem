from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UuidPkMixin


class PaymentRecord(UuidPkMixin, TimestampMixin, Base):
    __tablename__ = "payment_records"
    __table_args__ = (
        CheckConstraint("provider = 'actionhub'", name="ck_payment_records_provider"),
        CheckConstraint(
            "financial_status IN "
            "('pending','paid','failed','cancelled','partially_refunded','refunded','unknown')",
            name="ck_payment_records_status",
        ),
        CheckConstraint("currency = 'BRL'", name="ck_payment_records_currency"),
        CheckConstraint("expected_cents >= 0", name="ck_payment_records_expected"),
        CheckConstraint(
            "amount_paid_cents IS NULL OR amount_paid_cents >= 0",
            name="ck_payment_records_paid",
        ),
        CheckConstraint(
            "amount_refunded_cents IS NULL OR amount_refunded_cents >= 0",
            name="ck_payment_records_refunded",
        ),
        CheckConstraint(
            "amount_paid_cents IS NULL OR amount_refunded_cents IS NULL "
            "OR amount_refunded_cents <= amount_paid_cents",
            name="ck_payment_records_refund_lte_paid",
        ),
        Index(
            "uq_payment_records_external_ref",
            "provider",
            "external_reference",
            unique=True,
            postgresql_where="external_reference IS NOT NULL",
        ),
        Index(
            "uq_payment_records_idempotency",
            "provider",
            "idempotency_key",
            unique=True,
            postgresql_where="idempotency_key IS NOT NULL",
        ),
        Index("ix_payment_records_order", "order_id"),
    )

    order_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("orders.id", ondelete="RESTRICT"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String(40), nullable=False, default="actionhub")
    external_reference: Mapped[str | None] = mapped_column(String(120))
    idempotency_key: Mapped[str | None] = mapped_column(String(120))
    expected_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="BRL")
    financial_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    external_status_raw: Mapped[str | None] = mapped_column(String(80))
    amount_paid_cents: Mapped[int | None] = mapped_column(Integer)
    amount_refunded_cents: Mapped[int | None] = mapped_column(Integer)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PaymentIntegrationEvent(UuidPkMixin, Base):
    __tablename__ = "payment_integration_events"
    __table_args__ = (
        CheckConstraint("provider = 'actionhub'", name="ck_payment_events_provider"),
        CheckConstraint(
            "process_status IN ('received','ignored','applied','failed')",
            name="ck_payment_events_process_status",
        ),
        Index(
            "uq_payment_events_external_id",
            "provider",
            "external_event_id",
            unique=True,
        ),
    )

    provider: Mapped[str] = mapped_column(String(40), nullable=False, default="actionhub")
    external_event_id: Mapped[str] = mapped_column(String(160), nullable=False)
    payment_record_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("payment_records.id", ondelete="SET NULL")
    )
    external_type: Mapped[str | None] = mapped_column(String(80))
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    provider_occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    process_status: Mapped[str] = mapped_column(String(20), nullable=False, default="received")
    sanitized_error: Mapped[str | None] = mapped_column(Text)
