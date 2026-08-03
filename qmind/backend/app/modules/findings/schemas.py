from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.enums import FindingStatus, FindingType

# Re-export for callers that imported FindingType from this module
__all__ = [
    "FindingType",
    "FindingStatus",
    "FindingCreate",
    "FindingUpdate",
    "FindingOut",
    "FindingTransitionResult",
    "RejectIn",
    "WithdrawIn",
    "DiscardIn",
]


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


class FindingUpdate(BaseModel):
    """Draft-only edit — assessment_id is immutable."""

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
    finding_type: FindingType
    severity: str | None
    status: FindingStatus
    title: str
    body: str
    insufficient_evidence: bool
    insufficient_evidence_rationale: str | None
    author_membership_id: UUID
    approved_by: UUID | None = None
    withdrawn_reason: str | None = None
    discard_reason: str | None = None
    rework_of_finding_id: UUID | None = None
    requirement_ids: list[UUID] = Field(default_factory=list)
    evidence_ids: list[UUID] = Field(default_factory=list)
    submitted_at: datetime | None = None
    approved_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class FindingTransitionResult(BaseModel):
    finding: FindingOut
    from_status: FindingStatus
    to_status: FindingStatus
    event: str
    preserved_finding_id: UUID | None = None  # withdrawn row kept on rework


class RejectIn(BaseModel):
    reason: str = Field(..., min_length=1, max_length=2000)


class WithdrawIn(BaseModel):
    reason: str = Field(..., min_length=1, max_length=2000)


class DiscardIn(BaseModel):
    reason: str | None = Field(default=None, max_length=2000)
