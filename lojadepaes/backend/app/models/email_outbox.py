from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import UuidPkMixin


class EmailOutbox(UuidPkMixin, Base):
    __tablename__ = "email_outbox"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('order_submitted','payment_approved','order_accepted',"
            "'date_request_received','date_request_proposed','adaptation_proposed')",
            name="ck_email_outbox_kind",
        ),
        CheckConstraint(
            "status IN ('pending','skipped','sent','failed')",
            name="ck_email_outbox_status",
        ),
        CheckConstraint("attempts >= 0", name="ck_email_outbox_attempts"),
    )

    order_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=True, index=True
    )
    date_request_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("date_requests.id", ondelete="SET NULL"), nullable=True, index=True
    )
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    to_address: Mapped[str] = mapped_column(String(254), nullable=False)
    subject: Mapped[str] = mapped_column(String(180), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(Text)
    provider_message_id: Mapped[str | None] = mapped_column(String(200))
    dedupe_key: Mapped[str] = mapped_column(String(160), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
