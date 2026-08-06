"""Interview + Answer — Interview is SoT for interviews; agenda is projection."""

from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.audit import write_audit
from app.auth.context import OrgContext
from app.db import tenant_connection
from app.errors import AppError
from app.modules.agenda.service import sync_interview_agenda_event
from app.modules.interviews.schemas import (
    AnswerCreate,
    AnswerOut,
    AnswerUpdate,
    InterviewCreate,
    InterviewOut,
    InterviewTransitionResult,
    InterviewUpdate,
    QuestionOut,
)
from app.modules.orgs.service import require_role

_MUTATE_ROLES = ("org_admin", "consultant_auditor", "quality_manager")
_READ_ROLES = _MUTATE_ROLES + ("process_owner", "reader")
_PLAN_ASSESSMENT = frozenset({"draft", "planned", "in_progress"})
_FIELD_EDITABLE_ASSESSMENT = frozenset({"in_progress"})
_ANSWERABLE_INTERVIEW = frozenset({"planned", "confirmed", "in_progress"})
_MUTABLE_INTERVIEW = frozenset({"planned", "confirmed", "in_progress"})
_INTERVIEW_COLS = """
    i.id, i.organization_id, i.assessment_id, i.conducted_at, i.mode, i.status,
    i.title, i.objective, i.process_name, i.org_contact_name,
    i.interviewer_membership_id, i.participant_membership_ids,
    i.scheduled_at, i.duration_minutes, i.location, i.remote_link,
    i.preparation, i.outside_period_justification,
    i.created_at, i.updated_at
"""


