from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from app.auth.deps import OrgContextDep
from app.modules.audit_plan import service
from app.modules.audit_plan.schemas import (
    AuditPlanOut,
    AuditPlanPatch,
    AuditPlanReadyIn,
    AuditPlanRefreshIn,
)
from app.schemas.common import ERROR_RESPONSES, IdempotencyKeyHeader

router = APIRouter(tags=["audit-plan"])


@router.get(
    "/assessments/{assessment_id}/audit-plan",
    response_model=AuditPlanOut,
    operation_id="getOrCreateAuditPlan",
    responses={404: ERROR_RESPONSES[404], 409: ERROR_RESPONSES[409]},
    summary="Obter ou criar o Plano da Auditoria (1:1 com a avaliação)",
)
def get_or_create_audit_plan(
    assessment_id: UUID, ctx: OrgContextDep
) -> AuditPlanOut:
    return service.get_or_create(ctx, assessment_id)


@router.patch(
    "/assessments/{assessment_id}/audit-plan",
    response_model=AuditPlanOut,
    operation_id="patchAuditPlan",
    responses={
        404: ERROR_RESPONSES[404],
        409: ERROR_RESPONSES[409],
        422: ERROR_RESPONSES[422],
    },
    summary="Atualizar o Plano da Auditoria (autosave / emenda)",
)
def patch_audit_plan(
    assessment_id: UUID,
    payload: AuditPlanPatch,
    ctx: OrgContextDep,
    _idempotency_key: IdempotencyKeyHeader = None,
) -> AuditPlanOut:
    return service.patch_plan(ctx, assessment_id, payload)


@router.post(
    "/assessments/{assessment_id}/audit-plan/ready",
    response_model=AuditPlanOut,
    operation_id="markAuditPlanReady",
    responses={
        404: ERROR_RESPONSES[404],
        409: ERROR_RESPONSES[409],
        422: ERROR_RESPONSES[422],
    },
    summary="Marcar o plano como ready (checklist completo)",
)
def mark_audit_plan_ready(
    assessment_id: UUID,
    ctx: OrgContextDep,
    payload: AuditPlanReadyIn | None = None,
    _idempotency_key: IdempotencyKeyHeader = None,
) -> AuditPlanOut:
    return service.mark_ready(ctx, assessment_id, payload or AuditPlanReadyIn())


@router.post(
    "/assessments/{assessment_id}/audit-plan/refresh-from-preparation",
    response_model=AuditPlanOut,
    operation_id="refreshAuditPlanFromPreparation",
    responses={404: ERROR_RESPONSES[404], 409: ERROR_RESPONSES[409]},
    summary="Preencher campos vazios a partir do Wizard (sem sobrescrever manuais)",
)
def refresh_audit_plan_from_preparation(
    assessment_id: UUID,
    ctx: OrgContextDep,
    payload: AuditPlanRefreshIn | None = None,
) -> AuditPlanOut:
    return service.refresh_from_preparation(
        ctx, assessment_id, payload or AuditPlanRefreshIn()
    )
