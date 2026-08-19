from __future__ import annotations

from uuid import UUID

from sqlalchemy import text

from app.auth.context import OrgContext
from app.db import tenant_connection
from app.errors import AppError
from app.modules.improvement_cases.schemas import (
    ImprovementCaseCreate,
    ImprovementCaseOut,
    ImprovementCasePatch,
    ImprovementCaseStatus,
)
from app.modules.orgs.service import require_role

_READ_ROLES = (
    "org_admin",
    "consultant_auditor",
    "quality_manager",
    "process_owner",
    "reader",
    "action_owner",
    "platform_admin",
)
# Same write gate as Organization Profile PATCH / Action Item create.
_WRITE_ROLES = (
    "org_admin",
    "consultant_auditor",
    "quality_manager",
    "platform_admin",
)

_COLUMNS = """
    id, organization_id, problem_statement, impact_statement, related_process,
    status, created_by, created_at, updated_at
"""

_ALLOWED_TRANSITIONS: dict[ImprovementCaseStatus, frozenset[ImprovementCaseStatus]] = {
    "open": frozenset({"analyzing"}),
    "analyzing": frozenset({"open", "acting"}),
    "acting": frozenset({"analyzing", "reviewing"}),
    "reviewing": frozenset({"acting", "closed"}),
    "closed": frozenset({"reviewing"}),
}


def _row_to_out(row) -> ImprovementCaseOut:
    return ImprovementCaseOut(
        id=row.id,
        organization_id=row.organization_id,
        problem_statement=row.problem_statement,
        impact_statement=row.impact_statement,
        related_process=row.related_process,
        status=row.status,
        created_by=row.created_by,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _assert_transition(
    current: ImprovementCaseStatus, nxt: ImprovementCaseStatus
) -> None:
    if nxt == current:
        return
    allowed = _ALLOWED_TRANSITIONS.get(current, frozenset())
    if nxt not in allowed:
        raise AppError(
            "invalid_transition",
            f"Transition from '{current}' to '{nxt}' is not allowed",
            status_code=409,
        )


def create_case(ctx: OrgContext, payload: ImprovementCaseCreate) -> ImprovementCaseOut:
    require_role(ctx, *_WRITE_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        row = conn.execute(
            text(
                f"""
                INSERT INTO improvement_cases (
                  organization_id, problem_statement, impact_statement,
                  related_process, status, created_by
                )
                VALUES (
                  :org, :problem, :impact, :process, 'open', :author
                )
                RETURNING {_COLUMNS}
                """
            ),
            {
                "org": ctx.organization_id,
                "problem": payload.problem_statement,
                "impact": payload.impact_statement,
                "process": payload.related_process,
                "author": ctx.principal.user_id,
            },
        ).one()
        conn.commit()
    return _row_to_out(row)


def list_cases(ctx: OrgContext, *, limit: int = 50) -> list[ImprovementCaseOut]:
    require_role(ctx, *_READ_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        rows = conn.execute(
            text(
                f"""
                SELECT {_COLUMNS}
                FROM improvement_cases
                WHERE organization_id = :org
                ORDER BY updated_at DESC
                LIMIT :lim
                """
            ),
            {"org": ctx.organization_id, "lim": limit},
        ).all()
    return [_row_to_out(r) for r in rows]


def get_case(ctx: OrgContext, case_id: UUID) -> ImprovementCaseOut:
    require_role(ctx, *_READ_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        row = conn.execute(
            text(
                f"""
                SELECT {_COLUMNS}
                FROM improvement_cases
                WHERE id = :id AND organization_id = :org
                """
            ),
            {"id": case_id, "org": ctx.organization_id},
        ).first()
    if row is None:
        raise AppError("not_found", "Improvement case not found", status_code=404)
    return _row_to_out(row)


def patch_case(
    ctx: OrgContext, case_id: UUID, payload: ImprovementCasePatch
) -> ImprovementCaseOut:
    require_role(ctx, *_WRITE_ROLES)
    data = payload.model_dump(exclude_unset=True)
    if not data:
        return get_case(ctx, case_id)

    current = get_case(ctx, case_id)
    if "status" in data:
        _assert_transition(current.status, data["status"])

    sets = [f"{col} = :{col}" for col in data]
    sets.append("updated_at = now()")
    params = {"id": case_id, "org": ctx.organization_id, **data}
    with tenant_connection(ctx.organization_id) as conn:
        row = conn.execute(
            text(
                f"""
                UPDATE improvement_cases
                SET {", ".join(sets)}
                WHERE id = :id AND organization_id = :org
                RETURNING {_COLUMNS}
                """
            ),
            params,
        ).first()
        if row is None:
            raise AppError("not_found", "Improvement case not found", status_code=404)
        conn.commit()
    return _row_to_out(row)
