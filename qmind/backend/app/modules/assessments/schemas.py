from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.schemas.enums import AssessmentStatus, AssessmentType


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
    type: AssessmentType = AssessmentType.diagnosis
    maturity_model_id: UUID | None = None
    scope: list[ScopeItemIn] = Field(default_factory=list)


class AssessmentOut(BaseModel):
    id: UUID
    organization_id: UUID
    assessment_model_id: UUID
    standard_version_id: UUID
    maturity_model_id: UUID | None
    type: AssessmentType
    status: AssessmentStatus
    lead_membership_id: UUID | None
    started_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class AssessmentTransitionResult(BaseModel):
    assessment: AssessmentOut
    from_status: AssessmentStatus
    to_status: AssessmentStatus
    event: str


class CloseIn(BaseModel):
    waiver_reason: str | None = Field(default=None, max_length=2000)


class ReopenIn(BaseModel):
    reason: str = Field(..., min_length=1, max_length=2000)


# Backward-compatible alias used by earlier tests/imports
AssessmentPlanResult = AssessmentTransitionResult


class ScopeOut(BaseModel):
    id: UUID
    assessment_id: UUID
    org_process_id: UUID | None
    requirement_id: UUID | None
    created_at: datetime


class TeamMemberIn(BaseModel):
    membership_id: UUID
    team_role: str | None = None


class TeamMemberOut(BaseModel):
    id: UUID
    assessment_id: UUID
    membership_id: UUID
    team_role: str | None
    created_at: datetime