def _as_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _interview_out(
    row,
    *,
    agenda_event_id: UUID | None = None,
    overlap_warnings: list[str] | None = None,
) -> InterviewOut:
    return InterviewOut(
        id=row.id,
        organization_id=row.organization_id,
        assessment_id=row.assessment_id,
        conducted_at=row.conducted_at,
        mode=row.mode,
        status=row.status,
        title=getattr(row, "title", None) or "",
        objective=getattr(row, "objective", None) or "",
        process_name=getattr(row, "process_name", None) or "",
        org_contact_name=getattr(row, "org_contact_name", None) or "",
        interviewer_membership_id=getattr(row, "interviewer_membership_id", None),
        participant_membership_ids=list(
            getattr(row, "participant_membership_ids", None) or []
        ),
        scheduled_at=getattr(row, "scheduled_at", None),
        duration_minutes=getattr(row, "duration_minutes", None),
        location=getattr(row, "location", None) or "",
        remote_link=getattr(row, "remote_link", None) or "",
        preparation=getattr(row, "preparation", None) or "",
        agenda_event_id=agenda_event_id,
        overlap_warnings=overlap_warnings or [],
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _answer_out(row) -> AnswerOut:
    return AnswerOut(
        id=row.id,
        organization_id=row.organization_id,
        interview_id=row.interview_id,
        question_id=row.question_id,
        criterion_id=row.criterion_id,
        body=row.body,
        author_membership_id=row.author_membership_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _lock_assessment(conn: Connection, org_id: UUID, assessment_id: UUID):
    row = conn.execute(
        text(
            """
            SELECT id, status, assessment_model_id, lead_membership_id
            FROM assessments
            WHERE id = :id AND organization_id = :org
            FOR UPDATE
            """
        ),
        {"id": assessment_id, "org": org_id},
    ).first()
    if row is None:
        raise AppError("not_found", "Assessment not found", status_code=404)
    return row


def _lock_interview(conn: Connection, org_id: UUID, interview_id: UUID):
    row = conn.execute(
        text(
            f"""
            SELECT {_INTERVIEW_COLS},
                   a.status AS assessment_status,
                   a.lead_membership_id
            FROM interviews i
            JOIN assessments a
              ON a.id = i.assessment_id AND a.organization_id = i.organization_id
            WHERE i.id = :id AND i.organization_id = :org
            FOR UPDATE OF i
            """
        ),
        {"id": interview_id, "org": org_id},
    ).first()
    if row is None:
        raise AppError("not_found", "Interview not found", status_code=404)
    return row


def _assert_field_collecting(assessment_status: str) -> None:
    if assessment_status not in _FIELD_EDITABLE_ASSESSMENT:
        raise AppError(
            "interview_phase_closed",
            f"Interview edits require assessment in_progress (current={assessment_status})",
            status_code=409,
        )


def _assert_plan_or_field(assessment_status: str) -> None:
    if assessment_status not in _PLAN_ASSESSMENT:
        raise AppError(
            "interview_phase_closed",
            f"Interview planning requires draft/planned/in_progress (current={assessment_status})",
            status_code=409,
        )


def _assert_interview_editable(interview_status: str, assessment_status: str) -> None:
    _assert_field_collecting(assessment_status)
    if interview_status not in _ANSWERABLE_INTERVIEW:
        raise AppError(
            "interview_locked",
            f"Interview is not editable (status={interview_status})",
            status_code=409,
        )


def _assert_memberships(
    conn: Connection, org_id: UUID, membership_ids: list[UUID]
) -> None:
    if not membership_ids:
        return
    rows = conn.execute(
        text(
            """
            SELECT id FROM memberships
            WHERE organization_id = :org
              AND status = 'active'
              AND id = ANY(:ids)
            """
        ),
        {"org": org_id, "ids": membership_ids},
    ).all()
    found = {r.id for r in rows}
    missing = [str(m) for m in membership_ids if m not in found]
    if missing:
        raise AppError(
            "invalid_participant",
            "Participante não pertence à organização ativa",
            status_code=422,
        )


def _plan_period(conn: Connection, org_id: UUID, assessment_id: UUID) -> tuple[date | None, date | None]:
    row = conn.execute(
        text(
            """
            SELECT planned_start, planned_end
            FROM assessment_audit_plans
            WHERE assessment_id = :aid AND organization_id = :org
            """
        ),
        {"aid": assessment_id, "org": org_id},
    ).first()
    if row is None:
        return None, None
    return row.planned_start, row.planned_end


def _validate_schedule_window(
    conn: Connection,
    org_id: UUID,
    assessment_id: UUID,
    scheduled_at: datetime | None,
    duration_minutes: int | None,
    outside_justification: str,
) -> None:
    if scheduled_at is None:
        return
    start = _as_utc(scheduled_at)
    assert start is not None
    ends = start
    if duration_minutes:
        from datetime import timedelta

        ends = start + timedelta(minutes=duration_minutes)
    if ends <= start and duration_minutes:
        raise AppError(
            "invalid_time_range",
            "Término deve ser posterior ao início",
            status_code=422,
        )
    p_start, p_end = _plan_period(conn, org_id, assessment_id)
    if p_start and p_end:
        day = start.date()
        if day < p_start or day > p_end:
            if not (outside_justification or "").strip():
                raise AppError(
                    "outside_plan_period",
                    "Atividade fora do período do plano — informe justificativa",
                    status_code=422,
                )


def _process_in_scope(
    conn: Connection, org_id: UUID, assessment_id: UUID, process_name: str
) -> None:
    name = (process_name or "").strip()
    if not name:
        return
    row = conn.execute(
        text(
            """
            SELECT processes FROM assessment_audit_plans
            WHERE assessment_id = :aid AND organization_id = :org
            """
        ),
        {"aid": assessment_id, "org": org_id},
    ).first()
    if row is None:
        return
    import json

    processes = row.processes
    if isinstance(processes, str):
        processes = json.loads(processes)
    names = {
        (p.get("name") or "").strip().lower()
        for p in (processes or [])
        if isinstance(p, dict)
    }
    if names and name.lower() not in names:
        raise AppError(
            "process_out_of_scope",
            "Processo não pertence ao escopo do plano",
            status_code=422,
        )


def _overlap_warnings(
    conn: Connection,
    org_id: UUID,
    *,
    membership_ids: list[UUID],
    starts: datetime,
    ends: datetime,
    exclude_interview_id: UUID | None = None,
) -> list[str]:
    if not membership_ids:
        return []
    sql = """
            SELECT i.id, i.title, i.scheduled_at, i.duration_minutes,
                   i.interviewer_membership_id, i.participant_membership_ids
            FROM interviews i
            WHERE i.organization_id = :org
              AND i.status NOT IN ('cancelled', 'completed')
              AND i.scheduled_at IS NOT NULL
    """
    params: dict = {"org": org_id}
    if exclude_interview_id is not None:
        sql += " AND i.id <> :exclude"
        params["exclude"] = exclude_interview_id
    rows = conn.execute(text(sql), params).all()
    warnings: list[str] = []
    people = set(membership_ids)
    for r in rows:
        other_start = _as_utc(r.scheduled_at)
        if other_start is None:
            continue
        from datetime import timedelta

        other_end = other_start + timedelta(minutes=int(r.duration_minutes or 60))
        if other_end <= starts or ends <= other_start:
            continue
        involved = set()
        if r.interviewer_membership_id:
            involved.add(r.interviewer_membership_id)
        involved.update(r.participant_membership_ids or [])
        if people & involved:
            label = (r.title or "outra entrevista").strip()
            warnings.append(f"Sobreposição com «{label}» para a mesma pessoa")
    return warnings


def _agenda_id_for(conn: Connection, org_id: UUID, interview_id: UUID) -> UUID | None:
    row = conn.execute(
        text(
            """
            SELECT id FROM agenda_events
            WHERE organization_id = :org
              AND is_auto = true
              AND source_kind = 'interview'
              AND source_id = :sid
            """
        ),
        {"org": org_id, "sid": interview_id},
    ).first()
    return row.id if row else None


def _sync_and_out(conn: Connection, ctx: OrgContext, row, warnings: list[str] | None = None) -> InterviewOut:
    # Attach lead for sync fallback
    class _Proxy:
        pass

    proxy = _Proxy()
    for attr in (
        "id",
        "assessment_id",
        "conducted_at",
        "scheduled_at",
        "status",
        "mode",
        "title",
        "objective",
        "process_name",
        "interviewer_membership_id",
        "participant_membership_ids",
        "duration_minutes",
        "location",
        "remote_link",
        "preparation",
    ):
        setattr(proxy, attr, getattr(row, attr, None))
    setattr(proxy, "lead_membership_id", getattr(row, "lead_membership_id", None))
    event_id = sync_interview_agenda_event(conn, ctx, proxy)
    return _interview_out(row, agenda_event_id=event_id, overlap_warnings=warnings or [])


def list_assessment_questions(ctx: OrgContext, assessment_id: UUID) -> list[QuestionOut]:
    require_role(ctx, *_READ_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        assess = conn.execute(
            text(
                """
                SELECT assessment_model_id FROM assessments
                WHERE id = :id AND organization_id = :org
                """
            ),
            {"id": assessment_id, "org": ctx.organization_id},
        ).first()
        if assess is None:
            raise AppError("not_found", "Assessment not found", status_code=404)
        rows = conn.execute(
            text(
                """
                SELECT id, assessment_model_id, criterion_id, code, prompt_text, sort_order
                FROM questions
                WHERE assessment_model_id = :mid
                ORDER BY sort_order, code
                """
            ),
            {"mid": assess.assessment_model_id},
        ).all()
    return [
        QuestionOut(
            id=r.id,
            assessment_model_id=r.assessment_model_id,
            criterion_id=r.criterion_id,
            code=r.code,
            prompt_text=r.prompt_text,
            sort_order=r.sort_order,
        )
        for r in rows
    ]


def create_interview(
    ctx: OrgContext, assessment_id: UUID, payload: InterviewCreate
) -> InterviewOut:
    require_role(ctx, *_MUTATE_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        assess = _lock_assessment(conn, ctx.organization_id, assessment_id)
        _assert_plan_or_field(assess.status)
        members = list(payload.participant_membership_ids or [])
        if payload.interviewer_membership_id:
            members.append(payload.interviewer_membership_id)
        _assert_memberships(conn, ctx.organization_id, members)
        _process_in_scope(conn, ctx.organization_id, assessment_id, payload.process_name)
        scheduled = _as_utc(payload.scheduled_at)
        duration = payload.duration_minutes
        _validate_schedule_window(
            conn,
            ctx.organization_id,
            assessment_id,
            scheduled,
            duration,
            payload.outside_period_justification,
        )
        warnings: list[str] = []
        if scheduled:
            from datetime import timedelta

            ends = scheduled + timedelta(minutes=int(duration or 60))
            warnings = _overlap_warnings(
                conn,
                ctx.organization_id,
                membership_ids=members,
                starts=scheduled,
                ends=ends,
            )
        row = conn.execute(
            text(
                """
                INSERT INTO interviews (
                  organization_id, assessment_id, conducted_at, mode, status,
                  title, objective, process_name, org_contact_name,
                  interviewer_membership_id, participant_membership_ids,
                  scheduled_at, duration_minutes, location, remote_link,
                  preparation, outside_period_justification
                ) VALUES (
                  :org, :assess, :conducted, :mode, 'planned',
                  :title, :objective, :process_name, :org_contact,
                  :interviewer, :parts,
                  :scheduled, :duration, :location, :remote,
                  :prep, :outside
                )
                RETURNING id, organization_id, assessment_id, conducted_at, mode,
                          status, title, objective, process_name, org_contact_name,
                          interviewer_membership_id, participant_membership_ids,
                          scheduled_at, duration_minutes, location, remote_link,
                          preparation, outside_period_justification,
                          created_at, updated_at
                """
            ),
            {
                "org": ctx.organization_id,
                "assess": assessment_id,
                "conducted": _as_utc(payload.conducted_at),
                "mode": payload.mode.value if payload.mode else None,
                "title": (payload.title or "").strip(),
                "objective": (payload.objective or "").strip(),
                "process_name": (payload.process_name or "").strip(),
                "org_contact": (payload.org_contact_name or "").strip(),
                "interviewer": payload.interviewer_membership_id,
                "parts": payload.participant_membership_ids or [],
                "scheduled": scheduled,
                "duration": duration,
                "location": (payload.location or "").strip(),
                "remote": (payload.remote_link or "").strip(),
                "prep": (payload.preparation or "").strip(),
                "outside": (payload.outside_period_justification or "").strip(),
            },
        ).one()
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="interview.create",
            resource_type="interview",
            resource_id=row.id,
            to_status="planned",
            metadata={"assessment_id": str(assessment_id)},
        )
        # Build row-like with lead
        from types import SimpleNamespace

        sync_row = SimpleNamespace(
            **{c: getattr(row, c) for c in row._mapping.keys()},
            lead_membership_id=assess.lead_membership_id,
        )
        out = _sync_and_out(conn, ctx, sync_row, warnings)
        conn.commit()
    return out


def update_interview(
    ctx: OrgContext, interview_id: UUID, payload: InterviewUpdate
) -> InterviewOut:
    require_role(ctx, *_MUTATE_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        row = _lock_interview(conn, ctx.organization_id, interview_id)
        _assert_plan_or_field(row.assessment_status)
        if row.status not in _MUTABLE_INTERVIEW:
            raise AppError(
                "interview_locked",
                f"Interview is not editable (status={row.status})",
                status_code=409,
            )
        title = payload.title if payload.title is not None else row.title
        objective = payload.objective if payload.objective is not None else row.objective
        process_name = (
            payload.process_name if payload.process_name is not None else row.process_name
        )
        org_contact = (
            payload.org_contact_name
            if payload.org_contact_name is not None
            else row.org_contact_name
        )
        interviewer = (
            payload.interviewer_membership_id
            if payload.interviewer_membership_id is not None
            else row.interviewer_membership_id
        )
        parts = (
            payload.participant_membership_ids
            if payload.participant_membership_ids is not None
            else list(row.participant_membership_ids or [])
        )
        if payload.clear_scheduled_at:
            scheduled = None
        elif payload.scheduled_at is not None:
            scheduled = _as_utc(payload.scheduled_at)
        else:
            scheduled = _as_utc(row.scheduled_at)
        duration = (
            payload.duration_minutes
            if payload.duration_minutes is not None
            else row.duration_minutes
        )
        location = payload.location if payload.location is not None else row.location
        remote = payload.remote_link if payload.remote_link is not None else row.remote_link
        prep = payload.preparation if payload.preparation is not None else row.preparation
        outside = (
            payload.outside_period_justification
            if payload.outside_period_justification is not None
            else getattr(row, "outside_period_justification", "")
        )
        mode = payload.mode.value if payload.mode is not None else row.mode
        conducted = (
            _as_utc(payload.conducted_at)
            if payload.conducted_at is not None
            else row.conducted_at
        )

        members = list(parts)
        if interviewer:
            members.append(interviewer)
        _assert_memberships(conn, ctx.organization_id, members)
        _process_in_scope(conn, ctx.organization_id, row.assessment_id, process_name or "")
        _validate_schedule_window(
            conn,
            ctx.organization_id,
            row.assessment_id,
            scheduled,
            duration,
            outside or "",
        )
        warnings: list[str] = []
        if scheduled:
            from datetime import timedelta

            ends = scheduled + timedelta(minutes=int(duration or 60))
            warnings = _overlap_warnings(
                conn,
                ctx.organization_id,
                membership_ids=members,
                starts=scheduled,
                ends=ends,
                exclude_interview_id=interview_id,
            )
        updated = conn.execute(
            text(
                """
                UPDATE interviews SET
                  title = :title,
                  objective = :objective,
                  process_name = :process_name,
                  org_contact_name = :org_contact,
                  interviewer_membership_id = :interviewer,
                  participant_membership_ids = :parts,
                  scheduled_at = :scheduled,
                  duration_minutes = :duration,
                  location = :location,
                  remote_link = :remote,
                  preparation = :prep,
                  outside_period_justification = :outside,
                  mode = :mode,
                  conducted_at = :conducted,
                  updated_at = now()
                WHERE id = :id AND organization_id = :org
                RETURNING id, organization_id, assessment_id, conducted_at, mode,
                          status, title, objective, process_name, org_contact_name,
                          interviewer_membership_id, participant_membership_ids,
                          scheduled_at, duration_minutes, location, remote_link,
                          preparation, outside_period_justification,
                          created_at, updated_at
                """
            ),
            {
                "id": interview_id,
                "org": ctx.organization_id,
                "title": (title or "").strip(),
                "objective": (objective or "").strip(),
                "process_name": (process_name or "").strip(),
                "org_contact": (org_contact or "").strip(),
                "interviewer": interviewer,
                "parts": parts,
                "scheduled": scheduled,
                "duration": duration,
                "location": (location or "").strip(),
                "remote": (remote or "").strip(),
                "prep": (prep or "").strip(),
                "outside": (outside or "").strip(),
                "mode": mode,
                "conducted": conducted,
            },
        ).one()
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="interview.update",
            resource_type="interview",
            resource_id=interview_id,
        )
        from types import SimpleNamespace

        sync_row = SimpleNamespace(
            **{c: getattr(updated, c) for c in updated._mapping.keys()},
            lead_membership_id=row.lead_membership_id,
        )
        out = _sync_and_out(conn, ctx, sync_row, warnings)
        conn.commit()
    return out


def list_interviews(ctx: OrgContext, assessment_id: UUID) -> list[InterviewOut]:
    require_role(ctx, *_READ_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        assess = conn.execute(
            text(
                "SELECT id FROM assessments WHERE id = :id AND organization_id = :org"
            ),
            {"id": assessment_id, "org": ctx.organization_id},
        ).first()
        if assess is None:
            raise AppError("not_found", "Assessment not found", status_code=404)
        rows = conn.execute(
            text(
                f"""
                SELECT {_INTERVIEW_COLS}
                FROM interviews i
                WHERE i.assessment_id = :aid AND i.organization_id = :org
                ORDER BY COALESCE(i.scheduled_at, i.created_at), i.created_at
                """
            ),
            {"aid": assessment_id, "org": ctx.organization_id},
        ).all()
        out = []
        for r in rows:
            out.append(
                _interview_out(r, agenda_event_id=_agenda_id_for(conn, ctx.organization_id, r.id))
            )
    return out


def get_interview(ctx: OrgContext, interview_id: UUID) -> InterviewOut:
    require_role(ctx, *_READ_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        row = conn.execute(
            text(
                f"""
                SELECT {_INTERVIEW_COLS}
                FROM interviews i
                WHERE i.id = :id AND i.organization_id = :org
                """
            ),
            {"id": interview_id, "org": ctx.organization_id},
        ).first()
        if row is None:
            raise AppError("not_found", "Interview not found", status_code=404)
        return _interview_out(
            row, agenda_event_id=_agenda_id_for(conn, ctx.organization_id, row.id)
        )


def _transition(
    ctx: OrgContext,
    interview_id: UUID,
    *,
    allowed_from: frozenset[str],
    to_status: str,
    event: str,
    require_field: bool,
    set_conducted: bool = False,
) -> InterviewTransitionResult:
    require_role(ctx, *_MUTATE_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        row = _lock_interview(conn, ctx.organization_id, interview_id)
        if require_field:
            _assert_field_collecting(row.assessment_status)
        else:
            _assert_plan_or_field(row.assessment_status)
        if row.status not in allowed_from:
            raise AppError(
                "invalid_transition",
                f"{event} requires {sorted(allowed_from)} (current={row.status})",
                status_code=409,
            )
        if to_status == "in_progress" and row.assessment_status != "in_progress":
            raise AppError(
                "interview_phase_closed",
                "Iniciar entrevista exige avaliação em andamento",
                status_code=409,
            )
        sql = """
            UPDATE interviews
            SET status = :to_status,
                conducted_at = CASE
                  WHEN :set_conducted THEN COALESCE(conducted_at, now())
                  ELSE conducted_at
                END,
                updated_at = now()
            WHERE id = :id AND organization_id = :org AND status = :from_status
            RETURNING id, organization_id, assessment_id, conducted_at, mode,
                      status, title, objective, process_name, org_contact_name,
                      interviewer_membership_id, participant_membership_ids,
                      scheduled_at, duration_minutes, location, remote_link,
                      preparation, outside_period_justification,
                      created_at, updated_at
        """
        updated = conn.execute(
            text(sql),
            {
                "id": interview_id,
                "org": ctx.organization_id,
                "to_status": to_status,
                "from_status": row.status,
                "set_conducted": set_conducted,
            },
        ).first()
        if updated is None:
            raise AppError("invalid_transition", f"Interview {event} race", status_code=409)
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action=f"interview.{event}",
            resource_type="interview",
            resource_id=interview_id,
            from_status=row.status,
            to_status=to_status,
        )
        from types import SimpleNamespace

        sync_row = SimpleNamespace(
            **{c: getattr(updated, c) for c in updated._mapping.keys()},
            lead_membership_id=row.lead_membership_id,
        )
        interview = _sync_and_out(conn, ctx, sync_row)
        conn.commit()
    return InterviewTransitionResult(
        interview=interview,
        from_status=row.status,
        to_status=to_status,
        event=event,
    )


def confirm_interview(ctx: OrgContext, interview_id: UUID) -> InterviewTransitionResult:
    return _transition(
        ctx,
        interview_id,
        allowed_from=frozenset({"planned"}),
        to_status="confirmed",
        event="confirm",
        require_field=False,
    )


def start_interview(ctx: OrgContext, interview_id: UUID) -> InterviewTransitionResult:
    return _transition(
        ctx,
        interview_id,
        allowed_from=frozenset({"planned", "confirmed"}),
        to_status="in_progress",
        event="start",
        require_field=True,
    )


def complete_interview(ctx: OrgContext, interview_id: UUID) -> InterviewTransitionResult:
    return _transition(
        ctx,
        interview_id,
        allowed_from=frozenset({"planned", "confirmed", "in_progress"}),
        to_status="completed",
        event="complete",
        require_field=True,
        set_conducted=True,
    )


def cancel_interview(ctx: OrgContext, interview_id: UUID) -> InterviewTransitionResult:
    return _transition(
        ctx,
        interview_id,
        allowed_from=frozenset({"planned", "confirmed", "in_progress"}),
        to_status="cancelled",
        event="cancel",
        require_field=False,
    )


def _validate_answer_refs(
    conn: Connection,
    org_id: UUID,
    assessment_id: UUID,
    question_id: UUID | None,
    criterion_id: UUID | None,
) -> None:
    if question_id is not None:
        q = conn.execute(
            text(
                """
                SELECT q.id
                FROM questions q
                JOIN assessments a ON a.assessment_model_id = q.assessment_model_id
                WHERE q.id = :qid
                  AND a.id = :aid
                  AND a.organization_id = :org
                """
            ),
            {"qid": question_id, "aid": assessment_id, "org": org_id},
        ).first()
        if q is None:
            raise AppError(
                "not_found",
                "Question not found for this assessment model",
                status_code=404,
            )
    if criterion_id is not None:
        c = conn.execute(
            text("SELECT id FROM criteria WHERE id = :id"),
            {"id": criterion_id},
        ).first()
        if c is None:
            raise AppError("not_found", "Criterion not found", status_code=404)


def create_answer(
    ctx: OrgContext, interview_id: UUID, payload: AnswerCreate
) -> AnswerOut:
    require_role(ctx, *_MUTATE_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        interview = _lock_interview(conn, ctx.organization_id, interview_id)
        _assert_interview_editable(interview.status, interview.assessment_status)
        _validate_answer_refs(
            conn,
            ctx.organization_id,
            interview.assessment_id,
            payload.question_id,
            payload.criterion_id,
        )
        row = conn.execute(
            text(
                """
                INSERT INTO answers (
                  organization_id, interview_id, question_id, criterion_id,
                  body, author_membership_id
                ) VALUES (
                  :org, :interview, :qid, :cid, :body, :author
                )
                RETURNING id, organization_id, interview_id, question_id, criterion_id,
                          body, author_membership_id, created_at, updated_at
                """
            ),
            {
                "org": ctx.organization_id,
                "interview": interview_id,
                "qid": payload.question_id,
                "cid": payload.criterion_id,
                "body": payload.body.strip(),
                "author": ctx.membership_id,
            },
        ).one()
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="answer.create",
            resource_type="answer",
            resource_id=row.id,
            metadata={"interview_id": str(interview_id)},
        )
        conn.commit()
    return _answer_out(row)


def list_answers(ctx: OrgContext, interview_id: UUID) -> list[AnswerOut]:
    require_role(ctx, *_READ_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        interview = conn.execute(
            text(
                "SELECT id FROM interviews WHERE id = :id AND organization_id = :org"
            ),
            {"id": interview_id, "org": ctx.organization_id},
        ).first()
        if interview is None:
            raise AppError("not_found", "Interview not found", status_code=404)
        rows = conn.execute(
            text(
                """
                SELECT id, organization_id, interview_id, question_id, criterion_id,
                       body, author_membership_id, created_at, updated_at
                FROM answers
                WHERE interview_id = :iid AND organization_id = :org
                ORDER BY created_at
                """
            ),
            {"iid": interview_id, "org": ctx.organization_id},
        ).all()
    return [_answer_out(r) for r in rows]


def update_answer(ctx: OrgContext, answer_id: UUID, payload: AnswerUpdate) -> AnswerOut:
    require_role(ctx, *_MUTATE_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        row = conn.execute(
            text(
                """
                SELECT a.id, a.interview_id, i.status AS interview_status,
                       ass.status AS assessment_status
                FROM answers a
                JOIN interviews i
                  ON i.id = a.interview_id AND i.organization_id = a.organization_id
                JOIN assessments ass
                  ON ass.id = i.assessment_id AND ass.organization_id = a.organization_id
                WHERE a.id = :id AND a.organization_id = :org
                FOR UPDATE OF a
                """
            ),
            {"id": answer_id, "org": ctx.organization_id},
        ).first()
        if row is None:
            raise AppError("not_found", "Answer not found", status_code=404)
        _assert_interview_editable(row.interview_status, row.assessment_status)
        updated = conn.execute(
            text(
                """
                UPDATE answers
                SET body = :body, updated_at = now()
                WHERE id = :id AND organization_id = :org
                RETURNING id, organization_id, interview_id, question_id, criterion_id,
                          body, author_membership_id, created_at, updated_at
                """
            ),
            {
                "id": answer_id,
                "org": ctx.organization_id,
                "body": payload.body.strip(),
            },
        ).one()
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="answer.update",
            resource_type="answer",
            resource_id=answer_id,
        )
        conn.commit()
    return _answer_out(updated)
