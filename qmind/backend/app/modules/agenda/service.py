"""Organization agenda — manual events + auto projection from reliable dates."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import text
from sqlalchemy.engine import Connection, Row

from app.audit import write_audit
from app.auth.context import OrgContext
from app.db import admin_connection, tenant_connection
from app.errors import AppError
from app.modules.agenda.schemas import (
    AgendaBoardOut,
    AgendaDaySummary,
    AgendaEventCreate,
    AgendaEventOut,
    AgendaEventUpdate,
)
from app.modules.orgs.service import require_role

_MUTATE = ("org_admin", "consultant_auditor", "quality_manager")
_READ = _MUTATE + ("process_owner", "reader")

_TYPE_LABEL = {
    "interview": "Entrevista",
    "meeting": "Reunião",
    "visit": "Visita",
    "reminder": "Lembrete",
    "milestone": "Marco",
    "deadline": "Prazo",
    "other": "Compromisso",
    "sprint_planning": "Planning da sprint",
    "daily_check_in": "Daily check-in",
    "sprint_review": "Review da sprint",
    "retrospective": "Retrospectiva",
}

_CEREMONY_EVENT_TYPES = frozenset(
    {"sprint_planning", "daily_check_in", "sprint_review", "retrospective"}
)

_ASSESSMENT_TYPE_LABEL = {
    "diagnosis": "Diagnóstico",
    "internal_audit": "Avaliação interna",
    "external_audit": "Avaliação externa",
    "certification_prep": "Preparação para certificação",
    "other": "Avaliação",
}

_ASSESSMENT_STATUS_LABEL = {
    "draft": "Em preparação",
    "planned": "Planejada",
    "in_progress": "Em andamento",
    "analysis": "Em análise",
    "actions": "Plano de ação",
    "report": "Relatório",
    "closed": "Concluída",
    "cancelled": "Cancelada",
}


def _assert_ceremony_sprint(event_type: str | None, sprint_id: UUID | None) -> None:
    """Ceremonies only make sense inside a sprint — refuse a dangling ceremony."""
    if event_type in _CEREMONY_EVENT_TYPES and sprint_id is None:
        raise AppError(
            "ceremony_sprint_required",
            "Cerimônias de sprint exigem uma sprint vinculada.",
            status_code=422,
        )


def _assessment_public_label(assessment_type: str, status: str) -> str:
    """Rótulo pt-BR para UI — nunca expor enum cru da API."""
    tipo = _ASSESSMENT_TYPE_LABEL.get(assessment_type, "Avaliação")
    situacao = _ASSESSMENT_STATUS_LABEL.get(status, status.replace("_", " "))
    return f"{tipo} · {situacao}"


def _tz(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except Exception:
        return ZoneInfo("America/Sao_Paulo")


def _org_timezone(conn: Connection, org_id: UUID) -> str:
    row = conn.execute(
        text("SELECT timezone FROM organizations WHERE id = :id"),
        {"id": org_id},
    ).first()
    return (row.timezone if row else None) or "America/Sao_Paulo"


def _day_bounds_utc(day: date, tz_name: str) -> tuple[datetime, datetime]:
    z = _tz(tz_name)
    start_local = datetime(day.year, day.month, day.day, 0, 0, 0, tzinfo=z)
    end_local = start_local + timedelta(days=1)
    return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)


def _local_date(dt: datetime, tz_name: str) -> date:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(_tz(tz_name)).date()


def _action_for(event_type: str, status: str, assessment_id: UUID | None, source_kind: str | None, source_id: UUID | None) -> tuple[str, str | None]:
    if status == "cancelled":
        return "Evento cancelado", None
    if status == "completed":
        return "Ver detalhes", f"/assessments/{assessment_id}" if assessment_id else "/assessments"
    if event_type == "interview" and source_kind == "interview" and source_id and assessment_id:
        return (
            "Iniciar entrevista",
            f"/assessments/{assessment_id}/audit-plan?startInterview={source_id}",
        )
    if event_type == "meeting" and assessment_id:
        return "Ver no plano", f"/assessments/{assessment_id}/audit-plan"
    if event_type == "deadline" and assessment_id:
        return "Revisar pendência", f"/assessments/{assessment_id}/work"
    if event_type == "milestone" and assessment_id:
        return "Abrir avaliação", f"/assessments/{assessment_id}"
    if assessment_id:
        return "Abrir avaliação", f"/assessments/{assessment_id}"
    return "Preparar atividade", "/assessments"


def _guidance_pack(event_type: str, title: str) -> tuple[str, str, str]:
    """why_it_matters, preparation, what_happens (stored in guidance if empty)."""
    packs = {
        "interview": (
            "A entrevista coleta fatos com as pessoas envolvidas no processo.",
            "Combine horário, confirme participantes e tenha perguntas em mãos.",
            f"Vai acontecer: {title}.",
        ),
        "meeting": (
            "A reunião alinha o time e evita retrabalho na avaliação.",
            "Prepare pauta curta e materiais que serão compartilhados.",
            f"Vai acontecer: {title}.",
        ),
        "visit": (
            "A visita observa o trabalho no local onde ele ocorre.",
            "Confirme acesso ao site e o que será observado.",
            f"Vai acontecer: {title}.",
        ),
        "reminder": (
            "O lembrete evita perder um passo importante da jornada.",
            "Reserve alguns minutos no horário marcado.",
            f"Lembrete: {title}.",
        ),
        "milestone": (
            "O marco marca um avanço claro da avaliação.",
            "Revise o que falta para considerar o marco concluído.",
            f"Marco: {title}.",
        ),
        "deadline": (
            "O prazo concentra atenção em uma entrega com data.",
            "Verifique o que ainda falta e quem é o responsável.",
            f"Prazo: {title}.",
        ),
        "other": (
            "Este compromisso faz parte do trabalho da avaliação.",
            "Confirme horário, pessoas e o resultado esperado.",
            f"Compromisso: {title}.",
        ),
        "sprint_planning": (
            "O planning alinha o time sobre o objetivo e as ações da sprint.",
            "Revise o backlog e confirme quem fará cada ação.",
            f"Planning: {title}.",
        ),
        "daily_check_in": (
            "O acompanhamento diário mantém visibilidade sem burocracia.",
            "Registre progresso, bloqueios e próximo passo.",
            f"Check-in: {title}.",
        ),
        "sprint_review": (
            "A review inspeciona o que foi entregue na sprint.",
            "Prepare demonstração do que foi implementado.",
            f"Review: {title}.",
        ),
        "retrospective": (
            "A retrospectiva melhora como o time trabalha na próxima sprint.",
            "Liste o que funcionou, o que atrapalhou e uma melhoria concreta.",
            f"Retrospectiva: {title}.",
        ),
    }
    return packs.get(event_type, packs["other"])


def _member_labels(org_id: UUID, ids: list[UUID]) -> dict[UUID, str]:
    if not ids:
        return {}
    with admin_connection() as conn:
        rows = conn.execute(
            text(
                """
                SELECT m.id, coalesce(nullif(u.display_name, ''), u.email) AS label
                FROM memberships m
                JOIN users u ON u.id = m.user_id
                WHERE m.organization_id = :org AND m.id = ANY(:ids)
                """
            ),
            {"org": org_id, "ids": ids},
        ).all()
    return {r.id: r.label for r in rows}


def _row_to_out(
    row: Row,
    *,
    tz_name: str,
    assessment_label: str | None,
    owner_label: str | None,
    now: datetime,
) -> AgendaEventOut:
    status = row.status
    starts = row.starts_at
    if starts.tzinfo is None:
        starts = starts.replace(tzinfo=timezone.utc)
    overdue = status == "scheduled" and starts < now
    action_label, href = _action_for(
        row.event_type, status, row.assessment_id, row.source_kind, row.source_id
    )
    why, prep, what = _guidance_pack(row.event_type, row.title)
    guidance = (row.guidance or "").strip() or what
    participants = list(row.participant_membership_ids or [])
    return AgendaEventOut(
        id=row.id,
        organization_id=row.organization_id,
        assessment_id=row.assessment_id,
        assessment_label=assessment_label,
        title=row.title,
        description=row.description or "",
        event_type=row.event_type,
        starts_at=starts,
        ends_at=row.ends_at,
        timezone=row.timezone or tz_name,
        owner_membership_id=row.owner_membership_id,
        owner_label=owner_label,
        participant_membership_ids=participants,
        location_or_link=row.location_or_link or "",
        status=status,
        guidance=guidance,
        related_action=row.related_action or "",
        source_kind=row.source_kind,
        source_id=row.source_id,
        is_auto=bool(row.is_auto),
        plan_activity_kind=getattr(row, "plan_activity_kind", None),
        sprint_id=getattr(row, "sprint_id", None),
        is_overdue=overdue,
        primary_action_label=action_label if not overdue else f"{action_label} (atrasado)",
        primary_action_href=href,
        why_it_matters=why,
        preparation=prep,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _upsert_auto(
    conn: Connection,
    ctx: OrgContext,
    *,
    source_kind: str,
    source_id: UUID,
    assessment_id: UUID | None,
    title: str,
    description: str,
    event_type: str,
    starts_at: datetime,
    ends_at: datetime | None,
    timezone_name: str,
    owner_membership_id: UUID | None,
    guidance: str,
    related_action: str,
    status: str = "scheduled",
    participant_membership_ids: list[UUID] | None = None,
    location_or_link: str = "",
    force_status: bool = False,
) -> UUID | None:
    existing = conn.execute(
        text(
            """
            SELECT id, status FROM agenda_events
            WHERE organization_id = :org
              AND is_auto = true
              AND source_kind = :sk
              AND source_id = :sid
            """
        ),
        {"org": ctx.organization_id, "sk": source_kind, "sid": source_id},
    ).first()
    parts = participant_membership_ids or []
    params = {
        "org": ctx.organization_id,
        "aid": assessment_id,
        "title": title,
        "desc": description,
        "etype": event_type,
        "starts": starts_at,
        "ends": ends_at,
        "tz": timezone_name,
        "owner": owner_membership_id,
        "parts": parts,
        "loc": location_or_link or "",
        "guidance": guidance,
        "raction": related_action,
        "sk": source_kind,
        "sid": source_id,
        "status": status,
        "uid": ctx.principal.user_id,
    }
    if existing is None:
        row = conn.execute(
            text(
                """
                INSERT INTO agenda_events (
                  organization_id, assessment_id, title, description, event_type,
                  starts_at, ends_at, timezone, owner_membership_id,
                  participant_membership_ids, location_or_link, status,
                  guidance, related_action, source_kind, source_id, is_auto,
                  created_by_user_id, updated_by_user_id
                ) VALUES (
                  :org, :aid, :title, :desc, :etype,
                  :starts, :ends, :tz, :owner,
                  :parts, :loc, :status,
                  :guidance, :raction, :sk, :sid, true,
                  :uid, :uid
                )
                RETURNING id
                """
            ),
            params,
        ).one()
        return row.id
    # Never silently delete — cancel/complete via status. Structural refresh only
    # while scheduled, unless force_status (interview cancel/complete sync).
    if existing.status != "scheduled" and not force_status:
        return existing.id
    conn.execute(
        text(
            """
            UPDATE agenda_events SET
              title = :title,
              description = :desc,
              starts_at = :starts,
              ends_at = :ends,
              assessment_id = :aid,
              owner_membership_id = :owner,
              participant_membership_ids = :parts,
              location_or_link = :loc,
              guidance = :guidance,
              related_action = :raction,
              status = CASE
                WHEN :force THEN :status
                ELSE status
              END,
              updated_at = now(),
              updated_by_user_id = :uid
            WHERE id = :id AND organization_id = :org
            """
        ),
        {**params, "id": existing.id, "force": force_status},
    )
    return existing.id


def _interview_agenda_status(interview_status: str) -> str:
    if interview_status == "completed":
        return "completed"
    if interview_status == "cancelled":
        return "cancelled"
    return "scheduled"


def sync_interview_agenda_event(
    conn: Connection,
    ctx: OrgContext,
    interview_row,
    *,
    timezone_name: str | None = None,
) -> UUID | None:
    """Idempotent Interview → AgendaEvent projection (source_kind=interview)."""
    starts = interview_row.scheduled_at or interview_row.conducted_at
    if starts is None:
        # No reliable datetime yet — cancel prior auto event if any (keep row).
        existing = conn.execute(
            text(
                """
                SELECT id, status FROM agenda_events
                WHERE organization_id = :org
                  AND is_auto = true
                  AND source_kind = 'interview'
                  AND source_id = :sid
                """
            ),
            {"org": ctx.organization_id, "sid": interview_row.id},
        ).first()
        if existing and existing.status == "scheduled":
            conn.execute(
                text(
                    """
                    UPDATE agenda_events
                    SET status = 'cancelled', updated_at = now(),
                        updated_by_user_id = :uid
                    WHERE id = :id AND organization_id = :org
                    """
                ),
                {
                    "id": existing.id,
                    "org": ctx.organization_id,
                    "uid": ctx.principal.user_id,
                },
            )
            return existing.id
        return existing.id if existing else None

    tz_name = timezone_name or _org_timezone(conn, ctx.organization_id)
    duration = interview_row.duration_minutes or 60
    ends = starts + timedelta(minutes=int(duration))
    title = (getattr(interview_row, "title", None) or "").strip() or "Entrevista da avaliação"
    loc_parts = [
        (getattr(interview_row, "location", None) or "").strip(),
        (getattr(interview_row, "remote_link", None) or "").strip(),
    ]
    location = " | ".join(p for p in loc_parts if p)
    prep = (getattr(interview_row, "preparation", None) or "").strip()
    objective = (getattr(interview_row, "objective", None) or "").strip()
    process = (getattr(interview_row, "process_name", None) or "").strip()
    desc_bits = [f"Situação: {interview_row.status}"]
    if process:
        desc_bits.insert(0, f"Processo: {process}")
    if interview_row.mode:
        desc_bits.append(f"Modo: {interview_row.mode}")
    why, default_prep, what = _guidance_pack("interview", title)
    owner = (
        getattr(interview_row, "interviewer_membership_id", None)
        or getattr(interview_row, "lead_membership_id", None)
    )
    participants = list(getattr(interview_row, "participant_membership_ids", None) or [])
    agenda_status = _interview_agenda_status(interview_row.status)
    return _upsert_auto(
        conn,
        ctx,
        source_kind="interview",
        source_id=interview_row.id,
        assessment_id=interview_row.assessment_id,
        title=title[:200],
        description="; ".join(desc_bits),
        event_type="interview",
        starts_at=starts,
        ends_at=ends,
        timezone_name=tz_name,
        owner_membership_id=owner,
        guidance=f"{what} {(prep or default_prep)} {objective}".strip(),
        related_action="start_interview",
        status=agenda_status,
        participant_membership_ids=participants,
        location_or_link=location[:500],
        force_status=True,
    )


def sync_auto_events(ctx: OrgContext, *, require_mutate: bool = True) -> int:
    """Project domain dates with reliable timestamps into agenda_events (idempotent)."""
    if require_mutate:
        require_role(ctx, *_MUTATE)
    with tenant_connection(ctx.organization_id) as conn:
        tz_name = _org_timezone(conn, ctx.organization_id)
        n = 0

        interviews = conn.execute(
            text(
                """
                SELECT i.id, i.assessment_id, i.conducted_at, i.scheduled_at,
                       i.status, i.mode, i.title, i.objective, i.process_name,
                       i.interviewer_membership_id, i.participant_membership_ids,
                       i.duration_minutes, i.location, i.remote_link, i.preparation,
                       a.lead_membership_id
                FROM interviews i
                JOIN assessments a ON a.id = i.assessment_id
                WHERE i.organization_id = :org
                  AND (
                    i.scheduled_at IS NOT NULL
                    OR i.conducted_at IS NOT NULL
                    OR i.status IN ('cancelled', 'completed')
                  )
                """
            ),
            {"org": ctx.organization_id},
        ).all()
        for i in interviews:
            sync_interview_agenda_event(conn, ctx, i, timezone_name=tz_name)
            n += 1

        actions = conn.execute(
            text(
                """
                SELECT ai.id, ai.due_at, ai.description, ai.owner_membership_id,
                       ai.status, ap.assessment_id
                FROM action_items ai
                JOIN action_plans ap ON ap.id = ai.action_plan_id
                WHERE ai.organization_id = :org
                  AND ai.status NOT IN ('done', 'cancelled', 'ineffective_closed')
                """
            ),
            {"org": ctx.organization_id},
        ).all()
        for a in actions:
            if a.due_at is None:
                continue
            title = (a.description or "Prazo de ação").strip()[:120]
            why, prep, what = _guidance_pack("deadline", title)
            _upsert_auto(
                conn,
                ctx,
                source_kind="action_item",
                source_id=a.id,
                assessment_id=a.assessment_id,
                title=f"Prazo: {title}",
                description="Prazo de item do plano de ação.",
                event_type="deadline",
                starts_at=a.due_at,
                ends_at=None,
                timezone_name=tz_name,
                owner_membership_id=a.owner_membership_id,
                guidance=f"{what} {prep}",
                related_action="review_action_item",
            )
            n += 1

        assessments = conn.execute(
            text(
                """
                SELECT id, started_at, closed_at, lead_membership_id, type, status
                FROM assessments
                WHERE organization_id = :org
                """
            ),
            {"org": ctx.organization_id},
        ).all()
        for a in assessments:
            if a.started_at:
                _upsert_auto(
                    conn,
                    ctx,
                    source_kind="assessment_started",
                    source_id=a.id,
                    assessment_id=a.id,
                    title="Início da avaliação",
                    description="Marco automático: avaliação iniciada.",
                    event_type="milestone",
                    starts_at=a.started_at,
                    ends_at=None,
                    timezone_name=tz_name,
                    owner_membership_id=a.lead_membership_id,
                    guidance="A execução em campo começou. Continue entrevistas e evidências.",
                    related_action="open_assessment",
                )
                n += 1
            if a.closed_at:
                _upsert_auto(
                    conn,
                    ctx,
                    source_kind="assessment_closed",
                    source_id=a.id,
                    assessment_id=a.id,
                    title="Conclusão da avaliação",
                    description="Marco automático: avaliação encerrada.",
                    event_type="milestone",
                    starts_at=a.closed_at,
                    ends_at=None,
                    timezone_name=tz_name,
                    owner_membership_id=a.lead_membership_id,
                    guidance="A avaliação foi concluída. Use o mapa para consultar o histórico.",
                    related_action="open_assessment",
                )
                n += 1

        reports = conn.execute(
            text(
                """
                SELECT id, assessment_id, published_at
                FROM reports
                WHERE organization_id = :org AND published_at IS NOT NULL
                """
            ),
            {"org": ctx.organization_id},
        ).all()
        for r in reports:
            _upsert_auto(
                conn,
                ctx,
                source_kind="report_published",
                source_id=r.id,
                assessment_id=r.assessment_id,
                title="Publicação do relatório",
                description="Marco automático: relatório publicado.",
                event_type="milestone",
                starts_at=r.published_at,
                ends_at=None,
                timezone_name=tz_name,
                owner_membership_id=None,
                guidance="O relatório foi publicado. Compartilhe com a organização.",
                related_action="open_report",
            )
            n += 1

        conn.commit()
        return n


def _fetch_events(
    conn: Connection,
    org_id: UUID,
    start_utc: datetime,
    end_utc: datetime,
    *,
    include_overdue_before: datetime | None = None,
) -> list[Row]:
    if include_overdue_before:
        return list(
            conn.execute(
                text(
                    """
                    SELECT *
                    FROM agenda_events
                    WHERE organization_id = :org
                      AND status <> 'cancelled'
                      AND (
                        (starts_at >= :start AND starts_at < :end)
                        OR (status = 'scheduled' AND starts_at < :now)
                      )
                    ORDER BY starts_at ASC
                    """
                ),
                {
                    "org": org_id,
                    "start": start_utc,
                    "end": end_utc,
                    "now": include_overdue_before,
                },
            ).all()
        )
    return list(
        conn.execute(
            text(
                """
                SELECT *
                FROM agenda_events
                WHERE organization_id = :org
                  AND status <> 'cancelled'
                  AND starts_at >= :start AND starts_at < :end
                ORDER BY starts_at ASC
                """
            ),
            {"org": org_id, "start": start_utc, "end": end_utc},
        ).all()
    )


def _enrich(ctx: OrgContext, rows: list[Row], tz_name: str) -> list[AgendaEventOut]:
    now = datetime.now(timezone.utc)
    assessment_ids = list({r.assessment_id for r in rows if r.assessment_id})
    labels: dict[UUID, str] = {}
    if assessment_ids:
        with admin_connection() as conn:
            arows = conn.execute(
                text(
                    """
                    SELECT id, type, status FROM assessments
                    WHERE organization_id = :org AND id = ANY(:ids)
                    """
                ),
                {"org": ctx.organization_id, "ids": assessment_ids},
            ).all()
            for a in arows:
                labels[a.id] = _assessment_public_label(a.type, a.status)

    owner_ids = list({r.owner_membership_id for r in rows if r.owner_membership_id})
    owners = _member_labels(ctx.organization_id, owner_ids)
    return [
        _row_to_out(
            r,
            tz_name=tz_name,
            assessment_label=labels.get(r.assessment_id) if r.assessment_id else None,
            owner_label=owners.get(r.owner_membership_id) if r.owner_membership_id else None,
            now=now,
        )
        for r in rows
    ]


def get_board(ctx: OrgContext, selected: date | None = None) -> AgendaBoardOut:
    require_role(ctx, *_READ)
    # Best-effort projection of reliable domain dates (idempotent).
    try:
        sync_auto_events(ctx, require_mutate=False)
    except Exception:
        pass

    with tenant_connection(ctx.organization_id) as conn:
        tz_name = _org_timezone(conn, ctx.organization_id)
        z = _tz(tz_name)
        today_local = datetime.now(z).date()
        sel = selected or today_local
        month_start = date(sel.year, sel.month, 1)
        if sel.month == 12:
            month_end = date(sel.year + 1, 1, 1)
        else:
            month_end = date(sel.year, sel.month + 1, 1)

        m_start, _ = _day_bounds_utc(month_start, tz_name)
        _, m_end = _day_bounds_utc(month_end - timedelta(days=1), tz_name)
        # extend end to first of next month
        m_end = _day_bounds_utc(month_end, tz_name)[0]

        month_rows = _fetch_events(conn, ctx.organization_id, m_start, m_end)
        t_start, t_end = _day_bounds_utc(today_local, tz_name)
        s_start, s_end = _day_bounds_utc(sel, tz_name)
        today_rows = _fetch_events(conn, ctx.organization_id, t_start, t_end)
        sel_rows = _fetch_events(conn, ctx.organization_id, s_start, s_end)
        overdue_rows = conn.execute(
            text(
                """
                SELECT * FROM agenda_events
                WHERE organization_id = :org
                  AND status = 'scheduled'
                  AND starts_at < :now
                ORDER BY starts_at ASC
                LIMIT 20
                """
            ),
            {"org": ctx.organization_id, "now": datetime.now(timezone.utc)},
        ).all()

        in_progress = conn.execute(
            text(
                """
                SELECT id, type, status, started_at
                FROM assessments
                WHERE organization_id = :org
                  AND status IN ('planned', 'in_progress', 'analysis', 'actions', 'report')
                ORDER BY updated_at DESC
                LIMIT 8
                """
            ),
            {"org": ctx.organization_id},
        ).all()

    today_out = _enrich(ctx, today_rows, tz_name)
    sel_out = _enrich(ctx, sel_rows, tz_name)
    overdue_out = _enrich(ctx, overdue_rows, tz_name)
    month_out = _enrich(ctx, month_rows, tz_name)

    markers: dict[str, AgendaDaySummary] = {}
    for ev in month_out:
        d = _local_date(ev.starts_at, tz_name).isoformat()
        cur = markers.get(d) or AgendaDaySummary(date=d, count=0, has_overdue=False)
        markers[d] = AgendaDaySummary(
            date=d,
            count=cur.count + 1,
            has_overdue=cur.has_overdue or ev.is_overdue,
        )

    upcoming = sorted(
        [e for e in (today_out + overdue_out + sel_out) if e.status == "scheduled"],
        key=lambda e: e.starts_at,
    )
    next_up = upcoming[0] if upcoming else None

    return AgendaBoardOut(
        timezone=tz_name,
        selected_date=sel.isoformat(),
        next_up=next_up,
        today=today_out,
        selected_day=sel_out,
        overdue=overdue_out,
        in_progress_assessments=[
            {
                "id": str(a.id),
                "label": _assessment_public_label(a.type, a.status),
                "href": f"/assessments/{a.id}",
            }
            for a in in_progress
        ],
        month_markers=sorted(markers.values(), key=lambda m: m.date),
    )


def list_events(ctx: OrgContext, day: date) -> list[AgendaEventOut]:
    require_role(ctx, *_READ)
    with tenant_connection(ctx.organization_id) as conn:
        tz_name = _org_timezone(conn, ctx.organization_id)
        start, end = _day_bounds_utc(day, tz_name)
        rows = _fetch_events(conn, ctx.organization_id, start, end)
    return _enrich(ctx, rows, tz_name)


def get_event(ctx: OrgContext, event_id: UUID) -> AgendaEventOut:
    require_role(ctx, *_READ)
    with tenant_connection(ctx.organization_id) as conn:
        tz_name = _org_timezone(conn, ctx.organization_id)
        row = conn.execute(
            text(
                """
                SELECT * FROM agenda_events
                WHERE id = :id AND organization_id = :org
                """
            ),
            {"id": event_id, "org": ctx.organization_id},
        ).first()
        if row is None:
            raise AppError("not_found", "Evento não encontrado", status_code=404)
    return _enrich(ctx, [row], tz_name)[0]


def create_event(ctx: OrgContext, payload: AgendaEventCreate) -> AgendaEventOut:
    require_role(ctx, *_MUTATE)
    _assert_ceremony_sprint(payload.event_type, payload.sprint_id)
    with tenant_connection(ctx.organization_id) as conn:
        tz_name = payload.timezone or _org_timezone(conn, ctx.organization_id)
        if payload.assessment_id:
            ok = conn.execute(
                text(
                    """
                    SELECT 1 FROM assessments
                    WHERE id = :id AND organization_id = :org
                    """
                ),
                {"id": payload.assessment_id, "org": ctx.organization_id},
            ).first()
            if not ok:
                raise AppError("invalid_assessment", "Avaliação inválida nesta organização", status_code=400)
        if payload.sprint_id:
            ok = conn.execute(
                text(
                    """
                    SELECT 1 FROM agile_sprints
                    WHERE id = :id AND organization_id = :org
                    """
                ),
                {"id": payload.sprint_id, "org": ctx.organization_id},
            ).first()
            if not ok:
                raise AppError("invalid_sprint", "Sprint inválida nesta organização", status_code=400)

        row = conn.execute(
            text(
                """
                INSERT INTO agenda_events (
                  organization_id, assessment_id, title, description, event_type,
                  starts_at, ends_at, timezone, owner_membership_id,
                  participant_membership_ids, location_or_link, status,
                  guidance, related_action, plan_activity_kind, sprint_id, is_auto,
                  created_by_user_id, updated_by_user_id
                ) VALUES (
                  :org, :aid, :title, :desc, :etype,
                  :starts, :ends, :tz, :owner,
                  :parts, :loc, 'scheduled',
                  :guidance, :raction, :pak, :sid, false,
                  :uid, :uid
                )
                RETURNING *
                """
            ),
            {
                "org": ctx.organization_id,
                "aid": payload.assessment_id,
                "title": payload.title.strip(),
                "desc": payload.description or "",
                "etype": payload.event_type,
                "starts": payload.starts_at,
                "ends": payload.ends_at,
                "tz": tz_name,
                "owner": payload.owner_membership_id,
                "parts": payload.participant_membership_ids or [],
                "loc": payload.location_or_link or "",
                "guidance": payload.guidance or "",
                "raction": payload.related_action or "",
                "pak": payload.plan_activity_kind,
                "sid": payload.sprint_id,
                "uid": ctx.principal.user_id,
            },
        ).one()
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="agenda.event.create",
            resource_type="agenda_event",
            resource_id=row.id,
            metadata={
                "event_type": payload.event_type,
                "plan_activity_kind": payload.plan_activity_kind,
            },
        )
        conn.commit()
        tz_name = _org_timezone(conn, ctx.organization_id)
    return _enrich(ctx, [row], tz_name)[0]


def update_event(ctx: OrgContext, event_id: UUID, payload: AgendaEventUpdate) -> AgendaEventOut:
    require_role(ctx, *_MUTATE)
    with tenant_connection(ctx.organization_id) as conn:
        cur = conn.execute(
            text(
                """
                SELECT * FROM agenda_events
                WHERE id = :id AND organization_id = :org
                FOR UPDATE
                """
            ),
            {"id": event_id, "org": ctx.organization_id},
        ).first()
        if cur is None:
            raise AppError("not_found", "Evento não encontrado", status_code=404)
        if cur.is_auto:
            structural = any(
                v is not None
                for v in (
                    payload.title,
                    payload.description,
                    payload.event_type,
                    payload.starts_at,
                    payload.ends_at,
                    payload.timezone,
                    payload.owner_membership_id,
                    payload.participant_membership_ids,
                    payload.location_or_link,
                    payload.guidance,
                    payload.related_action,
                    payload.assessment_id,
                )
            )
            if structural:
                raise AppError(
                    "auto_event_readonly",
                    "Eventos automáticos não podem ser editados — conclua ou cancele.",
                    status_code=409,
                )
            if payload.status is None:
                raise AppError(
                    "auto_event_readonly",
                    "Informe concluir ou cancelar para este evento automático.",
                    status_code=409,
                )

        fields = {
            "title": payload.title if payload.title is not None else cur.title,
            "description": payload.description if payload.description is not None else cur.description,
            "event_type": payload.event_type if payload.event_type is not None else cur.event_type,
            "starts_at": payload.starts_at if payload.starts_at is not None else cur.starts_at,
            "ends_at": payload.ends_at if payload.ends_at is not None else cur.ends_at,
            "timezone": payload.timezone if payload.timezone is not None else cur.timezone,
            "owner_membership_id": (
                payload.owner_membership_id
                if payload.owner_membership_id is not None
                else cur.owner_membership_id
            ),
            "participant_membership_ids": (
                payload.participant_membership_ids
                if payload.participant_membership_ids is not None
                else list(cur.participant_membership_ids or [])
            ),
            "location_or_link": (
                payload.location_or_link
                if payload.location_or_link is not None
                else cur.location_or_link
            ),
            "guidance": payload.guidance if payload.guidance is not None else cur.guidance,
            "related_action": (
                payload.related_action if payload.related_action is not None else cur.related_action
            ),
            "assessment_id": (
                payload.assessment_id if payload.assessment_id is not None else cur.assessment_id
            ),
            "status": payload.status if payload.status is not None else cur.status,
            "plan_activity_kind": (
                payload.plan_activity_kind
                if payload.plan_activity_kind is not None
                else getattr(cur, "plan_activity_kind", None)
            ),
            "sprint_id": (
                payload.sprint_id if payload.sprint_id is not None else getattr(cur, "sprint_id", None)
            ),
        }

        _assert_ceremony_sprint(fields["event_type"], fields["sprint_id"])

        if fields["sprint_id"]:
            ok = conn.execute(
                text(
                    """
                    SELECT 1 FROM agile_sprints
                    WHERE id = :id AND organization_id = :org
                    """
                ),
                {"id": fields["sprint_id"], "org": ctx.organization_id},
            ).first()
            if not ok:
                raise AppError("invalid_sprint", "Sprint inválida nesta organização", status_code=400)

        row = conn.execute(
            text(
                """
                UPDATE agenda_events SET
                  title = :title,
                  description = :description,
                  event_type = :event_type,
                  starts_at = :starts_at,
                  ends_at = :ends_at,
                  timezone = :timezone,
                  owner_membership_id = :owner_membership_id,
                  participant_membership_ids = :participant_membership_ids,
                  location_or_link = :location_or_link,
                  guidance = :guidance,
                  related_action = :related_action,
                  assessment_id = :assessment_id,
                  status = :status,
                  plan_activity_kind = :plan_activity_kind,
                  sprint_id = :sprint_id,
                  updated_at = now(),
                  updated_by_user_id = :uid
                WHERE id = :id AND organization_id = :org
                RETURNING *
                """
            ),
            {**fields, "id": event_id, "org": ctx.organization_id, "uid": ctx.principal.user_id},
        ).one()

        action = "agenda.event.update"
        if payload.status == "completed":
            action = "agenda.event.complete"
        elif payload.status == "cancelled":
            action = "agenda.event.cancel"

        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action=action,
            resource_type="agenda_event",
            resource_id=event_id,
            from_status=cur.status,
            to_status=row.status,
        )
        conn.commit()
        tz_name = row.timezone or _org_timezone(conn, ctx.organization_id)
    return _enrich(ctx, [row], tz_name)[0]
