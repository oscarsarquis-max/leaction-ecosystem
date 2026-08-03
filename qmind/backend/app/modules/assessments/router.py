from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from app.auth.deps import OrgContextDep
from app.modules.assessments import service
from app.modules.assessments.schemas import (
    AssessmentCreate,
    AssessmentOut,
    AssessmentPlanResult,
)

router = APIRouter(prefix="/assessments", tags=["assessments"])


@router.post("", response_model=AssessmentOut, status_code=201)
def create_assessment(payload: AssessmentCreate, ctx: OrgContextDep) -> AssessmentOut:
    return service.create_draft(ctx, payload)


@router.get("", response_model=list[AssessmentOut])
def list_assessments(ctx: OrgContextDep) -> list[AssessmentOut]:
    return service.list_assessments(ctx)


@router.post("/{assessment_id}/transitions/plan", response_model=AssessmentPlanResult)
def plan_assessment(assessment_id: UUID, ctx: OrgContextDep) -> AssessmentPlanResult:
    return service.transition_plan(ctx, assessment_id)
