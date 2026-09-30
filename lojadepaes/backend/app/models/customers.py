from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UuidPkMixin


class CustomerAccount(UuidPkMixin, TimestampMixin, Base):
    __tablename__ = "customer_accounts"
    __table_args__ = (
        UniqueConstraint("email", name="uq_customer_accounts_email"),
        UniqueConstraint("cpf_hmac", name="uq_customer_accounts_cpf_hmac"),
        Index("ix_customer_accounts_created", "created_at"),
    )

    name: Mapped[str] = mapped_column(String(160), nullable=False)
    email: Mapped[str] = mapped_column(String(254), nullable=False)
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cpf_hmac: Mapped[str] = mapped_column(String(64), nullable=False)
    cpf_last2: Mapped[str] = mapped_column(String(2), nullable=False)
    marketing_opt_in: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class CustomerSession(UuidPkMixin, Base):
    __tablename__ = "customer_sessions"
    __table_args__ = (Index("ix_customer_sessions_expires", "expires_at"),)

    account_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("customer_accounts.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CustomerChallenge(UuidPkMixin, Base):
    __tablename__ = "customer_challenges"
    __table_args__ = (
        Index("ix_customer_challenges_email_created", "email", "created_at"),
        UniqueConstraint("token_hash", name="uq_customer_challenges_token"),
    )

    account_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("customer_accounts.id", ondelete="CASCADE")
    )
    email: Mapped[str] = mapped_column(String(254), nullable=False)
    purpose: Mapped[str] = mapped_column(String(20), nullable=False)
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
