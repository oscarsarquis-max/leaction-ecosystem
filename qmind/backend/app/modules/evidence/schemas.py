from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class AuthorizeUploadIn(BaseModel):
    assessment_id: UUID
    classification: Literal["public", "internal", "confidential", "restricted"] = "confidential"
    content_type: str = Field(default="application/octet-stream", max_length=200)
    declared_byte_size: int | None = Field(default=None, ge=1, le=100_000_000)


class ReceiveUploadIn(BaseModel):
    """Simulates binary receipt before real S3 integration."""

    content_hash: str = Field(min_length=8, max_length=128)
    content_type: str = Field(default="application/octet-stream", max_length=200)
    byte_size: int = Field(ge=1, le=100_000_000)


class EvidenceOut(BaseModel):
    id: UUID
    organization_id: UUID
    assessment_id: UUID | None
    status: str
    classification: str
    content_type: str | None
    byte_size: int | None
    content_hash: str | None
    storage_key: str | None
    version_no: int
    legal_hold: bool
    created_at: datetime
    updated_at: datetime


class EvidenceTransitionResult(BaseModel):
    evidence: EvidenceOut
    from_status: str
    to_status: str
    event: str
