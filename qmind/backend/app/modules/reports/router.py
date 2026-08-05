from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query

from app.auth.deps import OrgContextDep
from app.modules.reports import service
from app.modules.reports.schemas import (
    DiscardIn,
    DownloadUrlOut,
    JobOut,
    ReasonIn,
    ReportCreate,
    ReportOut,
    ReportTransitionResult,
)
from app.schemas.common import (
    ERROR_RESPONSES,
    CursorQuery,
    IdempotencyKeyHeader,
    LimitQuery,
)

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post(
    "",
    response_model=ReportOut,
    status_code=201,
    operation_id="createReport",
    responses={409: ERROR_RESPONSES[409], 422: ERROR_RESPONSES[422]},
)
def create_report(
    payload: ReportCreate,
    ctx: OrgContextDep,
    _idempotency_key: IdempotencyKeyHeader = None,
) -> ReportOut:
    return service.create_draft(ctx, payload)


@router.get(
    "",
    response_model=list[ReportOut],
    operation_id="listReports",
)
def list_reports(
    ctx: OrgContextDep,
    assessment_id: UUID = Query(..., description="Required assessment filter"),
    limit: LimitQuery = 50,
    cursor: CursorQuery = None,
) -> list[ReportOut]:
    _ = cursor
    return service.list_reports(ctx, assessment_id)[:limit]


@router.get(
    "/{report_id}",
    response_model=ReportOut,
    operation_id="getReport",
    responses={404: ERROR_RESPONSES[404]},
)
def get_report(report_id: UUID, ctx: OrgContextDep) -> ReportOut:
    return service.get_report(ctx, report_id)


@router.post(
    "/{report_id}/refresh-snapshot",
    response_model=ReportOut,
    operation_id="refreshReportSnapshot",
    responses={409: ERROR_RESPONSES[409]},
)
def refresh_snapshot(report_id: UUID, ctx: OrgContextDep) -> ReportOut:
    return service.refresh_snapshot(ctx, report_id)


@router.post(
    "/{report_id}/transitions/submit",
    response_model=ReportTransitionResult,
    operation_id="submitReport",
    responses={409: ERROR_RESPONSES[409]},
)
def submit(report_id: UUID, ctx: OrgContextDep) -> ReportTransitionResult:
    return service.submit(ctx, report_id)


@router.post(
    "/{report_id}/transitions/request_changes",
    response_model=ReportTransitionResult,
    operation_id="requestReportChanges",
    responses={403: ERROR_RESPONSES[403], 409: ERROR_RESPONSES[409], 422: ERROR_RESPONSES[422]},
)
def request_changes(
    report_id: UUID, payload: ReasonIn, ctx: OrgContextDep
) -> ReportTransitionResult:
    return service.request_changes(ctx, report_id, payload)


@router.post(
    "/{report_id}/transitions/discard",
    response_model=ReportTransitionResult,
    operation_id="discardReport",
    responses={409: ERROR_RESPONSES[409]},
)
def discard(
    report_id: UUID,
    ctx: OrgContextDep,
    payload: DiscardIn | None = None,
) -> ReportTransitionResult:
    return service.discard(ctx, report_id, payload)


@router.post(
    "/{report_id}/transitions/publish",
    response_model=ReportTransitionResult,
    operation_id="publishReport",
    responses={403: ERROR_RESPONSES[403], 409: ERROR_RESPONSES[409]},
    summary="Publish report (idempotent; Idempotency-Key optional)",
)
def publish(
    report_id: UUID,
    ctx: OrgContextDep,
    _idempotency_key: IdempotencyKeyHeader = None,
) -> ReportTransitionResult:
    return service.publish(ctx, report_id)


@router.post(
    "/{report_id}/transitions/archive",
    response_model=ReportTransitionResult,
    operation_id="archiveReport",
    responses={409: ERROR_RESPONSES[409]},
)
def archive(report_id: UUID, ctx: OrgContextDep) -> ReportTransitionResult:
    return service.archive(ctx, report_id)


@router.post(
    "/{report_id}/export-pdf",
    response_model=JobOut,
    status_code=202,
    operation_id="exportReportPdf",
    responses={403: ERROR_RESPONSES[403], 409: ERROR_RESPONSES[409]},
    summary="Enqueue PDF export job (server + client idempotency)",
)
def export_pdf(
    report_id: UUID,
    ctx: OrgContextDep,
    _idempotency_key: IdempotencyKeyHeader = None,
) -> JobOut:
    return service.enqueue_pdf_export(ctx, report_id)


@router.get(
    "/{report_id}/export-pdf/download-url",
    response_model=DownloadUrlOut,
    operation_id="getReportPdfDownloadUrl",
    responses={
        403: ERROR_RESPONSES[403],
        404: ERROR_RESPONSES[404],
        409: ERROR_RESPONSES[409],
    },
    summary="Presigned PDF download (membership + RLS; URL not audited)",
)
def export_pdf_download_url(report_id: UUID, ctx: OrgContextDep) -> DownloadUrlOut:
    return service.export_pdf_download_url(ctx, report_id)
