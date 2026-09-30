from datetime import datetime
from uuid import UUID

from sqlalchemy import (
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
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UuidPkMixin


class HouseFidelityCampaign(UuidPkMixin, TimestampMixin, Base):
    __tablename__ = "house_fidelity_campaigns"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft','paused','active')",
            name="ck_house_fidelity_campaigns_status",
        ),
        UniqueConstraint("slug", "version", name="uq_house_fidelity_campaigns_slug_version"),
    )

    slug: Mapped[str] = mapped_column(String(80), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    rules_version: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rules_effective_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rules_json: Mapped[str] = mapped_column(Text, nullable=False)


class HouseFidelityRuleChange(UuidPkMixin, Base):
    __tablename__ = "house_fidelity_rule_changes"

    campaign_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("house_fidelity_campaigns.id", ondelete="RESTRICT"),
        nullable=False,
    )
    previous_rules_version: Mapped[str] = mapped_column(String(20), nullable=False)
    new_rules_version: Mapped[str] = mapped_column(String(20), nullable=False)
    previous_rules_json: Mapped[str] = mapped_column(Text, nullable=False)
    new_rules_json: Mapped[str] = mapped_column(Text, nullable=False)
    starts_at_preserved: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    effective_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class HouseFidelityEnrollment(UuidPkMixin, TimestampMixin, Base):
    __tablename__ = "house_fidelity_enrollments"
    __table_args__ = (
        UniqueConstraint(
            "account_id", "campaign_id", name="uq_house_fidelity_enrollments_account_campaign"
        ),
    )

    account_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("customer_accounts.id", ondelete="CASCADE"), nullable=False
    )
    campaign_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("house_fidelity_campaigns.id", ondelete="RESTRICT"),
        nullable=False,
    )
    rules_version: Mapped[str] = mapped_column(String(20), nullable=False)
    enrolled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class HouseFidelityEvent(UuidPkMixin, TimestampMixin, Base):
    __tablename__ = "house_fidelity_events"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('qualify','reverse','manual_grant','manual_reverse','partial_review')",
            name="ck_house_fidelity_events_kind",
        ),
        CheckConstraint(
            "status IN ('applied','reversed','pending')",
            name="ck_house_fidelity_events_status",
        ),
        UniqueConstraint("campaign_id", "order_id", "kind", name="uq_house_fidelity_events_order_kind"),
        Index("ix_house_fidelity_events_account_cycle", "account_id", "cycle_year", "cycle_month"),
    )

    campaign_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("house_fidelity_campaigns.id", ondelete="RESTRICT"),
        nullable=False,
    )
    account_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("customer_accounts.id", ondelete="CASCADE"), nullable=False
    )
    order_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("orders.id", ondelete="RESTRICT")
    )
    kind: Mapped[str] = mapped_column(String(24), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="applied")
    cycle_year: Mapped[int] = mapped_column(Integer, nullable=False)
    cycle_month: Mapped[int] = mapped_column(Integer, nullable=False)
    eligible_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reason: Mapped[str] = mapped_column(String(280), nullable=False, default="")
    actor_ref: Mapped[str | None] = mapped_column(String(80))


class HouseFidelityCredit(UuidPkMixin, TimestampMixin, Base):
    __tablename__ = "house_fidelity_credits"
    __table_args__ = (
        CheckConstraint(
            "status IN ('available','reserved','used','returned')",
            name="ck_house_fidelity_credits_status",
        ),
        UniqueConstraint(
            "campaign_id",
            "account_id",
            "cycle_year",
            "cycle_month",
            "group_index",
            name="uq_house_fidelity_credits_group",
        ),
        Index("ix_house_fidelity_credits_account_status", "account_id", "status"),
    )

    campaign_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("house_fidelity_campaigns.id", ondelete="RESTRICT"),
        nullable=False,
    )
    account_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("customer_accounts.id", ondelete="CASCADE"), nullable=False
    )
    source_event_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("house_fidelity_events.id", ondelete="RESTRICT"),
        nullable=False,
    )
    cycle_year: Mapped[int] = mapped_column(Integer, nullable=False)
    cycle_month: Mapped[int] = mapped_column(Integer, nullable=False)
    group_index: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="available")
    reserved_order_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("orders.id", ondelete="SET NULL")
    )
    used_order_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("orders.id", ondelete="SET NULL")
    )


class HouseFidelityAdjustment(UuidPkMixin, Base):
    __tablename__ = "house_fidelity_adjustments"

    campaign_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("house_fidelity_campaigns.id", ondelete="RESTRICT"),
        nullable=False,
    )
    account_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("customer_accounts.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(24), nullable=False)
    reason: Mapped[str] = mapped_column(String(280), nullable=False)
    actor_ref: Mapped[str] = mapped_column(String(80), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
