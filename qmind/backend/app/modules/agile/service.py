"""Squads, memberships, sprints and sprint cards (ISOI-007)."""

from __future__ import annotations

from statistics import mean, median
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.audit import write_audit
from app.auth.context import OrgContext
from app.db import admin_connection, tenant_connection
from app.errors import AppError
from app.modules.agile.schemas import (
    CarryDecisionIn,
    SprintActivateIn,
    SprintCardAllocateIn,
    SprintCardOut,
    SprintCardPositionIn,
    SprintCompleteIn,
    SprintCreate,
    SprintOut,
    SprintUpdate,
    SquadCreate,
    SquadMembershipCreate,
    SquadMembershipOut,
    SquadMembershipUpdate,
    SquadOut,
    SquadUpdate,
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

_TERMINAL_ITEM_STATUSES = ("done", "cancelled", "ineffective_closed")

_SQUAD_COLS = """
    id, organization_id, name, purpose, status,
    default_sprint_length_days, created_by, created_at, updated_at
"""
_SPRINT_COLS = """
    id, organization_id, squad_id, name, goal, starts_at, ends_at, timezone,
    status, capacity_points, wip_limit_in_progress, activation_skip_cards_rationale,
    created_by, activated_by, closed_by, created_at, activated_at, closed_at, updated_at
"""
_CARD_COLS = """
    id, organization_id, sprint_id, action_item_id, priority, estimate_points,
    position, committed_at, removed_at, removal_reason, carried_from_sprint_id,
    created_by, created_at, updated_at
"""
_MEMBERSHIP_COLS = """
    id, organization_id, squad_id, membership_id, agile_role, status,
    created_by, created_at, updated_at
"""


def _require_mutate(ctx: OrgContext) -> None:
    require_role(ctx, *_MUTATE)


def _require_read(ctx: OrgContext) -> None:
    require_role(ctx, *_READ)


def _squad_out(row) -> SquadOut:
    return SquadOut(
        id=row.id,
        organization_id=row.organization_id,
        name=row.name,
        purpose=row.purpose or "",
        status=row.status,
        default_sprint_length_days=row.default_sprint_length_days,
        created_by=row.created_by,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _sprint_out(row) -> SprintOut:
    return SprintOut(
        id=row.id,
        organization_id=row.organization_id,
        squad_id=row.squad_id,
        name=row.name,
        goal=row.goal or "",
        starts_at=row.starts_at,
        ends_at=row.ends_at,
        timezone=row.timezone,
        status=row.status,
        capacity_points=row.capacity_points,
        wip_limit_in_progress=row.wip_limit_in_progress,
        activation_skip_cards_rationale=row.activation_skip_cards_rationale,
        created_by=row.created_by,
        activated_by=row.activated_by,
        closed_by=row.closed_by,
        created_at=row.created_at,
        activated_at=row.activated_at,
        closed_at=row.closed_at,
        updated_at=row.updated_at,
    )


def _card_out(row) -> SprintCardOut:
    return SprintCardOut(
        id=row.id,
        organization_id=row.organization_id,
        sprint_id=row.sprint_id,
        action_item_id=row.action_item_id,
        priority=row.priority,
        estimate_points=row.estimate_points,
        position=row.position,
        committed_at=row.committed_at,
        removed_at=row.removed_at,
        removal_reason=row.removal_reason,
        carried_from_sprint_id=row.carried_from_sprint_id,
        created_by=row.created_by,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _member_labels(org_id: UUID, membership_ids: list[UUID]) -> dict[UUID, tuple[str, str]]:
    if not membership_ids:
        return {}
    with admin_connection() as conn:
        rows = conn.execute(
            text(
                """
                SELECT m.id,
                       coalesce(nullif(u.display_name, ''), u.email) AS display_name,
                       u.email
                FROM memberships m
                JOIN users u ON u.id = m.user_id
                WHERE m.organization_id = :org AND m.id = ANY(:ids)
                """
            ),
            {"org": org_id, "ids": membership_ids},
        ).all()
    return {r.id: (r.display_name, r.email) for r in rows}


def _membership_out(row, labels: dict[UUID, tuple[str, str]]) -> SquadMembershipOut:
    label = labels.get(row.membership_id)
    return SquadMembershipOut(
        id=row.id,
        organization_id=row.organization_id,
        squad_id=row.squad_id,
        membership_id=row.membership_id,
        agile_role=row.agile_role,
        status=row.status,
        member_display_name=label[0] if label else None,
        member_email=label[1] if label else None,
        created_by=row.created_by,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _lock_squad(conn: Connection, org_id: UUID, squad_id: UUID):
    row = conn.execute(
        text(
            f"""
            SELECT {_SQUAD_COLS}
            FROM agile_squads
            WHERE id = :id AND organization_id = :org
            FOR UPDATE
            """
        ),
        {"id": squad_id, "org": org_id},
    ).first()
    if row is None:
        raise AppError("not_found", "Squad not found", status_code=404)
    return row


def _lock_sprint(conn: Connection, org_id: UUID, sprint_id: UUID):
    row = conn.execute(
        text(
            f"""
            SELECT {_SPRINT_COLS}
            FROM agile_sprints
            WHERE id = :id AND organization_id = :org
            FOR UPDATE
            """
        ),
        {"id": sprint_id, "org": org_id},
    ).first()
    if row is None:
        raise AppError("not_found", "Sprint not found", status_code=404)
    return row


def _count_active_value_owners(conn: Connection, org_id: UUID, squad_id: UUID) -> int:
    row = conn.execute(
        text(
            """
            SELECT count(*) AS n
            FROM agile_squad_memberships
            WHERE organization_id = :org
              AND squad_id = :squad
              AND agile_role = 'value_owner'
              AND status = 'active'
            """
        ),
        {"org": org_id, "squad": squad_id},
    ).one()
    return int(row.n)


def _assert_squad_has_value_owner(conn: Connection, org_id: UUID, squad_id: UUID) -> None:
    squad = conn.execute(
        text(
            "SELECT status FROM agile_squads WHERE id = :id AND organization_id = :org"
        ),
        {"id": squad_id, "org": org_id},
    ).first()
    if squad is None or squad.status != "active":
        return
    if _count_active_value_owners(conn, org_id, squad_id) < 1:
        raise AppError(
            "squad_missing_value_owner",
            "Active squad requires at least one value_owner",
            status_code=409,
        )


def _assert_membership_active(conn: Connection, org_id: UUID, membership_id: UUID) -> None:
    row = conn.execute(
        text(
            """
            SELECT status FROM memberships
            WHERE id = :id AND organization_id = :org
            """
        ),
        {"id": membership_id, "org": org_id},
    ).first()
    if row is None:
        raise AppError("not_found", "Membership not found", status_code=404)
    if row.status != "active":
        raise AppError(
            "membership_inactive",
            "Inactive membership cannot be assigned to squad",
            status_code=409,
        )


def create_squad(ctx: OrgContext, payload: SquadCreate) -> SquadOut:
    """Create an active squad and its value_owner in a single transaction.

    An active squad without a value_owner is not a valid state, so the squad row
    and the value_owner membership are committed together or not at all.
    """
    _require_mutate(ctx)
    with tenant_connection(ctx.organization_id) as conn:
        _assert_membership_active(conn, ctx.organization_id, payload.value_owner_membership_id)
        row = conn.execute(
            text(
                f"""
                INSERT INTO agile_squads (
                  organization_id, name, purpose, default_sprint_length_days,
                  status, created_by
                ) VALUES (
                  :org, :name, :purpose, :days, 'active', :uid
                )
                RETURNING {_SQUAD_COLS}
                """
            ),
            {
                "org": ctx.organization_id,
                "name": payload.name.strip(),
                "purpose": payload.purpose or "",
                "days": payload.default_sprint_length_days,
                "uid": ctx.principal.user_id,
            },
        ).one()
        owner = conn.execute(
            text(
                f"""
                INSERT INTO agile_squad_memberships (
                  organization_id, squad_id, membership_id, agile_role, status, created_by
                ) VALUES (
                  :org, :squad, :mem, 'value_owner', 'active', :uid
                )
                RETURNING {_MEMBERSHIP_COLS}
                """
            ),
            {
                "org": ctx.organization_id,
                "squad": row.id,
                "mem": payload.value_owner_membership_id,
                "uid": ctx.principal.user_id,
            },
        ).one()
        _assert_squad_has_value_owner(conn, ctx.organization_id, row.id)
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="agile.squad.create",
            resource_type="agile_squad",
            resource_id=row.id,
            metadata={"value_owner_membership_id": str(payload.value_owner_membership_id)},
        )
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="agile.squad_membership.create",
            resource_type="agile_squad_membership",
            resource_id=owner.id,
            metadata={"agile_role": "value_owner"},
        )
        conn.commit()
    return _squad_out(row)


def list_squads(ctx: OrgContext, *, status: str | None = None) -> list[SquadOut]:
    _require_read(ctx)
    with tenant_connection(ctx.organization_id) as conn:
        if status:
            rows = conn.execute(
                text(
                    f"""
                    SELECT {_SQUAD_COLS}
                    FROM agile_squads
                    WHERE organization_id = :org AND status = :status
                    ORDER BY name
                    """
                ),
                {"org": ctx.organization_id, "status": status},
            ).all()
        else:
            rows = conn.execute(
                text(
                    f"""
                    SELECT {_SQUAD_COLS}
                    FROM agile_squads
                    WHERE organization_id = :org
                    ORDER BY name
                    """
                ),
                {"org": ctx.organization_id},
            ).all()
    return [_squad_out(r) for r in rows]


def get_squad(ctx: OrgContext, squad_id: UUID) -> SquadOut:
    _require_read(ctx)
    with tenant_connection(ctx.organization_id) as conn:
        row = conn.execute(
            text(
                f"""
                SELECT {_SQUAD_COLS}
                FROM agile_squads
                WHERE id = :id AND organization_id = :org
                """
            ),
            {"id": squad_id, "org": ctx.organization_id},
        ).first()
        if row is None:
            raise AppError("not_found", "Squad not found", status_code=404)
    return _squad_out(row)


def update_squad(ctx: OrgContext, squad_id: UUID, payload: SquadUpdate) -> SquadOut:
    _require_mutate(ctx)
    with tenant_connection(ctx.organization_id) as conn:
        cur = _lock_squad(conn, ctx.organization_id, squad_id)
        new_status = payload.status if payload.status is not None else cur.status
        row = conn.execute(
            text(
                f"""
                UPDATE agile_squads SET
                  name = :name,
                  purpose = :purpose,
                  status = :status,
                  default_sprint_length_days = :days,
                  updated_at = now()
                WHERE id = :id AND organization_id = :org
                RETURNING {_SQUAD_COLS}
                """
            ),
            {
                "id": squad_id,
                "org": ctx.organization_id,
                "name": payload.name.strip() if payload.name is not None else cur.name,
                "purpose": payload.purpose if payload.purpose is not None else cur.purpose,
                "status": new_status,
                "days": (
                    payload.default_sprint_length_days
                    if payload.default_sprint_length_days is not None
                    else cur.default_sprint_length_days
                ),
            },
        ).one()
        if new_status == "active":
            _assert_squad_has_value_owner(conn, ctx.organization_id, squad_id)
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="agile.squad.update",
            resource_type="agile_squad",
            resource_id=squad_id,
            from_status=cur.status,
            to_status=row.status,
        )
        conn.commit()
    return _squad_out(row)


def add_squad_membership(
    ctx: OrgContext, squad_id: UUID, payload: SquadMembershipCreate
) -> SquadMembershipOut:
    _require_mutate(ctx)
    with tenant_connection(ctx.organization_id) as conn:
        _lock_squad(conn, ctx.organization_id, squad_id)
        _assert_membership_active(conn, ctx.organization_id, payload.membership_id)
        row = conn.execute(
            text(
                f"""
                INSERT INTO agile_squad_memberships (
                  organization_id, squad_id, membership_id, agile_role, created_by
                ) VALUES (
                  :org, :squad, :mem, :role, :uid
                )
                RETURNING {_MEMBERSHIP_COLS}
                """
            ),
            {
                "org": ctx.organization_id,
                "squad": squad_id,
                "mem": payload.membership_id,
                "role": payload.agile_role,
                "uid": ctx.principal.user_id,
            },
        ).one()
        _assert_squad_has_value_owner(conn, ctx.organization_id, squad_id)
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="agile.squad_membership.create",
            resource_type="agile_squad_membership",
            resource_id=row.id,
            metadata={"agile_role": payload.agile_role},
        )
        conn.commit()
        labels = _member_labels(ctx.organization_id, [payload.membership_id])
    return _membership_out(row, labels)


