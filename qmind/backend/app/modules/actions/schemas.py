from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


ActionKind = Literal["correction", "corrective_action", "improvement"]


class ActionPlanCreate(BaseModel):
    assessment_id: UUID
    empty_plan_rationale: str | None = None


class ActionPlanOut(BaseModel):
    id: UUID
    organization_id: UUID
    assessment_id: UUID
    status: str
    empty_plan_rationale: str | None
    created_at: datetime
    updated_at: datetime


class ActionPlanTransitionResult(BaseModel):
    plan: ActionPlanOut
    from_status: str
    to_status: str
    event: str


class ActionItemCreate(BaseModel):
    finding_id: UUID | None = None
    action_kind: ActionKind
    description: str = Field(..., min_length=1)
    owner_membership_id: UUID
    due_at: datetime
    efficacy_required: bool | None = None


class ActionItemOut(BaseModel):
    id: UUID
    organization_id: UUID
    action_plan_id: UUID
    finding_id: UUID | None
    action_kind: str
    description: str
    owner_membership_id: UUID
    due_at: datetime
    status: str
    is_overdue: bool
    efficacy_required: bool
    source_finding_withdrawn: bool = False
    validated_by: UUID | None = None
    efficacy_confirmed_by: UUID | None = None
    cancel_reason: str | None = None
    reject_reason: str | None = None
    efficacy_fail_reason: str | None = None
    created_at: datetime
    updated_at: datetime


class ActionItemTransitionResult(BaseModel):
    item: ActionItemOut
    from_status: str
    to_status: str
    event: str


class ReasonIn(BaseModel):
    reason: str = Field(..., min_length=1, max_length=2000)
