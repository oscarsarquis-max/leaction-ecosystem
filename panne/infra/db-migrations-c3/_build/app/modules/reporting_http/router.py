from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header
from fastapi.responses import PlainTextResponse, Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.db import get_runtime_session
from app.modules.identity_organization.authorization import Principal
from app.modules.production_http.deps import (
    get_runtime_principal,
    parse_if_match,
    require_correlation_id,
    require_idempotency_key,
)
from app.modules.production_http.errors import raise_domain
from app.modules.reporting_analytics import services
from app.modules.reporting_http.csv_export import build_csv
from app.modules.reporting_http.serialize import preference_out, snapshot_out, view_out

router = APIRouter()


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FilterBody(StrictModel):
    period_start: str | None = None
    period_end: str | None = None
    timezone: str | None = None
    establishment_id: str | None = None
    technical_product_id: str | None = None
    formulation_id: str | None = None
    formulation_version_id: str | None = None
    production_order_id: str | None = None
    production_batch_id: str | None = None
    status: str | None = None
    ingredient_id: str | None = None
    supplier_id: str | None = None
    cost_category: str | None = None
    price_channel: str | None = None
    compliance_status: str | None = None
    cursor: str | None = None
    limit: int | None = None
    order_by: str | None = None


class SavedViewBody(StrictModel):
    code: str
    display_name: str | None = None
    report_code: str
    filters: FilterBody | None = None


class PreferenceBody(StrictModel):
    layout: dict


def _run(action):
    try:
        return action()
    except Exception as exc:
        raise_domain(exc)
        raise


def _command_keys(
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
):
    require_correlation_id(x_correlation_id)
    return require_idempotency_key(idempotency_key)


@router.get("/reporting/catalog")
def catalog(
    principal: Principal = Depends(get_runtime_principal),
    session: Session = Depends(get_runtime_session),
):
    del session
    return {"items": services.authorized_catalog(principal)}


@router.get("/reporting/metrics")
def metrics(principal: Principal = Depends(get_runtime_principal)):
    return {"items": services.metric_dictionary(principal)}


@router.get("/reporting/reports/{report_code}")
def report_get(
    report_code: str,
    period_start: str | None = None,
    period_end: str | None = None,
    timezone: str | None = None,
    establishment_id: str | None = None,
    technical_product_id: str | None = None,
    status: str | None = None,
    price_channel: str | None = None,
    limit: int | None = None,
    order_by: str | None = None,
    principal: Principal = Depends(get_runtime_principal),
    session: Session = Depends(get_runtime_session),
):
    filters = {
        key: value
        for key, value in {
            "period_start": period_start,
            "period_end": period_end,
            "timezone": timezone,
            "establishment_id": establishment_id,
            "technical_product_id": technical_product_id,
            "status": status,
            "price_channel": price_channel,
            "limit": limit,
            "order_by": order_by,
        }.items()
        if value is not None
    }
    return {"data": _run(lambda: services.run_report(session, principal, report_code, filters))}


@router.get("/reporting/reports/{report_code}/metrics/{metric_code}/drill-down")
def drill(
    report_code: str,
    metric_code: str,
    period_start: str | None = None,
    period_end: str | None = None,
    timezone: str | None = None,
    limit: int | None = None,
    cursor: str | None = None,
    principal: Principal = Depends(get_runtime_principal),
    session: Session = Depends(get_runtime_session),
):
    filters = {
        "period_start": period_start,
        "period_end": period_end,
        "timezone": timezone,
        "limit": limit,
        "cursor": cursor,
    }
    return {"data": _run(lambda: services.run_drill_down(session, principal, report_code, metric_code, filters))}


@router.post("/reporting/snapshots")
def create_snapshot(
    report_code: str,
    body: FilterBody,
    principal: Principal = Depends(get_runtime_principal),
    session: Session = Depends(get_runtime_session),
    idempotency_key: UUID = Depends(_command_keys),
):
    row = _run(
        lambda: services.create_snapshot(
            session,
            principal,
            report_code,
            body.model_dump(exclude_none=True),
            idempotency_key=idempotency_key,
        )
    )
    return {"data": snapshot_out(row)}


@router.get("/reporting/snapshots")
def snapshots(
    principal: Principal = Depends(get_runtime_principal),
    session: Session = Depends(get_runtime_session),
):
    return {"items": [snapshot_out(row) for row in services.list_snapshots(session, principal)]}


