from datetime import date
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UuidPkMixin


class RecipeBase(UuidPkMixin, TimestampMixin, Base):
    __tablename__ = "recipe_bases"
    __table_args__ = (
        CheckConstraint("char_length(code) BETWEEN 1 AND 40", name="ck_recipe_bases_code"),
        CheckConstraint("char_length(name) BETWEEN 1 AND 120", name="ck_recipe_bases_name"),
    )

    code: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class ScheduleSettings(Base):
    __tablename__ = "schedule_settings"
    __table_args__ = (
        CheckConstraint("id = 1", name="ck_schedule_settings_singleton"),
        CheckConstraint("daily_physical_limit > 0", name="ck_schedule_settings_physical"),
        CheckConstraint("daily_base_limit > 0", name="ck_schedule_settings_bases"),
        CheckConstraint("horizon_days > 0", name="ck_schedule_settings_horizon"),
        CheckConstraint("min_advance_hours >= 0", name="ck_schedule_settings_advance"),
        CheckConstraint(
            "eligibility_mode IN ('inherit','explicit')",
            name="ck_schedule_settings_eligibility",
        ),
        CheckConstraint(
            "reservation_policy IN ('unset','request','admin_accept','payment')",
            name="ck_schedule_settings_policy",
        ),
    )

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, default=1)
    production_weekdays: Mapped[list[int]] = mapped_column(ARRAY(Integer), nullable=False)
    daily_physical_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    daily_base_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    horizon_days: Mapped[int] = mapped_column(Integer, nullable=False, default=56)
    min_advance_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    eligibility_mode: Mapped[str] = mapped_column(String(16), nullable=False, default="inherit")
    occupancy_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    reservation_policy: Mapped[str] = mapped_column(String(20), nullable=False, default="unset")


class ScheduleWeekOverride(UuidPkMixin, TimestampMixin, Base):
    __tablename__ = "schedule_week_overrides"
    __table_args__ = (
        CheckConstraint(
            "daily_physical_limit IS NULL OR daily_physical_limit >= 0",
            name="ck_week_override_physical",
        ),
        CheckConstraint(
            "daily_base_limit IS NULL OR daily_base_limit >= 0",
            name="ck_week_override_bases",
        ),
        CheckConstraint(
            "eligibility_mode IN ('inherit','explicit')",
            name="ck_week_override_eligibility",
        ),
    )

    week_start: Mapped[date] = mapped_column(Date, nullable=False, unique=True)
    production_weekdays: Mapped[list[int] | None] = mapped_column(ARRAY(Integer))
    daily_physical_limit: Mapped[int | None] = mapped_column(Integer)
    daily_base_limit: Mapped[int | None] = mapped_column(Integer)
    eligibility_mode: Mapped[str] = mapped_column(String(16), nullable=False, default="inherit")


class ScheduleDateOverride(UuidPkMixin, TimestampMixin, Base):
    __tablename__ = "schedule_date_overrides"
    __table_args__ = (
        CheckConstraint(
            "open_state IN ('inherit','open','closed')",
            name="ck_date_override_open_state",
        ),
        CheckConstraint(
            "daily_physical_limit IS NULL OR daily_physical_limit >= 0",
            name="ck_date_override_physical",
        ),
        CheckConstraint(
            "daily_base_limit IS NULL OR daily_base_limit >= 0",
            name="ck_date_override_bases",
        ),
        CheckConstraint(
            "eligibility_mode IN ('inherit','explicit')",
            name="ck_date_override_eligibility",
        ),
    )

    local_date: Mapped[date] = mapped_column(Date, nullable=False, unique=True)
    open_state: Mapped[str] = mapped_column(String(16), nullable=False, default="inherit")
    daily_physical_limit: Mapped[int | None] = mapped_column(Integer)
    daily_base_limit: Mapped[int | None] = mapped_column(Integer)
    eligibility_mode: Mapped[str] = mapped_column(String(16), nullable=False, default="inherit")


class ScheduleEligibleBase(UuidPkMixin, Base):
    __tablename__ = "schedule_eligible_bases"
    __table_args__ = (
        UniqueConstraint(
            "scope_kind", "scope_id", "recipe_base_id", name="uq_schedule_eligible_base"
        ),
        CheckConstraint(
            "scope_kind IN ('default','week','date')",
            name="ck_schedule_eligible_scope",
        ),
        CheckConstraint(
            "(scope_kind = 'default' AND scope_id IS NULL) OR "
            "(scope_kind <> 'default' AND scope_id IS NOT NULL)",
            name="ck_schedule_eligible_scope_id",
        ),
    )

    scope_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    scope_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True))
    recipe_base_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("recipe_bases.id", ondelete="RESTRICT"),
        nullable=False,
    )
