from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator
from pydantic_core import PydanticCustomError

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


class VacancySlotOut(BaseModel):
    id: str
    starts_at: str
    ends_at: str
    remaining: int


class SuggestionsOut(BaseModel):
    context_date: date | None
    context_source: Literal["selected", "next_eligible", "none"]
    context_label: str | None
    mode: Literal["new_types", "already_programmed", "empty"]
    title: str
    message: str | None
    items: list[SuggestionItemOut]
    slots: list[VacancySlotOut] = Field(default_factory=list)


QUANTITY_REQUIRED_MESSAGE = "Informe a quantidade de pães: 1 ou mais."


class DateRequestLineIn(BaseModel):
    variant_id: UUID
    quantity: int = Field(ge=1)


class DateRequestCreateIn(BaseModel):
    desired_date: date
    customer_name: str = Field(min_length=1, max_length=160)
    customer_email: str = Field(min_length=3, max_length=254)
    intended_quantity: int | None = Field(default=None)
    message: str | None = Field(default=None, max_length=2000)
    idempotency_key: str = Field(min_length=8, max_length=120)
    lines: list[DateRequestLineIn] = Field(default_factory=list)

    @field_validator("intended_quantity", mode="before")
    @classmethod
    def parse_intended_quantity(cls, value: object) -> int | None:
        if value is None or value == "":
            return None
        if isinstance(value, bool):
            raise PydanticCustomError("intended_quantity", QUANTITY_REQUIRED_MESSAGE)
        if isinstance(value, float):
            if not value.is_integer() or value < 1:
                raise PydanticCustomError("intended_quantity", QUANTITY_REQUIRED_MESSAGE)
            return int(value)
        if isinstance(value, int):
            if value < 1:
                raise PydanticCustomError("intended_quantity", QUANTITY_REQUIRED_MESSAGE)
            return value
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return None
            if not stripped.isdigit() or int(stripped) < 1:
                raise PydanticCustomError("intended_quantity", QUANTITY_REQUIRED_MESSAGE)
            return int(stripped)
        raise PydanticCustomError("intended_quantity", QUANTITY_REQUIRED_MESSAGE)


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


class DateRequestNotificationOut(BaseModel):
    id: UUID | None = None
    kind: str
    status: str
    last_error: str | None = None


class DateRequestAdminOut(BaseModel):
    id: UUID
    public_reference: str = ""
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
    notifications: list[DateRequestNotificationOut] = Field(default_factory=list)
    allowed_actions: list[str] = Field(default_factory=list)
    reply_preview: str | None = None
    converted_order_id: UUID | None = None
    converted_order_href: str | None = None
    accept_preview: dict | None = None


class DateRequestAdminList(BaseModel):
    items: list[DateRequestAdminOut]
    pending_count: int = 0


class DateRequestAddressIn(BaseModel):
    delivery_street: str | None = None
    delivery_number: str | None = None
    delivery_complement: str | None = None
    delivery_district: str | None = None
    delivery_city: str | None = None
    delivery_state: str | None = None
    delivery_postal_code: str | None = None


class DateRequestActionIn(BaseModel):
    action: Literal["propose", "close", "accept", "request_completion"]
    proposed_date: date | None = None
    note: str | None = Field(default=None, max_length=2000)
    address: DateRequestAddressIn | None = None
    lines: list[DateRequestLineIn] = Field(default_factory=list)


class DateRequestCommercialPreviewIn(BaseModel):
    lines: list[DateRequestLineIn] = Field(default_factory=list)


class DateRequestCompleteIn(DateRequestAddressIn):
    token: str = Field(min_length=8, max_length=128)


class DateRequestPublicDetailOut(BaseModel):
    id: UUID
    status: str
    desired_date: date
    gaps: list[str] = Field(default_factory=list)
    converted: bool = False
    message: str
    order_href: str | None = None
    delivery_pending: bool = False
