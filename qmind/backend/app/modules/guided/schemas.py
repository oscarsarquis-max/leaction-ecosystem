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


class GuidedAnswerOut(BaseModel):
    question_id: str
    question_version: str
    answer_value: AnswerValue | None = None
    description: str = ""
    na_justification: str = ""
    evidence_mode: EvidenceMode = "none"
    evidence_ids: list[UUID] = Field(default_factory=list)
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
