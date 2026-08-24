"""Ceremony records linked to agenda events (ISOI-007)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import text

from app.audit import write_audit
from app.auth.context import OrgContext
from app.db import tenant_connection
from app.errors import AppError
from app.modules.agile.schemas import CeremonyRecordCreate, CeremonyRecordOut
from app.modules.orgs.service import require_role

_MUTATE = (
    "org_admin",
    "quality_manager",
    "process_owner",
    "action_owner",
    "consultant_auditor",
)
_READ = _MUTATE + ("reader",)

_CEREMONY_EVENT_TYPES = frozenset(
    {"sprint_planning", "daily_check_in", "sprint_review", "retrospective"}
)


def _require_mutate(ctx: OrgContext) -> None:
    require_role(ctx, *_MUTATE)


def _require_read(ctx: OrgContext) -> None:
    require_role(ctx, *_READ)


def _record_out(row) -> CeremonyRecordOut:
    return CeremonyRecordOut(
        id=row.id,
        organization_id=row.organization_id,
        sprint_id=row.sprint_id,
        agenda_event_id=row.agenda_event_id,
        ceremony_type=row.ceremony_type,
        summary=row.summary or "",
        decisions=row.decisions or "",
        follow_up=row.follow_up or "",
        recorded_by=row.recorded_by,
        recorded_at=row.recorded_at,
        revision=row.revision,
    )


def create_ceremony_record(
    ctx: OrgContext, sprint_id: UUID, payload: CeremonyRecordCreate
) -> CeremonyRecordOut:
    _require_mutate(ctx)
    with tenant_connection(ctx.organization_id) as conn:
        sprint = conn.execute(
            text(
                """
                SELECT id FROM agile_sprints
                WHERE id = :id AND organization_id = :org
                """
            ),
            {"id": sprint_id, "org": ctx.organization_id},
        ).first()
        if sprint is None:
            raise AppError("not_found", "Sprint not found", status_code=404)
        event = conn.execute(
            text(
                """
                SELECT id, event_type, sprint_id FROM agenda_events
                WHERE id = :id AND organization_id = :org
                """
            ),
            {"id": payload.agenda_event_id, "org": ctx.organization_id},
        ).first()
        if event is None:
            raise AppError("not_found", "Agenda event not found", status_code=404)
        if event.event_type not in _CEREMONY_EVENT_TYPES:
            raise AppError(
                "invalid_ceremony_event",
                "Agenda event must be a ceremony type",
                status_code=422,
            )
        if event.sprint_id is None or event.sprint_id != sprint_id:
            raise AppError(
                "ceremony_sprint_mismatch",
                "Agenda event must be bound to this sprint",
                status_code=409,
            )
        if payload.ceremony_type != event.event_type:
            raise AppError(
                "ceremony_type_mismatch",
                "ceremony_type must match agenda event_type",
                status_code=422,
            )
        prev = conn.execute(
            text(
                """
                SELECT coalesce(max(revision), 0) AS rev
                FROM agile_ceremony_records
                WHERE sprint_id = :sid AND agenda_event_id = :eid
                  AND organization_id = :org AND ceremony_type = :ctype
                """
            ),
            {
                "sid": sprint_id,
                "eid": payload.agenda_event_id,
                "org": ctx.organization_id,
                "ctype": payload.ceremony_type,
            },
        ).one()
        revision = int(prev.rev) + 1
        row = conn.execute(
            text(
                """
                INSERT INTO agile_ceremony_records (
                  organization_id, sprint_id, agenda_event_id, ceremony_type,
                  summary, decisions, follow_up, recorded_by, revision
                ) VALUES (
                  :org, :sid, :eid, :ctype, :summary, :decisions, :follow_up, :uid, :rev
                )
                RETURNING *
                """
            ),
            {
                "org": ctx.organization_id,
                "sid": sprint_id,
                "eid": payload.agenda_event_id,
                "ctype": payload.ceremony_type,
                "summary": payload.summary or "",
                "decisions": payload.decisions or "",
                "follow_up": payload.follow_up or "",
                "uid": ctx.principal.user_id,
                "rev": revision,
            },
        ).one()
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="agile.ceremony_record.create",
            resource_type="agile_ceremony_record",
            resource_id=row.id,
            metadata={"revision": revision, "ceremony_type": payload.ceremony_type},
        )
        conn.commit()
    return _record_out(row)


def list_ceremony_records(
    ctx: OrgContext, sprint_id: UUID, *, ceremony_type: str | None = None
) -> list[CeremonyRecordOut]:
    _require_read(ctx)
    with tenant_connection(ctx.organization_id) as conn:
        sprint = conn.execute(
            text(
                "SELECT 1 FROM agile_sprints WHERE id = :id AND organization_id = :org"
            ),
            {"id": sprint_id, "org": ctx.organization_id},
        ).first()
        if sprint is None:
            raise AppError("not_found", "Sprint not found", status_code=404)
        if ceremony_type:
            rows = conn.execute(
                text(
                    """
                    SELECT * FROM agile_ceremony_records
                    WHERE sprint_id = :sid AND organization_id = :org
                      AND ceremony_type = :ctype
                    ORDER BY recorded_at DESC, revision DESC
                    """
                ),
                {"sid": sprint_id, "org": ctx.organization_id, "ctype": ceremony_type},
            ).all()
        else:
            rows = conn.execute(
                text(
                    """
                    SELECT * FROM agile_ceremony_records
                    WHERE sprint_id = :sid AND organization_id = :org
                    ORDER BY recorded_at DESC, revision DESC
                    """
                ),
                {"sid": sprint_id, "org": ctx.organization_id},
            ).all()
    return [_record_out(r) for r in rows]