def list_squad_memberships(ctx: OrgContext, squad_id: UUID) -> list[SquadMembershipOut]:
    _require_read(ctx)
    with tenant_connection(ctx.organization_id) as conn:
        squad = conn.execute(
            text(
                "SELECT 1 FROM agile_squads WHERE id = :id AND organization_id = :org"
            ),
            {"id": squad_id, "org": ctx.organization_id},
        ).first()
        if squad is None:
            raise AppError("not_found", "Squad not found", status_code=404)
        rows = conn.execute(
            text(
                f"""
                SELECT {_MEMBERSHIP_COLS}
                FROM agile_squad_memberships
                WHERE squad_id = :squad AND organization_id = :org
                ORDER BY created_at
                """
            ),
            {"squad": squad_id, "org": ctx.organization_id},
        ).all()
        labels = _member_labels(
            ctx.organization_id, [r.membership_id for r in rows]
        )
    return [_membership_out(r, labels) for r in rows]


def update_squad_membership(
    ctx: OrgContext,
    squad_id: UUID,
    agile_membership_id: UUID,
    payload: SquadMembershipUpdate,
) -> SquadMembershipOut:
    _require_mutate(ctx)
    with tenant_connection(ctx.organization_id) as conn:
        cur = conn.execute(
            text(
                f"""
                SELECT {_MEMBERSHIP_COLS}
                FROM agile_squad_memberships
                WHERE id = :id AND squad_id = :squad AND organization_id = :org
                FOR UPDATE
                """
            ),
            {"id": agile_membership_id, "squad": squad_id, "org": ctx.organization_id},
        ).first()
        if cur is None:
            raise AppError("not_found", "Squad membership not found", status_code=404)
        row = conn.execute(
            text(
                f"""
                UPDATE agile_squad_memberships SET
                  agile_role = :role,
                  status = :status,
                  updated_at = now()
                WHERE id = :id AND organization_id = :org
                RETURNING {_MEMBERSHIP_COLS}
                """
            ),
            {
                "id": agile_membership_id,
                "org": ctx.organization_id,
                "role": payload.agile_role if payload.agile_role is not None else cur.agile_role,
                "status": payload.status if payload.status is not None else cur.status,
            },
        ).one()
        _assert_squad_has_value_owner(conn, ctx.organization_id, squad_id)
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="agile.squad_membership.update",
            resource_type="agile_squad_membership",
            resource_id=agile_membership_id,
            from_status=cur.status,
            to_status=row.status,
        )
        conn.commit()
        labels = _member_labels(ctx.organization_id, [row.membership_id])
    return _membership_out(row, labels)


