"""Execution Intelligence orchestration and immutable history (ISOI-009)."""

from __future__ import annotations

import json
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.auth.context import OrgContext
from app.config import get_settings
from app.db import tenant_connection
from app.errors import AppError
from app.idempotency import assert_same_request, key_hash, request_fingerprint
from app.modules.improvement_cases import service as cases_service
from app.modules.improvement_cases.execution_intelligence_builder import (
    build_execution_intelligence_input,
)
from app.modules.improvement_cases.execution_intelligence_schemas import (
    ExecutionIntelligenceInput,
    ExecutionIntelligenceResult,
    ExecutionIntelligenceRunOut,
    dump_jsonable,
)
from app.modules.improvement_cases.fingerprint import (
    fingerprint_execution_intelligence_input,
)
from app.modules.oi.client import OrganizationalIntelligenceClient
from app.modules.orgs.service import require_role

_EXECUTE_ROLES = (
    "org_admin",
    "quality_manager",
    "process_owner",
    "consultant_auditor",
    "platform_admin",
)
_COLS = """
    id, organization_id, improvement_case_id, schema_version, mechanism_version,
    request_id, correlation_id, generated_at, input_snapshot, input_fingerprint,
    result, created_by, created_at, request_fingerprint
"""


def _json(value):
    return json.loads(value) if isinstance(value, str) else value


def _row_to_run(row, *, is_stale: bool) -> ExecutionIntelligenceRunOut:
    return ExecutionIntelligenceRunOut(
        id=row.id,
        organization_id=row.organization_id,
        improvement_case_id=row.improvement_case_id,
        schema_version=row.schema_version,
        mechanism_version=row.mechanism_version,
        request_id=row.request_id,
        correlation_id=row.correlation_id,
        generated_at=row.generated_at,
        input_fingerprint=row.input_fingerprint,
        input_snapshot=ExecutionIntelligenceInput.model_validate(_json(row.input_snapshot)),
        result=ExecutionIntelligenceResult.model_validate(_json(row.result)),
        created_by=row.created_by,
        created_at=row.created_at,
        is_stale=is_stale,
    )


def current_context_fingerprint(ctx: OrgContext, case_id: UUID) -> str:
    return fingerprint_execution_intelligence_input(
        build_execution_intelligence_input(ctx, case_id)
    )


def _idempotency_scope(case_id: UUID) -> str:
    return f"improvement-case:{case_id}:execution-intelligence"


def _idempotency_fingerprint(
    scope: str, case_id: UUID, input_fingerprint: str
) -> str:
    return request_fingerprint(
        scope,
        {
            "improvement_case_id": case_id,
            "input_fingerprint": input_fingerprint,
        },
    )


def _existing_by_key(
    ctx: OrgContext, case_id: UUID, raw_key: str, input_fingerprint: str
) -> ExecutionIntelligenceRunOut | None:
    scope = _idempotency_scope(case_id)
    fingerprint = _idempotency_fingerprint(scope, case_id, input_fingerprint)
    with tenant_connection(ctx.organization_id) as conn:
        row = conn.execute(
            text(
                f"""
                SELECT {_COLS}
                FROM improvement_case_execution_intelligence_runs
                WHERE organization_id = :org
                  AND idempotency_scope = :scope
                  AND idempotency_key_hash = :key_hash
                """
            ),
            {
                "org": ctx.organization_id,
                "scope": scope,
                "key_hash": key_hash(raw_key),
            },
        ).first()
    if row is None:
        return None
    assert_same_request(row.request_fingerprint, fingerprint)
    stale = row.input_fingerprint != current_context_fingerprint(ctx, case_id)
    return _row_to_run(row, is_stale=stale)


def _validate_result(
    payload: ExecutionIntelligenceInput,
    result: ExecutionIntelligenceResult,
) -> None:
    echoes = (
        ("core_organization_id", result.core_organization_id, payload.core_organization_id),
        ("improvement_case_id", result.improvement_case_id, payload.improvement_case_id),
        ("request_id", result.request_id, payload.request_id),
        ("correlation_id", result.correlation_id, payload.correlation_id),
        ("schema_version", result.schema_version, payload.schema_version),
    )
    for name, actual, expected in echoes:
        if actual != expected:
            raise AppError(
                "oi_execution_echo_mismatch",
                f"QMind OI response {name} does not match the request",
                status_code=502,
            )
    allowed = set(payload.fact_refs)
    invented = sorted(
        {
            ref
            for signal in result.signals
            for ref in signal.supporting_fact_refs
            if ref not in allowed
        }
    )
    if invented:
        raise AppError(
            "oi_invented_fact_ref",
            "QMind OI response references facts absent from the Core snapshot",
            status_code=502,
        )


