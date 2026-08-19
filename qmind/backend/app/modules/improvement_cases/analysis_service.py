"""Improvement case analysis runs — Core orchestration (ISOI-003)."""

from __future__ import annotations

import json
from uuid import UUID

from sqlalchemy import text

from app.auth.context import OrgContext
from app.config import get_settings
from app.db import tenant_connection
from app.errors import AppError
from app.modules.improvement_cases import service as cases_service
from app.modules.improvement_cases.fingerprint import fingerprint_problem_context_input
from app.modules.improvement_cases.problem_context_builder import build_problem_context_input
from app.modules.improvement_cases.problem_schemas import (
    ImprovementCaseAnalysisRunOut,
    ProblemAnalysis,
    dump_jsonable,
)
from app.modules.oi.client import OrganizationalIntelligenceClient
from app.modules.orgs import service as orgs_service

_RUN_COLUMNS = """
    id, organization_id, improvement_case_id, schema_version, request_id,
    correlation_id, generated_at, input_fingerprint, analysis, created_at
"""


def _row_to_run(row, *, is_stale: bool = False) -> ImprovementCaseAnalysisRunOut:
    envelope = row.analysis
    if isinstance(envelope, str):
        envelope = json.loads(envelope)
    return ImprovementCaseAnalysisRunOut(
        id=row.id,
        organization_id=row.organization_id,
        improvement_case_id=row.improvement_case_id,
        schema_version=row.schema_version,
        request_id=row.request_id,
        correlation_id=row.correlation_id,
        generated_at=row.generated_at,
        input_fingerprint=row.input_fingerprint,
        analysis=ProblemAnalysis.model_validate(envelope),
        created_at=row.created_at,
        is_stale=is_stale,
    )


def _current_fingerprint(ctx: OrgContext, case_id: UUID) -> str:
    case = cases_service.get_case(ctx, case_id)
    profile = orgs_service.get_or_create_organization_profile(ctx)
    payload = build_problem_context_input(
        case_id=case.id,
        problem_statement=case.problem_statement,
        impact_statement=case.impact_statement,
        related_process=case.related_process,
        profile=profile,
        core_organization_id=ctx.organization_id,
    )
    return fingerprint_problem_context_input(payload)


def persist_analysis_run(
    ctx: OrgContext,
    *,
    case_id: UUID,
    envelope: ProblemAnalysis,
    input_fingerprint: str,
) -> ImprovementCaseAnalysisRunOut:
    payload = dump_jsonable(envelope)
    with tenant_connection(ctx.organization_id) as conn:
        row = conn.execute(
            text(
                f"""
                INSERT INTO improvement_case_analysis_runs (
                  organization_id, improvement_case_id, schema_version,
                  request_id, correlation_id, generated_at, input_fingerprint, analysis
                )
                VALUES (
                  :org, :case_id, :schema_version,
                  :request_id, :correlation_id, :generated_at, :fp, CAST(:analysis AS jsonb)
                )
                RETURNING {_RUN_COLUMNS}
                """
            ),
            {
                "org": ctx.organization_id,
                "case_id": case_id,
                "schema_version": envelope.schema_version,
                "request_id": envelope.request_id,
                "correlation_id": envelope.correlation_id,
                "generated_at": envelope.generated_at,
                "fp": input_fingerprint,
                "analysis": json.dumps(payload),
            },
        ).one()
        conn.commit()
    return _row_to_run(row, is_stale=False)


def list_analysis_runs(
    ctx: OrgContext,
    case_id: UUID,
    *,
    limit: int = 50,
) -> list[ImprovementCaseAnalysisRunOut]:
    cases_service.get_case(ctx, case_id)  # read gate + 404
    current_fp = _current_fingerprint(ctx, case_id)
    with tenant_connection(ctx.organization_id) as conn:
        rows = conn.execute(
            text(
                f"""
                SELECT {_RUN_COLUMNS}
                FROM improvement_case_analysis_runs
                WHERE improvement_case_id = :case_id AND organization_id = :org
                ORDER BY created_at DESC
                LIMIT :lim
                """
            ),
            {"case_id": case_id, "org": ctx.organization_id, "lim": limit},
        ).all()
    out: list[ImprovementCaseAnalysisRunOut] = []
    for i, row in enumerate(rows):
        stale = i == 0 and row.input_fingerprint != current_fp
        out.append(_row_to_run(row, is_stale=stale if i == 0 else False))
    return out


def get_analysis_run(
    ctx: OrgContext,
    case_id: UUID,
    run_id: UUID,
) -> ImprovementCaseAnalysisRunOut:
    cases_service.get_case(ctx, case_id)
    current_fp = _current_fingerprint(ctx, case_id)
    with tenant_connection(ctx.organization_id) as conn:
        row = conn.execute(
            text(
                f"""
                SELECT {_RUN_COLUMNS}
                FROM improvement_case_analysis_runs
                WHERE id = :id
                  AND improvement_case_id = :case_id
                  AND organization_id = :org
                """
            ),
            {"id": run_id, "case_id": case_id, "org": ctx.organization_id},
        ).first()
    if row is None:
        raise AppError("not_found", "Analysis run not found", status_code=404)

    # Mark stale only when this run is the latest for the case.
    with tenant_connection(ctx.organization_id) as conn:
        latest_id = conn.execute(
            text(
                """
                SELECT id FROM improvement_case_analysis_runs
                WHERE improvement_case_id = :case_id AND organization_id = :org
                ORDER BY created_at DESC
                LIMIT 1
                """
            ),
            {"case_id": case_id, "org": ctx.organization_id},
        ).scalar()
    is_latest = latest_id == row.id
    return _row_to_run(
        row,
        is_stale=is_latest and row.input_fingerprint != current_fp,
    )


def create_analysis_run(
    ctx: OrgContext,
    case_id: UUID,
    *,
    client: OrganizationalIntelligenceClient | None = None,
) -> ImprovementCaseAnalysisRunOut:
    """Write roles only — synchronous OI call; persist only after guards."""
    from app.modules.improvement_cases.service import _WRITE_ROLES
    from app.modules.orgs.service import require_role

    require_role(ctx, *_WRITE_ROLES)

    case = cases_service.get_case(ctx, case_id)
    profile = orgs_service.get_or_create_organization_profile(ctx)
    settings = get_settings()
    payload = build_problem_context_input(
        case_id=case.id,
        problem_statement=case.problem_statement,
        impact_statement=case.impact_statement,
        related_process=case.related_process,
        profile=profile,
        core_organization_id=ctx.organization_id,
    )
    fp = fingerprint_problem_context_input(payload)
    oi_client = client or OrganizationalIntelligenceClient(settings)
    result = oi_client.analyze_problem(payload)

    if result.core_organization_id != ctx.organization_id:
        raise AppError(
            "oi_organization_mismatch",
            "QMind OI response core_organization_id does not match the current organization",
            status_code=502,
        )
    if result.improvement_case_id != case_id:
        raise AppError(
            "oi_improvement_case_mismatch",
            "QMind OI response improvement_case_id does not match the requested case",
            status_code=502,
        )

    return persist_analysis_run(
        ctx,
        case_id=case_id,
        envelope=result,
        input_fingerprint=fp,
    )