def create_sprint(ctx: OrgContext, payload: SprintCreate) -> SprintOut:
    _require_mutate(ctx)
    if payload.ends_at <= payload.starts_at:
        raise AppError("invalid_dates", "ends_at must be after starts_at", status_code=422)
    with tenant_connection(ctx.organization_id) as conn:
        squad = conn.execute(
            text(
                "SELECT id FROM agile_squads WHERE id = :id AND organization_id = :org"
            ),
            {"id": payload.squad_id, "org": ctx.organization_id},
        ).first()
        if squad is None:
            raise AppError("not_found", "Squad not found", status_code=404)
        row = conn.execute(
            text(
                f"""
                INSERT INTO agile_sprints (
                  organization_id, squad_id, name, goal, starts_at, ends_at, timezone,
                  capacity_points, wip_limit_in_progress, created_by
                ) VALUES (
                  :org, :squad, :name, :goal, :starts, :ends, :tz,
                  :cap, :wip, :uid
                )
                RETURNING {_SPRINT_COLS}
                """
            ),
            {
                "org": ctx.organization_id,
                "squad": payload.squad_id,
                "name": payload.name.strip(),
                "goal": payload.goal or "",
                "starts": payload.starts_at,
                "ends": payload.ends_at,
                "tz": payload.timezone,
                "cap": payload.capacity_points,
                "wip": payload.wip_limit_in_progress,
                "uid": ctx.principal.user_id,
            },
        ).one()
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="agile.sprint.create",
            resource_type="agile_sprint",
            resource_id=row.id,
        )
        conn.commit()
    return _sprint_out(row)


