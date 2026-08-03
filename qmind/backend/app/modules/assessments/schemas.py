from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class ScopeItemIn(BaseModel):
    org_process_id: UUID | None = None
    requirement_id: UUID | None = None

    @model_validator(mode="after")
    def one_target(self) -> ScopeItemIn:
        if bool(self.org_process_id) == bool(self.requirement_id):
            raise ValueError("Provide exactly one of org_process_id or requirement_id")
        return self


class AssessmentCreate(BaseModel):
    assessment_model_id: UUID
    standard_version_id: UUID
    type: Literal["diagnosis", "internal_audit", "other"] = "diagnosis"
    maturity_model_id: UUID | None = None
    scope: list[ScopeItemIn] = Field(default_factory=list)


class AssessmentOut(BaseModel):
    id: UUID
    organization_id: UUID
    assessment_model_id: UUID
    standard_version_id: UUID
    maturity_model_id: UUID | None
    type: str
    status: str
    lead_membership_id: UUID | None
    created_at: datetime
    updated_at: datetime


class AssessmentPlanResult(BaseModel):
    assessment: AssessmentOut
    from_status: str
    to_status: str
    event: str = "plan"
