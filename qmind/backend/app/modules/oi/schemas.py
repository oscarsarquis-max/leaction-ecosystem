"""Wire DTOs mirroring QMind OI Boundary Contract v1 (OI-001).

Owned by Core for serialization — do NOT import qmind_oi.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

SCHEMA_VERSION_V1 = "1.0"

BusinessModel = Literal[
    "",
    "b2b",
    "b2c",
    "b2b2c",
    "services",
    "manufacturing",
    "mixed",
    "other",
]
EmployeeRange = Literal[
    "",
    "1-10",
    "11-50",
    "51-200",
    "201-500",
    "501-1000",
    "1000+",
]
CertificationStatus = Literal[
    "unknown",
    "none",
    "in_progress",
    "certified",
    "expired",
    "not_applicable",
]
QualityStructure = Literal[
    "unknown",
    "none",
    "informal",
    "formal_partial",
    "formal",
]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SourceRef(StrictModel):
    system: str = Field(min_length=1)
    component: str = Field(min_length=1)


class EnvelopeMetadata(StrictModel):
    producer_version: str | None = None
    environment: Literal["local", "test", "homolog", "prod"] | None = None
    trace_id: str | None = None


class OrganizationFacts(StrictModel):
    display_name: str | None = Field(default=None, max_length=200)


class OrganizationProfileFacts(StrictModel):
    trade_name: str | None = Field(default=None, max_length=200)
    legal_name: str | None = Field(default=None, max_length=200)
    summary: str | None = Field(default=None, max_length=4000)
    industry: str | None = Field(default=None, max_length=200)
    business_model: BusinessModel | None = None
    employee_range: EmployeeRange | None = None
    unit_count: int | None = Field(default=None, ge=0)
    certification_status: CertificationStatus | None = None
    quality_structure: QualityStructure | None = None


class OrganizationContextPayload(StrictModel):
    organization: OrganizationFacts | None = None
    profile: OrganizationProfileFacts | None = None


class OrganizationContextInput(StrictModel):
    """Core → OI envelope (schema 1.0)."""

    schema_version: str = Field(min_length=1)
    core_organization_id: UUID
    request_id: str = Field(min_length=1)
    correlation_id: str = Field(min_length=1)
    occurred_at: datetime
    source: SourceRef
    context: OrganizationContextPayload = Field(default_factory=OrganizationContextPayload)
    metadata: EnvelopeMetadata | None = None
    idempotency_key: str | None = Field(default=None, min_length=1, max_length=200)


class EvidenceReference(StrictModel):
    source_type: str = Field(min_length=1)
    source_id: str = Field(min_length=1)


class InsightExplanation(StrictModel):
    reasons: list[str] = Field(default_factory=list)
    evidence_refs: list[EvidenceReference] = Field(default_factory=list)
    supporting_facts: list[str] = Field(default_factory=list)
    mechanism_version: str | None = None


class OrganizationalInsight(StrictModel):
    insight_id: str = Field(min_length=1)
    type: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=200)
    summary: str = Field(min_length=1, max_length=4000)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    evidence_refs: list[EvidenceReference] = Field(default_factory=list)
    explanation: InsightExplanation | None = None


class OrganizationalInsights(StrictModel):
    """OI → Core envelope (schema 1.0)."""

    schema_version: str = Field(min_length=1)
    core_organization_id: UUID
    request_id: str = Field(min_length=1)
    correlation_id: str = Field(min_length=1)
    generated_at: datetime
    insights: list[OrganizationalInsight] = Field(default_factory=list)
    explanations: list[InsightExplanation] = Field(default_factory=list)
    metadata: EnvelopeMetadata | None = None


def dump_jsonable(model: BaseModel) -> dict[str, Any]:
    return model.model_dump(mode="json")