def list_sprints(
    ctx: OrgContext, *, squad_id: UUID | None = None, status: str | None = None
) -> list[SprintOut]:
    _require_read(ctx)
    clauses = ["organization_id = :org"]
    params: dict = {"org": ctx.organization_id}
    if squad_id:
        clauses.append("squad_id = :squad")
        params["squad"] = squad_id
    if status:
        clauses.append("status = :status")
        params["status"] = status
    where = " AND ".join(clauses)
    with tenant_connection(ctx.organization_id) as conn:
        rows = conn.execute(
            text(
                f"""
                SELECT {_SPRINT_COLS}
                FROM agile_sprints
                WHERE {where}
                ORDER BY starts_at DESC
                """
            ),
            params,
        ).all()
    return [_sprint_out(r) for r in rows]


def get_sprint(ctx: OrgContext, sprint_id: UUID) -> SprintOut:
    _require_read(ctx)
    with tenant_connection(ctx.organization_id) as conn:
        row = conn.execute(
            text(
                f"""
                SELECT {_SPRINT_COLS}
                FROM agile_sprints
                WHERE id = :id AND organization_id = :org
                """
            ),
            {"id": sprint_id, "org": ctx.organization_id},
        ).first()
        if row is None:
            raise AppError("not_found", "Sprint not found", status_code=404)
    return _sprint_out(row)


def update_sprint(
    ctx: OrgContext, sprint_id: UUID, payload: SprintUpdate
) -> SprintOut:
    _require_mutate(ctx)
    with tenant_connection(ctx.organization_id) as conn:
        cur = _lock_sprint(conn, ctx.organization_id, sprint_id)
        if cur.status not in ("planned", "active"):
            raise AppError(
                "sprint_not_editable",
                f"Cannot edit sprint in status {cur.status}",
                status_code=409,
            )
        starts = payload.starts_at if payload.starts_at is not None else cur.starts_at
        ends = payload.ends_at if payload.ends_at is not None else cur.ends_at
        if ends <= starts:
            raise AppError("invalid_dates", "ends_at must be after starts_at", status_code=422)
        new_status = payload.status if payload.status is not None else cur.status
        if new_status == "active" and cur.status != "active":
            raise AppError(
                "use_activate_endpoint",
                "Use POST .../activate to activate sprint",
                status_code=409,
            )
        row = conn.execute(
            text(
                f"""
                UPDATE agile_sprints SET
                  name = :name,
                  goal = :goal,
                  starts_at = :starts,
                  ends_at = :ends,
                  timezone = :tz,
                  capacity_points = :cap,
                  wip_limit_in_progress = :wip,
                  status = :status,
                  updated_at = now()
                WHERE id = :id AND organization_id = :org
                RETURNING {_SPRINT_COLS}
                """
            ),
            {
                "id": sprint_id,
                "org": ctx.organization_id,
                "name": payload.name.strip() if payload.name is not None else cur.name,
                "goal": payload.goal if payload.goal is not None else cur.goal,
                "starts": starts,
                "ends": ends,
                "tz": payload.timezone if payload.timezone is not None else cur.timezone,
                "cap": (
                    payload.capacity_points
                    if payload.capacity_points is not None
                    else cur.capacity_points
                ),
                "wip": (
                    payload.wip_limit_in_progress
                    if payload.wip_limit_in_progress is not None
                    else cur.wip_limit_in_progress
                ),
                "status": new_status,
            },
        ).one()
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="agile.sprint.update",
            resource_type="agile_sprint",
            resource_id=sprint_id,
        )
        conn.commit()
    return _sprint_out(row)


