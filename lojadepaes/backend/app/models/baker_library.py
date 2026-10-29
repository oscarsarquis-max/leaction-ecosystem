from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import UuidPkMixin


class GigioUsageEvent(UuidPkMixin, Base):
    __tablename__ = "gigio_usage_events"
    __table_args__ = (Index("ix_gigio_usage_origin_created", "origin", "created_at"),)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    origin: Mapped[str] = mapped_column(String(20), nullable=False)
    function: Mapped[str] = mapped_column(String(32), nullable=False)
    ok: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tokens_in: Mapped[int | None] = mapped_column(Integer)
    tokens_out: Mapped[int | None] = mapped_column(Integer)
    fail_kind: Mapped[str | None] = mapped_column(String(40))
    subject_hmac: Mapped[str | None] = mapped_column(String(64))
    article_id: Mapped[str | None] = mapped_column(String(80))
    provider: Mapped[str | None] = mapped_column(String(20))


class GigioCreditOperation(Base):
    __tablename__ = "gigio_credit_operations"

    operation_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    subject_hmac: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="reserved")
    reply_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class HubPlansEvent(Base):
    __tablename__ = "hub_plans_events"
    __table_args__ = (Index("ix_hub_plans_events_subject", "subject_hmac", "received_at"),)

    event_id: Mapped[str] = mapped_column(String(120), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    subject_hmac: Mapped[str | None] = mapped_column(String(64))
    business_status: Mapped[str | None] = mapped_column(String(40))
    issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    process_status: Mapped[str] = mapped_column(String(20), nullable=False, default="received")
    payload_json: Mapped[str | None] = mapped_column(Text)


class HubAuthorizationCache(Base):
    __tablename__ = "hub_authorization_cache"

    subject_hmac: Mapped[str] = mapped_column(String(64), primary_key=True)
    app_id: Mapped[str] = mapped_column(String(40), nullable=False, default="lojadepaes")
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    plan_sku: Mapped[str | None] = mapped_column(String(80))
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="hub")
