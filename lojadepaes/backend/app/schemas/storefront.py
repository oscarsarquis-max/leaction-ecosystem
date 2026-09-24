from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class StorefrontItemIn(BaseModel):
    model_config = ConfigDict(extra="ignore")

    variant_id: UUID
    quantity: int = Field(ge=1, le=20)
    adaptation_text: str | None = Field(default=None, max_length=500)
    adaptation_reason: Literal["preference", "dietary_restriction"] | None = None


class StorefrontQuoteIn(BaseModel):
    requested_date: date
    items: list[StorefrontItemIn]
    quoted_cents: int | None = Field(default=None, ge=1)


class StorefrontSubmitIn(StorefrontQuoteIn):
    customer_name: str = Field(min_length=1, max_length=160)
    customer_email: str = Field(min_length=3, max_length=254)
    customer_phone: str | None = Field(default=None, max_length=40)
    customer_note: str = Field(default="", max_length=2000)
    idempotency_key: str = Field(min_length=8, max_length=120)
    id_sessao: str | None = Field(default=None, max_length=36)
    quoted_cents: int = Field(ge=1)
    delivery_street: str = Field(default="", max_length=160)
    delivery_number: str = Field(default="", max_length=20)
    delivery_complement: str = Field(default="", max_length=80)
    delivery_district: str = Field(default="", max_length=80)
    delivery_city: str = Field(default="", max_length=80)
    delivery_state: str = Field(default="", max_length=2)
    delivery_postal_code: str = Field(default="", max_length=12)


class DeliveryAddressIn(BaseModel):
    delivery_street: str = Field(min_length=1, max_length=160)
    delivery_number: str = Field(min_length=1, max_length=20)
    delivery_complement: str = Field(default="", max_length=80)
    delivery_district: str = Field(min_length=1, max_length=80)
    delivery_city: str = Field(min_length=1, max_length=80)
    delivery_state: str = Field(min_length=2, max_length=2)
    delivery_postal_code: str = Field(min_length=8, max_length=12)


class StorefrontOrderOut(BaseModel):
    public_reference: str
    status: str
    visitor_state: str
    requested_date: str | None
    proposed_date: str | None
    confirmed: bool
    holds_capacity: bool
    financially_settled: bool
    customer_name: str | None
    customer_email: str | None
    delivery_address: dict | None = None
    total_cents: int | None
    currency: str
    items: list[dict]
    payment: dict
    notice: str
    access_token: str | None = None


class StorefrontCheckoutIn(BaseModel):
    method: Literal["pix", "card"]
    replace: bool = False


class StorefrontCheckoutOut(BaseModel):
    checkout_url: str | None
    external_reference: str | None
    expected_cents: int
    reused: bool
    method: str
    pix: dict | None = None


class ProposeDateIn(BaseModel):
    date: date


class AdaptationRespondIn(BaseModel):
    decision: Literal["accept_alternative", "decline"]


class WebhookIn(BaseModel):
    token: str | None = Field(default=None, min_length=20)
