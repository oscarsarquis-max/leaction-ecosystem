from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.schemas.enums import InterviewMode, InterviewStatus


class InterviewCreate(BaseModel):
    mode: InterviewMode | None = None
    conducted_at: datetime | None = None


class InterviewOut(BaseModel):
    id: UUID
    organization_id: UUID
    assessment_id: UUID
    conducted_at: datetime | None
    mode: InterviewMode | None
    status: InterviewStatus
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
