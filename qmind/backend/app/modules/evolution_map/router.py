"""Evolution Map HTTP API — deterministic advisory suggestions (no generative AI)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from app.auth.deps import OrgContextDep
from app.modules.evolution_map import service
from app.modules.evolution_map.schemas import (
    ConvertSuggestionToActionIn,
    ConvertSuggestionToActionOut,
    DismissSuggestionIn,
    EvolutionGenerateIn,
    EvolutionPackageOut,
    EvolutionSuggestionOut,
    InvestigateSuggestionIn,
)
from app.schemas.common import ERROR_RESPONSES, IdempotencyKeyHeader

router = APIRouter(tags=["evolution-map"])


@router.get(
    "/assessments/{assessment_id}/evolution-map",
    response_model=EvolutionPackageOut | None,
    operation_id="getAssessmentEvolutionMap",
    responses={403: ERROR_RESPONSES[403], 404: ERROR_RESPONSES[404]},
    summary="Active evolution suggestion package for an assessment (or null)",
)
def get_evolution_map(
    assessment_id: UUID, ctx: OrgContextDep
) -> EvolutionPackageOut | None:
    return service.get_active_package(ctx, assessment_id)


@router.post(
    "/assessments/{assessment_id}/evolution-map/generate",
    response_model=EvolutionPackageOut,
    status_code=200,
    operation_id="generateAssessmentEvolutionMap",
    responses={
        403: ERROR_RESPONSES[403],
        404: ERROR_RESPONSES[404],
        409: ERROR_RESPONSES[409],
    },
    summary="Generate or regenerate deterministic evolution suggestions",
)
def generate_evolution_map(
    assessment_id: UUID,
    ctx: OrgContextDep,
    payload: EvolutionGenerateIn | None = None,
    _idempotency_key: IdempotencyKeyHeader = None,
) -> EvolutionPackageOut:
    return service.generate_package(ctx, assessment_id, payload)


@router.get(
    "/evolution-suggestions/{suggestion_id}",
    response_model=EvolutionSuggestionOut,
    operation_id="getEvolutionSuggestion",
    responses={403: ERROR_RESPONSES[403], 404: ERROR_RESPONSES[404]},
)
def get_suggestion(suggestion_id: UUID, ctx: OrgContextDep) -> EvolutionSuggestionOut:
    return service.get_suggestion(ctx, suggestion_id)


@router.post(
    "/evolution-suggestions/{suggestion_id}/accept",
    response_model=EvolutionSuggestionOut,
    operation_id="acceptEvolutionSuggestion",
    responses={
        403: ERROR_RESPONSES[403],
        404: ERROR_RESPONSES[404],
        409: ERROR_RESPONSES[409],
    },
)
def accept_suggestion(
    suggestion_id: UUID,
    ctx: OrgContextDep,
    _idempotency_key: IdempotencyKeyHeader = None,
) -> EvolutionSuggestionOut:
    return service.accept_suggestion(ctx, suggestion_id)


@router.post(
    "/evolution-suggestions/{suggestion_id}/dismiss",
    response_model=EvolutionSuggestionOut,
    operation_id="dismissEvolutionSuggestion",
    responses={
        403: ERROR_RESPONSES[403],
        404: ERROR_RESPONSES[404],
        409: ERROR_RESPONSES[409],
        422: ERROR_RESPONSES[422],
    },
)
def dismiss_suggestion(
    suggestion_id: UUID,
    payload: DismissSuggestionIn,
    ctx: OrgContextDep,
    _idempotency_key: IdempotencyKeyHeader = None,
) -> EvolutionSuggestionOut:
    return service.dismiss_suggestion(ctx, suggestion_id, payload)


@router.post(
    "/evolution-suggestions/{suggestion_id}/investigate",
    response_model=EvolutionSuggestionOut,
    operation_id="investigateEvolutionSuggestion",
    responses={
        403: ERROR_RESPONSES[403],
        404: ERROR_RESPONSES[404],
        409: ERROR_RESPONSES[409],
    },
)
def investigate_suggestion(
    suggestion_id: UUID,
    ctx: OrgContextDep,
    payload: InvestigateSuggestionIn | None = None,
    _idempotency_key: IdempotencyKeyHeader = None,
) -> EvolutionSuggestionOut:
    return service.investigate_suggestion(ctx, suggestion_id, payload)


@router.post(
    "/evolution-suggestions/{suggestion_id}/convert-to-action",
    response_model=ConvertSuggestionToActionOut,
    operation_id="convertEvolutionSuggestionToAction",
    responses={
        403: ERROR_RESPONSES[403],
        404: ERROR_RESPONSES[404],
        409: ERROR_RESPONSES[409],
        422: ERROR_RESPONSES[422],
    },
    summary="Convert accepted suggestion into a confirmed action item",
)
def convert_suggestion(
    suggestion_id: UUID,
    payload: ConvertSuggestionToActionIn,
    ctx: OrgContextDep,
    _idempotency_key: IdempotencyKeyHeader = None,
) -> ConvertSuggestionToActionOut:
    return service.convert_suggestion_to_action(ctx, suggestion_id, payload)
