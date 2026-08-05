from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.enums import JobStatus, ReportStatus


class ReportCreate(BaseModel):
    assessment_id: UUID
    include_maturity: bool = True
    include_action_plan: bool = True


class ReportOut(BaseModel):
    id: UUID
    organization_id: UUID
    assessment_id: UUID
    version_no: int
    status: ReportStatus
    structured_content: dict[str, Any]
    maturity_assessment_id: UUID | None
    export_storage_key: str | None
    supersedes_report_id: UUID | None
    discard_reason: str | None
    published_at: datetime | None
    published_by: UUID | None
    author_membership_id: UUID | None
    created_at: datetime
    updated_at: datetime


class ReportTransitionResult(BaseModel):
    report: ReportOut
    from_status: ReportStatus
    to_status: ReportStatus
    event: str


class ReasonIn(BaseModel):
    reason: str = Field(..., min_length=1, max_length=2000)


class DiscardIn(BaseModel):
    reason: str | None = Field(default=None, max_length=2000)


class JobOut(BaseModel):
    id: UUID
    organization_id: UUID
    job_type: str
    status: JobStatus
    idempotency_key: str
    input_ref: dict[str, Any]
    created_at: datetime
    attempt_count: int = 0
    max_attempts: int = 5
    error_code: str | None = None
    error_safe_message: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    output_ref: dict[str, Any] = Field(default_factory=dict)


class DownloadUrlOut(BaseModel):
    url: str
    expires_in_seconds: int