@router.get("/reporting/snapshots/{snapshot_id}")
def snapshot_get(
    snapshot_id: UUID,
    principal: Principal = Depends(get_runtime_principal),
    session: Session = Depends(get_runtime_session),
):
    return {"data": snapshot_out(_run(lambda: services.get_snapshot(session, principal, snapshot_id)))}


@router.post("/reporting/snapshots/{snapshot_id}/recalculate")
def snapshot_recalculate(
    snapshot_id: UUID,
    principal: Principal = Depends(get_runtime_principal),
    session: Session = Depends(get_runtime_session),
):
    _run(lambda: services.refuse_recalculate_snapshot(session, principal, snapshot_id))


@router.get("/reporting/snapshots/{snapshot_id}/export.csv")
def snapshot_csv(
    snapshot_id: UUID,
    principal: Principal = Depends(get_runtime_principal),
    session: Session = Depends(get_runtime_session),
    idempotency_key: UUID = Depends(_command_keys),
):
    payload = _run(lambda: services.open_snapshot(session, principal, snapshot_id))
    csv_text = build_csv(payload)
    rows = len(payload.get("indicators") or [])
    _run(
        lambda: services.register_export(
            session,
            principal,
            snapshot_id,
            "csv",
            rows,
            payload.get("content_hash") or "",
            idempotency_key=idempotency_key,
        )
    )
    return PlainTextResponse(csv_text, media_type="text/csv; charset=utf-8")


@router.get("/reporting/snapshots/{snapshot_id}/print")
def snapshot_print(
    snapshot_id: UUID,
    principal: Principal = Depends(get_runtime_principal),
    session: Session = Depends(get_runtime_session),
    idempotency_key: UUID = Depends(_command_keys),
):
    payload = _run(lambda: services.open_snapshot(session, principal, snapshot_id))
    _run(
        lambda: services.register_export(
            session,
            principal,
            snapshot_id,
            "html",
            len(payload.get("indicators") or []),
            payload.get("content_hash") or "",
            idempotency_key=idempotency_key,
        )
    )
    cards = "".join(
        f"<tr><th>{item.get('name')}</th><td>{item.get('status')}</td><td>{item.get('value') or '—'}</td></tr>"
        for item in payload.get("indicators") or []
    )
    html = (
        "<!doctype html><html lang='pt-BR'><head><meta charset='utf-8'><title>Relatório Panne</title>"
        "<style>body{font-family:Georgia,serif;color:#323334;background:#E5E4D6;padding:24px}"
        "nav,.submenu,.shell-tools{display:none}@media print{nav{display:none}}</style></head><body>"
        f"<h1>Relatório {payload.get('report_code')}</h1>"
        f"<p>Dados até {payload.get('data_cutoff_at')} · hash {payload.get('content_hash')}</p>"
        f"<table>{cards}</table></body></html>"
    )
    return Response(html, media_type="text/html; charset=utf-8")


@router.get("/reporting/saved-views")
def saved_views(
    principal: Principal = Depends(get_runtime_principal),
    session: Session = Depends(get_runtime_session),
):
    return {"items": [view_out(row) for row in services.list_saved_views(session, principal)]}


@router.post("/reporting/saved-views")
def create_view(
    body: SavedViewBody,
    principal: Principal = Depends(get_runtime_principal),
    session: Session = Depends(get_runtime_session),
    idempotency_key: UUID = Depends(_command_keys),
):
    filters = body.filters.model_dump(exclude_none=True) if body.filters else {}
    row = _run(
        lambda: services.create_saved_view(
            session,
            principal,
            {"code": body.code, "display_name": body.display_name, "report_code": body.report_code, "filters": filters},
            idempotency_key=idempotency_key,
        )
    )
    return {"data": view_out(row)}


@router.get("/reporting/preferences/{report_code}")
def get_pref(
    report_code: str,
    principal: Principal = Depends(get_runtime_principal),
    session: Session = Depends(get_runtime_session),
):
    row = services.get_preference(session, principal, report_code)
    return {"data": None if row is None else preference_out(row)}


@router.patch("/reporting/preferences/{report_code}")
def patch_pref(
    report_code: str,
    body: PreferenceBody,
    principal: Principal = Depends(get_runtime_principal),
    session: Session = Depends(get_runtime_session),
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
):
    version = parse_if_match(if_match, required=False) or 1
    row = _run(lambda: services.update_preference(session, principal, report_code, body.layout, expected_version=version))
    return {"data": preference_out(row), "row_version": row.row_version}
