"""Check-ins, impediments and dependencies (ISOI-007)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.audit import write_audit
from app.auth.context import OrgContext
from app.db import tenant_connection
from app.errors import AppError
from app.modules.agile.schemas import (
    CheckInCreate,
    CheckInOut,
    DependencyCreate,
    DependencyOut,
    ImpedimentCreate,
    ImpedimentOut,
    ImpedimentUpdate,
)
from app.modules.orgs.service import require_role

_MUTATE = (
    "org_admin",
    "quality_manager",
    "process_owner",
    "action_owner",
    "consultant_auditor",
)
_READ = _MUTATE + ("reader",)


def _require_mutate(ctx: OrgContext) -> None:
    require_role(ctx, *_MUTATE)


def _require_read(ctx: OrgContext) -> None:
    require_role(ctx, *_READ)


def _assert_action_item(conn: Connection, org_id: UUID, action_item_id: UUID) -> None:
    row = conn.execute(
        text(
            """
            SELECT id FROM action_items
            WHERE id = :id AND organization_id = :org
            """
        ),
        {"id": action_item_id, "org": org_id},
    ).first()
    if row is None:
        raise AppError("not_found", "ActionItem not found", status_code=404)


def _assert_action_allocated_to_sprint(
    conn: Connection, org_id: UUID, action_item_id: UUID, sprint_id: UUID
) -> None:
    """Reject execution records pointing at a sprint the action is not committed to.

    Only a live allocation counts: a card removed from the sprint (carry-over,
    de-allocation) can no longer receive new check-ins or impediments, even
    though the records already written against it remain readable.
    """
    row = conn.execute(
        text(
            """
            SELECT 1 FROM agile_sprint_cards
            WHERE organization_id = :org
              AND action_item_id = :aid
              AND sprint_id = :sid
              AND removed_at IS NULL
            """
        ),
        {"org": org_id, "aid": action_item_id, "sid": sprint_id},
    ).first()
    if row is None:
        raise AppError(
            "action_sprint_mismatch",
            "ActionItem is not currently allocated to this sprint",
            status_code=409,
        )


def _checkin_out(row) -> CheckInOut:
    return CheckInOut(
        id=row.id,
        organization_id=row.organization_id,
        action_item_id=row.action_item_id,
        sprint_id=row.sprint_id,
        health=row.health,
        progress_note=row.progress_note,
        next_step=row.next_step or "",
        reported_by=row.reported_by,
        reported_at=row.reported_at,
    )


def create_check_in(
    ctx: OrgContext, action_item_id: UUID, payload: CheckInCreate
) -> CheckInOut:
    _require_mutate(ctx)
    with tenant_connection(ctx.organization_id) as conn:
        _assert_action_item(conn, ctx.organization_id, action_item_id)
        if payload.sprint_id is not None:
            _assert_action_allocated_to_sprint(
                conn, ctx.organization_id, action_item_id, payload.sprint_id
            )
        if payload.idempotency_key:
            existing = conn.execute(
                text(
                    """
                    SELECT id, organization_id, action_item_id, sprint_id,
                           health, progress_note, next_step, reported_by, reported_at
                    FROM action_execution_check_ins
                    WHERE organization_id = :org
                      AND action_item_id = :aid
                      AND idempotency_key = :key
                    """
                ),
                {
                    "org": ctx.organization_id,
                    "aid": action_item_id,
                    "key": payload.idempotency_key,
                },
            ).first()
            if existing:
                return _checkin_out(existing)
        row = conn.execute(
            text(
                """
                INSERT INTO action_execution_check_ins (
                  organization_id, action_item_id, sprint_id, health,
                  progress_note, next_step, reported_by, idempotency_key
                ) VALUES (
                  :org, :aid, :sid, :health, :note, :next, :uid, :key
                )
                RETURNING id, organization_id, action_item_id, sprint_id,
                          health, progress_note, next_step, reported_by, reported_at
                """
            ),
            {
                "org": ctx.organization_id,
                "aid": action_item_id,
                "sid": payload.sprint_id,
                "health": payload.health,
                "note": payload.progress_note.strip(),
                "next": payload.next_step or "",
                "uid": ctx.principal.user_id,
                "key": payload.idempotency_key,
            },
        ).one()
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="action_execution.check_in.create",
            resource_type="action_execution_check_in",
            resource_id=row.id,
            metadata={"health": payload.health},
        )
        conn.commit()
    return _checkin_out(row)


def list_check_ins(ctx: OrgContext, action_item_id: UUID) -> list[CheckInOut]:
    _require_read(ctx)
    with tenant_connection(ctx.organization_id) as conn:
        _assert_action_item(conn, ctx.organization_id, action_item_id)
        rows = conn.execute(
            text(
                """
                SELECT id, organization_id, action_item_id, sprint_id,
                       health, progress_note, next_step, reported_by, reported_at
                FROM action_execution_check_ins
                WHERE action_item_id = :aid AND organization_id = :org
                ORDER BY reported_at DESC
                """
            ),
            {"aid": action_item_id, "org": ctx.organization_id},
        ).all()
    return [_checkin_out(r) for r in rows]


def _impediment_out(row) -> ImpedimentOut:
    return ImpedimentOut(
        id=row.id,
        organization_id=row.organization_id,
        action_item_id=row.action_item_id,
        sprint_id=row.sprint_id,
        title=row.title,
        description=row.description or "",
        severity=row.severity,
        status=row.status,
        owner_membership_id=row.owner_membership_id,
        opened_by=row.opened_by,
        opened_at=row.opened_at,
        resolved_by=row.resolved_by,
        resolved_at=row.resolved_at,
        resolution_note=row.resolution_note,
        updated_at=row.updated_at,
    )


def create_impediment(
    ctx: OrgContext, action_item_id: UUID, payload: ImpedimentCreate
) -> ImpedimentOut:
    _require_mutate(ctx)
    with tenant_connection(ctx.organization_id) as conn:
        _assert_action_item(conn, ctx.organization_id, action_item_id)
        if payload.sprint_id is not None:
            _assert_action_allocated_to_sprint(
                conn, ctx.organization_id, action_item_id, payload.sprint_id
            )
        row = conn.execute(
            text(
                """
                INSERT INTO action_impediments (
                  organization_id, action_item_id, sprint_id, title, description,
                  severity, owner_membership_id, opened_by
                ) VALUES (
                  :org, :aid, :sid, :title, :desc, :sev, :owner, :uid
                )
                RETURNING *
                """
            ),
            {
                "org": ctx.organization_id,
                "aid": action_item_id,
                "sid": payload.sprint_id,
                "title": payload.title.strip(),
                "desc": payload.description or "",
                "sev": payload.severity,
                "owner": payload.owner_membership_id,
                "uid": ctx.principal.user_id,
            },
        ).one()
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="action_impediment.create",
            resource_type="action_impediment",
            resource_id=row.id,
        )
        conn.commit()
    return _impediment_out(row)


def list_impediments(ctx: OrgContext, action_item_id: UUID) -> list[ImpedimentOut]:
    _require_read(ctx)
    with tenant_connection(ctx.organization_id) as conn:
        _assert_action_item(conn, ctx.organization_id, action_item_id)
        rows = conn.execute(
            text(
                """
                SELECT * FROM action_impediments
                WHERE action_item_id = :aid AND organization_id = :org
                ORDER BY opened_at DESC
                """
            ),
            {"aid": action_item_id, "org": ctx.organization_id},
        ).all()
    return [_impediment_out(r) for r in rows]


def update_impediment(
    ctx: OrgContext,
    action_item_id: UUID,
    impediment_id: UUID,
    payload: ImpedimentUpdate,
) -> ImpedimentOut:
    _require_mutate(ctx)
    with tenant_connection(ctx.organization_id) as conn:
        cur = conn.execute(
            text(
                """
                SELECT * FROM action_impediments
                WHERE id = :id AND action_item_id = :aid AND organization_id = :org
                FOR UPDATE
                """
            ),
            {"id": impediment_id, "aid": action_item_id, "org": ctx.organization_id},
        ).first()
        if cur is None:
            raise AppError("not_found", "Impediment not found", status_code=404)
        new_status = payload.status if payload.status is not None else cur.status
        resolving = new_status in ("resolved", "cancelled") and cur.status == "open"
        row = conn.execute(
            text(
                """
                UPDATE action_impediments SET
                  status = :status,
                  severity = :sev,
                  owner_membership_id = :owner,
                  resolution_note = :note,
                  resolved_by = CASE WHEN :resolving THEN :uid ELSE resolved_by END,
                  resolved_at = CASE WHEN :resolving THEN now() ELSE resolved_at END,
                  updated_at = now()
                WHERE id = :id AND organization_id = :org
                RETURNING *
                """
            ),
            {
                "id": impediment_id,
                "org": ctx.organization_id,
                "status": new_status,
                "sev": payload.severity if payload.severity is not None else cur.severity,
                "owner": (
                    payload.owner_membership_id
                    if payload.owner_membership_id is not None
                    else cur.owner_membership_id
                ),
                "note": (
                    payload.resolution_note
                    if payload.resolution_note is not None
                    else cur.resolution_note
                ),
                "resolving": resolving,
                "uid": ctx.principal.user_id,
            },
        ).one()
        action = "action_impediment.update"
        if resolving:
            action = "action_impediment.resolve"
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action=action,
            resource_type="action_impediment",
            resource_id=impediment_id,
            from_status=cur.status,
            to_status=row.status,
        )
        conn.commit()
    return _impediment_out(row)


def _dependency_out(row) -> DependencyOut:
    return DependencyOut(
        id=row.id,
        organization_id=row.organization_id,
        predecessor_action_item_id=row.predecessor_action_item_id,
        dependent_action_item_id=row.dependent_action_item_id,
        dependency_type=row.dependency_type,
        status=row.status,
        created_by=row.created_by,
        created_at=row.created_at,
        removed_by=row.removed_by,
        removed_at=row.removed_at,
        removal_reason=row.removal_reason,
    )


def _detect_blocks_cycle(
    conn: Connection,
    org_id: UUID,
    predecessor_id: UUID,
    dependent_id: UUID,
) -> bool:
    """Return True if adding predecessor→dependent blocks edge creates a cycle."""
    visited: set[UUID] = set()
    stack = [dependent_id]
    while stack:
        node = stack.pop()
        if node == predecessor_id:
            return True
        if node in visited:
            continue
        visited.add(node)
        rows = conn.execute(
            text(
                """
                SELECT dependent_action_item_id AS next_id
                FROM action_dependencies
                WHERE organization_id = :org
                  AND predecessor_action_item_id = :pred
                  AND dependency_type = 'blocks'
                  AND status = 'active'
                """
            ),
            {"org": org_id, "pred": node},
        ).all()
        stack.extend(r.next_id for r in rows)
    return False


def create_dependency(
    ctx: OrgContext, action_item_id: UUID, payload: DependencyCreate
) -> DependencyOut:
    _require_mutate(ctx)
    if payload.dependent_action_item_id != action_item_id:
        raise AppError(
            "dependency_path_mismatch",
            "URL action id must match dependent_action_item_id",
            status_code=422,
        )
    with tenant_connection(ctx.organization_id) as conn:
        for aid in (payload.predecessor_action_item_id, payload.dependent_action_item_id):
            _assert_action_item(conn, ctx.organization_id, aid)
        if payload.dependency_type == "blocks":
            if _detect_blocks_cycle(
                conn,
                ctx.organization_id,
                payload.predecessor_action_item_id,
                payload.dependent_action_item_id,
            ):
                raise AppError(
                    "dependency_cycle",
                    "blocks dependency would create a cycle",
                    status_code=409,
                )
        try:
            row = conn.execute(
                text(
                    """
                    INSERT INTO action_dependencies (
                      organization_id, predecessor_action_item_id,
                      dependent_action_item_id, dependency_type, created_by
                    ) VALUES (
                      :org, :pred, :dep, :dtype, :uid
                    )
                    RETURNING *
                    """
                ),
                {
                    "org": ctx.organization_id,
                    "pred": payload.predecessor_action_item_id,
                    "dep": payload.dependent_action_item_id,
                    "dtype": payload.dependency_type,
                    "uid": ctx.principal.user_id,
                },
            ).one()
        except Exception as exc:
            msg = str(exc).lower()
            if "uq_action_deps_active_pair_type" in msg or "unique" in msg:
                raise AppError(
                    "dependency_duplicate",
                    "Dependency already exists",
                    status_code=409,
                ) from exc
            raise
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="action_dependency.create",
            resource_type="action_dependency",
            resource_id=row.id,
        )
        conn.commit()
    return _dependency_out(row)


def list_dependencies(
    ctx: OrgContext, action_item_id: UUID, *, include_removed: bool = False
) -> list[DependencyOut]:
    _require_read(ctx)
    status_clause = "" if include_removed else "AND status = 'active'"
    with tenant_connection(ctx.organization_id) as conn:
        _assert_action_item(conn, ctx.organization_id, action_item_id)
        rows = conn.execute(
            text(
                f"""
                SELECT * FROM action_dependencies
                WHERE organization_id = :org
                  AND (
                    predecessor_action_item_id = :aid
                    OR dependent_action_item_id = :aid
                  )
                  {status_clause}
                ORDER BY created_at
                """
            ),
            {"aid": action_item_id, "org": ctx.organization_id},
        ).all()
    return [_dependency_out(r) for r in rows]


def delete_dependency(
    ctx: OrgContext,
    action_item_id: UUID,
    dependency_id: UUID,
    *,
    removal_reason: str | None = None,
) -> None:
    """Soft-delete: the edge stops counting but stays auditable as history."""
    _require_mutate(ctx)
    with tenant_connection(ctx.organization_id) as conn:
        row = conn.execute(
            text(
                """
                SELECT id, status FROM action_dependencies
                WHERE id = :id AND organization_id = :org
                  AND (
                    predecessor_action_item_id = :aid
                    OR dependent_action_item_id = :aid
                  )
                FOR UPDATE
                """
            ),
            {"id": dependency_id, "org": ctx.organization_id, "aid": action_item_id},
        ).first()
        if row is None:
            raise AppError("not_found", "Dependency not found", status_code=404)
        if row.status == "removed":
            raise AppError("not_found", "Dependency not found", status_code=404)
        conn.execute(
            text(
                """
                UPDATE action_dependencies SET
                  status = 'removed',
                  removed_by = :uid,
                  removed_at = now(),
                  removal_reason = :reason
                WHERE id = :id AND organization_id = :org AND status = 'active'
                """
            ),
            {
                "id": dependency_id,
                "org": ctx.organization_id,
                "uid": ctx.principal.user_id,
                "reason": removal_reason,
            },
        )
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="action_dependency.remove",
            resource_type="action_dependency",
            resource_id=dependency_id,
            from_status="active",
            to_status="removed",
            metadata={"removal_reason": removal_reason} if removal_reason else None,
        )
        conn.commit()
