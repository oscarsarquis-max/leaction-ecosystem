from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

FinancialKind = Literal["none", "unknown", "open", "settled"]
OrderStatusLiteral = Literal[
    "draft", "submitted", "confirmed", "in_production", "ready", "completed", "cancelled"
]
ModalityLiteral = Literal["pickup", "delivery"]


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=200)


class AccessModeResponse(BaseModel):
    local_passwordless: bool


class SessionResponse(BaseModel):
    username: str
    csrf_token: str
    bakery_timezone: str


class OrderListQuery(BaseModel):
    reference: str | None = Field(default=None, max_length=20)
    status: OrderStatusLiteral | None = None
    created_from: date | None = None
    created_to: date | None = None
    production_batch_id: UUID | None = None
    fulfillment_slot_id: UUID | None = None
    modality: ModalityLiteral | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=50)


class MoneyOut(BaseModel):
    cents: int | None
    currency: str = "BRL"


class OrderListItemOut(BaseModel):
    id: UUID
    public_reference: str
    created_at: datetime
    status: str
    customer_name: str | None
    bread_units: int
    fulfillment_modality: str | None
    production_batch_id: UUID | None
    production_batch_code: str | None
    fulfillment_slot_id: UUID | None
    slot_starts_at: datetime | None
    slot_ends_at: datetime | None
    total: MoneyOut
    financial_kind: FinancialKind
    adaptation_attention: bool = False


class OrderListOut(BaseModel):
    items: list[OrderListItemOut]
    page: int
    page_size: int
    total: int


class ExtraOut(BaseModel):
    ingredient_id: UUID
    name: str
    surcharge: MoneyOut
    snapshot_complete: bool


class ItemOut(BaseModel):
    id: UUID
    dough_type_id: UUID | None = None
    bread_shape_id: UUID | None = None
    dough_name: str
    shape_name: str
    quantity: int
    unit_price: MoneyOut
    line_total: MoneyOut
    extras: list[ExtraOut]
    snapshot_complete: bool
    provisional: bool
    adaptation: dict | None = None


class AddressOut(BaseModel):
    street: str | None
    number: str | None
    complement: str | None
    district: str | None
    city: str | None
    state: str | None
    postal_code: str | None


class HistoryOut(BaseModel):
    id: UUID
    from_status: str | None
    to_status: str
    reason: str | None
    actor_ref: str | None
    created_at: datetime


class NoteOut(BaseModel):
    id: UUID
    body: str
    author_ref: str | None
    created_at: datetime


class PaymentRecordOut(BaseModel):
    id: UUID
    provider: str
    external_reference: str | None
    expected_cents: int
    currency: str
    financial_status: str
    external_status_raw: str | None
    amount_paid_cents: int | None
    amount_refunded_cents: int | None
    confirmed_at: datetime | None
    last_synced_at: datetime | None
    sanitized_error: str | None = None
    method: str | None = None
    pix_expires_at: datetime | None = None


class PaymentEventOut(BaseModel):
    id: UUID
    external_event_id: str
    payment_record_id: UUID | None
    external_type: str | None
    received_at: datetime
    provider_occurred_at: datetime | None
    process_status: str
    sanitized_error: str | None


class OrderDetailOut(BaseModel):
    id: UUID
    public_reference: str
    created_at: datetime
    updated_at: datetime
    status: str
    allowed_actions: list[str]
    customer_name: str | None
    customer_email: str | None
    customer_phone: str | None
    address: AddressOut
    customer_note: str
    fulfillment_modality: str | None
    production_batch_id: UUID | None
    production_batch_code: str | None
    fulfillment_slot_id: UUID | None
    slot_starts_at: datetime | None
    slot_ends_at: datetime | None
    confirmed_at: datetime | None
    production_started_at: datetime | None
    ready_at: datetime | None
    completed_at: datetime | None
    cancelled_at: datetime | None
    cancellation_reason: str | None
    currency: str
    subtotal: MoneyOut
    delivery_fee: MoneyOut
    discount: MoneyOut
    total: MoneyOut
    items: list[ItemOut]
    history: list[HistoryOut]
    notes: list[NoteOut]
    payment_records: list[PaymentRecordOut]
    payment_events: list[PaymentEventOut]
    financial_kind: FinancialKind
    financially_settled: bool
    holds_capacity: bool
    snapshots_locked: bool
    production_local_date: date | None = None
    proposed_production_date: date | None = None
    has_unresolved_adaptations: bool = False


class CancelRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=280)


class NoteCreateRequest(BaseModel):
    body: str = Field(min_length=1, max_length=2000)


class AdaptationEvaluateIn(BaseModel):
    decision: Literal["accept", "propose_alternative", "decline"]
    response: str = Field(default="", max_length=2000)
