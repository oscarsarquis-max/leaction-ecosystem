from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from app.auth.deps import OrgContextDep
from app.modules.reports import service as reports_service
from app.modules.reports.schemas import JobOut
from app.schemas.common import ERROR_RESPONSES

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get(
    "/{job_id}",
    response_model=JobOut,
    operation_id="getJob",
    responses={403: ERROR_RESPONSES[403], 404: ERROR_RESPONSES[404]},
    summary="Get async job status (org-scoped via RLS)",
)
def get_job(job_id: UUID, ctx: OrgContextDep) -> JobOut:
    return reports_service.get_job(ctx, job_id)