def activate_sprint(
    ctx: OrgContext, sprint_id: UUID, payload: SprintActivateIn | None = None
) -> SprintOut:
    _require_mutate(ctx)
    payload = payload or SprintActivateIn()
    with tenant_connection(ctx.organization_id) as conn:
        cur = _lock_sprint(conn, ctx.organization_id, sprint_id)
        if cur.status != "planned":
            raise AppError(
                "invalid_transition",
                f"activate requires planned (current={cur.status})",
                status_code=409,
            )
        if not (cur.goal or "").strip():
            raise AppError(
                "sprint_goal_required",
                "Sprint goal is required for activation",
                status_code=422,
            )
        if cur.ends_at <= cur.starts_at:
            raise AppError("invalid_dates", "Invalid sprint period", status_code=422)
        card_count = conn.execute(
            text(
                """
                SELECT count(*) AS n
                FROM agile_sprint_cards
                WHERE sprint_id = :sid AND organization_id = :org AND removed_at IS NULL
                """
            ),
            {"sid": sprint_id, "org": ctx.organization_id},
        ).one().n
        rationale = payload.activation_skip_cards_rationale
        if card_count < 1:
            if not (rationale or "").strip():
                raise AppError(
                    "sprint_cards_required",
                    "Activation requires at least one card or activation_skip_cards_rationale",
                    status_code=422,
                )
        else:
            rationale = None
        other_active = conn.execute(
            text(
                """
                SELECT id FROM agile_sprints
                WHERE squad_id = :squad AND organization_id = :org
                  AND status = 'active' AND id <> :id
                """
            ),
            {"squad": cur.squad_id, "org": ctx.organization_id, "id": sprint_id},
        ).first()
        if other_active:
            raise AppError(
                "sprint_already_active",
                "Squad already has an active sprint",
                status_code=409,
            )
        row = conn.execute(
            text(
                f"""
                UPDATE agile_sprints SET
                  status = 'active',
                  activated_by = :uid,
                  activated_at = now(),
                  activation_skip_cards_rationale = :rat,
                  updated_at = now()
                WHERE id = :id AND organization_id = :org AND status = 'planned'
                RETURNING {_SPRINT_COLS}
                """
            ),
            {
                "id": sprint_id,
                "org": ctx.organization_id,
                "uid": ctx.principal.user_id,
                "rat": rationale,
            },
        ).first()
        if row is None:
            raise AppError("conflict", "Concurrent sprint status change", status_code=409)
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="agile.sprint.activate",
            resource_type="agile_sprint",
            resource_id=sprint_id,
            from_status="planned",
            to_status="active",
        )
        conn.commit()
    return _sprint_out(row)


def _apply_carry_decision(
    conn: Connection,
    ctx: OrgContext,
    sprint_id: UUID,
    decision: CarryDecisionIn,
) -> None:
    card = conn.execute(
        text(
            f"""
            SELECT {_CARD_COLS}
            FROM agile_sprint_cards
            WHERE sprint_id = :sid AND action_item_id = :aid
              AND organization_id = :org AND removed_at IS NULL
            FOR UPDATE
            """
        ),
        {"sid": sprint_id, "aid": decision.action_item_id, "org": ctx.organization_id},
    ).first()
    if card is None:
        raise AppError(
            "carry_card_not_found",
            f"Active card for action {decision.action_item_id} not in sprint",
            status_code=422,
        )
    if decision.decision == "backlog":
        conn.execute(
            text(
                """
                UPDATE agile_sprint_cards SET
                  removed_at = now(),
                  removal_reason = 'carry_to_backlog',
                  updated_at = now()
                WHERE id = :id AND organization_id = :org
                """
            ),
            {"id": card.id, "org": ctx.organization_id},
        )
        return
    try:
        target_sprint_id = UUID(decision.decision)
    except ValueError as exc:
        raise AppError(
            "invalid_carry_decision",
            "decision must be backlog or a sprint UUID",
            status_code=422,
        ) from exc
    target = conn.execute(
        text(
            """
            SELECT id, status FROM agile_sprints
            WHERE id = :id AND organization_id = :org
            """
        ),
        {"id": target_sprint_id, "org": ctx.organization_id},
    ).first()
    if target is None:
        raise AppError("not_found", "Target sprint not found", status_code=404)
    if target.status != "planned":
        raise AppError(
            "invalid_carry_target",
            "Carry-over target sprint must be planned",
            status_code=409,
        )
    conn.execute(
        text(
            """
            UPDATE agile_sprint_cards SET
              removed_at = now(),
              removal_reason = 'carry_over',
              updated_at = now()
            WHERE id = :id AND organization_id = :org
            """
        ),
        {"id": card.id, "org": ctx.organization_id},
    )
    existing = conn.execute(
        text(
            """
            SELECT id FROM agile_sprint_cards
            WHERE action_item_id = :aid AND organization_id = :org
              AND removed_at IS NULL
            """
        ),
        {"aid": decision.action_item_id, "org": ctx.organization_id},
    ).first()
    if existing:
        raise AppError(
            "card_already_allocated",
            "ActionItem already allocated to another sprint",
            status_code=409,
        )
    max_pos = conn.execute(
        text(
            """
            SELECT coalesce(max(position), -1) AS mp
            FROM agile_sprint_cards
            WHERE sprint_id = :sid AND organization_id = :org AND removed_at IS NULL
            """
        ),
        {"sid": target_sprint_id, "org": ctx.organization_id},
    ).one().mp
    conn.execute(
        text(
            """
            INSERT INTO agile_sprint_cards (
              organization_id, sprint_id, action_item_id, priority, estimate_points,
              position, carried_from_sprint_id, created_by
            ) VALUES (
              :org, :sid, :aid, :pri, :est, :pos, :from_sid, :uid
            )
            """
        ),
        {
            "org": ctx.organization_id,
            "sid": target_sprint_id,
            "aid": decision.action_item_id,
            "pri": card.priority,
            "est": card.estimate_points,
            "pos": int(max_pos) + 1,
            "from_sid": sprint_id,
            "uid": ctx.principal.user_id,
        },
    )


