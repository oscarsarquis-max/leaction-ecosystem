"""Schemas de contrato. extra=forbid. Decimais como string."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


def decimal_str(value: Decimal | None) -> str | None:
    return None if value is None else format(value, "f")


class PageQuery(StrictModel):
    cursor: str | None = None
    limit: int = Field(default=20, ge=1, le=50)


class PlanCreate(StrictModel):
    establishment_id: UUID
    operational_date: date
    shift: str | None = None
    notes: str | None = Field(default=None, max_length=2000)


class PlanItemWrite(StrictModel):
    technical_product_id: UUID
    target_mode: str
    target_quantity: str
    sort_order: int
    unit_weight_g: str | None = None
    priority: int = 50
    notes: str | None = Field(default=None, max_length=2000)


class OrderCreate(StrictModel):
    establishment_id: UUID
    technical_product_id: UUID
    target_mode: str
    target_quantity: str
    unit_weight_g: str | None = None
    plan_id: UUID | None = None
    plan_item_id: UUID | None = None
    formulation_version_id: UUID | None = None
    scale_calculation_id: UUID | None = None
    priority: int = 50
    planned_start_at: datetime | None = None
    planned_end_at: datetime | None = None


class ReasonBody(StrictModel):
    reason: str = Field(min_length=1, max_length=2000)


class DependencyCreate(StrictModel):
    predecessor_order_id: UUID
    dependency_type: str
    relation_note: str | None = Field(default=None, max_length=200)
    quantity: str | None = None


class SplitBatchesBody(StrictModel):
    count: int = Field(ge=1, le=50)


class PolicyBody(StrictModel):
    weighing_policy: str
    verification_policy: str
    completion_tolerance: str
    allow_short_close: bool
    require_manual_lot: bool = False
    absolute_tolerance: str | None = None
    percent_tolerance: str | None = None
    reason: str | None = Field(default=None, max_length=2000)


class WeighingRecordBody(StrictModel):
    batch_material_id: UUID
    quantity: str
    measurement_unit_id: UUID
    lot_code: str | None = Field(default=None, max_length=80)
    expires_on: date | None = None
    scale_reference: str | None = Field(default=None, max_length=80)
    justification: str | None = Field(default=None, max_length=2000)


class WeighingCorrectBody(StrictModel):
    quantity: str
    measurement_unit_id: UUID
    lot_code: str | None = Field(default=None, max_length=80)
    justification: str | None = Field(default=None, max_length=2000)


class VerifyBody(StrictModel):
    decision: str
    justification: str | None = Field(default=None, max_length=2000)


class ConsumptionBody(StrictModel):
    batch_material_id: UUID
    consumption_type: str
    quantity: str
    measurement_unit_id: UUID
    weighing_entry_id: UUID | None = None
    lot_code: str | None = Field(default=None, max_length=80)
    reason: str | None = Field(default=None, max_length=2000)
    corrects_id: UUID | None = None


class YieldBody(StrictModel):
    measurement_type: str
    quantity: str
    measurement_unit_id: UUID
    notes: str | None = Field(default=None, max_length=2000)


class OccurrenceBody(StrictModel):
    category: str
    severity: str
    description: str = Field(min_length=1, max_length=2000)
    is_blocking: bool = False
    batch_id: UUID | None = None
    order_step_id: UUID | None = None


class ResolveOccurrenceBody(StrictModel):
    notes: str = Field(min_length=1, max_length=2000)


class SheetIssueBody(StrictModel):
    purpose: str
    batch_id: UUID | None = None


class RoleGrantBody(StrictModel):
    role: str
    reason: str = Field(min_length=1, max_length=2000)


class RoleRevokeBody(StrictModel):
    reason: str = Field(min_length=1, max_length=2000)


class ResourceRef(StrictModel):
    id: UUID
    row_version: int | None = None


def envelope(data: Any, row_version: int | None = None) -> dict:
    payload = {"data": data}
    if row_version is not None:
        payload["row_version"] = row_version
    return payload
