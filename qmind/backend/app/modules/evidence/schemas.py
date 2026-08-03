from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.enums import (
    EvidenceClassification,
    EvidenceLinkTargetType,
    EvidenceStatus,
)


class AuthorizeUploadIn(BaseModel):
    assessment_id: UUID
    classification: EvidenceClassification = EvidenceClassification.confidential
    content_type: str = Field(..., max_length=200)
    declared_byte_size: int = Field(..., ge=1, le=100_000_000)


class AuthorizeUploadOut(BaseModel):
    evidence: "EvidenceOut"
    upload: "PresignedUploadOut"


class PresignedUploadOut(BaseModel):
    url: str
    method: str
    headers: dict[str, str]
    expires_in_seconds: int


class EvidenceOut(BaseModel):
    id: UUID
    organization_id: UUID
    assessment_id: UUID | None
    status: EvidenceStatus
    classification: EvidenceClassification
    content_type: str | None
    byte_size: int | None
    content_hash: str | None
    storage_key: str | None
    version_no: int
    legal_hold: bool
    upload_expires_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class EvidenceTransitionResult(BaseModel):
    evidence: EvidenceOut
    from_status: EvidenceStatus
    to_status: EvidenceStatus
    event: str


class DownloadUrlOut(BaseModel):
    url: str
    expires_in_seconds: int


class CleanupResult(BaseModel):
    disposed_count: int


class EvidenceLinkCreate(BaseModel):
    target_type: EvidenceLinkTargetType
    target_id: UUID


class EvidenceLinkOut(BaseModel):
    id: UUID
    organization_id: UUID
    evidence_id: UUID
    target_type: EvidenceLinkTargetType
    target_id: UUID
    created_at: datetime