def complete_sprint(
    ctx: OrgContext, sprint_id: UUID, payload: SprintCompleteIn
) -> SprintOut:
    _require_mutate(ctx)
    with tenant_connection(ctx.organization_id) as conn:
        cur = _lock_sprint(conn, ctx.organization_id, sprint_id)
        if cur.status != "active":
            raise AppError(
                "invalid_transition",
                f"complete requires active (current={cur.status})",
                status_code=409,
            )
        incomplete = conn.execute(
            text(
                """
                SELECT sc.action_item_id, ai.status
                FROM agile_sprint_cards sc
                JOIN action_items ai ON ai.id = sc.action_item_id
                  AND ai.organization_id = sc.organization_id
                WHERE sc.sprint_id = :sid AND sc.organization_id = :org
                  AND sc.removed_at IS NULL
                  AND ai.status NOT IN ('done', 'cancelled', 'ineffective_closed')
                """
            ),
            {"sid": sprint_id, "org": ctx.organization_id},
        ).all()
        decisions_by_item = {d.action_item_id: d for d in payload.carry_decisions}
        missing = [
            str(r.action_item_id)
            for r in incomplete
            if r.action_item_id not in decisions_by_item
        ]
        if missing:
            raise AppError(
                "carry_decisions_required",
                f"Incomplete cards require carry_decisions: {', '.join(missing)}",
                status_code=422,
            )
        for decision in payload.carry_decisions:
            _apply_carry_decision(conn, ctx, sprint_id, decision)
        row = conn.execute(
            text(
                f"""
                UPDATE agile_sprints SET
                  status = 'completed',
                  closed_by = :uid,
                  closed_at = now(),
                  updated_at = now()
                WHERE id = :id AND organization_id = :org AND status = 'active'
                RETURNING {_SPRINT_COLS}
                """
            ),
            {"id": sprint_id, "org": ctx.organization_id, "uid": ctx.principal.user_id},
        ).first()
        if row is None:
            raise AppError("conflict", "Concurrent sprint status change", status_code=409)
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="agile.sprint.complete",
            resource_type="agile_sprint",
            resource_id=sprint_id,
            from_status="active",
            to_status="completed",
            metadata={"carry_count": len(payload.carry_decisions)},
        )
        conn.commit()
    return _sprint_out(row)


def allocate_card(
    ctx: OrgContext, sprint_id: UUID, payload: SprintCardAllocateIn
) -> SprintCardOut:
    _require_mutate(ctx)
    with tenant_connection(ctx.organization_id) as conn:
        sprint = conn.execute(
            text(
                "SELECT id, status FROM agile_sprints WHERE id = :id AND organization_id = :org"
            ),
            {"id": sprint_id, "org": ctx.organization_id},
        ).first()
        if sprint is None:
            raise AppError("not_found", "Sprint not found", status_code=404)
        if sprint.status not in ("planned", "active"):
            raise AppError(
                "sprint_not_allocatable",
                "Cards can only be allocated to planned or active sprints",
                status_code=409,
            )
        item = conn.execute(
            text(
                """
                SELECT id, status FROM action_items
                WHERE id = :id AND organization_id = :org
                """
            ),
            {"id": payload.action_item_id, "org": ctx.organization_id},
        ).first()
        if item is None:
            raise AppError("not_found", "ActionItem not found", status_code=404)
        if item.status in _TERMINAL_ITEM_STATUSES:
            raise AppError(
                "terminal_action_item",
                "Cannot allocate terminal ActionItem to sprint",
                status_code=409,
            )
        existing = conn.execute(
            text(
                """
                SELECT id, sprint_id FROM agile_sprint_cards
                WHERE action_item_id = :aid AND organization_id = :org
                  AND removed_at IS NULL
                """
            ),
            {"aid": payload.action_item_id, "org": ctx.organization_id},
        ).first()
        if existing:
            raise AppError(
                "card_already_allocated",
                "ActionItem already allocated to a sprint",
                status_code=409,
            )
        if payload.position is not None:
            position = payload.position
        else:
            max_pos = conn.execute(
                text(
                    """
                    SELECT coalesce(max(position), -1) AS mp
                    FROM agile_sprint_cards
                    WHERE sprint_id = :sid AND organization_id = :org AND removed_at IS NULL
                    """
                ),
                {"sid": sprint_id, "org": ctx.organization_id},
            ).one().mp
            position = int(max_pos) + 1
        row = conn.execute(
            text(
                f"""
                INSERT INTO agile_sprint_cards (
                  organization_id, sprint_id, action_item_id, priority, estimate_points,
                  position, created_by
                ) VALUES (
                  :org, :sid, :aid, :pri, :est, :pos, :uid
                )
                RETURNING {_CARD_COLS}
                """
            ),
            {
                "org": ctx.organization_id,
                "sid": sprint_id,
                "aid": payload.action_item_id,
                "pri": payload.priority,
                "est": payload.estimate_points,
                "pos": position,
                "uid": ctx.principal.user_id,
            },
        ).one()
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="agile.sprint_card.allocate",
            resource_type="agile_sprint_card",
            resource_id=row.id,
            metadata={"action_item_id": str(payload.action_item_id)},
        )
        conn.commit()
    return _card_out(row)


