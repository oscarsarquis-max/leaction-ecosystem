from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.admin import MoneyOut
from app.schemas.schedule import ScheduleLineIn


class SuggestionsQuery(BaseModel):
    selected: date | None = None
    lines: list[ScheduleLineIn] = Field(default_factory=list)


class SuggestionItemOut(BaseModel):
    name: str
    slug: str
    presentation: str
    image_url: str | None
    image_alt: str
    price: MoneyOut
    price_is_from: bool
    href: str


class SuggestionsOut(BaseModel):
    context_date: date | None
    context_source: Literal["selected", "next_eligible", "none"]
    context_label: str | None
    mode: Literal["new_types", "already_programmed", "empty"]
    title: str
    message: str | None
    items: list[SuggestionItemOut]


class DateRequestLineIn(BaseModel):
    variant_id: UUID
    quantity: int = Field(ge=1)


class DateRequestCreateIn(BaseModel):
    desired_date: date
    customer_name: str = Field(min_length=1, max_length=160)
    customer_email: str = Field(min_length=3, max_length=254)
    intended_quantity: int | None = Field(default=None, ge=1)
    message: str | None = Field(default=None, max_length=2000)
    idempotency_key: str = Field(min_length=8, max_length=120)
    lines: list[DateRequestLineIn] = Field(default_factory=list)


class DateRequestPublicOut(BaseModel):
    id: UUID
    status: str
    desired_date: date
    message: str


class DateRequestEventOut(BaseModel):
    action: str
    actor_ref: str | None
    detail: str | None
    created_at: str


class DateRequestAdminOut(BaseModel):
    id: UUID
    status: str
    desired_date: date
    proposed_date: date | None
    customer_name: str
    customer_email: str
    intended_quantity: int | None
    message: str | None
    admin_note: str | None
    cart_context: list | dict | None
    created_at: str
    events: list[DateRequestEventOut]


class DateRequestAdminList(BaseModel):
    items: list[DateRequestAdminOut]


class DateRequestActionIn(BaseModel):
    action: Literal["propose", "close"]
    proposed_date: date | None = None
    note: str | None = Field(default=None, max_length=2000)
