from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import UuidPkMixin


class AdminSession(UuidPkMixin, Base):
    __tablename__ = "admin_sessions"
    __table_args__ = (Index("ix_admin_sessions_expires_at", "expires_at"),)

    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    csrf_token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    username: Mapped[str] = mapped_column(String(80), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    client_host: Mapped[str | None] = mapped_column(String(80))


class AdminLoginAttempt(UuidPkMixin, Base):
    __tablename__ = "admin_login_attempts"
    __table_args__ = (Index("ix_admin_login_attempts_user_created", "username", "created_at"),)

    username: Mapped[str] = mapped_column(String(80), nullable=False)
    client_host: Mapped[str] = mapped_column(String(80), nullable=False)
    succeeded: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AdminAccount(UuidPkMixin, Base):
    __tablename__ = "admin_accounts"
    __table_args__ = (UniqueConstraint("username", name="uq_admin_accounts_username"),)

    username: Mapped[str] = mapped_column(String(80), nullable=False)
    password_hash: Mapped[str | None] = mapped_column(Text)
    password_set_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AdminActivationToken(UuidPkMixin, Base):
    __tablename__ = "admin_activation_tokens"
    __table_args__ = (
        Index("ix_admin_activation_username_created", "username", "created_at"),
        UniqueConstraint("token_hash", name="uq_admin_activation_token_hash"),
    )

    username: Mapped[str] = mapped_column(String(80), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    purpose: Mapped[str] = mapped_column(String(40), nullable=False, default="set_password")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    invalidated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AdminActivationDispatch(UuidPkMixin, Base):
    __tablename__ = "admin_activation_dispatches"
    __table_args__ = (Index("ix_admin_activation_dispatch_sent", "username", "sent_at"),)

    username: Mapped[str] = mapped_column(String(80), nullable=False)
    recipient: Mapped[str] = mapped_column(String(254), nullable=False)
    provider_message_id: Mapped[str | None] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
