"""Audit plan programming — meetings/milestones on AgendaEvent; interviews via Interview."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.audit import write_audit
from app.auth.context import OrgContext
from app.db import tenant_connection
from app.errors import AppError
from app.modules.agenda.service import _org_timezone
from app.modules.audit_plan.schedule_schemas import (
    AuditPlanScheduleOut,
    OverlapWarning,
    ScheduleItemOut,
    ScheduleMeetingCreate,
    ScheduleMeetingUpdate,
    ScheduleMilestoneCreate,
    ScheduleMilestoneUpdate,
    SchedulePending,
)
from app.modules.interviews import service as interview_service
from app.modules.orgs.service import require_role

_MUTATE = ("org_admin", "consultant_auditor", "quality_manager")
_READ = _MUTATE + ("process_owner", "reader")

_MEETING_TITLES: dict[str, str] = {
    "opening_meeting": "Reunião de abertura",
    "closing_meeting": "Reunião de encerramento",
    "additional_meeting": "Reunião adicional",
}

_MILESTONE_TITLES: dict[str, str] = {
    "milestone_preparation_done": "Preparação concluída",
    "milestone_plan_approved": "Plano aprovado",
    "milestone_field_start": "Início do campo",
    "milestone_field_done": "Campo concluído",
    "milestone_analysis_done": "Análise concluída",
    "milestone_report_due": "Relatório previsto",
    "milestone_closure_due": "Encerramento previsto",
    "milestone_custom": "Marco personalizado",
}


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _assert_memberships(conn: Connection, org_id: UUID, ids: list[UUID]) -> None:
    if not ids:
        return
    rows = conn.execute(
        text(
            """
            SELECT id FROM memberships
            WHERE organization_id = :org AND status = 'active' AND id = ANY(:ids)
            """
        ),
        {"org": org_id, "ids": ids},
    ).all()
    found = {r.id for r in rows}
    missing = [str(i) for i in ids if i not in found]
    if missing:
        raise AppError(
            "invalid_participant",
            "Participante não pertence à organização ativa",
            status_code=422,
        )


def _plan_row(conn: Connection, org_id: UUID, assessment_id: UUID):
    row = conn.execute(
        text(
            """
            SELECT id, planned_start, planned_end, processes, lead_membership_id
            FROM assessment_audit_plans
            WHERE assessment_id = :aid AND organization_id = :org
            """
        ),
        {"aid": assessment_id, "org": org_id},
    ).first()
    return row


def _ensure_assessment(conn: Connection, org_id: UUID, assessment_id: UUID):
    row = conn.execute(
        text(
            "SELECT id, status FROM assessments WHERE id = :id AND organization_id = :org"
        ),
        {"id": assessment_id, "org": org_id},
    ).first()
    if row is None:
        raise AppError("not_found", "Assessment not found", status_code=404)
    return row


def _validate_period(
    plan,
    starts: datetime,
    justification: str,
) -> None:
    if plan is None or plan.planned_start is None or plan.planned_end is None:
        return
    day = starts.date()
    if day < plan.planned_start or day > plan.planned_end:
        if not (justification or "").strip():
            raise AppError(
                "outside_plan_period",
                "Atividade fora do período do plano — informe justificativa",
                status_code=422,
            )


def _find_plan_event(
    conn: Connection,
    org_id: UUID,
    assessment_id: UUID,
    kind: str,
    *,
    include_cancelled: bool = False,
):
    sql = """
        SELECT * FROM agenda_events
        WHERE organization_id = :org
          AND assessment_id = :aid
          AND plan_activity_kind = :kind
    """
    if not include_cancelled:
        sql += " AND status <> 'cancelled'"
    sql += " ORDER BY created_at DESC LIMIT 1"
    return conn.execute(
        text(sql),
        {"org": org_id, "aid": assessment_id, "kind": kind},
    ).first()


def get_schedule(ctx: OrgContext, assessment_id: UUID) -> AuditPlanScheduleOut:
    require_role(ctx, *_READ)
    interviews = interview_service.list_interviews(ctx, assessment_id)
    with tenant_connection(ctx.organization_id) as conn:
        _ensure_assessment(conn, ctx.organization_id, assessment_id)
        tz_name = _org_timezone(conn, ctx.organization_id)
        plan = _plan_row(conn, ctx.organization_id, assessment_id)
        events = conn.execute(
            text(
                """
                SELECT * FROM agenda_events
                WHERE organization_id = :org
                  AND assessment_id = :aid
                  AND (
                    plan_activity_kind IS NOT NULL
                    OR (is_auto = true AND source_kind = 'interview')
                  )
                ORDER BY starts_at NULLS LAST, created_at
                """
            ),
            {"org": ctx.organization_id, "aid": assessment_id},
        ).all()

    items: list[ScheduleItemOut] = []
    interview_by_id = {i.id: i for i in interviews}
    seen_interview_events: set[UUID] = set()

    for ev in events:
        if ev.source_kind == "interview" and ev.source_id:
            seen_interview_events.add(ev.source_id)
            iv = interview_by_id.get(ev.source_id)
            title = (iv.title if iv and iv.title else None) or ev.title
            items.append(
                ScheduleItemOut(
                    kind="interview",
                    id=ev.source_id,
                    title=title,
                    status=iv.status if iv else ev.status,
                    starts_at=ev.starts_at,
                    ends_at=ev.ends_at,
                    timezone=ev.timezone or tz_name,
                    location_or_link=ev.location_or_link or "",
                    preparation=(iv.preparation if iv else "") or "",
                    objective=(iv.objective if iv else "") or "",
                    process_name=(iv.process_name if iv else "") or "",
                    owner_membership_id=ev.owner_membership_id,
                    participant_membership_ids=list(ev.participant_membership_ids or []),
                    interview_id=ev.source_id,
                    agenda_event_id=ev.id,
                    primary_action_label="Iniciar entrevista"
                    if (iv and iv.status in ("planned", "confirmed"))
                    else "Ver entrevista",
                    primary_action_href=(
                        f"/assessments/{assessment_id}/audit-plan?startInterview={ev.source_id}"
                    ),
                    next_action="Iniciar primeira entrevista"
                    if (iv and iv.status in ("planned", "confirmed"))
                    else "",
                )
            )
            continue
        kind = "meeting" if (ev.event_type == "meeting") else "milestone"
        items.append(
            ScheduleItemOut(
                kind=kind,  # type: ignore[arg-type]
                id=ev.id,
                title=ev.title,
                status=ev.status,
                starts_at=ev.starts_at,
                ends_at=ev.ends_at,
                timezone=ev.timezone or tz_name,
                location_or_link=ev.location_or_link or "",
                preparation=ev.guidance or "",
                objective=ev.description or "",
                owner_membership_id=ev.owner_membership_id,
                participant_membership_ids=list(ev.participant_membership_ids or []),
                plan_activity_kind=ev.plan_activity_kind,
                agenda_event_id=ev.id,
                primary_action_label="Ver na agenda",
                primary_action_href="/assessments",
                next_action="",
            )
        )

    # Interviews without agenda yet (no scheduled_at)
    for iv in interviews:
        if iv.id in seen_interview_events:
            continue
        items.append(
            ScheduleItemOut(
                kind="interview",
                id=iv.id,
                title=iv.title or "Entrevista (sem horário)",
                status=iv.status,
                starts_at=iv.scheduled_at,
                ends_at=None,
                timezone=tz_name,
                location_or_link=" | ".join(
                    p for p in [iv.location, iv.remote_link] if p
                ),
                preparation=iv.preparation,
                objective=iv.objective,
                process_name=iv.process_name,
                owner_membership_id=iv.interviewer_membership_id,
                participant_membership_ids=iv.participant_membership_ids,
                interview_id=iv.id,
                agenda_event_id=iv.agenda_event_id,
                primary_action_label="Agendar horário",
                primary_action_href=f"/assessments/{assessment_id}/audit-plan",
                next_action="Agendar entrevista",
            )
        )

    items.sort(key=lambda x: (x.starts_at or datetime.max.replace(tzinfo=timezone.utc), x.title))

    overlaps = _detect_overlaps(items)
    has_opening = any(
        i.plan_activity_kind == "opening_meeting" and i.status != "cancelled" for i in items
    )
    has_closing = any(
        i.plan_activity_kind == "closing_meeting" and i.status != "cancelled" for i in items
    )

    pendings: list[SchedulePending] = []
    if not has_opening:
        pendings.append(
            SchedulePending(key="opening", label="Definir reunião de abertura", blocking=True)
        )
    if not has_closing:
        pendings.append(
            SchedulePending(
                key="closing", label="Definir reunião de encerramento", blocking=True
            )
        )
    if plan and plan.lead_membership_id is None:
        pendings.append(
            SchedulePending(key="lead", label="Definir auditor responsável", blocking=True)
        )
    if plan is None or plan.planned_start is None or plan.planned_end is None:
        pendings.append(
            SchedulePending(key="period", label="Definir período do plano", blocking=True)
        )

    # Processes coverage — interview or justification (no artificial count)
    import json

    processes = []
    if plan and plan.processes is not None:
        processes = plan.processes
        if isinstance(processes, str):
            processes = json.loads(processes)
    active_iv_processes = {
        (i.process_name or "").strip().lower()
        for i in interviews
        if i.status != "cancelled" and (i.process_name or "").strip()
    }
    uncovered = []
    for p in processes or []:
        if not isinstance(p, dict):
            continue
        name = (p.get("name") or "").strip()
        if not name:
            continue
        just = (p.get("interview_justification") or "").strip()
        if name.lower() not in active_iv_processes and not just:
            uncovered.append(name)
    if uncovered:
        pendings.append(
            SchedulePending(
                key="process_interviews",
                label="Processos sem entrevista nem justificativa: "
                + ", ".join(uncovered[:5]),
                blocking=True,
            )
        )

    if overlaps:
        pendings.append(
            SchedulePending(
                key="overlap",
                label="Resolver conflito de horário",
                blocking=False,
            )
        )

    next_action = pendings[0].label if pendings else "Revisar programação"
    if not pendings:
        planned_iv = [i for i in interviews if i.status in ("planned", "confirmed")]
        if planned_iv:
            next_action = "Iniciar primeira entrevista"
        else:
            next_action = "Revisar programação"

    return AuditPlanScheduleOut(
        assessment_id=assessment_id,
        organization_id=ctx.organization_id,
        timezone=tz_name,
        agenda_href="/assessments",
        items=items,
        interviews=interviews,
        overlaps=overlaps,
        pendings=pendings,
        next_action=next_action,
        has_opening_meeting=has_opening,
        has_closing_meeting=has_closing,
    )


def _detect_overlaps(items: list[ScheduleItemOut]) -> list[OverlapWarning]:
    warnings: list[OverlapWarning] = []
    timed = [i for i in items if i.starts_at and i.status not in ("cancelled", "completed")]
    for idx, a in enumerate(timed):
        a_start = _as_utc(a.starts_at)  # type: ignore[arg-type]
        a_end = _as_utc(a.ends_at) if a.ends_at else a_start + timedelta(hours=1)
        a_people = set(a.participant_membership_ids)
        if a.owner_membership_id:
            a_people.add(a.owner_membership_id)
        for b in timed[idx + 1 :]:
            b_start = _as_utc(b.starts_at)  # type: ignore[arg-type]
            b_end = _as_utc(b.ends_at) if b.ends_at else b_start + timedelta(hours=1)
            if a_end <= b_start or b_end <= a_start:
                continue
            b_people = set(b.participant_membership_ids)
            if b.owner_membership_id:
                b_people.add(b.owner_membership_id)
            shared = a_people & b_people
            if not shared:
                continue
            warnings.append(
                OverlapWarning(
                    message=f"Sobreposição: «{a.title}» e «{b.title}»",
                    membership_id=next(iter(shared)),
                    item_ids=[a.id, b.id],
                )
            )
    return warnings


def create_meeting(
    ctx: OrgContext, assessment_id: UUID, payload: ScheduleMeetingCreate
) -> AuditPlanScheduleOut:
    require_role(ctx, *_MUTATE)
    with tenant_connection(ctx.organization_id) as conn:
        _ensure_assessment(conn, ctx.organization_id, assessment_id)
        plan = _plan_row(conn, ctx.organization_id, assessment_id)
        starts = _as_utc(payload.starts_at)
        ends = starts + timedelta(minutes=payload.duration_minutes)
        if ends <= starts:
            raise AppError("invalid_time_range", "Término deve ser posterior ao início", status_code=422)
        _validate_period(plan, starts, payload.outside_period_justification)
        members = list(payload.participant_membership_ids or [])
        if payload.owner_membership_id:
            members.append(payload.owner_membership_id)
        _assert_memberships(conn, ctx.organization_id, members)
        tz_name = payload.timezone or _org_timezone(conn, ctx.organization_id)
        title = (payload.title or _MEETING_TITLES.get(payload.kind, "Reunião")).strip()

        if payload.kind in ("opening_meeting", "closing_meeting"):
            existing = _find_plan_event(
                conn, ctx.organization_id, assessment_id, payload.kind
            )
            if existing:
                row = conn.execute(
                    text(
                        """
                        UPDATE agenda_events SET
                          title = :title,
                          description = :desc,
                          starts_at = :starts,
                          ends_at = :ends,
                          timezone = :tz,
                          owner_membership_id = :owner,
                          participant_membership_ids = :parts,
                          location_or_link = :loc,
                          guidance = :prep,
                          status = 'scheduled',
                          updated_at = now(),
                          updated_by_user_id = :uid
                        WHERE id = :id AND organization_id = :org
                        RETURNING id
                        """
                    ),
                    {
                        "id": existing.id,
                        "org": ctx.organization_id,
                        "title": title,
                        "desc": (payload.objective or "").strip(),
                        "starts": starts,
                        "ends": ends,
                        "tz": tz_name,
                        "owner": payload.owner_membership_id,
                        "parts": payload.participant_membership_ids or [],
                        "loc": (payload.location_or_link or "").strip(),
                        "prep": (payload.preparation or "").strip(),
                        "uid": ctx.principal.user_id,
                    },
                ).one()
                write_audit(
                    conn,
                    organization_id=ctx.organization_id,
                    actor_type="user",
                    actor_user_id=ctx.principal.user_id,
                    actor_membership_id=ctx.membership_id,
                    action="audit_plan.meeting.update",
                    resource_type="agenda_event",
                    resource_id=row.id,
                    metadata={"kind": payload.kind},
                )
                conn.commit()
                return get_schedule(ctx, assessment_id)

        row = conn.execute(
            text(
                """
                INSERT INTO agenda_events (
                  organization_id, assessment_id, title, description, event_type,
                  starts_at, ends_at, timezone, owner_membership_id,
                  participant_membership_ids, location_or_link, status,
                  guidance, related_action, plan_activity_kind, is_auto,
                  created_by_user_id, updated_by_user_id
                ) VALUES (
                  :org, :aid, :title, :desc, 'meeting',
                  :starts, :ends, :tz, :owner,
                  :parts, :loc, 'scheduled',
                  :prep, 'open_audit_plan', :kind, false,
                  :uid, :uid
                )
                RETURNING id
                """
            ),
            {
                "org": ctx.organization_id,
                "aid": assessment_id,
                "title": title,
                "desc": (payload.objective or "").strip(),
                "starts": starts,
                "ends": ends,
                "tz": tz_name,
                "owner": payload.owner_membership_id,
                "parts": payload.participant_membership_ids or [],
                "loc": (payload.location_or_link or "").strip(),
                "prep": (payload.preparation or "").strip(),
                "kind": payload.kind,
                "uid": ctx.principal.user_id,
            },
        ).one()
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="audit_plan.meeting.create",
            resource_type="agenda_event",
            resource_id=row.id,
            metadata={"kind": payload.kind},
        )
        conn.commit()
    return get_schedule(ctx, assessment_id)


def update_meeting(
    ctx: OrgContext,
    assessment_id: UUID,
    event_id: UUID,
    payload: ScheduleMeetingUpdate,
) -> AuditPlanScheduleOut:
    require_role(ctx, *_MUTATE)
    with tenant_connection(ctx.organization_id) as conn:
        _ensure_assessment(conn, ctx.organization_id, assessment_id)
        cur = conn.execute(
            text(
                """
                SELECT * FROM agenda_events
                WHERE id = :id AND organization_id = :org AND assessment_id = :aid
                  AND event_type = 'meeting' AND plan_activity_kind IS NOT NULL
                FOR UPDATE
                """
            ),
            {"id": event_id, "org": ctx.organization_id, "aid": assessment_id},
        ).first()
        if cur is None:
            raise AppError("not_found", "Reunião não encontrada", status_code=404)
        plan = _plan_row(conn, ctx.organization_id, assessment_id)
        starts = _as_utc(payload.starts_at) if payload.starts_at is not None else _as_utc(cur.starts_at)
        duration = payload.duration_minutes
        if duration is None and cur.ends_at and cur.starts_at:
            duration = max(1, int((_as_utc(cur.ends_at) - _as_utc(cur.starts_at)).total_seconds() // 60))
        duration = duration or 60
        ends = starts + timedelta(minutes=duration)
        if ends <= starts:
            raise AppError("invalid_time_range", "Término deve ser posterior ao início", status_code=422)
        just = payload.outside_period_justification or ""
        _validate_period(plan, starts, just)
        parts = (
            payload.participant_membership_ids
            if payload.participant_membership_ids is not None
            else list(cur.participant_membership_ids or [])
        )
        owner = (
            payload.owner_membership_id
            if payload.owner_membership_id is not None
            else cur.owner_membership_id
        )
        members = list(parts)
        if owner:
            members.append(owner)
        _assert_memberships(conn, ctx.organization_id, members)
        status = payload.status if payload.status is not None else cur.status
        waiver = (
            (payload.waiver_reason or "").strip()
            if payload.waiver_reason is not None
            else getattr(cur, "waiver_reason", None) or ""
        )
        if status == "waived" and len(waiver) < 8:
            raise AppError(
                "validation_error",
                "Justificativa da dispensa é obrigatória (mínimo 8 caracteres)",
                status_code=422,
            )
        if status != "waived":
            waiver = ""
        conn.execute(
            text(
                """
                UPDATE agenda_events SET
                  title = :title,
                  description = :desc,
                  starts_at = :starts,
                  ends_at = :ends,
                  timezone = :tz,
                  owner_membership_id = :owner,
                  participant_membership_ids = :parts,
                  location_or_link = :loc,
                  guidance = :prep,
                  status = :status,
                  waiver_reason = :waiver,
                  updated_at = now(),
                  updated_by_user_id = :uid
                WHERE id = :id AND organization_id = :org
                """
            ),
            {
                "id": event_id,
                "org": ctx.organization_id,
                "title": (payload.title if payload.title is not None else cur.title).strip(),
                "desc": (
                    payload.objective if payload.objective is not None else cur.description or ""
                ).strip(),
                "starts": starts,
                "ends": ends,
                "tz": payload.timezone or cur.timezone,
                "owner": owner,
                "parts": parts,
                "loc": (
                    payload.location_or_link
                    if payload.location_or_link is not None
                    else cur.location_or_link or ""
                ).strip(),
                "prep": (
                    payload.preparation if payload.preparation is not None else cur.guidance or ""
                ).strip(),
                "status": status,
                "waiver": waiver,
                "uid": ctx.principal.user_id,
            },
        )
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="audit_plan.meeting.update",
            resource_type="agenda_event",
            resource_id=event_id,
            from_status=cur.status,
            to_status=status,
        )
        conn.commit()
    return get_schedule(ctx, assessment_id)


def create_milestone(
    ctx: OrgContext, assessment_id: UUID, payload: ScheduleMilestoneCreate
) -> AuditPlanScheduleOut:
    require_role(ctx, *_MUTATE)
    with tenant_connection(ctx.organization_id) as conn:
        _ensure_assessment(conn, ctx.organization_id, assessment_id)
        plan = _plan_row(conn, ctx.organization_id, assessment_id)
        occurs = _as_utc(payload.occurs_at)
        _validate_period(plan, occurs, payload.outside_period_justification)
        if payload.owner_membership_id:
            _assert_memberships(conn, ctx.organization_id, [payload.owner_membership_id])
        tz_name = payload.timezone or _org_timezone(conn, ctx.organization_id)
        title = (
            payload.title or _MILESTONE_TITLES.get(payload.kind, "Marco")
        ).strip()
        row = conn.execute(
            text(
                """
                INSERT INTO agenda_events (
                  organization_id, assessment_id, title, description, event_type,
                  starts_at, ends_at, timezone, owner_membership_id,
                  status, guidance, related_action, plan_activity_kind, is_auto,
                  created_by_user_id, updated_by_user_id
                ) VALUES (
                  :org, :aid, :title, :desc, 'milestone',
                  :starts, NULL, :tz, :owner,
                  'scheduled', :notes, 'open_audit_plan', :kind, false,
                  :uid, :uid
                )
                RETURNING id
                """
            ),
            {
                "org": ctx.organization_id,
                "aid": assessment_id,
                "title": title,
                "desc": (payload.notes or "").strip(),
                "starts": occurs,
                "tz": tz_name,
                "owner": payload.owner_membership_id,
                "notes": (payload.notes or "").strip(),
                "kind": payload.kind,
                "uid": ctx.principal.user_id,
            },
        ).one()
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="audit_plan.milestone.create",
            resource_type="agenda_event",
            resource_id=row.id,
            metadata={"kind": payload.kind},
        )
        conn.commit()
    return get_schedule(ctx, assessment_id)


def update_milestone(
    ctx: OrgContext,
    assessment_id: UUID,
    event_id: UUID,
    payload: ScheduleMilestoneUpdate,
) -> AuditPlanScheduleOut:
    require_role(ctx, *_MUTATE)
    with tenant_connection(ctx.organization_id) as conn:
        _ensure_assessment(conn, ctx.organization_id, assessment_id)
        cur = conn.execute(
            text(
                """
                SELECT * FROM agenda_events
                WHERE id = :id AND organization_id = :org AND assessment_id = :aid
                  AND event_type = 'milestone' AND plan_activity_kind IS NOT NULL
                FOR UPDATE
                """
            ),
            {"id": event_id, "org": ctx.organization_id, "aid": assessment_id},
        ).first()
        if cur is None:
            raise AppError("not_found", "Marco não encontrado", status_code=404)
        plan = _plan_row(conn, ctx.organization_id, assessment_id)
        occurs = (
            _as_utc(payload.occurs_at) if payload.occurs_at is not None else _as_utc(cur.starts_at)
        )
        _validate_period(plan, occurs, payload.outside_period_justification or "")
        owner = (
            payload.owner_membership_id
            if payload.owner_membership_id is not None
            else cur.owner_membership_id
        )
        if owner:
            _assert_memberships(conn, ctx.organization_id, [owner])
        status = payload.status if payload.status is not None else cur.status
        conn.execute(
            text(
                """
                UPDATE agenda_events SET
                  title = :title,
                  description = :desc,
                  starts_at = :starts,
                  timezone = :tz,
                  owner_membership_id = :owner,
                  guidance = :notes,
                  status = :status,
                  updated_at = now(),
                  updated_by_user_id = :uid
                WHERE id = :id AND organization_id = :org
                """
            ),
            {
                "id": event_id,
                "org": ctx.organization_id,
                "title": (payload.title if payload.title is not None else cur.title).strip(),
                "desc": (
                    payload.notes if payload.notes is not None else cur.description or ""
                ).strip(),
                "starts": occurs,
                "tz": payload.timezone or cur.timezone,
                "owner": owner,
                "notes": (
                    payload.notes if payload.notes is not None else cur.guidance or ""
                ).strip(),
                "status": status,
                "uid": ctx.principal.user_id,
            },
        )
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="audit_plan.milestone.update",
            resource_type="agenda_event",
            resource_id=event_id,
            from_status=cur.status,
            to_status=status,
        )
        conn.commit()
    return get_schedule(ctx, assessment_id)


def schedule_readiness_flags(ctx: OrgContext, assessment_id: UUID) -> dict:
    """Flags used by audit plan readiness checklist."""
    schedule = get_schedule(ctx, assessment_id)
    return {
        "has_opening_meeting": schedule.has_opening_meeting,
        "has_closing_meeting": schedule.has_closing_meeting,
        "process_coverage_ok": not any(
            p.key == "process_interviews" for p in schedule.pendings
        ),
        "has_overlap": len(schedule.overlaps) > 0,
        "next_action": schedule.next_action,
    }
