"""Serviços de catálogo, execução, snapshot, visão salva e exportação."""

import json
from datetime import datetime
from hashlib import sha256
from time import time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.identity_organization.authorization import (
    PERMISSION_REPORTING_EXPORT,
    PERMISSION_REPORTING_SAVED_VIEW_MANAGE,
    PERMISSION_REPORTING_SNAPSHOT_CREATE,
    Principal,
    require_permission,
)
from app.modules.production_planning.errors import (
    ConcurrencyError,
    IdempotencyConflictError,
    ImmutableError,
    ValidationError,
)
from app.modules.reporting_analytics.catalog import REPORTS
from app.modules.reporting_analytics.constants import (
    CACHE_TTL_SECONDS,
    EXPORT_ROW_LIMIT,
    SNAPSHOT_BYTES_MAX,
)
from app.modules.reporting_analytics.engine import drill_down, execute_report
from app.modules.reporting_analytics.filters import ReportFilters, normalize_filters
from app.modules.reporting_analytics.metrics import METRICS
from app.modules.reporting_analytics.models import (
    ReportingCommand,
    ReportingCoverageItem,
    ReportingDashboardPreference,
    ReportingExecution,
    ReportingExport,
    ReportingSavedView,
    ReportingSnapshot,
)

_CACHE: dict[tuple, tuple[float, dict]] = {}


def _org(principal: Principal):
    if principal.selected is None:
        raise ValidationError("organizacao_nao_selecionada")
    return principal.selected.organization_id


def _digest(payload: dict) -> str:
    return sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


def _replay(session: Session, organization_id, key, command: str, payload: dict):
    if key is None:
        return None
    row = session.scalar(
        select(ReportingCommand).where(
            ReportingCommand.organization_id == organization_id,
            ReportingCommand.idempotency_key == key,
        )
    )
    if row is None:
        return None
    if row.command != command or row.payload_digest != _digest(payload):
        raise IdempotencyConflictError("idempotencia_conflito")
    return row


def _store_command(session, organization_id, key, command, payload, resource_type, resource_id, actor_user_id):
    if key is None:
        return
    session.add(
        ReportingCommand(
            organization_id=organization_id,
            idempotency_key=key,
            command=command,
            payload_digest=_digest(payload),
            resource_type=resource_type,
            resource_id=resource_id,
            actor_user_id=actor_user_id,
        )
    )


def authorized_catalog(principal: Principal) -> list[dict]:
    items = []
    for spec in REPORTS.values():
        if spec.permission not in principal.permissions:
            continue
        items.append(
            {
                "code": spec.code,
                "name": spec.name,
                "description": spec.description,
                "version": spec.version,
                "metrics": list(spec.metrics),
            }
        )
    return items


def metric_dictionary(principal: Principal) -> list[dict]:
    allowed = {code for spec in REPORTS.values() if spec.permission in principal.permissions for code in spec.metrics}
    result = []
    for code in allowed:
        spec = METRICS[code]
        result.append(
            {
                "code": spec.code,
                "name": spec.name,
                "description": spec.description,
                "version": spec.version,
                "unit": spec.unit,
                "numerator": spec.numerator,
                "denominator": spec.denominator,
                "absence": spec.absence,
                "origins": list(spec.origins),
            }
        )
    return result


def _cache_key(principal: Principal, report_code: str, filters: ReportFilters):
    perms = tuple(sorted(principal.permissions))
    return (principal.user_id, _org(principal), perms, report_code, json.dumps(filters.as_dict(), sort_keys=True))


def run_report(session: Session, principal: Principal, report_code: str, raw_filters: dict | None) -> dict:
    filters = normalize_filters(raw_filters)
    key = _cache_key(principal, report_code, filters)
    cached = _CACHE.get(key)
    if cached is not None:
        stored_at, payload = cached
        if time() - stored_at < CACHE_TTL_SECONDS:
            return payload
    payload = execute_report(session, principal, report_code, filters, persist_coverage=True)
    _CACHE[key] = (time(), payload)
    return payload


def create_snapshot(session: Session, principal: Principal, report_code: str, raw_filters: dict, *, idempotency_key):
    require_permission(principal, PERMISSION_REPORTING_SNAPSHOT_CREATE)
    org = _org(principal)
    replay = _replay(session, org, idempotency_key, "reporting.snapshot.create", {"report_code": report_code, **raw_filters})
    if replay is not None:
        return session.get(ReportingSnapshot, replay.resource_id)
    payload = run_report(session, principal, report_code, raw_filters)
    encoded = json.dumps(payload, default=str).encode()
    if len(encoded) > SNAPSHOT_BYTES_MAX:
        raise ValidationError("exportacao_excedida")
    filters = normalize_filters(raw_filters)
    execution = ReportingExecution(
        organization_id=org,
        report_code=report_code,
        report_version=payload["report_version"],
        query_version=payload["query_version"],
        metrics_version=payload["metrics_version"],
        filters=filters.as_dict(),
        timezone=filters.timezone,
        period_start=filters.period_start,
        period_end=filters.period_end,
        data_cutoff_at=datetime.fromisoformat(str(payload["data_cutoff_at"]).replace("Z", "+00:00")),
        completeness=payload["completeness"],
        coverage={"items": payload.get("_coverage_rows") or []},
        duration_ms=payload["duration_ms"],
        content_hash=payload["content_hash"],
        actor_user_id=principal.user_id,
    )
    session.add(execution)
    session.flush()
    snapshot = ReportingSnapshot(
        organization_id=org,
        reporting_execution_id=execution.id,
        payload={k: v for k, v in payload.items() if not k.startswith("_")},
        content_hash=payload["content_hash"],
    )
    session.add(snapshot)
    session.flush()
    for item in payload.get("_coverage_rows") or []:
        session.add(
            ReportingCoverageItem(
                organization_id=org,
                reporting_execution_id=execution.id,
                domain=item["domain"],
                universe=item["universe"],
                valid_count=item["valid_count"],
                missing_count=item["missing_count"],
                reason=item["reason"],
            )
        )
    _store_command(
        session, org, idempotency_key, "reporting.snapshot.create",
        {"report_code": report_code, **raw_filters}, "reporting_snapshot", snapshot.id, principal.user_id,
    )
    session.flush()
    return snapshot


