from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query

from app.auth.deps import OrgContextDep
from app.modules.reports import service
from app.modules.reports.schemas import (
    DiscardIn,
    JobOut,
    ReasonIn,
    ReportCreate,
    ReportOut,
    ReportTransitionResult,
)

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("", response_model=ReportOut, status_code=201)
def create_report(payload: ReportCreate, ctx: OrgContextDep) -> ReportOut:
    return service.create_draft(ctx, payload)


@router.get("", response_model=list[ReportOut])
def list_reports(ctx: OrgContextDep, assessment_id: UUID = Query(...)) -> list[ReportOut]:
    return service.list_reports(ctx, assessment_id)


@router.get("/{report_id}", response_model=ReportOut)
def get_report(report_id: UUID, ctx: OrgContextDep) -> ReportOut:
    return service.get_report(ctx, report_id)


@router.post("/{report_id}/refresh-snapshot", response_model=ReportOut)
def refresh_snapshot(report_id: UUID, ctx: OrgContextDep) -> ReportOut:
    return service.refresh_snapshot(ctx, report_id)


@router.post("/{report_id}/transitions/submit", response_model=ReportTransitionResult)
def submit(report_id: UUID, ctx: OrgContextDep) -> ReportTransitionResult:
    return service.submit(ctx, report_id)


@router.post("/{report_id}/transitions/request_changes", response_model=ReportTransitionResult)
def request_changes(
    report_id: UUID, payload: ReasonIn, ctx: OrgContextDep
) -> ReportTransitionResult:
    return service.request_changes(ctx, report_id, payload)


@router.post("/{report_id}/transitions/discard", response_model=ReportTransitionResult)
def discard(
    report_id: UUID,
    ctx: OrgContextDep,
    payload: DiscardIn | None = None,
) -> ReportTransitionResult:
    return service.discard(ctx, report_id, payload)


@router.post("/{report_id}/transitions/publish", response_model=ReportTransitionResult)
def publish(report_id: UUID, ctx: OrgContextDep) -> ReportTransitionResult:
    return service.publish(ctx, report_id)


@router.post("/{report_id}/transitions/archive", response_model=ReportTransitionResult)
def archive(report_id: UUID, ctx: OrgContextDep) -> ReportTransitionResult:
    return service.archive(ctx, report_id)


@router.post("/{report_id}/export-pdf", response_model=JobOut, status_code=202)
def export_pdf(report_id: UUID, ctx: OrgContextDep) -> JobOut:
    return service.enqueue_pdf_export(ctx, report_id)
