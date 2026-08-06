from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.schemas.enums import InterviewMode, InterviewStatus


class InterviewCreate(BaseModel):
    """Create interview — planning fields optional; answers still require in_progress."""

    mode: InterviewMode | None = None
    conducted_at: datetime | None = None
    title: str = Field(default="", max_length=200)
    objective: str = Field(default="", max_length=4000)
    process_name: str = Field(default="", max_length=200)
    org_contact_name: str = Field(default="", max_length=200)
    interviewer_membership_id: UUID | None = None
    participant_membership_ids: list[UUID] = Field(default_factory=list)
    scheduled_at: datetime | None = None
    duration_minutes: int | None = Field(default=None, ge=1, le=24 * 60)
    location: str = Field(default="", max_length=500)
    remote_link: str = Field(default="", max_length=500)
    preparation: str = Field(default="", max_length=4000)
    outside_period_justification: str = Field(default="", max_length=2000)


class InterviewUpdate(BaseModel):
    mode: InterviewMode | None = None
    conducted_at: datetime | None = None
    title: str | None = Field(default=None, max_length=200)
    objective: str | None = Field(default=None, max_length=4000)
    process_name: str | None = Field(default=None, max_length=200)
    org_contact_name: str | None = Field(default=None, max_length=200)
    interviewer_membership_id: UUID | None = None
    participant_membership_ids: list[UUID] | None = None
    scheduled_at: datetime | None = None
    duration_minutes: int | None = Field(default=None, ge=1, le=24 * 60)
    location: str | None = Field(default=None, max_length=500)
    remote_link: str | None = Field(default=None, max_length=500)
    preparation: str | None = Field(default=None, max_length=4000)
    outside_period_justification: str | None = Field(default=None, max_length=2000)
    clear_scheduled_at: bool = False


class InterviewOut(BaseModel):
    id: UUID
    organization_id: UUID
    assessment_id: UUID
    conducted_at: datetime | None
    mode: InterviewMode | None
    status: InterviewStatus
    title: str = ""
    objective: str = ""
    process_name: str = ""
    org_contact_name: str = ""
    interviewer_membership_id: UUID | None = None
    participant_membership_ids: list[UUID] = Field(default_factory=list)
    scheduled_at: datetime | None = None
    duration_minutes: int | None = None
    location: str = ""
    remote_link: str = ""
    preparation: str = ""
    agenda_event_id: UUID | None = None
    overlap_warnings: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class InterviewTransitionResult(BaseModel):
    interview: InterviewOut
    from_status: InterviewStatus
    to_status: InterviewStatus
    event: str


class AnswerCreate(BaseModel):
    body: str = Field(..., min_length=1, max_length=20000)
    question_id: UUID | None = None
    criterion_id: UUID | None = None

    @model_validator(mode="after")
    def at_most_one_ref(self) -> AnswerCreate:
        if self.question_id and self.criterion_id:
            raise ValueError("Provide at most one of question_id or criterion_id")
        return self


class AnswerUpdate(BaseModel):
    body: str = Field(..., min_length=1, max_length=20000)


class AnswerOut(BaseModel):
    id: UUID
    organization_id: UUID
    interview_id: UUID
    question_id: UUID | None
    criterion_id: UUID | None
    body: str
    author_membership_id: UUID | None
    created_at: datetime
    updated_at: datetime


class QuestionOut(BaseModel):
    id: UUID
    assessment_model_id: UUID
    criterion_id: UUID | None
    code: str
    prompt_text: str
    sort_order: int