def get_snapshot(session: Session, principal: Principal, snapshot_id) -> ReportingSnapshot:
    org = _org(principal)
    row = session.get(ReportingSnapshot, snapshot_id)
    if row is None or row.organization_id != org:
        raise ValidationError("recurso_nao_encontrado")
    execution = session.get(ReportingExecution, row.reporting_execution_id)
    if execution is None:
        raise ValidationError("recurso_nao_encontrado")
    spec = REPORTS[execution.report_code]
    require_permission(principal, spec.permission)
    return row


def list_snapshots(session: Session, principal: Principal) -> list[ReportingSnapshot]:
    return list(
        session.scalars(
            select(ReportingSnapshot).where(ReportingSnapshot.organization_id == _org(principal))
        )
    )


def create_saved_view(session: Session, principal: Principal, body: dict, *, idempotency_key):
    require_permission(principal, PERMISSION_REPORTING_SAVED_VIEW_MANAGE)
    org = _org(principal)
    replay = _replay(session, org, idempotency_key, "reporting.saved_view.create", body)
    if replay is not None:
        return session.get(ReportingSavedView, replay.resource_id)
    if body.get("report_code") not in REPORTS:
        raise ValidationError("relatorio_desconhecido")
    require_permission(principal, REPORTS[body["report_code"]].permission)
    filters = normalize_filters(body.get("filters"))
    row = ReportingSavedView(
        organization_id=org,
        code=body["code"],
        display_name=body.get("display_name") or body["code"],
        report_code=body["report_code"],
        filters=filters.as_dict(),
        created_by_user_id=principal.user_id,
    )
    session.add(row)
    session.flush()
    _store_command(session, org, idempotency_key, "reporting.saved_view.create", body, "reporting_saved_view", row.id, principal.user_id)
    return row


def list_saved_views(session: Session, principal: Principal) -> list[ReportingSavedView]:
    return list(
        session.scalars(select(ReportingSavedView).where(ReportingSavedView.organization_id == _org(principal)))
    )


def update_preference(session: Session, principal: Principal, report_code: str, layout: dict, *, expected_version: int):
    org = _org(principal)
    if report_code not in REPORTS:
        raise ValidationError("relatorio_desconhecido")
    require_permission(principal, REPORTS[report_code].permission)
    row = session.scalar(
        select(ReportingDashboardPreference).where(
            ReportingDashboardPreference.organization_id == org,
            ReportingDashboardPreference.user_id == principal.user_id,
            ReportingDashboardPreference.report_code == report_code,
        )
    )
    if row is None:
        row = ReportingDashboardPreference(
            organization_id=org,
            user_id=principal.user_id,
            report_code=report_code,
            layout=layout,
        )
        session.add(row)
        session.flush()
        return row
    if row.row_version != expected_version:
        raise ConcurrencyError("versao_conflito")
    row.layout = layout
    row.row_version += 1
    session.flush()
    return row


def get_preference(session: Session, principal: Principal, report_code: str) -> ReportingDashboardPreference | None:
    return session.scalar(
        select(ReportingDashboardPreference).where(
            ReportingDashboardPreference.organization_id == _org(principal),
            ReportingDashboardPreference.user_id == principal.user_id,
            ReportingDashboardPreference.report_code == report_code,
        )
    )


def register_export(session: Session, principal: Principal, snapshot_id, kind: str, row_count: int, content_hash: str, *, idempotency_key):
    require_permission(principal, PERMISSION_REPORTING_EXPORT)
    if row_count > EXPORT_ROW_LIMIT:
        raise ValidationError("exportacao_excedida")
    snapshot = get_snapshot(session, principal, snapshot_id)
    org = _org(principal)
    payload = {"snapshot_id": str(snapshot.id), "kind": kind, "row_count": row_count}
    replay = _replay(session, org, idempotency_key, "reporting.export", payload)
    if replay is not None:
        return session.get(ReportingExport, replay.resource_id)
    row = ReportingExport(
        organization_id=org,
        reporting_execution_id=snapshot.reporting_execution_id,
        kind=kind,
        row_count=row_count,
        content_hash=content_hash,
        created_by_user_id=principal.user_id,
    )
    session.add(row)
    session.flush()
    _store_command(session, org, idempotency_key, "reporting.export", payload, "reporting_export", row.id, principal.user_id)
    return row


def open_snapshot(session: Session, principal: Principal, snapshot_id) -> dict:
    row = get_snapshot(session, principal, snapshot_id)
    return row.payload


def refuse_recalculate_snapshot(session: Session, principal: Principal, snapshot_id) -> None:
    get_snapshot(session, principal, snapshot_id)
    raise ImmutableError("snapshot_imutavel")


def run_drill_down(session: Session, principal: Principal, report_code: str, metric_code: str, raw_filters: dict):
    filters = normalize_filters(raw_filters)
    return drill_down(session, principal, report_code, metric_code, filters)
