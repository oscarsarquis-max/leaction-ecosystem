"""Build ProblemContextInput from ImprovementCase + Organization Profile (no ISO rules)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.modules.improvement_cases.problem_schemas import (
    SCHEMA_VERSION_V1,
    ProblemContextInput,
    ProblemFacts,
)
from app.modules.oi.schemas import OrganizationProfileFacts, SourceRef
from app.modules.orgs.schemas import OrganizationProfileOut


def build_problem_context_input(
    *,
    case_id: UUID,
    problem_statement: str,
    impact_statement: str,
    related_process: str,
    profile: OrganizationProfileOut,
    core_organization_id: UUID,
    request_id: str | None = None,
    correlation_id: str | None = None,
    requested_at: datetime | None = None,
) -> ProblemContextInput:
    rid = request_id or str(uuid4())
    cid = correlation_id or rid
    when = requested_at or datetime.now(UTC)

    facts = OrganizationProfileFacts(
        trade_name=profile.trade_name,
        legal_name=profile.legal_name,
        summary=profile.summary,
        industry=profile.industry,
        business_model=profile.business_model,
        employee_range=profile.employee_range,
        unit_count=profile.unit_count,
        certification_status=profile.certification_status,
        quality_structure=profile.quality_structure,
    )

    return ProblemContextInput(
        schema_version=SCHEMA_VERSION_V1,
        core_organization_id=core_organization_id,
        improvement_case_id=case_id,
        request_id=rid,
        correlation_id=cid,
        requested_at=when,
        source=SourceRef(
            system="qmind-core",
            component="improvement-case-problem-analysis",
        ),
        organization_profile=facts,
        problem=ProblemFacts(
            statement=problem_statement,
            impact_statement=impact_statement,
            related_process=related_process,
        ),
    )