def create_run(
    ctx: OrgContext,
    case_id: UUID,
    *,
    idempotency_key: str | None = None,
    client: OrganizationalIntelligenceClient | None = None,
) -> ExecutionIntelligenceRunOut:
    require_role(ctx, *_EXECUTE_ROLES)
    cases_service.get_case(ctx, case_id)
    raw_key = (idempotency_key or "").strip() or None
    if raw_key and len(raw_key) > 200:
        raise AppError(
            "invalid_idempotency_key",
            "Idempotency-Key must have at most 200 characters",
            status_code=422,
        )
    snapshot = build_execution_intelligence_input(ctx, case_id)
    fingerprint = fingerprint_execution_intelligence_input(snapshot)
    if raw_key:
        existing = _existing_by_key(ctx, case_id, raw_key, fingerprint)
        if existing is not None:
            return existing

    # Builder owns and closes its read transaction before the network call.
    result = (client or OrganizationalIntelligenceClient(get_settings())).analyze_execution(
        snapshot
    )
    _validate_result(snapshot, result)

    # Optimistic context guard: never persist an interpretation of facts that
    # changed while OI was evaluating the request.
    if current_context_fingerprint(ctx, case_id) != fingerprint:
        raise AppError(
            "execution_context_changed",
            "Execution context changed during analysis; run it again",
            status_code=409,
        )

    scope = _idempotency_scope(case_id) if raw_key else None
    req_fp = (
        _idempotency_fingerprint(scope, case_id, fingerprint) if scope else None
    )
    params = {
        "org": ctx.organization_id,
        "case_id": case_id,
        "schema_version": result.schema_version,
        "mechanism_version": result.mechanism_version,
        "request_id": result.request_id,
        "correlation_id": result.correlation_id,
        "generated_at": result.generated_at,
        "snapshot": json.dumps(dump_jsonable(snapshot)),
        "fingerprint": fingerprint,
        "result": json.dumps(dump_jsonable(result)),
        "scope": scope,
        "key_hash": key_hash(raw_key) if raw_key else None,
        "request_fingerprint": req_fp,
        "created_by": ctx.principal.user_id,
    }
    try:
        with tenant_connection(ctx.organization_id) as conn:
            row = conn.execute(
                text(
                    f"""
                    INSERT INTO improvement_case_execution_intelligence_runs (
                      organization_id, improvement_case_id, schema_version,
                      mechanism_version, request_id, correlation_id, generated_at,
                      input_snapshot, input_fingerprint, result, idempotency_scope,
                      idempotency_key_hash, request_fingerprint, created_by
                    ) VALUES (
                      :org, :case_id, :schema_version, :mechanism_version,
                      :request_id, :correlation_id, :generated_at,
                      CAST(:snapshot AS jsonb), :fingerprint, CAST(:result AS jsonb),
                      :scope, :key_hash, :request_fingerprint, :created_by
                    )
                    RETURNING {_COLS}
                    """
                ),
                params,
            ).one()
            conn.commit()
    except IntegrityError:
        if raw_key:
            replay = _existing_by_key(ctx, case_id, raw_key, fingerprint)
            if replay is not None:
                return replay
        raise
    return _row_to_run(row, is_stale=False)


def list_runs(
    ctx: OrgContext, case_id: UUID, *, limit: int = 50
) -> list[ExecutionIntelligenceRunOut]:
    cases_service.get_case(ctx, case_id)
    current = current_context_fingerprint(ctx, case_id)
    with tenant_connection(ctx.organization_id) as conn:
        rows = conn.execute(
            text(
                f"""
                SELECT {_COLS}
                FROM improvement_case_execution_intelligence_runs
                WHERE organization_id = :org AND improvement_case_id = :case_id
                ORDER BY created_at DESC LIMIT :limit
                """
            ),
            {"org": ctx.organization_id, "case_id": case_id, "limit": limit},
        ).all()
    return [_row_to_run(row, is_stale=row.input_fingerprint != current) for row in rows]


def get_run(
    ctx: OrgContext, case_id: UUID, run_id: UUID
) -> ExecutionIntelligenceRunOut:
    cases_service.get_case(ctx, case_id)
    current = current_context_fingerprint(ctx, case_id)
    with tenant_connection(ctx.organization_id) as conn:
        row = conn.execute(
            text(
                f"""
                SELECT {_COLS}
                FROM improvement_case_execution_intelligence_runs
                WHERE id = :id AND organization_id = :org
                  AND improvement_case_id = :case_id
                """
            ),
            {"id": run_id, "org": ctx.organization_id, "case_id": case_id},
        ).first()
    if row is None:
        raise AppError("not_found", "Execution Intelligence run not found", status_code=404)
    return _row_to_run(row, is_stale=row.input_fingerprint != current)


def latest_run(ctx: OrgContext, case_id: UUID) -> ExecutionIntelligenceRunOut:
    runs = list_runs(ctx, case_id, limit=1)
    if not runs:
        raise AppError("not_found", "Execution Intelligence run not found", status_code=404)
    return runs[0]