def remove_card(
    ctx: OrgContext,
    sprint_id: UUID,
    action_item_id: UUID,
    *,
    removal_reason: str = "",
) -> None:
    _require_mutate(ctx)
    with tenant_connection(ctx.organization_id) as conn:
        card = conn.execute(
            text(
                f"""
                SELECT {_CARD_COLS}
                FROM agile_sprint_cards
                WHERE sprint_id = :sid AND action_item_id = :aid
                  AND organization_id = :org AND removed_at IS NULL
                FOR UPDATE
                """
            ),
            {"sid": sprint_id, "aid": action_item_id, "org": ctx.organization_id},
        ).first()
        if card is None:
            raise AppError("not_found", "Sprint card not found", status_code=404)
        conn.execute(
            text(
                """
                UPDATE agile_sprint_cards SET
                  removed_at = now(),
                  removal_reason = :reason,
                  updated_at = now()
                WHERE id = :id AND organization_id = :org
                """
            ),
            {"id": card.id, "org": ctx.organization_id, "reason": removal_reason or ""},
        )
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="agile.sprint_card.remove",
            resource_type="agile_sprint_card",
            resource_id=card.id,
        )
        conn.commit()


def update_card_position(
    ctx: OrgContext,
    sprint_id: UUID,
    action_item_id: UUID,
    payload: SprintCardPositionIn,
) -> SprintCardOut:
    _require_mutate(ctx)
    with tenant_connection(ctx.organization_id) as conn:
        row = conn.execute(
            text(
                f"""
                UPDATE agile_sprint_cards SET
                  position = :pos,
                  updated_at = now()
                WHERE sprint_id = :sid AND action_item_id = :aid
                  AND organization_id = :org AND removed_at IS NULL
                RETURNING {_CARD_COLS}
                """
            ),
            {
                "sid": sprint_id,
                "aid": action_item_id,
                "org": ctx.organization_id,
                "pos": payload.position,
            },
        ).first()
        if row is None:
            raise AppError("not_found", "Sprint card not found", status_code=404)
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="agile.sprint_card.reposition",
            resource_type="agile_sprint_card",
            resource_id=row.id,
            metadata={"position": payload.position},
        )
        conn.commit()
    return _card_out(row)


