from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.enums import Applicability, MaturityStatus


class MaturityPackageCreate(BaseModel):
    assessment_id: UUID


class ScoreUpsert(BaseModel):
    criterion_id: UUID
    applicability: Applicability
    level: int | None = Field(default=None, ge=1, le=5)
    na_rationale: str | None = None
    rationale: str | None = None
    evidence_ids: list[UUID] = Field(default_factory=list)


class ScoresUpsertIn(BaseModel):
    scores: list[ScoreUpsert] = Field(..., min_length=1)
    # Client MUST NOT send aggregates — ignored if present (rejected explicitly)
    global_score: Decimal | None = None
    dimension_scores: dict[str, Decimal] | None = None


class ScoreOut(BaseModel):
    id: UUID
    criterion_id: UUID
    criterion_code: str | None = None
    dimension_id: UUID | None = None
    dimension_code: str | None = None
    applicability: Applicability
    level: int | None
    na_rationale: str | None
    rationale: str | None
    evidence_ids: list[UUID] = Field(default_factory=list)


class DimensionScoreOut(BaseModel):
    dimension_id: UUID
    dimension_code: str
    score: Decimal
    applicable_count: int


class MaturityPackageOut(BaseModel):
    id: UUID
    organization_id: UUID
    assessment_id: UUID
    version_no: int
    supersedes_id: UUID | None
    maturity_model_id: UUID
    model_code: str | None = None
    model_version: str | None = None
    status: MaturityStatus
    global_score: Decimal | None
    author_membership_id: UUID
    approved_by: UUID | None = None
    discard_reason: str | None = None
    scores: list[ScoreOut] = Field(default_factory=list)
    dimension_scores: list[DimensionScoreOut] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class MaturityTransitionResult(BaseModel):
    package: MaturityPackageOut
    from_status: MaturityStatus
    to_status: MaturityStatus
    event: str
    new_package_id: UUID | None = None  # supersede


class ReasonIn(BaseModel):
    reason: str = Field(..., min_length=1, max_length=2000)


class DiscardIn(BaseModel):
    reason: str | None = Field(default=None, max_length=2000)
