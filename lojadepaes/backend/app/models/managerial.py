"""Exclusão gerencial e alertas do proprietário. Não substitui pedido nem pagamento."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
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
from app.models.mixins import UuidPkMixin


class ManagerialExclusion(UuidPkMixin, Base):
    __tablename__ = "managerial_exclusions"
    __table_args__ = (
        CheckConstraint(
            "subject_type IN ('order','date_request')",
            name="ck_managerial_exclusions_subject",
        ),
        Index(
            "uq_managerial_exclusion_active",
            "subject_type",
            "subject_id",
            unique=True,
            postgresql_where=text("reversed_at IS NULL"),
        ),
    )

    subject_type: Mapped[str] = mapped_column(String(20), nullable=False)
    subject_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    reason: Mapped[str] = mapped_column(String(280), nullable=False)
    author_ref: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    reversed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reversed_by: Mapped[str | None] = mapped_column(String(120))
    reverse_reason: Mapped[str | None] = mapped_column(String(280))


class OpsOwnerAlert(UuidPkMixin, Base):
    __tablename__ = "ops_owner_alerts"
    __table_args__ = (
        CheckConstraint("channel IN ('email','whatsapp')", name="ck_ops_owner_alerts_channel"),
        CheckConstraint(
            "status IN ('awaiting','accepted','delivered','failed','disabled')",
            name="ck_ops_owner_alerts_status",
        ),
        UniqueConstraint("event_key", "channel", name="uq_ops_owner_alerts_event_channel"),
    )

    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    event_key: Mapped[str] = mapped_column(String(160), nullable=False)
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    order_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True))
    date_request_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True))
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    summary: Mapped[str] = mapped_column(String(500), nullable=False)
    last_error: Mapped[str | None] = mapped_column(String(280))
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    provider_reference: Mapped[str | None] = mapped_column(String(120))
    email_outbox_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class OpsChannelSetting(Base):
    __tablename__ = "ops_channel_settings"
    __table_args__ = (
        CheckConstraint("channel IN ('whatsapp')", name="ck_ops_channel_settings_channel"),
    )

    channel: Mapped[str] = mapped_column(String(20), primary_key=True)
    destination: Mapped[str] = mapped_column(String(40), nullable=False, default="")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_by: Mapped[str] = mapped_column(String(120), nullable=False, default="")


class AdminPushSubscription(UuidPkMixin, Base):
    __tablename__ = "admin_push_subscriptions"
    __table_args__ = (
        UniqueConstraint("endpoint_hash", name="uq_admin_push_endpoint"),
        Index("ix_admin_push_actor_active", "actor_ref", "active"),
    )

    actor_ref: Mapped[str] = mapped_column(String(120), nullable=False)
    endpoint: Mapped[str] = mapped_column(Text, nullable=False)
    endpoint_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    p256dh: Mapped[str] = mapped_column(String(200), nullable=False)
    auth_secret: Mapped[str] = mapped_column(String(200), nullable=False)
    label: Mapped[str] = mapped_column(String(40), nullable=False, default="Este aparelho")
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    failure_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(String(280))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_reason: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class OpsPushDelivery(UuidPkMixin, Base):
    __tablename__ = "ops_push_deliveries"
    __table_args__ = (
        CheckConstraint(
            "status IN ('awaiting','accepted','failed','inactive')",
            name="ck_ops_push_deliveries_status",
        ),
        UniqueConstraint("event_key", "subscription_id", name="uq_ops_push_event_device"),
    )

    event_key: Mapped[str] = mapped_column(String(160), nullable=False)
    subscription_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    body: Mapped[str] = mapped_column(String(180), nullable=False)
    path: Mapped[str] = mapped_column(String(200), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(String(280))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
