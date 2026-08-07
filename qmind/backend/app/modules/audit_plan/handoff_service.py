"""Planning → Field handoff: conclude planning, opening meeting, start field."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.audit import write_audit
from app.auth.context import OrgContext
from app.db import tenant_connection
from app.errors import AppError
from app.modules.assessments import service as assessment_service
from app.modules.audit_plan import schedule_service, service as plan_service
from app.modules.audit_plan.handoff_schemas import (
    ConcludePlanningIn,
    ConcludePlanningOut,
    OpeningMeetingOut,
    OpeningMeetingPerformIn,
    OpeningMeetingWaiveIn,
    StartFieldIn,
    StartFieldOut,
)
from app.modules.audit_plan.schemas import AuditPlanReadyIn
from app.modules.audit_plan.schedule_schemas import AuditPlanScheduleOut
from app.modules.orgs.service import require_role

_MUTATE = ("org_admin", "consultant_auditor", "quality_manager")


def _opening_event(conn: Connection, org_id: UUID, assessment_id: UUID):
    return conn.execute(
        text(
            """
            SELECT id, status, starts_at, waiver_reason, guidance, description,
                   participant_membership_ids, owner_membership_id
            FROM agenda_events
            WHERE organization_id = :org
              AND assessment_id = :aid
              AND plan_activity_kind = 'opening_meeting'
              AND status <> 'cancelled'
            ORDER BY
              CASE status
                WHEN 'completed' THEN 0
                WHEN 'waived' THEN 1
                ELSE 2
              END,
              starts_at
            LIMIT 1
            """
        ),
        {"org": org_id, "aid": assessment_id},
    ).first()


def _optional_plan_row(conn: Connection, org_id: UUID, assessment_id: UUID):
    return conn.execute(
        text(
            """
            SELECT id, plan_status, updated_at
            FROM assessment_audit_plans
            WHERE assessment_id = :aid AND organization_id = :org
            FOR UPDATE
            """
        ),
        {"aid": assessment_id, "org": org_id},
    ).first()


def assert_plan_ready_for_assessment_plan(
    conn: Connection,
    org_id: UUID,
    assessment_id: UUID,
    *,
    require_plan: bool = False,
) -> None:
    """Gate for draft → planned: when a plan exists (or is required), it must be ready."""
    row = _optional_plan_row(conn, org_id, assessment_id)
    if row is None:
        if require_plan:
            raise AppError(
                "plan_missing",
                "Elabore o Plano da Auditoria antes de concluir o planejamento",
                status_code=422,
            )
        return
    if row.plan_status == "amended":
        raise AppError(
            "plan_amended_requires_reconfirm",
            "Há uma emenda pendente no plano. Revise, reconfirme (Concluir Plano) e tente de novo",
            status_code=422,
        )
    if row.plan_status != "ready":
        raise AppError(
            "plan_not_ready",
            "O Plano da Auditoria precisa estar pronto (Concluir Plano) antes de concluir o planejamento",
            status_code=422,
        )


def assert_plan_ready_for_field(
    conn: Connection,
    org_id: UUID,
    assessment_id: UUID,
    *,
    require_plan: bool = False,
) -> None:
    """Gate for planned → in_progress when the audit plan path is in use."""
    row = _optional_plan_row(conn, org_id, assessment_id)
    if row is None:
        if require_plan:
            raise AppError(
                "plan_missing",
                "Elabore o Plano da Auditoria antes de iniciar o campo",
                status_code=422,
            )
        return
    if row.plan_status == "amended":
        raise AppError(
            "plan_amended_requires_reconfirm",
            "Emenda pendente: revise o plano, conclua novamente e só então inicie o campo",
            status_code=422,
        )
    if row.plan_status != "ready":
        raise AppError(
            "plan_not_ready",
            "O Plano da Auditoria precisa estar ready para iniciar a execução em campo",
            status_code=422,
        )

    opening = _opening_event(conn, org_id, assessment_id)
    if opening is None:
        raise AppError(
            "opening_meeting_required",
            "Programe a reunião de abertura antes de iniciar o campo",
            status_code=422,
        )
    if opening.status not in ("completed", "waived"):
        raise AppError(
            "opening_meeting_required",
            "Registre a reunião de abertura como realizada ou dispense-a com justificativa",
            status_code=422,
        )


def conclude_planning(
    ctx: OrgContext, assessment_id: UUID, payload: ConcludePlanningIn | None = None
) -> ConcludePlanningOut:
    """Mark plan ready (if needed) + official draft → planned, atomically."""
    require_role(ctx, *_MUTATE)
    payload = payload or ConcludePlanningIn()

    # Ensure plan exists / derived
    plan = plan_service.get_or_create(ctx, assessment_id)

    if plan.plan_status == "amended":
        raise AppError(
            "plan_amended_requires_reconfirm",
            "Há emenda pendente. Use «Concluir Plano» para reconfirmar antes de concluir o planejamento",
            status_code=422,
        )

    if plan.plan_status != "ready":
        if not payload.mark_ready_if_needed:
            raise AppError(
                "plan_not_ready",
                "Conclua o Plano (checklist) antes de concluir o planejamento",
                status_code=422,
            )
        if not plan.readiness.ready:
            raise AppError(
                "validation_error",
                "Plano incompleto: " + "; ".join(plan.readiness.blockers or ["checklist pendente"]),
                status_code=422,
            )
        plan = plan_service.mark_ready(
            ctx,
            assessment_id,
            AuditPlanReadyIn(expected_updated_at=payload.expected_updated_at or plan.updated_at),
        )

    # Pre-check with require_plan (transition_plan also gates when plan exists)
    with tenant_connection(ctx.organization_id) as conn:
        row = assessment_service._lock_assessment(conn, ctx.organization_id, assessment_id)
        assert_plan_ready_for_assessment_plan(
            conn, ctx.organization_id, assessment_id, require_plan=True
        )
        if row.status not in ("draft", "planned"):
            raise AppError(
                "invalid_transition",
                f"Concluir planejamento exige avaliação em draft (atual={row.status})",
                status_code=409,
            )
        conn.commit()

    transition = assessment_service.transition_plan(ctx, assessment_id)
    plan = plan_service.get_or_create(ctx, assessment_id)

    return ConcludePlanningOut(plan=plan, transition=transition)


def start_field_execution(
    ctx: OrgContext, assessment_id: UUID, payload: StartFieldIn | None = None
) -> StartFieldOut:
    """Official planned → in_progress with handoff guards (always requires plan path)."""
    require_role(ctx, *_MUTATE)
    _ = payload or StartFieldIn()
    with tenant_connection(ctx.organization_id) as conn:
        assessment_service._lock_assessment(conn, ctx.organization_id, assessment_id)
        assert_plan_ready_for_field(
            conn, ctx.organization_id, assessment_id, require_plan=True
        )
        conn.commit()
    transition = assessment_service.transition_start(ctx, assessment_id)
    return StartFieldOut(
        transition=transition,
        redirect_href=f"/assessments/{assessment_id}/work",
    )


def perform_opening_meeting(
    ctx: OrgContext,
    assessment_id: UUID,
    event_id: UUID,
    payload: OpeningMeetingPerformIn,
) -> OpeningMeetingOut:
    require_role(ctx, *_MUTATE)
    with tenant_connection(ctx.organization_id) as conn:
        assessment_service._lock_assessment(conn, ctx.organization_id, assessment_id)
        cur = conn.execute(
            text(
                """
                SELECT id, status, plan_activity_kind, starts_at, guidance, description,
                       participant_membership_ids
                FROM agenda_events
                WHERE id = :id AND organization_id = :org AND assessment_id = :aid
                FOR UPDATE
                """
            ),
            {"id": event_id, "org": ctx.organization_id, "aid": assessment_id},
        ).first()
        if cur is None or cur.plan_activity_kind != "opening_meeting":
            raise AppError("not_found", "Reunião de abertura não encontrada", status_code=404)
        if cur.status == "waived":
            raise AppError(
                "conflict",
                "Esta reunião foi dispensada; remova a dispensa antes de registrar realização",
                status_code=409,
            )
        if cur.status == "completed":
            # Idempotent
            conn.commit()
            return OpeningMeetingOut(
                event_id=event_id,
                status="completed",
                message="Reunião de abertura já estava registrada como realizada",
            )

        notes_parts = []
        if payload.observations.strip():
            notes_parts.append(f"Observações: {payload.observations.strip()}")
        if payload.adjustments.strip():
            notes_parts.append(f"Ajustes: {payload.adjustments.strip()}")
        if payload.pendings.strip():
            notes_parts.append(f"Pendências: {payload.pendings.strip()}")
        guidance = "\n".join(notes_parts) if notes_parts else (cur.guidance or "")

        starts = payload.actual_starts_at or cur.starts_at
        participants = (
            payload.participant_membership_ids
            if payload.participant_membership_ids is not None
            else list(cur.participant_membership_ids or [])
        )
        if participants:
            schedule_service._assert_memberships(conn, ctx.organization_id, participants)

        conn.execute(
            text(
                """
                UPDATE agenda_events SET
                  status = 'completed',
                  starts_at = :starts,
                  participant_membership_ids = :parts,
                  guidance = :guidance,
                  waiver_reason = '',
                  updated_at = now(),
                  updated_by_user_id = :uid
                WHERE id = :id AND organization_id = :org
                """
            ),
            {
                "id": event_id,
                "org": ctx.organization_id,
                "starts": starts,
                "parts": participants,
                "guidance": guidance,
                "uid": ctx.principal.user_id,
            },
        )
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="audit_plan.opening_meeting.perform",
            resource_type="agenda_event",
            resource_id=event_id,
            from_status=cur.status,
            to_status="completed",
            metadata={"assessment_id": str(assessment_id)},
        )
        conn.commit()
    return OpeningMeetingOut(
        event_id=event_id,
        status="completed",
        message="Reunião de abertura registrada como realizada",
    )


def waive_opening_meeting(
    ctx: OrgContext,
    assessment_id: UUID,
    event_id: UUID,
    payload: OpeningMeetingWaiveIn,
) -> OpeningMeetingOut:
    require_role(ctx, *_MUTATE)
    reason = payload.waiver_reason.strip()
    if len(reason) < 8:
        raise AppError(
            "validation_error",
            "Justificativa da dispensa é obrigatória (mínimo 8 caracteres)",
            status_code=422,
        )

    with tenant_connection(ctx.organization_id) as conn:
        assessment_service._lock_assessment(conn, ctx.organization_id, assessment_id)
        cur = conn.execute(
            text(
                """
                SELECT id, status, plan_activity_kind
                FROM agenda_events
                WHERE id = :id AND organization_id = :org AND assessment_id = :aid
                FOR UPDATE
                """
            ),
            {"id": event_id, "org": ctx.organization_id, "aid": assessment_id},
        ).first()
        if cur is None or cur.plan_activity_kind != "opening_meeting":
            raise AppError("not_found", "Reunião de abertura não encontrada", status_code=404)
        if cur.status == "waived":
            conn.commit()
            return OpeningMeetingOut(
                event_id=event_id,
                status="waived",
                message="Reunião de abertura já estava dispensada",
            )
        if cur.status == "completed":
            raise AppError(
                "conflict",
                "Reunião já realizada — não é possível dispensar",
                status_code=409,
            )

        conn.execute(
            text(
                """
                UPDATE agenda_events SET
                  status = 'waived',
                  waiver_reason = :reason,
                  updated_at = now(),
                  updated_by_user_id = :uid
                WHERE id = :id AND organization_id = :org
                """
            ),
            {
                "id": event_id,
                "org": ctx.organization_id,
                "reason": reason,
                "uid": ctx.principal.user_id,
            },
        )
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="audit_plan.opening_meeting.waive",
            resource_type="agenda_event",
            resource_id=event_id,
            from_status=cur.status,
            to_status="waived",
            metadata={
                "assessment_id": str(assessment_id),
                "waiver_reason": reason,
            },
        )
        conn.commit()
    return OpeningMeetingOut(
        event_id=event_id,
        status="waived",
        message="Reunião de abertura dispensada com justificativa",
    )


def opening_meeting_state(schedule: AuditPlanScheduleOut) -> dict:
    opening = next(
        (
            i
            for i in schedule.items
            if i.plan_activity_kind == "opening_meeting" and i.status != "cancelled"
        ),
        None,
    )
    if opening is None:
        return {"present": False, "satisfied": False, "status": None, "event_id": None}
    return {
        "present": True,
        "satisfied": opening.status in ("completed", "waived"),
        "status": opening.status,
        "event_id": opening.id,
    }
