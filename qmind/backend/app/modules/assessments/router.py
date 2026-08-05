from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Response

from app.auth.deps import OrgContextDep
from app.modules.assessments import service
from app.modules.assessments.schemas import (
    AssessmentCreate,
    AssessmentOut,
    AssessmentTransitionResult,
    CloseIn,
    ReopenIn,
    ScopeItemIn,
    ScopeOptionOut,
    ScopeOut,
    TeamMemberIn,
    TeamMemberOut,
)
from app.schemas.common import (
    ERROR_RESPONSES,
    CursorQuery,
    IdempotencyKeyHeader,
    LimitQuery,
)

router = APIRouter(prefix="/assessments", tags=["assessments"])


@router.post(
    "",
    response_model=AssessmentOut,
    status_code=201,
    operation_id="createAssessment",
    responses={400: ERROR_RESPONSES[400], 403: ERROR_RESPONSES[403], 422: ERROR_RESPONSES[422]},
)
def create_assessment(
    payload: AssessmentCreate,
    ctx: OrgContextDep,
    _idempotency_key: IdempotencyKeyHeader = None,
) -> AssessmentOut:
    return service.create_draft(ctx, payload)


@router.get(
    "",
    response_model=list[AssessmentOut],
    operation_id="listAssessments",
    summary="List assessments (paginated query params)",
)
def list_assessments(
    ctx: OrgContextDep,
    limit: LimitQuery = 50,
    cursor: CursorQuery = None,
) -> list[AssessmentOut]:
    _ = cursor
    items = service.list_assessments(ctx)
    return items[:limit]


@router.get(
    "/{assessment_id}",
    response_model=AssessmentOut,
    operation_id="getAssessment",
    responses={404: ERROR_RESPONSES[404]},
)
def get_assessment(assessment_id: UUID, ctx: OrgContextDep) -> AssessmentOut:
    return service.get_assessment(ctx, assessment_id)


@router.get(
    "/{assessment_id}/scopes",
    response_model=list[ScopeOut],
    operation_id="listAssessmentScopes",
)
def list_scopes(assessment_id: UUID, ctx: OrgContextDep) -> list[ScopeOut]:
    return service.list_scopes(ctx, assessment_id)


@router.get(
    "/{assessment_id}/scope-options",
    response_model=list[ScopeOptionOut],
    operation_id="listAssessmentScopeOptions",
    summary="Human-readable scope options (no UUID typing)",
)
def list_scope_options(assessment_id: UUID, ctx: OrgContextDep) -> list[ScopeOptionOut]:
    return service.list_scope_options(ctx, assessment_id)


@router.post(
    "/{assessment_id}/scopes/ensure",
    response_model=list[ScopeOut],
    operation_id="ensureAssessmentScopes",
    summary="Auto-fill scope from model + guided preparation",
    responses={409: ERROR_RESPONSES[409]},
)
def ensure_scopes(assessment_id: UUID, ctx: OrgContextDep) -> list[ScopeOut]:
    return service.ensure_scopes(ctx, assessment_id)


@router.post(
    "/{assessment_id}/scopes",
    response_model=ScopeOut,
    status_code=201,
    operation_id="addAssessmentScope",
    responses={409: ERROR_RESPONSES[409]},
)
def add_scope(assessment_id: UUID, payload: ScopeItemIn, ctx: OrgContextDep) -> ScopeOut:
    return service.add_scope(ctx, assessment_id, payload)


@router.delete(
    "/{assessment_id}/scopes/{scope_id}",
    status_code=204,
    operation_id="deleteAssessmentScope",
    responses={404: ERROR_RESPONSES[404], 409: ERROR_RESPONSES[409]},
)
def delete_scope(assessment_id: UUID, scope_id: UUID, ctx: OrgContextDep) -> Response:
    service.delete_scope(ctx, assessment_id, scope_id)
    return Response(status_code=204)


@router.get(
    "/{assessment_id}/team",
    response_model=list[TeamMemberOut],
    operation_id="listAssessmentTeam",
)
def list_team(assessment_id: UUID, ctx: OrgContextDep) -> list[TeamMemberOut]:
    return service.list_team(ctx, assessment_id)


@router.post(
    "/{assessment_id}/team",
    response_model=TeamMemberOut,
    status_code=201,
    operation_id="addAssessmentTeamMember",
    responses={409: ERROR_RESPONSES[409]},
)
def add_team_member(
    assessment_id: UUID, payload: TeamMemberIn, ctx: OrgContextDep
) -> TeamMemberOut:
    return service.add_team_member(ctx, assessment_id, payload)


