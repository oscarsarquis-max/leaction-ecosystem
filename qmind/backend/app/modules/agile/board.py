"""Org-scoped execution board read model and domain moves (ISOI-007)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import text

from app.auth.context import OrgContext
from app.db import admin_connection, tenant_connection
from app.errors import AppError
from app.modules.actions import service as actions_service
from app.modules.actions.schemas import ReasonIn
from app.modules.agile import service as agile_service
from app.modules.agile.schemas import (
    BoardCardOut,
    BoardColumnOut,
    BoardColumnKey,
    BoardMoveIn,
    BoardMoveOut,
    BoardOut,
    SprintCardAllocateIn,
)
from app.modules.measurements import service as measurements_service
from app.modules.orgs.service import require_role
from app.schemas.enums import MeasurementPosture, TargetPosture

_READ = (
    "org_admin",
    "quality_manager",
    "process_owner",
    "action_owner",
    "consultant_auditor",
    "reader",
)
_MUTATE = _READ[:-1]

_COLUMN_LABELS: dict[BoardColumnKey, str] = {
    "backlog": "Backlog",
    "selected": "Selecionado para a sprint",
    "in_progress": "Em execução",
    "implemented": "Aguardando validação",
    "validated": "Aguardando eficácia",
    "ineffective": "Requer revisão",
    "done": "Concluído",
}

_FORWARD_COLUMNS = frozenset(
    {"selected", "in_progress", "implemented", "validated", "done"}
)


def _require_read(ctx: OrgContext) -> None:
    require_role(ctx, *_READ)


def _require_mutate(ctx: OrgContext) -> None:
    require_role(ctx, *_MUTATE)


def _owner_labels(org_id: UUID, membership_ids: list[UUID]) -> dict[UUID, tuple[str, str]]:
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


def _resolve_active_sprint(
    conn, org_id: UUID, squad_id: UUID | None, sprint_id: UUID | None
) -> tuple[UUID | None, int | None, str | None]:
    if sprint_id:
        row = conn.execute(
            text(
                """
                SELECT id, wip_limit_in_progress, status
                FROM agile_sprints
                WHERE id = :id AND organization_id = :org
                """
            ),
            {"id": sprint_id, "org": org_id},
        ).first()
        if row is None:
            raise AppError("not_found", "Sprint not found", status_code=404)
        return row.id, row.wip_limit_in_progress, row.status
    if squad_id:
        row = conn.execute(
            text(
                """
                SELECT id, wip_limit_in_progress, status
                FROM agile_sprints
                WHERE squad_id = :squad AND organization_id = :org AND status = 'active'
                LIMIT 1
                """
            ),
            {"squad": squad_id, "org": org_id},
        ).first()
        if row:
            return row.id, row.wip_limit_in_progress, row.status
    return None, None, None


def _current_case_fingerprints(
    ctx: OrgContext, case_ids: set[UUID]
) -> dict[UUID, str | None]:
    """Current problem-context fingerprint per improvement case.

    Reuses the same fingerprint the analysis-run list uses for `is_stale`, so a
    board badge and the case screen never disagree. Cases whose fingerprint
    cannot be rebuilt yield None (staleness unknown, never a false alarm).
    """
    if not case_ids:
        return {}
    from app.modules.improvement_cases import analysis_service

    out: dict[UUID, str | None] = {}
    for case_id in case_ids:
        try:
            out[case_id] = analysis_service.current_context_fingerprint(ctx, case_id)
        except Exception:
            out[case_id] = None
    return out


def _source_analysis_is_stale(row, fingerprints: dict[UUID, str | None]) -> bool | None:
    if not row.source_analysis_run_id:
        return None
    current = fingerprints.get(row.source_run_case_id)
    if current is None or row.source_run_fingerprint is None:
        return None
    return row.source_run_fingerprint != current


def _column_for_item(
    status: str,
    *,
    in_active_sprint: bool,
) -> BoardColumnKey | None:
    if status == "open":
        return "selected" if in_active_sprint else "backlog"
    mapping: dict[str, BoardColumnKey] = {
        "in_progress": "in_progress",
        "implemented": "implemented",
        "validated": "validated",
        "ineffective": "ineffective",
        "done": "done",
    }
    return mapping.get(status)


def get_board(
    ctx: OrgContext,
    *,
    squad_id: UUID | None = None,
    sprint_id: UUID | None = None,
) -> BoardOut:
    _require_read(ctx)
    org_id = ctx.organization_id
    with tenant_connection(org_id) as conn:
        active_sprint_id, wip_limit, sprint_status = _resolve_active_sprint(
            conn, org_id, squad_id, sprint_id
        )
        filter_squad = squad_id
        if filter_squad is None and active_sprint_id:
            sq = conn.execute(
                text("SELECT squad_id FROM agile_sprints WHERE id = :id"),
                {"id": active_sprint_id},
            ).first()
            filter_squad = sq.squad_id if sq else None

        squad_clause = ""
        params: dict = {"org": org_id}
        if filter_squad:
            squad_clause = "AND (sp.squad_id = :squad OR sp.id IS NULL)"
            params["squad"] = filter_squad

        rows = conn.execute(
            text(
                f"""
                SELECT
                  ai.id AS action_item_id,
                  ai.action_plan_id,
                  ai.description,
                  ai.action_kind,
                  ai.status,
                  ai.owner_membership_id,
                  ai.due_at,
                  ai.is_overdue,
                  ai.finding_id,
                  ai.source_analysis_run_id,
                  ai.source_finding_code,
                  run.input_fingerprint AS source_run_fingerprint,
                  run.improvement_case_id AS source_run_case_id,
                  ap.assessment_id,
                  ap.improvement_case_id,
                  sc.id AS card_id,
                  sc.priority,
                  sc.estimate_points,
                  sc.position,
                  sc.sprint_id,
                  sp.name AS sprint_name,
                  sp.status AS sprint_status,
                  sq.id AS squad_id,
                  sq.name AS squad_name,
                  (
                    SELECT count(*) FROM action_impediments imp
                    WHERE imp.action_item_id = ai.id
                      AND imp.organization_id = ai.organization_id
                      AND imp.status = 'open'
                  ) AS open_impediment_count,
                  (
                    SELECT count(*) FROM action_dependencies dep
                    JOIN action_items pred ON pred.id = dep.predecessor_action_item_id
                      AND pred.organization_id = dep.organization_id
                    WHERE dep.dependent_action_item_id = ai.id
                      AND dep.organization_id = ai.organization_id
                      AND dep.dependency_type = 'blocks'
                      AND dep.status = 'active'
                      AND pred.status NOT IN ('done', 'cancelled', 'ineffective_closed')
                  ) AS blocking_dependency_count,
                  ci.reported_at AS latest_check_in_at,
                  ci.health AS latest_check_in_health,
                  coalesce(ev.total, 0) AS evidence_count_total,
                  coalesce(ev.approved, 0) AS evidence_count_approved,
                  CASE
                    WHEN sc.removed_at IS NULL
                      AND sp.status = 'active'
                      AND sc.sprint_id = :active_sprint
                    THEN true
                    ELSE false
                  END AS in_active_sprint
                FROM action_items ai
                JOIN action_plans ap ON ap.id = ai.action_plan_id
                  AND ap.organization_id = ai.organization_id
                LEFT JOIN agile_sprint_cards sc ON sc.action_item_id = ai.id
                  AND sc.organization_id = ai.organization_id
                  AND sc.removed_at IS NULL
                LEFT JOIN agile_sprints sp ON sp.id = sc.sprint_id
                  AND sp.organization_id = sc.organization_id
                LEFT JOIN agile_squads sq ON sq.id = sp.squad_id
                  AND sq.organization_id = sp.organization_id
                LEFT JOIN improvement_case_analysis_runs run
                  ON run.id = ai.source_analysis_run_id
                  AND run.organization_id = ai.organization_id
                LEFT JOIN LATERAL (
                  SELECT c.reported_at, c.health
                  FROM action_execution_check_ins c
                  WHERE c.action_item_id = ai.id
                    AND c.organization_id = ai.organization_id
                  ORDER BY c.reported_at DESC
                  LIMIT 1
                ) ci ON true
                LEFT JOIN LATERAL (
                  SELECT count(*) AS total,
                         count(*) FILTER (WHERE e.status = 'approved') AS approved
                  FROM evidence_links el
                  JOIN evidences e ON e.id = el.evidence_id
                    AND e.organization_id = el.organization_id
                  WHERE el.organization_id = ai.organization_id
                    AND el.target_type = 'action_item'
                    AND el.target_id = ai.id
                    AND el.removed_at IS NULL
                ) ev ON true
                WHERE ai.organization_id = :org
                  AND ai.status NOT IN ('cancelled', 'ineffective_closed')
                  {squad_clause}
                ORDER BY sc.position NULLS LAST, ai.created_at
                """
            ),
            {**params, "active_sprint": active_sprint_id},
        ).all()

        postures = measurements_service.postures_by_action_plan(
            conn, org_id, list({r.action_plan_id for r in rows})
        )

    owner_ids = list({r.owner_membership_id for r in rows})
    labels = _owner_labels(org_id, owner_ids)
    current_fingerprints = _current_case_fingerprints(
        ctx, {r.source_run_case_id for r in rows if r.source_run_case_id}
    )

    columns: dict[BoardColumnKey, list[BoardCardOut]] = {
        k: [] for k in _COLUMN_LABELS
    }
    in_progress_count = 0

    for r in rows:
        in_active = bool(r.in_active_sprint)
        col = _column_for_item(r.status, in_active_sprint=in_active)
        if col is None:
            continue
        if active_sprint_id and col == "backlog" and in_active:
            continue
        if active_sprint_id and col == "selected" and not in_active:
            continue
        if sprint_id and r.sprint_id and r.sprint_id != sprint_id and col in (
            "backlog",
            "selected",
        ):
            if r.status == "open":
                continue
        label = labels.get(r.owner_membership_id, ("", ""))
        open_impediments = int(r.open_impediment_count or 0)
        blocking_deps = int(r.blocking_dependency_count or 0)
        measurement_posture, target_posture, indicator_count = postures.get(
            r.action_plan_id,
            (
                MeasurementPosture.not_planned.value,
                TargetPosture.unknown.value,
                0,
            ),
        )
        card = BoardCardOut(
            action_item_id=r.action_item_id,
            action_plan_id=r.action_plan_id,
            description=r.description,
            action_kind=r.action_kind,
            status=r.status,
            owner_membership_id=r.owner_membership_id,
            owner_display_name=label[0] or label[1] or "Responsável",
            owner_email=label[1] or "",
            due_at=r.due_at,
            is_overdue=bool(r.is_overdue),
            priority=r.priority,
            estimate_points=r.estimate_points,
            sprint_id=r.sprint_id,
            sprint_name=r.sprint_name,
            squad_id=r.squad_id,
            squad_name=r.squad_name,
            has_open_impediment=open_impediments > 0,
            has_blocking_dependency=blocking_deps > 0,
            open_impediment_count=open_impediments,
            blocking_dependency_count=blocking_deps,
            latest_check_in_at=r.latest_check_in_at,
            latest_check_in_health=r.latest_check_in_health,
            source_analysis_run_id=r.source_analysis_run_id,
            source_finding_code=r.source_finding_code,
            source_analysis_is_stale=_source_analysis_is_stale(r, current_fingerprints),
            assessment_id=r.assessment_id,
            improvement_case_id=r.improvement_case_id,
            finding_id=r.finding_id,
            card_id=r.card_id,
            position=r.position,
            evidence_count_total=int(r.evidence_count_total or 0),
            evidence_count_approved=int(r.evidence_count_approved or 0),
            indicator_count=indicator_count,
            measurement_posture=measurement_posture,
            target_posture=target_posture,
        )
        columns[col].append(card)
        if col == "in_progress":
            in_progress_count += 1

    wip_signal = bool(
        wip_limit is not None and in_progress_count > int(wip_limit)
    )

    return BoardOut(
        squad_id=filter_squad,
        sprint_id=sprint_id or active_sprint_id,
        active_sprint_id=active_sprint_id,
        wip_limit_in_progress=wip_limit,
        wip_signal=wip_signal,
        in_progress_count=in_progress_count,
        columns=[
            BoardColumnOut(key=k, label=_COLUMN_LABELS[k], cards=columns[k])
            for k in _COLUMN_LABELS
        ],
    )


def _has_open_impediment(ctx: OrgContext, action_item_id: UUID) -> bool:
    with tenant_connection(ctx.organization_id) as conn:
        row = conn.execute(
            text(
                """
                SELECT 1 FROM action_impediments
                WHERE action_item_id = :aid AND organization_id = :org
                  AND status = 'open'
                LIMIT 1
                """
            ),
            {"aid": action_item_id, "org": ctx.organization_id},
        ).first()
    return row is not None


def _assert_impediment_override(
    ctx: OrgContext, action_item_id: UUID, target: BoardColumnKey, justification: str | None
) -> None:
    if target not in _FORWARD_COLUMNS:
        return
    if not _has_open_impediment(ctx, action_item_id):
        return
    if not (justification or "").strip():
        raise AppError(
            "impediment_override_required",
            "Open impediment requires impediment_override_justification to advance",
            status_code=409,
        )


def _current_column(ctx: OrgContext, action_item_id: UUID) -> BoardColumnKey | None:
    board = get_board(ctx)
    for col in board.columns:
        for card in col.cards:
            if card.action_item_id == action_item_id:
                return col.key
    with tenant_connection(ctx.organization_id) as conn:
        row = conn.execute(
            text(
                """
                SELECT ai.status,
                  EXISTS (
                    SELECT 1 FROM agile_sprint_cards sc
                    JOIN agile_sprints sp ON sp.id = sc.sprint_id
                      AND sp.organization_id = sc.organization_id
                    WHERE sc.action_item_id = ai.id
                      AND sc.organization_id = ai.organization_id
                      AND sc.removed_at IS NULL
                      AND sp.status = 'active'
                  ) AS in_active
                FROM action_items ai
                WHERE ai.id = :id AND ai.organization_id = :org
                """
            ),
            {"id": action_item_id, "org": ctx.organization_id},
        ).first()
        if row is None:
            return None
        return _column_for_item(row.status, in_active_sprint=bool(row.in_active))


def move_card(ctx: OrgContext, payload: BoardMoveIn) -> BoardMoveOut:
    _require_mutate(ctx)
    from_col = _current_column(ctx, payload.action_item_id)
    target = payload.target_column
    _assert_impediment_override(
        ctx, payload.action_item_id, target, payload.impediment_override_justification
    )

    transition_event: str | None = None
    item_status = None

    if target == "selected":
        if not payload.sprint_id:
            raise AppError(
                "sprint_id_required",
                "sprint_id required when moving to selected",
                status_code=422,
            )
        agile_service.allocate_card(
            ctx,
            payload.sprint_id,
            SprintCardAllocateIn(action_item_id=payload.action_item_id),
        )
        transition_event = "allocate"
        with tenant_connection(ctx.organization_id) as conn:
            st = conn.execute(
                text("SELECT status FROM action_items WHERE id = :id"),
                {"id": payload.action_item_id},
            ).one()
            item_status = st.status

    elif target == "backlog":
        if not payload.sprint_id:
            with tenant_connection(ctx.organization_id) as conn:
                card = conn.execute(
                    text(
                        """
                        SELECT sc.sprint_id FROM agile_sprint_cards sc
                        WHERE sc.action_item_id = :aid AND sc.organization_id = :org
                          AND sc.removed_at IS NULL
                        """
                    ),
                    {"aid": payload.action_item_id, "org": ctx.organization_id},
                ).first()
            if card is None:
                raise AppError("not_found", "No active sprint allocation", status_code=404)
            sid = card.sprint_id
        else:
            sid = payload.sprint_id
        agile_service.remove_card(ctx, sid, payload.action_item_id, removal_reason="board_move")
        transition_event = "deallocate"
        item_status = "open"

    elif target == "in_progress":
        result = actions_service.start_item(ctx, payload.action_item_id)
        transition_event = result.event
        item_status = result.to_status

    elif target == "implemented":
        result = actions_service.mark_implemented(ctx, payload.action_item_id)
        transition_event = result.event
        item_status = result.to_status

    elif target == "validated":
        result = actions_service.validate_item(ctx, payload.action_item_id)
        transition_event = result.event
        item_status = result.to_status

    elif target == "done":
        with tenant_connection(ctx.organization_id) as conn:
            row = conn.execute(
                text("SELECT status, efficacy_required FROM action_items WHERE id = :id"),
                {"id": payload.action_item_id},
            ).first()
        if row is None:
            raise AppError("not_found", "ActionItem not found", status_code=404)
        if row.status == "validated":
            result = actions_service.confirm_efficacy(ctx, payload.action_item_id)
        elif row.status == "implemented" and not row.efficacy_required:
            result = actions_service.validate_item(ctx, payload.action_item_id)
        else:
            raise AppError(
                "invalid_transition",
                f"Cannot move to done from status {row.status}",
                status_code=409,
            )
        transition_event = result.event
        item_status = result.to_status

    elif target == "ineffective":
        if not (payload.efficacy_fail_reason or "").strip():
            raise AppError(
                "reason_required",
                "efficacy_fail_reason required to move to ineffective",
                status_code=422,
            )
        result = actions_service.fail_efficacy(
            ctx,
            payload.action_item_id,
            ReasonIn(reason=payload.efficacy_fail_reason or ""),
        )
        transition_event = result.event
        item_status = result.to_status

    else:
        raise AppError("invalid_column", f"Unknown target column {target}", status_code=422)

    if payload.impediment_override_justification and transition_event:
        with tenant_connection(ctx.organization_id) as conn:
            from app.audit import write_audit

            write_audit(
                conn,
                organization_id=ctx.organization_id,
                actor_type="user",
                actor_user_id=ctx.principal.user_id,
                actor_membership_id=ctx.membership_id,
                action="agile.board.impediment_override",
                resource_type="action_item",
                resource_id=payload.action_item_id,
                metadata={
                    "justification": payload.impediment_override_justification,
                    "target_column": target,
                },
            )
            conn.commit()

    return BoardMoveOut(
        action_item_id=payload.action_item_id,
        from_column=from_col,
        to_column=target,
        item_status=item_status,  # type: ignore[arg-type]
        transition_event=transition_event,
    )
