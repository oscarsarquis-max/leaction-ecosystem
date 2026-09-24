from datetime import date, datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UuidPkMixin


class DateRequest(UuidPkMixin, TimestampMixin, Base):
    __tablename__ = "date_requests"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','alternative_proposed','closed')",
            name="ck_date_requests_status",
        ),
        CheckConstraint(
            "intended_quantity IS NULL OR intended_quantity >= 1",
            name="ck_date_requests_quantity",
        ),
        UniqueConstraint("idempotency_key", name="uq_date_requests_idempotency"),
        Index("ix_date_requests_status_created", "status", "created_at"),
        Index("ix_date_requests_email_created", "customer_email", "created_at"),
    )

    desired_date: Mapped[date] = mapped_column(Date, nullable=False)
    customer_name: Mapped[str] = mapped_column(String(160), nullable=False)
    customer_email: Mapped[str] = mapped_column(String(254), nullable=False)
    intended_quantity: Mapped[int | None] = mapped_column(Integer)
    message: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    proposed_date: Mapped[date | None] = mapped_column(Date)
    admin_note: Mapped[str | None] = mapped_column(Text)
    cart_context: Mapped[list | dict | None] = mapped_column(JSONB)
    idempotency_key: Mapped[str] = mapped_column(String(120), nullable=False)
    client_host: Mapped[str] = mapped_column(String(80), nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    events: Mapped[list["DateRequestEvent"]] = relationship(
        order_by="DateRequestEvent.created_at",
    )


class DateRequestEvent(UuidPkMixin, Base):
    __tablename__ = "date_request_events"
    __table_args__ = (Index("ix_date_request_events_request", "request_id", "created_at"),)

    request_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("date_requests.id", ondelete="CASCADE"), nullable=False
    )
    action: Mapped[str] = mapped_column(String(40), nullable=False)
    actor_ref: Mapped[str | None] = mapped_column(String(80))
    detail: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
