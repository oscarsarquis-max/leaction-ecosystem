from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


GuidedStep = Literal[
    "organization",
    "qms_scope",
    "products_services",
    "sites",
    "processes",
    "stakeholders",
    "route",
    "review",
]

AnswerValue = Literal["yes", "partial", "no", "unknown", "not_applicable"]
EvidenceMode = Literal["none", "attach", "link_existing", "describe", "provide_later"]
GuidedEvidenceLinkType = Literal["attach", "link_existing"]


class GuidedEvidenceLinkOut(BaseModel):
    id: UUID
    organization_id: UUID
    guided_session_id: UUID
    guided_answer_id: UUID
    assessment_id: UUID
    question_id: str
    question_version: str
    evidence_id: UUID
    link_type: GuidedEvidenceLinkType
    created_by: UUID | None = None
    created_at: datetime
    # Denormalized evidence snapshot for Wizard UI (no signed URLs).
    evidence_status: str | None = None
    situation: str = ""
    collected_phase: str | None = None
    collection_origin: str | None = None
    content_type: str | None = None
    byte_size: int | None = None
    file_name: str | None = None
    evidence_updated_at: datetime | None = None


class GuidedEvidenceLinkCreate(BaseModel):
    evidence_id: UUID


class GuidedEvidenceStatusOut(BaseModel):
    question_id: str
    provide_later: bool = False
    related: int = 0
    awaiting_upload: int = 0
    processing: int = 0
    approved: int = 0
    rejected: int = 0
    promised_later: int = 0
    links: list[GuidedEvidenceLinkOut] = Field(default_factory=list)


class GuidedAnswerOut(BaseModel):
    id: UUID | None = None
    question_id: str
    question_version: str
    answer_value: AnswerValue | None = None
    description: str = ""
    na_justification: str = ""
    evidence_mode: EvidenceMode = "none"
    # Legacy mirror — source of truth after migration is evidence_links.
    evidence_ids: list[UUID] = Field(default_factory=list)
    evidence_links: list[GuidedEvidenceLinkOut] = Field(default_factory=list)
    evidence_note: str = ""
    provide_later: bool = False
    updated_at: datetime | None = None


class GuidedSessionOut(BaseModel):
    id: UUID
    assessment_id: UUID
    organization_id: UUID
    catalog_version: str
    status: str
    current_step: GuidedStep
    current_question_id: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)
    answers: list[GuidedAnswerOut] = Field(default_factory=list)
    answered_count: int = 0
    question_count: int = 0
    updated_at: datetime


class GuidedContextPatch(BaseModel):
    context: dict[str, Any] | None = None
    current_step: GuidedStep | None = None
    current_question_id: str | None = None


class GuidedPositionPatch(BaseModel):
    current_step: GuidedStep
    current_question_id: str | None = None


class GuidedAnswerUpsert(BaseModel):
    question_version: str
    answer_value: AnswerValue | None = None
    description: str = ""
    na_justification: str = ""
    evidence_mode: EvidenceMode = "none"
    evidence_ids: list[UUID] = Field(default_factory=list)
    evidence_note: str = ""
    provide_later: bool = False