@router.delete(
    "/{assessment_id}/team/{member_id}",
    status_code=204,
    operation_id="removeAssessmentTeamMember",
    responses={404: ERROR_RESPONSES[404], 409: ERROR_RESPONSES[409]},
)
def remove_team_member(assessment_id: UUID, member_id: UUID, ctx: OrgContextDep) -> Response:
    service.remove_team_member(ctx, assessment_id, member_id)
    return Response(status_code=204)


@router.post(
    "/{assessment_id}/transitions/plan",
    response_model=AssessmentTransitionResult,
    operation_id="planAssessment",
    responses={409: ERROR_RESPONSES[409]},
)
def plan_assessment(assessment_id: UUID, ctx: OrgContextDep) -> AssessmentTransitionResult:
    return service.transition_plan(ctx, assessment_id)


@router.post(
    "/{assessment_id}/transitions/start",
    response_model=AssessmentTransitionResult,
    operation_id="startAssessment",
    responses={409: ERROR_RESPONSES[409]},
)
def start_assessment(assessment_id: UUID, ctx: OrgContextDep) -> AssessmentTransitionResult:
    return service.transition_start(ctx, assessment_id)


@router.post(
    "/{assessment_id}/transitions/reopen_draft",
    response_model=AssessmentTransitionResult,
    operation_id="reopenDraftAssessment",
    responses={409: ERROR_RESPONSES[409]},
)
def reopen_draft(assessment_id: UUID, ctx: OrgContextDep) -> AssessmentTransitionResult:
    return service.transition_reopen_draft(ctx, assessment_id)


@router.post(
    "/{assessment_id}/transitions/cancel",
    response_model=AssessmentTransitionResult,
    operation_id="cancelAssessment",
    responses={409: ERROR_RESPONSES[409]},
)
def cancel_assessment(assessment_id: UUID, ctx: OrgContextDep) -> AssessmentTransitionResult:
    return service.transition_cancel(ctx, assessment_id)


@router.post(
    "/{assessment_id}/transitions/begin_analysis",
    response_model=AssessmentTransitionResult,
    operation_id="beginAssessmentAnalysis",
    responses={409: ERROR_RESPONSES[409]},
)
def begin_analysis(assessment_id: UUID, ctx: OrgContextDep) -> AssessmentTransitionResult:
    return service.transition_begin_analysis(ctx, assessment_id)


@router.post(
    "/{assessment_id}/transitions/open_actions",
    response_model=AssessmentTransitionResult,
    operation_id="openAssessmentActions",
    responses={409: ERROR_RESPONSES[409]},
)
def open_actions(assessment_id: UUID, ctx: OrgContextDep) -> AssessmentTransitionResult:
    return service.transition_open_actions(ctx, assessment_id)


@router.post(
    "/{assessment_id}/transitions/begin_report",
    response_model=AssessmentTransitionResult,
    operation_id="beginAssessmentReport",
    responses={409: ERROR_RESPONSES[409]},
)
def begin_report(assessment_id: UUID, ctx: OrgContextDep) -> AssessmentTransitionResult:
    return service.transition_begin_report(ctx, assessment_id)


@router.post(
    "/{assessment_id}/transitions/close",
    response_model=AssessmentTransitionResult,
    operation_id="closeAssessment",
    responses={403: ERROR_RESPONSES[403], 409: ERROR_RESPONSES[409], 422: ERROR_RESPONSES[422]},
)
def close_assessment(
    assessment_id: UUID,
    ctx: OrgContextDep,
    payload: CloseIn | None = None,
) -> AssessmentTransitionResult:
    return service.transition_close(
        ctx,
        assessment_id,
        waiver_reason=payload.waiver_reason if payload else None,
    )


@router.post(
    "/{assessment_id}/transitions/reopen",
    response_model=AssessmentTransitionResult,
    operation_id="reopenAssessment",
    responses={403: ERROR_RESPONSES[403], 409: ERROR_RESPONSES[409], 422: ERROR_RESPONSES[422]},
)
def reopen_assessment(
    assessment_id: UUID, payload: ReopenIn, ctx: OrgContextDep
) -> AssessmentTransitionResult:
    return service.transition_reopen(ctx, assessment_id, payload.reason)