def get_sprint_metrics(ctx: OrgContext, sprint_id: UUID):
    """Sprint health metrics for the current sprint cards.

    Cycle time is measured from the audit trail (`action_item.start` →
    first transition into `done`), which is the only tamper-evident record of
    when work actually moved. When an item predates the audit trail — or was
    carried in already started — the card `committed_at` and the item
    `updated_at` are used as documented fallbacks so a sprint never reports an
    empty cycle time purely because of missing history.

    Every duration is `None` when the sprint has no sample for it; a zero would
    read as "instantaneous" instead of "nothing measured yet".
    """
    from app.modules.agile.schemas import CHECK_IN_STALE_WINDOW_HOURS, SprintMetricsOut

    _require_read(ctx)
    with tenant_connection(ctx.organization_id) as conn:
        sprint = conn.execute(
            text(
                f"""
                SELECT {_SPRINT_COLS}
                FROM agile_sprints
                WHERE id = :id AND organization_id = :org
                """
            ),
            {"id": sprint_id, "org": ctx.organization_id},
        ).first()
        if sprint is None:
            raise AppError("not_found", "Sprint not found", status_code=404)
        stats = conn.execute(
            text(
                """
                SELECT
                  count(*) FILTER (WHERE sc.removed_at IS NULL) AS planned,
                  count(*) FILTER (
                    WHERE sc.removed_at IS NULL AND ai.status = 'done'
                  ) AS completed,
                  count(*) FILTER (
                    WHERE sc.carried_from_sprint_id IS NOT NULL AND sc.removed_at IS NULL
                  ) AS carry_over,
                  count(*) FILTER (
                    WHERE sc.removed_at IS NULL AND ai.status = 'in_progress'
                  ) AS in_progress,
                  count(*) FILTER (
                    WHERE sc.removed_at IS NULL AND ai.is_overdue = true
                  ) AS overdue
                FROM agile_sprint_cards sc
                JOIN action_items ai ON ai.id = sc.action_item_id
                  AND ai.organization_id = sc.organization_id
                WHERE sc.sprint_id = :sid AND sc.organization_id = :org
                """
            ),
            {"sid": sprint_id, "org": ctx.organization_id},
        ).one()
        open_imp = conn.execute(
            text(
                """
                SELECT count(*) AS n
                FROM action_impediments imp
                JOIN agile_sprint_cards sc ON sc.action_item_id = imp.action_item_id
                  AND sc.organization_id = imp.organization_id
                WHERE sc.sprint_id = :sid AND sc.organization_id = :org
                  AND sc.removed_at IS NULL AND imp.status = 'open'
                """
            ),
            {"sid": sprint_id, "org": ctx.organization_id},
        ).one().n
        timings = conn.execute(
            text(
                """
                WITH cards AS (
                  SELECT sc.action_item_id, sc.committed_at,
                         ai.status, ai.updated_at
                  FROM agile_sprint_cards sc
                  JOIN action_items ai ON ai.id = sc.action_item_id
                    AND ai.organization_id = sc.organization_id
                  WHERE sc.sprint_id = :sid AND sc.organization_id = :org
                    AND sc.removed_at IS NULL
                ),
                marks AS (
                  SELECT
                    c.*,
                    (
                      SELECT min(e.created_at) FROM platform_audit_events e
                      WHERE e.organization_id = :org
                        AND e.resource_type = 'action_item'
                        AND e.resource_id = c.action_item_id
                        AND e.action = 'action_item.start'
                    ) AS started_at,
                    (
                      SELECT min(e.created_at) FROM platform_audit_events e
                      WHERE e.organization_id = :org
                        AND e.resource_type = 'action_item'
                        AND e.resource_id = c.action_item_id
                        AND e.to_status = 'done'
                    ) AS done_at
                  FROM cards c
                )
                SELECT
                  CASE WHEN status = 'done' THEN
                    extract(epoch FROM (
                      coalesce(done_at, updated_at)
                      - coalesce(started_at, committed_at)
                    )) / 3600.0
                  END AS cycle_hours,
                  CASE WHEN status = 'in_progress' THEN
                    extract(epoch FROM (
                      now() - coalesce(started_at, committed_at)
                    )) / 3600.0
                  END AS in_progress_hours
                FROM marks
                """
            ),
            {"sid": sprint_id, "org": ctx.organization_id},
        ).all()
        blocked = conn.execute(
            text(
                """
                SELECT sum(
                  extract(epoch FROM (coalesce(imp.resolved_at, now()) - imp.opened_at))
                ) / 3600.0 AS hours
                FROM action_impediments imp
                JOIN agile_sprint_cards sc ON sc.action_item_id = imp.action_item_id
                  AND sc.organization_id = imp.organization_id
                WHERE sc.sprint_id = :sid AND sc.organization_id = :org
                  AND sc.removed_at IS NULL
                  AND imp.status IN ('open', 'resolved')
                """
            ),
            {"sid": sprint_id, "org": ctx.organization_id},
        ).one().hours
        stale_check_ins = conn.execute(
            text(
                """
                SELECT count(*) AS n
                FROM agile_sprint_cards sc
                WHERE sc.sprint_id = :sid AND sc.organization_id = :org
                  AND sc.removed_at IS NULL
                  AND NOT EXISTS (
                    SELECT 1 FROM action_execution_check_ins c
                    WHERE c.action_item_id = sc.action_item_id
                      AND c.organization_id = sc.organization_id
                      AND c.reported_at >= now() - make_interval(hours => :win)
                  )
                """
            ),
            {
                "sid": sprint_id,
                "org": ctx.organization_id,
                "win": CHECK_IN_STALE_WINDOW_HOURS,
            },
        ).one().n
        review = conn.execute(
            text(
                """
                SELECT summary FROM agile_ceremony_records
                WHERE sprint_id = :sid AND organization_id = :org
                  AND ceremony_type = 'sprint_review'
                ORDER BY recorded_at DESC, revision DESC
                LIMIT 1
                """
            ),
            {"sid": sprint_id, "org": ctx.organization_id},
        ).first()

    cycle_hours = sorted(
        float(r.cycle_hours) for r in timings if r.cycle_hours is not None
    )
    in_progress_hours = [
        float(r.in_progress_hours) for r in timings if r.in_progress_hours is not None
    ]
    review_outcome = (review.summary or "").strip() if review else ""

    return SprintMetricsOut(
        sprint_id=sprint_id,
        squad_id=sprint.squad_id,
        planned_cards=int(stats.planned or 0),
        completed_cards=int(stats.completed or 0),
        carry_over_cards=int(stats.carry_over or 0),
        in_progress_count=int(stats.in_progress or 0),
        open_impediments=int(open_imp or 0),
        overdue_actions=int(stats.overdue or 0),
        throughput=int(stats.completed or 0),
        goal=sprint.goal or "",
        status=sprint.status,
        average_cycle_time_hours=(
            round(mean(cycle_hours), 3) if cycle_hours else None
        ),
        median_cycle_time_hours=(
            round(median(cycle_hours), 3) if cycle_hours else None
        ),
        oldest_in_progress_age_hours=(
            round(max(in_progress_hours), 3) if in_progress_hours else None
        ),
        blocked_time_hours=(round(float(blocked), 3) if blocked is not None else None),
        cards_without_recent_check_in=int(stale_check_ins or 0),
        check_in_stale_window_hours=CHECK_IN_STALE_WINDOW_HOURS,
        review_outcome=review_outcome or None,
    )
