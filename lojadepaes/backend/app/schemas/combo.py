from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field

COMBO_MAX_QUANTITY = 10


class ComboOrderIn(BaseModel):
    variant_id: UUID
    bread_quantity: int = Field(ge=1, le=COMBO_MAX_QUANTITY)
    item_quantity: int = Field(ge=1, le=COMBO_MAX_QUANTITY)
    requested_date: date
    preferred_time: str | None = Field(default=None, max_length=8)
    customer_name: str = Field(min_length=1, max_length=160)
    customer_email: str = Field(min_length=3, max_length=254)
    customer_phone: str | None = Field(default=None, max_length=40)
    customer_note: str = Field(default="", max_length=2000)
    idempotency_key: str = Field(min_length=8, max_length=120)
    id_sessao: str | None = Field(default=None, max_length=36)
    quoted_cents: int = Field(ge=0)
    delivery_street: str = Field(default="", max_length=160)
    delivery_number: str = Field(default="", max_length=20)
    delivery_complement: str = Field(default="", max_length=80)
    delivery_district: str = Field(default="", max_length=80)
    delivery_city: str = Field(default="", max_length=80)
    delivery_state: str = Field(default="", max_length=2)
    delivery_postal_code: str = Field(default="", max_length=12)
    fulfillment_modality: str | None = Field(default=None, max_length=20)


class ComboOrderCreatedOut(BaseModel):
    combo_ref: str
    token: str
