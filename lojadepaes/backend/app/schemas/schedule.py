from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ScheduleLineIn(BaseModel):
    kind: Literal["product", "custom"]
    quantity: int = Field(ge=1)
    variant_id: UUID | None = None
    dough_type_id: UUID | None = None


class CalendarQuery(BaseModel):
    start: date | None = None
    end: date | None = None
    selected: date | None = None
    lines: list[ScheduleLineIn] = Field(default_factory=list)


class RecipeBaseIn(BaseModel):
    code: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=120)
    is_active: bool = True


class LinkedProductOut(BaseModel):
    id: UUID
    name: str


class RecipeBaseOut(BaseModel):
    id: UUID
    code: str
    name: str
    is_active: bool
    products: list[LinkedProductOut] = Field(default_factory=list)


class DoughLinkIn(BaseModel):
    recipe_base_id: UUID | None = None


class DefaultsIn(BaseModel):
    production_weekdays: list[int]
    daily_physical_limit: int = Field(ge=1)
    daily_base_limit: int = Field(ge=1)
    horizon_days: int = Field(ge=1, le=180)
    min_advance_hours: int = Field(ge=0, le=24 * 21)
    eligibility_mode: Literal["inherit", "explicit"] = "inherit"
    eligible_base_ids: list[UUID] | None = None


class WeekOverrideIn(BaseModel):
    week_start: date
    production_weekdays: list[int] | None = None
    daily_physical_limit: int | None = Field(default=None, ge=0)
    daily_base_limit: int | None = Field(default=None, ge=0)
    eligibility_mode: Literal["inherit", "explicit"] = "inherit"
    eligible_base_ids: list[UUID] | None = None


class DateOverrideIn(BaseModel):
    local_date: date
    open_state: Literal["inherit", "open", "closed"] = "inherit"
    daily_physical_limit: int | None = Field(default=None, ge=0)
    daily_base_limit: int | None = Field(default=None, ge=0)
    eligibility_mode: Literal["inherit", "explicit"] = "inherit"
    eligible_base_ids: list[UUID] | None = None
