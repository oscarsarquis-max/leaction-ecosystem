"""Wire DTOs for Problem Analysis (OI ISOI-003) — Core-owned mirrors, no qmind_oi import."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.oi.schemas import OrganizationProfileFacts, SourceRef, StrictModel

SCHEMA_VERSION_V1 = "1.0"

ContextStatus = Literal["insufficient_context", "ready_for_initial_analysis"]
SupportStatus = Literal[
    "requires_validation",
    "partially_supported",
    "supported_by_available_facts",
]
IsoBasis = Literal["4.1", "4.4"]


class ProblemFacts(StrictModel):
    statement: str = Field(min_length=1, max_length=4000)
    impact_statement: str = Field(min_length=1, max_length=4000)
    related_process: str = Field(min_length=1, max_length=4000)


class ProblemContextInput(StrictModel):
    schema_version: str = Field(min_length=1)
    core_organization_id: UUID
    improvement_case_id: UUID
    request_id: str = Field(min_length=1)
    correlation_id: str = Field(min_length=1)
    requested_at: datetime
    source: SourceRef
    organization_profile: OrganizationProfileFacts
    problem: ProblemFacts


class ProblemHypothesis(StrictModel):
    code: str = Field(min_length=1, max_length=80)
    statement: str = Field(min_length=1, max_length=2000)
    rationale: str = Field(min_length=1, max_length=4000)
    support_status: SupportStatus
    supporting_facts: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    iso_basis: list[IsoBasis] = Field(min_length=1)


class ProblemFinding(StrictModel):
    code: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=4000)
    relationship_to_problem: str = Field(min_length=1, max_length=2000)
    business_impact: str = Field(min_length=1, max_length=2000)
    supporting_facts: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    iso_basis: list[IsoBasis] = Field(min_length=1)
    recommended_next_step: str = Field(min_length=1, max_length=4000)
    requires_human_validation: bool = True


class ProblemAnalysis(StrictModel):
    schema_version: str = Field(min_length=1)
    core_organization_id: UUID
    improvement_case_id: UUID
    analysis_id: UUID
    request_id: str = Field(min_length=1)
    correlation_id: str = Field(min_length=1)
    generated_at: datetime
    context_status: ContextStatus
    interpretation_summary: str = Field(min_length=1, max_length=4000)
    hypotheses: list[ProblemHypothesis] = Field(default_factory=list)
    findings: list[ProblemFinding] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class ImprovementCaseAnalysisRunOut(BaseModel):
    id: UUID
    organization_id: UUID
    improvement_case_id: UUID
    schema_version: str
    request_id: str
    correlation_id: str
    generated_at: datetime
    input_fingerprint: str
    analysis: ProblemAnalysis
    created_at: datetime
    is_stale: bool = False


def dump_jsonable(model: BaseModel) -> dict[str, Any]:
    return model.model_dump(mode="json")
