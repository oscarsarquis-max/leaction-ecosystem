from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


FindingType = Literal["conformity", "nonconformity", "opportunity", "observation"]


class FindingCreate(BaseModel):
    assessment_id: UUID
    finding_type: FindingType
    title: str = Field(..., min_length=1, max_length=500)
    body: str = Field(..., min_length=1)
    severity: str | None = None
    requirement_ids: list[UUID] = Field(default_factory=list)
    evidence_ids: list[UUID] = Field(default_factory=list)
    insufficient_evidence: bool = False
    insufficient_evidence_rationale: str | None = None


class FindingOut(BaseModel):
    id: UUID
    organization_id: UUID
    assessment_id: UUID
    finding_type: str
    severity: str | None
    status: str
    title: str
    body: str
    insufficient_evidence: bool
    insufficient_evidence_rationale: str | None
    author_membership_id: UUID
    approved_by: UUID | None = None
    requirement_ids: list[UUID] = Field(default_factory=list)
    evidence_ids: list[UUID] = Field(default_factory=list)
    submitted_at: datetime | None = None
    approved_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class FindingTransitionResult(BaseModel):
    finding: FindingOut
    from_status: str
    to_status: str
    event: str


class RejectIn(BaseModel):
    reason: str = Field(..., min_length=1, max_length=2000)
