"""Action measurement plans, indicators and measurement records (ISOI-008 rev001).

Design rules that the tests pin down:

* One non-closed `ActionMeasurementPlan` per `ActionPlan`, with a named owner.
* A baseline is not a column on the definition — it is the indicator's first
  `MeasurementRecord`, so it carries who took it and when. An indicator either
  has that reading or a written reason why it cannot exist.
* `measurement_records` is append-only: the application role has no UPDATE
  right on it. Being superseded is therefore *derived* from the existence of a
  successor row, and a correction inserts that successor instead of rewriting
  the number someone already reported.
* Substantiation comes only from the evidence attached to the effective
  reading. Typing a number into a form does not make it true.
* Nothing here changes an ActionItem status. Measurement informs the human
  efficacy decision; it never makes it.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import IntegrityError

from app import clock
from app.audit import write_audit
from app.auth.context import OrgContext
from app.db import admin_connection, tenant_connection
from app.errors import AppError
from app.idempotency import assert_same_request, key_hash, request_fingerprint
from app.modules.evidence import service as evidence_service
from app.modules.measurements import evaluation
from app.modules.measurements.evaluation import IndicatorFacts
from app.modules.measurements.schemas import (
    IndicatorCreate,
    IndicatorOut,
    IndicatorRetireIn,
    IndicatorReviseIn,
    MeasurementCorrectionIn,
    MeasurementPlanCloseIn,
    MeasurementPlanCreate,
    MeasurementPlanOut,
    MeasurementPlanUpdate,
    MeasurementRecordCreate,
    MeasurementRecordOut,
    MeasurementSummaryOut,
    TargetEvaluationOut,
    unit_label,
)
from app.modules.orgs.service import require_role
from app.schemas.enums import (
    IndicatorUnitKind,
    MeasurementKind,
    MeasurementPosture,
    MeasurementRecordStatus,
    SubstantiationLevel,
    TargetPosture,
)

_WRITE_ROLES = ("org_admin", "consultant_auditor", "quality_manager")
_SCOPED_RECORD_ROLES = ("process_owner", "action_owner")
_RECORD_ROLES = _WRITE_ROLES + _SCOPED_RECORD_ROLES
_READ_ROLES = _RECORD_ROLES + ("reader",)

# A reading taken "now" arrives with the browser's clock, which is routinely a
# couple of minutes ahead of ours. Anything beyond that is a typo in the date.
_FUTURE_TOLERANCE = timedelta(minutes=5)

_PLAN_COLS = """
    id, organization_id, action_plan_id, assessment_id, improvement_case_id,
    objective, owner_membership_id, review_cadence_days, next_review_at,
    status, activated_by, activated_at, closed_by, closed_at,
    closure_reason, created_by, created_at, updated_at
"""

_INDICATOR_COLS = """
    id, organization_id, measurement_plan_id, code, name, question,
    owner_membership_id, value_type, unit_kind, custom_unit_label,
    currency_code, decimal_places, direction, baseline_unavailable_reason,
    target_value, target_min, target_max, target_due_at,
    measurement_frequency_days, data_source, collection_method, status,
    version, lineage_id, supersedes_indicator_id, revision_reason,
    retired_reason, created_by, created_at, updated_at
"""

# `status` is not a column: a reading is superseded exactly when a successor
# exists, and the successor link is unique.
_RECORD_SELECT = """
    SELECT mr.id, mr.organization_id, mr.measurement_plan_id,
           mr.indicator_definition_id, mr.measurement_kind, mr.value,
           mr.measured_at, mr.window_start, mr.window_end, mr.note,
           mr.collection_method, mr.supersedes_measurement_id,
           mr.correction_reason, mr.recorded_by, mr.recorded_at,
           s.id AS superseded_by_measurement_id
    FROM measurement_records mr
    LEFT JOIN measurement_records s
      ON s.supersedes_measurement_id = mr.id
     AND s.organization_id = mr.organization_id
"""

_EFFECTIVE = """
    NOT EXISTS (
      SELECT 1 FROM measurement_records s
       WHERE s.supersedes_measurement_id = mr.id
         AND s.organization_id = mr.organization_id
    )
"""


def _now() -> datetime:
    return clock.now()


def _clean(value: str | None) -> str:
    return (value or "").strip()


def _or_none(value: str | None) -> str | None:
    return _clean(value) or None


def _enum_value(value) -> str:
    return value.value if hasattr(value, "value") else str(value)


# --- owners --------------------------------------------------------------


def _owner_labels(org_id: UUID, membership_ids: list[UUID]) -> dict[UUID, tuple[str, str]]:
    """Membership id → (display name, email), for screens that must name people."""
    wanted = [m for m in dict.fromkeys(membership_ids) if m is not None]
    if not wanted:
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
            {"org": org_id, "ids": wanted},
        ).all()
    return {r.id: (r.display_name, r.email) for r in rows}


def _resolve_owner(
    conn: Connection,
    ctx: OrgContext,
    membership_id: UUID | None,
    *,
    fallback_to_actor: bool = True,
) -> UUID | None:
    """An owner is a *current* member of this organization, or nobody at all."""
    if membership_id is None:
        return ctx.membership_id if fallback_to_actor else None
    row = conn.execute(
        text(
            """
            SELECT id, status FROM memberships
            WHERE id = :id AND organization_id = :org
            """
        ),
        {"id": membership_id, "org": ctx.organization_id},
    ).first()
    if row is None:
        raise AppError("not_found", "Membership not found", status_code=404)
    if row.status != "active":
        raise AppError(
            "owner_not_active",
            "Só um membro ativo da organização pode ser responsável.",
            status_code=422,
        )
    return row.id


# --- row mappers ---------------------------------------------------------


def _plan_out(
    row,
    *,
    indicator_count: int = 0,
    active_indicator_count: int = 0,
    owner: tuple[str, str] | None = None,
) -> MeasurementPlanOut:
    return MeasurementPlanOut(
        id=row.id,
        organization_id=row.organization_id,
        action_plan_id=row.action_plan_id,
        assessment_id=row.assessment_id,
        improvement_case_id=row.improvement_case_id,
        objective=row.objective or "",
        owner_membership_id=row.owner_membership_id,
        owner_display_name=owner[0] if owner else None,
        owner_email=owner[1] if owner else None,
        review_cadence_days=row.review_cadence_days,
        next_review_at=row.next_review_at,
        status=row.status,
        activated_by=row.activated_by,
        activated_at=row.activated_at,
        closed_by=row.closed_by,
        closed_at=row.closed_at,
        closure_reason=row.closure_reason,
        created_by=row.created_by,
        created_at=row.created_at,
        updated_at=row.updated_at,
        indicator_count=indicator_count,
        active_indicator_count=active_indicator_count,
    )


def _indicator_out(
    row,
    *,
    baseline: tuple[Decimal | None, datetime | None, UUID | None] = (None, None, None),
    measurement_count: int = 0,
    latest_value: Decimal | None = None,
    latest_measured_at: datetime | None = None,
    owner: tuple[str, str] | None = None,
) -> IndicatorOut:
    baseline_value, baseline_at, baseline_id = baseline
    return IndicatorOut(
        id=row.id,
        organization_id=row.organization_id,
        measurement_plan_id=row.measurement_plan_id,
        code=row.code,
        name=row.name,
        question=row.question or "",
        owner_membership_id=row.owner_membership_id,
        owner_display_name=owner[0] if owner else None,
        owner_email=owner[1] if owner else None,
        value_type=row.value_type,
        unit_kind=row.unit_kind,
        custom_unit_label=row.custom_unit_label,
        currency_code=row.currency_code,
        decimal_places=int(row.decimal_places),
        unit_label=unit_label(row.unit_kind, row.custom_unit_label, row.currency_code),
        direction=row.direction,
        baseline_status=evaluation.baseline_status_of(
            baseline_value=baseline_value,
            baseline_unavailable_reason=row.baseline_unavailable_reason,
        ),
        baseline_value=baseline_value,
        baseline_at=baseline_at,
        baseline_measurement_id=baseline_id,
        baseline_unavailable_reason=row.baseline_unavailable_reason,
        target_value=row.target_value,
        target_min=row.target_min,
        target_max=row.target_max,
        target_due_at=row.target_due_at,
        measurement_frequency_days=row.measurement_frequency_days,
        data_source=row.data_source or "",
        collection_method=row.collection_method or "",
        status=row.status,
        version=int(row.version),
        lineage_id=row.lineage_id,
        supersedes_indicator_id=row.supersedes_indicator_id,
        revision_reason=row.revision_reason,
        retired_reason=row.retired_reason,
        created_by=row.created_by,
        created_at=row.created_at,
        updated_at=row.updated_at,
        measurement_count=measurement_count,
        latest_value=latest_value,
        latest_measured_at=latest_measured_at,
    )


def _record_out(row, *, links: int = 0, verified: int = 0) -> MeasurementRecordOut:
    superseded_by = row.superseded_by_measurement_id
    return MeasurementRecordOut(
        id=row.id,
        organization_id=row.organization_id,
        measurement_plan_id=row.measurement_plan_id,
        indicator_definition_id=row.indicator_definition_id,
        measurement_kind=row.measurement_kind,
        value=row.value,
        measured_at=row.measured_at,
        window_start=row.window_start,
        window_end=row.window_end,
        note=row.note or "",
        collection_method=row.collection_method or "",
        status=(
            MeasurementRecordStatus.superseded
            if superseded_by is not None
            else MeasurementRecordStatus.active
        ),
        supersedes_measurement_id=row.supersedes_measurement_id,
        superseded_by_measurement_id=superseded_by,
        correction_reason=row.correction_reason,
        evidence_link_count=links,
        verified_evidence_count=verified,
        substantiation=evaluation.substantiation_from_evidence(
            evidence_link_count=links, verified_evidence_count=verified
        ),
        recorded_by=row.recorded_by,
        recorded_at=row.recorded_at,
    )


# --- evidence behind a reading -------------------------------------------


def _evidence_counts(
    conn: Connection, org_id: UUID, record_ids: list[UUID]
) -> dict[UUID, tuple[int, int]]:
    """One query for the whole page: record id → (links, usable proof)."""
    wanted = [r for r in dict.fromkeys(record_ids) if r is not None]
    if not wanted:
        return {}
    rows = conn.execute(
        text(
            """
            SELECT el.target_id AS record_id,
                   count(*) AS link_count,
                   count(*) FILTER (WHERE e.status = 'approved') AS verified_count
            FROM evidence_links el
            JOIN evidences e
              ON e.id = el.evidence_id AND e.organization_id = el.organization_id
            WHERE el.organization_id = :org
              AND el.target_type = 'measurement_record'
              AND el.target_id = ANY(:ids)
              AND el.removed_at IS NULL
            GROUP BY el.target_id
            """
        ),
        {"org": org_id, "ids": wanted},
    ).all()
    return {r.record_id: (int(r.link_count), int(r.verified_count)) for r in rows}


# --- lookups -------------------------------------------------------------


def _fetch_plan(conn: Connection, org_id: UUID, plan_id: UUID, *, for_update=False):
    row = conn.execute(
        text(
            f"""
            SELECT {_PLAN_COLS}
            FROM action_measurement_plans
            WHERE id = :id AND organization_id = :org
            {"FOR UPDATE" if for_update else ""}
            """
        ),
        {"id": plan_id, "org": org_id},
    ).first()
    if row is None:
        raise AppError("not_found", "Measurement plan not found", status_code=404)
    return row


def _indicator_counts(conn: Connection, org_id: UUID, plan_id: UUID) -> tuple[int, int]:
    row = conn.execute(
        text(
            """
            SELECT count(*) AS total,
                   count(*) FILTER (WHERE status = 'active') AS active
            FROM indicator_definitions
            WHERE measurement_plan_id = :pid AND organization_id = :org
            """
        ),
        {"pid": plan_id, "org": org_id},
    ).one()
    return int(row.total or 0), int(row.active or 0)


def _plan_out_with_counts(conn: Connection, org_id: UUID, row) -> MeasurementPlanOut:
    total, active = _indicator_counts(conn, org_id, row.id)
    labels = _owner_labels(org_id, [row.owner_membership_id])
    return _plan_out(
        row,
        indicator_count=total,
        active_indicator_count=active,
        owner=labels.get(row.owner_membership_id),
    )


def _fetch_action_plan_context(conn: Connection, org_id: UUID, action_plan_id: UUID):
    row = conn.execute(
        text(
            """
            SELECT id, assessment_id, improvement_case_id, status
            FROM action_plans
            WHERE id = :id AND organization_id = :org
            """
        ),
        {"id": action_plan_id, "org": org_id},
    ).first()
    if row is None:
        raise AppError("not_found", "ActionPlan not found", status_code=404)
    return row


def _fetch_indicator(
    conn: Connection, org_id: UUID, indicator_id: UUID, *, for_update=False
):
    row = conn.execute(
        text(
            f"""
            SELECT {_INDICATOR_COLS}
            FROM indicator_definitions
            WHERE id = :id AND organization_id = :org
            {"FOR UPDATE" if for_update else ""}
            """
        ),
        {"id": indicator_id, "org": org_id},
    ).first()
    if row is None:
        raise AppError("not_found", "Indicator not found", status_code=404)
    return row


def _fetch_record(conn: Connection, org_id: UUID, record_id: UUID):
    row = conn.execute(
        text(f"{_RECORD_SELECT} WHERE mr.id = :id AND mr.organization_id = :org"),
        {"id": record_id, "org": org_id},
    ).first()
    if row is None:
        raise AppError("not_found", "Measurement record not found", status_code=404)
    return row


def _baseline_of(conn: Connection, org_id: UUID, indicator_id: UUID):
    """The baseline reading that is still in force, if there is one."""
    return conn.execute(
        text(
            f"""
            SELECT mr.id, mr.value, mr.measured_at
            FROM measurement_records mr
            WHERE mr.indicator_definition_id = :iid
              AND mr.organization_id = :org
              AND mr.measurement_kind = 'baseline'
              AND {_EFFECTIVE}
            ORDER BY mr.recorded_at DESC
            LIMIT 1
            """
        ),
        {"iid": indicator_id, "org": org_id},
    ).first()


def _observation_count(conn: Connection, org_id: UUID, indicator_id: UUID) -> int:
    """Readings taken *after* the action — the baseline is setup, not data."""
    return int(
        conn.execute(
            text(
                f"""
                SELECT count(*) FROM measurement_records mr
                WHERE mr.indicator_definition_id = :iid
                  AND mr.organization_id = :org
                  AND mr.measurement_kind = 'observation'
                  AND {_EFFECTIVE}
                """
            ),
            {"iid": indicator_id, "org": org_id},
        ).scalar_one()
        or 0
    )


# --- authorization -------------------------------------------------------


def _assert_owner_scope(conn: Connection, ctx: OrgContext, plan_row, indicator_row=None):
    """Rev001 R6 — an action owner records only for the work they answer for.

    A quality manager or auditor sees the whole organization. An `action_owner`
    who is nothing else may only touch a plan they own, an indicator they own,
    or a plan whose action items are theirs; otherwise they could report numbers
    for someone else's action.
    """
    roles = set(ctx.roles)
    if roles.intersection(_WRITE_ROLES) or "process_owner" in roles:
        return
    if "action_owner" not in roles:
        return
    mine = {plan_row.owner_membership_id}
    if indicator_row is not None:
        mine.add(indicator_row.owner_membership_id)
    if ctx.membership_id in mine:
        return
    owns_item = conn.execute(
        text(
            """
            SELECT 1 FROM action_items
            WHERE action_plan_id = :apid AND organization_id = :org
              AND owner_membership_id = :mid
            LIMIT 1
            """
        ),
        {
            "apid": plan_row.action_plan_id,
            "org": ctx.organization_id,
            "mid": ctx.membership_id,
        },
    ).first()
    if owns_item is None:
        raise AppError(
            "not_action_owner",
            "Você só pode registrar medições das ações sob sua responsabilidade.",
            status_code=403,
        )


# --- measurement plans ---------------------------------------------------


def create_plan(ctx: OrgContext, payload: MeasurementPlanCreate) -> MeasurementPlanOut:
    require_role(ctx, *_WRITE_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        action_plan = _fetch_action_plan_context(
            conn, ctx.organization_id, payload.action_plan_id
        )
        if action_plan.status == "cancelled":
            raise AppError(
                "action_plan_cancelled",
                "Um plano de ação cancelado não recebe plano de medição.",
                status_code=409,
            )
        existing = conn.execute(
            text(
                """
                SELECT id FROM action_measurement_plans
                WHERE organization_id = :org AND action_plan_id = :apid
                  AND status <> 'closed'
                """
            ),
            {"org": ctx.organization_id, "apid": payload.action_plan_id},
        ).first()
        if existing is not None:
            raise AppError(
                "measurement_plan_exists",
                "Este plano de ação já tem um plano de medição em aberto.",
                status_code=409,
            )

        # Whoever creates the plan owns it until it is handed over: an owner is
        # required to activate, and asking for it twice buys nothing.
        owner_id = _resolve_owner(conn, ctx, payload.owner_membership_id)
        plan_id = uuid4()
        row = conn.execute(
            text(
                f"""
                INSERT INTO action_measurement_plans (
                  id, organization_id, action_plan_id, assessment_id,
                  improvement_case_id, objective, owner_membership_id,
                  review_cadence_days, next_review_at, status, created_by
                ) VALUES (
                  :id, :org, :apid, :aid, :cid, :objective, :owner,
                  :cadence, :next_review, 'draft', :uid
                )
                RETURNING {_PLAN_COLS}
                """
            ),
            {
                "id": plan_id,
                "org": ctx.organization_id,
                "apid": payload.action_plan_id,
                "aid": action_plan.assessment_id,
                "cid": action_plan.improvement_case_id,
                "objective": _clean(payload.objective),
                "owner": owner_id,
                "cadence": payload.review_cadence_days,
                "next_review": payload.next_review_at,
                "uid": ctx.principal.user_id,
            },
        ).one()
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="measurement_plan.create",
            resource_type="action_measurement_plan",
            resource_id=plan_id,
            to_status="draft",
            metadata={
                "action_plan_id": str(payload.action_plan_id),
                "owner_membership_id": str(owner_id) if owner_id else None,
            },
        )
        # Read before committing: the tenant guard is transaction-local, so a
        # query issued after the commit would see nothing at all.
        out = _plan_out_with_counts(conn, ctx.organization_id, row)
        conn.commit()
        return out


def get_plan(ctx: OrgContext, plan_id: UUID) -> MeasurementPlanOut:
    require_role(ctx, *_READ_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        row = _fetch_plan(conn, ctx.organization_id, plan_id)
        return _plan_out_with_counts(conn, ctx.organization_id, row)


def list_plans(
    ctx: OrgContext,
    *,
    action_plan_id: UUID | None = None,
    status: str | None = None,
) -> list[MeasurementPlanOut]:
    require_role(ctx, *_READ_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        rows = conn.execute(
            text(
                f"""
                SELECT {_PLAN_COLS}
                FROM action_measurement_plans
                WHERE organization_id = :org
                  AND (CAST(:apid AS uuid) IS NULL OR action_plan_id = :apid)
                  AND (CAST(:status AS text) IS NULL OR status = :status)
                ORDER BY created_at DESC
                """
            ),
            {"org": ctx.organization_id, "apid": action_plan_id, "status": status},
        ).all()
        return [_plan_out_with_counts(conn, ctx.organization_id, r) for r in rows]


def update_plan(
    ctx: OrgContext, plan_id: UUID, payload: MeasurementPlanUpdate
) -> MeasurementPlanOut:
    require_role(ctx, *_WRITE_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        current = _fetch_plan(conn, ctx.organization_id, plan_id, for_update=True)
        if current.status == "closed":
            raise AppError(
                "measurement_plan_closed",
                "Plano de medição encerrado não pode ser alterado.",
                status_code=409,
            )
        objective = payload.objective_value()
        owner_id = current.owner_membership_id
        if payload.provided("owner_membership_id"):
            owner_id = _resolve_owner(
                conn, ctx, payload.owner_membership_id, fallback_to_actor=False
            )
            if owner_id is None and current.status == "active":
                raise AppError(
                    "measurement_plan_owner_required",
                    "Um plano de medição ativo precisa de um responsável.",
                    status_code=422,
                )
        row = conn.execute(
            text(
                f"""
                UPDATE action_measurement_plans
                SET objective = :objective,
                    owner_membership_id = :owner,
                    review_cadence_days = :cadence,
                    next_review_at = :next_review,
                    updated_at = now()
                WHERE id = :id AND organization_id = :org
                RETURNING {_PLAN_COLS}
                """
            ),
            {
                "id": plan_id,
                "org": ctx.organization_id,
                "objective": (
                    objective if objective is not None else (current.objective or "")
                ),
                "owner": owner_id,
                "cadence": (
                    payload.review_cadence_days
                    if payload.provided("review_cadence_days")
                    else current.review_cadence_days
                ),
                "next_review": (
                    payload.next_review_at
                    if payload.provided("next_review_at")
                    else current.next_review_at
                ),
            },
        ).one()
        out = _plan_out_with_counts(conn, ctx.organization_id, row)
        conn.commit()
        return out


def _activation_blockers(conn: Connection, org_id: UUID, plan_id: UUID) -> None:
    """Everything that has to be true before a plan can start proving things."""
    rows = conn.execute(
        text(
            f"""
            SELECT {_INDICATOR_COLS}
            FROM indicator_definitions
            WHERE measurement_plan_id = :pid AND organization_id = :org
              AND status = 'active'
            ORDER BY code
            """
        ),
        {"pid": plan_id, "org": org_id},
    ).all()
    if not rows:
        raise AppError(
            "measurement_plan_without_indicator",
            "Defina ao menos um indicador ativo antes de ativar o plano.",
            status_code=422,
        )
    for row in rows:
        baseline = _baseline_of(conn, org_id, row.id)
        settled = baseline is not None or bool(
            _clean(row.baseline_unavailable_reason)
        )
        if not settled:
            raise AppError(
                "indicator_baseline_required",
                "Cada indicador precisa da linha de base ou do motivo pelo qual "
                "ela não existe.",
                status_code=422,
            )
        if not evaluation.target_rule_is_complete_for(
            direction=row.direction,
            target_value=row.target_value,
            target_min=row.target_min,
            target_max=row.target_max,
        ):
            raise AppError(
                "indicator_target_required",
                f"O indicador {row.code} ainda não tem meta suficiente para "
                "julgar o resultado. Informe a meta antes de ativar o plano.",
                status_code=422,
            )
        if row.owner_membership_id is None:
            raise AppError(
                "indicator_owner_required",
                f"Informe quem responde pelo indicador {row.code} antes de "
                "ativar o plano.",
                status_code=422,
            )


def activate_plan(ctx: OrgContext, plan_id: UUID) -> MeasurementPlanOut:
    """A plan can only go live once it can actually prove something."""
    require_role(ctx, *_WRITE_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        current = _fetch_plan(conn, ctx.organization_id, plan_id, for_update=True)
        if current.status != "draft":
            raise AppError(
                "invalid_transition",
                f"activate requires draft (current={current.status})",
                status_code=409,
            )
        if current.owner_membership_id is None:
            raise AppError(
                "measurement_plan_owner_required",
                "Informe quem responde por este plano de medição antes de ativá-lo.",
                status_code=422,
            )
        _activation_blockers(conn, ctx.organization_id, plan_id)
        row = conn.execute(
            text(
                f"""
                UPDATE action_measurement_plans
                SET status = 'active', activated_by = :uid, activated_at = now(),
                    updated_at = now()
                WHERE id = :id AND organization_id = :org AND status = 'draft'
                RETURNING {_PLAN_COLS}
                """
            ),
            {"id": plan_id, "org": ctx.organization_id, "uid": ctx.principal.user_id},
        ).first()
        if row is None:
            raise AppError("conflict", "Concurrent status change", status_code=409)
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="measurement_plan.activate",
            resource_type="action_measurement_plan",
            resource_id=plan_id,
            from_status="draft",
            to_status="active",
        )
        out = _plan_out_with_counts(conn, ctx.organization_id, row)
        conn.commit()
        return out


def close_plan(
    ctx: OrgContext, plan_id: UUID, payload: MeasurementPlanCloseIn
) -> MeasurementPlanOut:
    require_role(ctx, *_WRITE_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        current = _fetch_plan(conn, ctx.organization_id, plan_id, for_update=True)
        if current.status == "closed":
            raise AppError(
                "invalid_transition",
                "Plano de medição já encerrado.",
                status_code=409,
            )
        row = conn.execute(
            text(
                f"""
                UPDATE action_measurement_plans
                SET status = 'closed', closed_by = :uid, closed_at = now(),
                    closure_reason = :reason, updated_at = now()
                WHERE id = :id AND organization_id = :org AND status <> 'closed'
                RETURNING {_PLAN_COLS}
                """
            ),
            {
                "id": plan_id,
                "org": ctx.organization_id,
                "uid": ctx.principal.user_id,
                "reason": payload.closure_reason,
            },
        ).first()
        if row is None:
            raise AppError("conflict", "Concurrent status change", status_code=409)
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="measurement_plan.close",
            resource_type="action_measurement_plan",
            resource_id=plan_id,
            from_status=current.status,
            to_status="closed",
            metadata={"closure_reason": payload.closure_reason},
        )
        out = _plan_out_with_counts(conn, ctx.organization_id, row)
        conn.commit()
        return out


# --- indicators ----------------------------------------------------------


def _assert_plan_editable(row) -> None:
    if row.status == "closed":
        raise AppError(
            "measurement_plan_closed",
            "Plano de medição encerrado não aceita novos indicadores.",
            status_code=409,
        )


def _assert_not_future(moment: datetime | None, *, field: str) -> None:
    if moment is None:
        return
    if moment > _now() + _FUTURE_TOLERANCE:
        raise AppError(
            "measured_at_in_future",
            f"{field} não pode estar no futuro: uma medição registra algo que "
            "já aconteceu.",
            status_code=422,
        )


def _assert_shape_coherent(
    *,
    direction: str,
    unit_kind: str,
    custom_unit_label: str | None,
    currency_code: str | None,
    target_value: Decimal | None,
    target_min: Decimal | None,
    target_max: Decimal | None,
    baseline_value: Decimal | None = None,
) -> None:
    """The same rules the schema enforces, re-checked after a partial merge."""
    if unit_kind == IndicatorUnitKind.custom.value and not _clean(custom_unit_label):
        raise AppError(
            "indicator_unit_incoherent",
            "Uma unidade personalizada precisa de um nome legível.",
            status_code=422,
        )
    if unit_kind == IndicatorUnitKind.currency.value and not currency_code:
        raise AppError(
            "indicator_unit_incoherent",
            "Um indicador em dinheiro precisa do código da moeda.",
            status_code=422,
        )
    if unit_kind != IndicatorUnitKind.currency.value and currency_code:
        raise AppError(
            "indicator_unit_incoherent",
            "O código da moeda só se aplica a indicadores em dinheiro.",
            status_code=422,
        )
    ranged = direction in evaluation.RANGE_DIRECTIONS
    if ranged and target_value is not None:
        raise AppError(
            "indicator_target_incoherent",
            "Uma faixa usa mínimo e máximo, não um valor único.",
            status_code=422,
        )
    if not ranged and (target_min is not None or target_max is not None):
        raise AppError(
            "indicator_target_incoherent",
            "Esta direção usa um valor de meta, não uma faixa.",
            status_code=422,
        )
    if ranged and target_min is not None and target_max is not None:
        if target_max < target_min:
            raise AppError(
                "indicator_target_incoherent",
                "O máximo da faixa precisa ser maior ou igual ao mínimo.",
                status_code=422,
            )
    if unit_kind == IndicatorUnitKind.percentage.value:
        for label, value in (
            ("meta", target_value),
            ("mínimo", target_min),
            ("máximo", target_max),
            ("linha de base", baseline_value),
        ):
            if value is not None and not (Decimal(0) <= value <= Decimal(100)):
                raise AppError(
                    "indicator_percentage_out_of_range",
                    f"O valor de {label} precisa estar entre 0 e 100 em um "
                    "indicador percentual.",
                    status_code=422,
                )


def _insert_baseline_record(
    conn: Connection,
    ctx: OrgContext,
    *,
    plan_id: UUID,
    indicator_id: UUID,
    value: Decimal,
    measured_at: datetime,
    collection_method: str,
    note: str,
) -> UUID:
    record_id = uuid4()
    conn.execute(
        text(
            """
            INSERT INTO measurement_records (
              id, organization_id, measurement_plan_id, indicator_definition_id,
              measurement_kind, value, measured_at, note, collection_method,
              recorded_by
            ) VALUES (
              :id, :org, :pid, :iid, 'baseline', :value, :measured_at, :note,
              :method, :uid
            )
            """
        ),
        {
            "id": record_id,
            "org": ctx.organization_id,
            "pid": plan_id,
            "iid": indicator_id,
            "value": value,
            "measured_at": measured_at,
            "note": note,
            "method": collection_method,
            "uid": ctx.principal.user_id,
        },
    )
    return record_id


def create_indicator(
    ctx: OrgContext, plan_id: UUID, payload: IndicatorCreate
) -> IndicatorOut:
    require_role(ctx, *_WRITE_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        plan = _fetch_plan(conn, ctx.organization_id, plan_id, for_update=True)
        _assert_plan_editable(plan)
        clash = conn.execute(
            text(
                """
                SELECT id FROM indicator_definitions
                WHERE organization_id = :org AND measurement_plan_id = :pid
                  AND code = :code AND status = 'active'
                """
            ),
            {"org": ctx.organization_id, "pid": plan_id, "code": payload.code},
        ).first()
        if clash is not None:
            raise AppError(
                "indicator_code_taken",
                f"Já existe um indicador ativo com o código {payload.code}.",
                status_code=409,
            )
        unit_kind = _enum_value(payload.unit_kind)
        _assert_shape_coherent(
            direction=payload.direction.value,
            unit_kind=unit_kind,
            custom_unit_label=payload.custom_unit_label,
            currency_code=payload.currency_code,
            target_value=payload.target_value,
            target_min=payload.target_min,
            target_max=payload.target_max,
            baseline_value=payload.baseline_value,
        )
        _assert_not_future(payload.baseline_at, field="A data da linha de base")
        owner_id = _resolve_owner(conn, ctx, payload.owner_membership_id)
        if owner_id is None:
            owner_id = plan.owner_membership_id

        indicator_id = uuid4()
        row = conn.execute(
            text(
                f"""
                INSERT INTO indicator_definitions (
                  id, organization_id, measurement_plan_id, code, name, question,
                  owner_membership_id, value_type, unit_kind, custom_unit_label,
                  currency_code, decimal_places, direction,
                  baseline_unavailable_reason, target_value, target_min,
                  target_max, target_due_at, measurement_frequency_days,
                  data_source, collection_method, status, version, lineage_id,
                  created_by
                ) VALUES (
                  :id, :org, :pid, :code, :name, :question,
                  :owner, 'decimal', :unit_kind, :custom_label,
                  :currency, :places, :direction,
                  :baseline_reason, :target, :tmin,
                  :tmax, :target_due, :freq,
                  :source, :method, 'active', 1, :id,
                  :uid
                )
                RETURNING {_INDICATOR_COLS}
                """
            ),
            {
                "id": indicator_id,
                "org": ctx.organization_id,
                "pid": plan_id,
                "code": payload.code,
                "name": payload.name,
                "question": _clean(payload.question),
                "owner": owner_id,
                "unit_kind": unit_kind,
                "custom_label": _or_none(payload.custom_unit_label),
                "currency": payload.currency_code,
                "places": payload.decimal_places,
                "direction": payload.direction.value,
                "baseline_reason": _or_none(payload.baseline_unavailable_reason),
                "target": payload.target_value,
                "tmin": payload.target_min,
                "tmax": payload.target_max,
                "target_due": payload.target_due_at,
                "freq": payload.measurement_frequency_days,
                "source": _clean(payload.data_source),
                "method": _clean(payload.collection_method),
                "uid": ctx.principal.user_id,
            },
        ).one()

        # The baseline is the indicator's first reading, not a field on it.
        baseline_id = None
        if payload.baseline_value is not None:
            baseline_id = _insert_baseline_record(
                conn,
                ctx,
                plan_id=plan_id,
                indicator_id=indicator_id,
                value=payload.baseline_value,
                measured_at=payload.baseline_at or _now(),
                collection_method=_clean(payload.collection_method),
                note="Linha de base informada na definição do indicador.",
            )
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="indicator.create",
            resource_type="indicator_definition",
            resource_id=indicator_id,
            metadata={
                "measurement_plan_id": str(plan_id),
                "code": payload.code,
                "baseline_measurement_id": str(baseline_id) if baseline_id else None,
                "owner_membership_id": str(owner_id) if owner_id else None,
            },
        )
        baseline = _baseline_of(conn, ctx.organization_id, indicator_id)
        labels = _owner_labels(ctx.organization_id, [row.owner_membership_id])
        conn.commit()
    return _indicator_out(
        row,
        baseline=(
            (baseline.value, baseline.measured_at, baseline.id)
            if baseline
            else (None, None, None)
        ),
        owner=labels.get(row.owner_membership_id),
    )


_INDICATOR_LIST_SQL = f"""
    SELECT {", ".join("i." + c.strip() for c in _INDICATOR_COLS.split(","))},
           b.id AS baseline_measurement_id,
           b.value AS baseline_value,
           b.measured_at AS baseline_at,
           coalesce(o.measurement_count, 0) AS measurement_count,
           o.latest_value,
           o.latest_measured_at
    FROM indicator_definitions i
    LEFT JOIN LATERAL (
      SELECT mr.id, mr.value, mr.measured_at
      FROM measurement_records mr
      WHERE mr.indicator_definition_id = i.id
        AND mr.organization_id = i.organization_id
        AND mr.measurement_kind = 'baseline'
        AND {_EFFECTIVE}
      ORDER BY mr.recorded_at DESC
      LIMIT 1
    ) b ON true
    LEFT JOIN LATERAL (
      SELECT count(*) AS measurement_count,
             (array_agg(
                mr.value ORDER BY mr.measured_at DESC, mr.recorded_at DESC
              ))[1] AS latest_value,
             max(mr.measured_at) AS latest_measured_at
      FROM measurement_records mr
      WHERE mr.indicator_definition_id = i.id
        AND mr.organization_id = i.organization_id
        AND mr.measurement_kind = 'observation'
        AND {_EFFECTIVE}
    ) o ON true
    WHERE i.measurement_plan_id = :pid AND i.organization_id = :org
      AND (:all OR i.status = 'active')
    ORDER BY i.code, i.version DESC
"""


def list_indicators(
    ctx: OrgContext, plan_id: UUID, *, include_superseded: bool = False
) -> list[IndicatorOut]:
    require_role(ctx, *_READ_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        _fetch_plan(conn, ctx.organization_id, plan_id)
        rows = conn.execute(
            text(_INDICATOR_LIST_SQL),
            {"pid": plan_id, "org": ctx.organization_id, "all": include_superseded},
        ).all()
    labels = _owner_labels(
        ctx.organization_id, [r.owner_membership_id for r in rows]
    )
    return [
        _indicator_out(
            r,
            baseline=(r.baseline_value, r.baseline_at, r.baseline_measurement_id),
            measurement_count=int(r.measurement_count or 0),
            latest_value=r.latest_value,
            latest_measured_at=r.latest_measured_at,
            owner=labels.get(r.owner_membership_id),
        )
        for r in rows
    ]


_REVISABLE_FIELDS = (
    "name",
    "question",
    "owner_membership_id",
    "unit_kind",
    "custom_unit_label",
    "currency_code",
    "decimal_places",
    "direction",
    "baseline_unavailable_reason",
    "target_value",
    "target_min",
    "target_max",
    "target_due_at",
    "measurement_frequency_days",
    "data_source",
    "collection_method",
)


def revise_indicator(
    ctx: OrgContext, indicator_id: UUID, payload: IndicatorReviseIn
) -> IndicatorOut:
    """Editing after data exists would rewrite history — so we version instead."""
    require_role(ctx, *_WRITE_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        current = _fetch_indicator(
            conn, ctx.organization_id, indicator_id, for_update=True
        )
        if current.status != "active":
            raise AppError(
                "indicator_not_active",
                "Somente um indicador ativo pode ser revisado.",
                status_code=409,
            )
        plan = _fetch_plan(conn, ctx.organization_id, current.measurement_plan_id)
        _assert_plan_editable(plan)

        fields: dict[str, object] = {}
        for name in _REVISABLE_FIELDS:
            if payload.provided(name):
                fields[name] = getattr(payload, name)
            else:
                fields[name] = getattr(current, name)
        # A name or a unit cannot be *removed*, only replaced.
        for name in ("name", "unit_kind", "decimal_places"):
            if fields[name] is None:
                fields[name] = getattr(current, name)
        fields["direction"] = _enum_value(fields["direction"])
        fields["unit_kind"] = _enum_value(fields["unit_kind"])
        fields["question"] = _clean(fields["question"])
        fields["data_source"] = _clean(fields["data_source"])
        fields["collection_method"] = _clean(fields["collection_method"])
        fields["custom_unit_label"] = _or_none(fields["custom_unit_label"])
        fields["baseline_unavailable_reason"] = _or_none(
            fields["baseline_unavailable_reason"]
        )
        if payload.provided("owner_membership_id"):
            fields["owner_membership_id"] = _resolve_owner(
                conn, ctx, payload.owner_membership_id, fallback_to_actor=False
            )

        baseline = _baseline_of(conn, ctx.organization_id, indicator_id)
        _assert_shape_coherent(
            direction=fields["direction"],
            unit_kind=fields["unit_kind"],
            custom_unit_label=fields["custom_unit_label"],
            currency_code=fields["currency_code"],
            target_value=fields["target_value"],
            target_min=fields["target_min"],
            target_max=fields["target_max"],
            baseline_value=baseline.value if baseline else None,
        )

        observations = _observation_count(conn, ctx.organization_id, indicator_id)
        assignments = ", ".join(f"{name} = :{name}" for name in _REVISABLE_FIELDS)
        if observations == 0:
            row = conn.execute(
                text(
                    f"""
                    UPDATE indicator_definitions
                    SET {assignments}, revision_reason = :reason, updated_at = now()
                    WHERE id = :id AND organization_id = :org
                    RETURNING {_INDICATOR_COLS}
                    """
                ),
                {
                    **fields,
                    "id": indicator_id,
                    "org": ctx.organization_id,
                    "reason": payload.revision_reason,
                },
            ).one()
            event = "indicator.update"
            new_id = indicator_id
        else:
            new_id = uuid4()
            conn.execute(
                text(
                    """
                    UPDATE indicator_definitions
                    SET status = 'superseded', updated_at = now()
                    WHERE id = :id AND organization_id = :org
                    """
                ),
                {"id": indicator_id, "org": ctx.organization_id},
            )
            columns = ", ".join(_REVISABLE_FIELDS)
            placeholders = ", ".join(f":{name}" for name in _REVISABLE_FIELDS)
            row = conn.execute(
                text(
                    f"""
                    INSERT INTO indicator_definitions (
                      id, organization_id, measurement_plan_id, code, value_type,
                      {columns},
                      status, version, lineage_id, supersedes_indicator_id,
                      revision_reason, created_by
                    ) VALUES (
                      :id, :org, :pid, :code, 'decimal',
                      {placeholders},
                      'active', :version, :lineage, :supersedes,
                      :reason, :uid
                    )
                    RETURNING {_INDICATOR_COLS}
                    """
                ),
                {
                    **fields,
                    "id": new_id,
                    "org": ctx.organization_id,
                    "pid": current.measurement_plan_id,
                    "code": current.code,
                    "version": int(current.version) + 1,
                    "lineage": current.lineage_id,
                    "supersedes": indicator_id,
                    "reason": payload.revision_reason,
                    "uid": ctx.principal.user_id,
                },
            ).one()
            event = "indicator.revise"
            # The new version measures the same thing from the same starting
            # point; without carrying the baseline over it would look as if
            # nobody ever knew where the indicator began.
            if baseline is not None:
                _insert_baseline_record(
                    conn,
                    ctx,
                    plan_id=current.measurement_plan_id,
                    indicator_id=new_id,
                    value=baseline.value,
                    measured_at=baseline.measured_at,
                    collection_method=str(fields["collection_method"]),
                    note=(
                        "Linha de base mantida da versão anterior do indicador "
                        f"(v{int(current.version)})."
                    ),
                )

        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action=event,
            resource_type="indicator_definition",
            resource_id=new_id,
            metadata={
                "revision_reason": payload.revision_reason,
                "supersedes_indicator_id": (
                    str(indicator_id) if new_id != indicator_id else None
                ),
                "existing_measurements": observations,
            },
        )
        new_baseline = _baseline_of(conn, ctx.organization_id, new_id)
        labels = _owner_labels(ctx.organization_id, [row.owner_membership_id])
        conn.commit()
    return _indicator_out(
        row,
        baseline=(
            (new_baseline.value, new_baseline.measured_at, new_baseline.id)
            if new_baseline
            else (None, None, None)
        ),
        owner=labels.get(row.owner_membership_id),
    )


def retire_indicator(
    ctx: OrgContext, indicator_id: UUID, payload: IndicatorRetireIn
) -> IndicatorOut:
    require_role(ctx, *_WRITE_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        current = _fetch_indicator(
            conn, ctx.organization_id, indicator_id, for_update=True
        )
        if current.status != "active":
            raise AppError(
                "indicator_not_active",
                "Somente um indicador ativo pode ser desativado.",
                status_code=409,
            )
        row = conn.execute(
            text(
                f"""
                UPDATE indicator_definitions
                SET status = 'retired', retired_reason = :reason, updated_at = now()
                WHERE id = :id AND organization_id = :org AND status = 'active'
                RETURNING {_INDICATOR_COLS}
                """
            ),
            {
                "id": indicator_id,
                "org": ctx.organization_id,
                "reason": payload.retired_reason,
            },
        ).one()
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="indicator.retire",
            resource_type="indicator_definition",
            resource_id=indicator_id,
            from_status="active",
            to_status="retired",
            metadata={"retired_reason": payload.retired_reason},
        )
        baseline = _baseline_of(conn, ctx.organization_id, indicator_id)
        labels = _owner_labels(ctx.organization_id, [row.owner_membership_id])
        conn.commit()
    return _indicator_out(
        row,
        baseline=(
            (baseline.value, baseline.measured_at, baseline.id)
            if baseline
            else (None, None, None)
        ),
        owner=labels.get(row.owner_membership_id),
    )


# --- measurement records -------------------------------------------------


def _record_with_counts(conn: Connection, org_id: UUID, record_id: UUID):
    row = _fetch_record(conn, org_id, record_id)
    counts = _evidence_counts(conn, org_id, [record_id]).get(record_id, (0, 0))
    return _record_out(row, links=counts[0], verified=counts[1])


def _replay_or_none(
    conn: Connection, org_id: UUID, scope: str, hashed: str, fingerprint: str
):
    """Same key, same request → the first answer. Same key, other request → 409."""
    row = conn.execute(
        text(
            """
            SELECT id, request_fingerprint FROM measurement_records
            WHERE organization_id = :org AND idempotency_scope = :scope
              AND idempotency_key_hash = :hash
            """
        ),
        {"org": org_id, "scope": scope, "hash": hashed},
    ).first()
    if row is None:
        return None
    assert_same_request(row.request_fingerprint, fingerprint)
    return row.id


def create_measurement(
    ctx: OrgContext, plan_id: UUID, payload: MeasurementRecordCreate
) -> MeasurementRecordOut:
    require_role(ctx, *_RECORD_ROLES)
    kind = _enum_value(payload.measurement_kind)
    with tenant_connection(ctx.organization_id) as conn:
        plan = _fetch_plan(conn, ctx.organization_id, plan_id)
        if plan.status == "closed":
            raise AppError(
                "measurement_plan_closed",
                "Plano de medição encerrado não aceita medições.",
                status_code=409,
            )
        # A baseline has to be recordable before the plan goes live — the plan
        # cannot be activated without one. Observations are what an active plan
        # collects.
        if kind == MeasurementKind.observation.value and plan.status != "active":
            raise AppError(
                "measurement_plan_not_active",
                "Ative o plano de medição antes de registrar medições.",
                status_code=409,
            )
        indicator = _fetch_indicator(
            conn, ctx.organization_id, payload.indicator_definition_id
        )
        if indicator.measurement_plan_id != plan_id:
            raise AppError(
                "indicator_plan_mismatch",
                "Este indicador pertence a outro plano de medição.",
                status_code=422,
            )
        if indicator.status != "active":
            raise AppError(
                "indicator_not_active",
                "Só é possível medir um indicador ativo.",
                status_code=409,
            )
        _assert_owner_scope(conn, ctx, plan, indicator)
        _assert_not_future(payload.measured_at, field="A data da medição")
        if kind == MeasurementKind.baseline.value:
            existing = _baseline_of(
                conn, ctx.organization_id, payload.indicator_definition_id
            )
            if existing is not None:
                raise AppError(
                    "baseline_already_recorded",
                    "Este indicador já tem linha de base. Corrija a medição "
                    "existente em vez de registrar outra.",
                    status_code=409,
                )

        scope = f"measurement_record.create:{plan_id}"
        hashed = fingerprint = None
        if payload.idempotency_key:
            hashed = key_hash(payload.idempotency_key)
            fingerprint = request_fingerprint(
                scope,
                {
                    "indicator_definition_id": payload.indicator_definition_id,
                    "measurement_kind": kind,
                    "value": str(payload.value),
                    "measured_at": payload.measured_at,
                    "window_start": payload.window_start,
                    "window_end": payload.window_end,
                    "note": _clean(payload.note),
                    "collection_method": _clean(payload.collection_method),
                    "evidence_ids": sorted(str(e) for e in payload.evidence_ids),
                },
            )
            replayed = _replay_or_none(
                conn, ctx.organization_id, scope, hashed, fingerprint
            )
            if replayed is not None:
                return _record_with_counts(conn, ctx.organization_id, replayed)

        record_id = uuid4()
        params = {
            "id": record_id,
            "org": ctx.organization_id,
            "pid": plan_id,
            "iid": payload.indicator_definition_id,
            "kind": kind,
            "value": payload.value,
            "measured_at": payload.measured_at,
            "wstart": payload.window_start,
            "wend": payload.window_end,
            "note": _clean(payload.note),
            "method": _clean(payload.collection_method)
            or (indicator.collection_method or ""),
            "scope": scope if hashed else None,
            "hash": hashed,
            "fingerprint": fingerprint,
            "uid": ctx.principal.user_id,
        }
        insert = text(
            """
            INSERT INTO measurement_records (
              id, organization_id, measurement_plan_id, indicator_definition_id,
              measurement_kind, value, measured_at, window_start, window_end,
              note, collection_method, idempotency_scope, idempotency_key_hash,
              request_fingerprint, recorded_by
            ) VALUES (
              :id, :org, :pid, :iid,
              :kind, :value, :measured_at, :wstart, :wend,
              :note, :method, :scope, :hash,
              :fingerprint, :uid
            )
            """
        )
        try:
            with conn.begin_nested():
                conn.execute(insert, params)
        except IntegrityError as exc:
            # Two concurrent retries of the same key: the loser reads the winner.
            if hashed is not None:
                replayed = _replay_or_none(
                    conn, ctx.organization_id, scope, hashed, fingerprint
                )
                if replayed is not None:
                    return _record_with_counts(conn, ctx.organization_id, replayed)
            if kind == MeasurementKind.baseline.value:
                raise AppError(
                    "baseline_already_recorded",
                    "Este indicador já tem linha de base.",
                    status_code=409,
                ) from exc
            raise

        if payload.evidence_ids:
            evidence_service.attach_evidences(
                conn,
                ctx,
                target_type="measurement_record",
                target_id=record_id,
                evidence_ids=list(payload.evidence_ids),
            )
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="measurement_record.create",
            resource_type="measurement_record",
            resource_id=record_id,
            metadata={
                "indicator_definition_id": str(payload.indicator_definition_id),
                "measurement_kind": kind,
                "value": str(payload.value),
                "measured_at": payload.measured_at.isoformat(),
                "evidence_ids": [str(e) for e in payload.evidence_ids],
            },
        )
        out = _record_with_counts(conn, ctx.organization_id, record_id)
        conn.commit()
        return out


def correct_measurement(
    ctx: OrgContext, record_id: UUID, payload: MeasurementCorrectionIn
) -> MeasurementRecordOut:
    """Corrections are append-only: the wrong number stays visible in history."""
    require_role(ctx, *_RECORD_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        current = _fetch_record(conn, ctx.organization_id, record_id)
        if current.superseded_by_measurement_id is not None:
            raise AppError(
                "measurement_already_superseded",
                "Esta medição já foi corrigida — corrija a versão mais recente.",
                status_code=409,
            )
        plan = _fetch_plan(conn, ctx.organization_id, current.measurement_plan_id)
        if plan.status == "closed":
            raise AppError(
                "measurement_plan_closed",
                "Plano de medição encerrado não aceita correções.",
                status_code=409,
            )
        indicator = _fetch_indicator(
            conn, ctx.organization_id, current.indicator_definition_id
        )
        _assert_owner_scope(conn, ctx, plan, indicator)
        measured_at = payload.measured_at or current.measured_at
        _assert_not_future(measured_at, field="A data da medição")

        scope = f"measurement_record.correct:{record_id}"
        hashed = fingerprint = None
        if payload.idempotency_key:
            hashed = key_hash(payload.idempotency_key)
            fingerprint = request_fingerprint(
                scope,
                {
                    "value": str(payload.value),
                    "measured_at": measured_at,
                    "note": _clean(payload.note),
                    "correction_reason": payload.correction_reason,
                    "evidence_ids": sorted(str(e) for e in payload.evidence_ids),
                },
            )
            replayed = _replay_or_none(
                conn, ctx.organization_id, scope, hashed, fingerprint
            )
            if replayed is not None:
                return _record_with_counts(conn, ctx.organization_id, replayed)

        new_id = uuid4()
        insert = text(
            """
            INSERT INTO measurement_records (
              id, organization_id, measurement_plan_id, indicator_definition_id,
              measurement_kind, value, measured_at, window_start, window_end,
              note, collection_method, supersedes_measurement_id,
              correction_reason, idempotency_scope, idempotency_key_hash,
              request_fingerprint, recorded_by
            ) VALUES (
              :id, :org, :pid, :iid,
              :kind, :value, :measured_at, :wstart, :wend,
              :note, :method, :supersedes,
              :reason, :scope, :hash,
              :fingerprint, :uid
            )
            """
        )
        params = {
            "id": new_id,
            "org": ctx.organization_id,
            "pid": current.measurement_plan_id,
            "iid": current.indicator_definition_id,
            "kind": current.measurement_kind,
            "value": payload.value,
            "measured_at": measured_at,
            "wstart": current.window_start,
            "wend": current.window_end,
            "note": _clean(payload.note) or (current.note or ""),
            "method": current.collection_method or "",
            "supersedes": record_id,
            "reason": payload.correction_reason,
            "scope": scope if hashed else None,
            "hash": hashed,
            "fingerprint": fingerprint,
            "uid": ctx.principal.user_id,
        }
        try:
            with conn.begin_nested():
                conn.execute(insert, params)
        except IntegrityError as exc:
            if hashed is not None:
                replayed = _replay_or_none(
                    conn, ctx.organization_id, scope, hashed, fingerprint
                )
                if replayed is not None:
                    return _record_with_counts(conn, ctx.organization_id, replayed)
            # `uq_measurement_one_successor`: somebody corrected it first.
            raise AppError(
                "measurement_already_superseded",
                "Esta medição já foi corrigida — corrija a versão mais recente.",
                status_code=409,
            ) from exc

        if payload.evidence_ids:
            evidence_service.attach_evidences(
                conn,
                ctx,
                target_type="measurement_record",
                target_id=new_id,
                evidence_ids=list(payload.evidence_ids),
            )
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="measurement_record.correct",
            resource_type="measurement_record",
            resource_id=new_id,
            metadata={
                "supersedes_measurement_id": str(record_id),
                "previous_value": str(current.value),
                "value": str(payload.value),
                "correction_reason": payload.correction_reason,
            },
        )
        out = _record_with_counts(conn, ctx.organization_id, new_id)
        conn.commit()
        return out


def list_measurements(
    ctx: OrgContext,
    plan_id: UUID,
    *,
    indicator_definition_id: UUID | None = None,
    include_superseded: bool = False,
) -> list[MeasurementRecordOut]:
    require_role(ctx, *_READ_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        _fetch_plan(conn, ctx.organization_id, plan_id)
        rows = conn.execute(
            text(
                f"""
                {_RECORD_SELECT}
                WHERE mr.measurement_plan_id = :pid AND mr.organization_id = :org
                  AND (
                    CAST(:iid AS uuid) IS NULL
                    OR mr.indicator_definition_id = :iid
                  )
                  AND (:all OR s.id IS NULL)
                ORDER BY mr.measured_at DESC, mr.recorded_at DESC
                """
            ),
            {
                "pid": plan_id,
                "org": ctx.organization_id,
                "iid": indicator_definition_id,
                "all": include_superseded,
            },
        ).all()
        counts = _evidence_counts(conn, ctx.organization_id, [r.id for r in rows])
    return [
        _record_out(r, links=counts.get(r.id, (0, 0))[0], verified=counts.get(r.id, (0, 0))[1])
        for r in rows
    ]


# --- projection ----------------------------------------------------------

_INDICATOR_FACTS_SQL = f"""
    SELECT i.id, i.code, i.name, i.unit_kind, i.custom_unit_label,
           i.currency_code, i.decimal_places, i.direction,
           i.baseline_unavailable_reason, i.owner_membership_id,
           i.target_value, i.target_min, i.target_max, i.target_due_at,
           i.measurement_frequency_days,
           p.action_plan_id,
           p.activated_at,
           b.value AS baseline_value,
           b.measured_at AS baseline_at,
           b.id AS baseline_measurement_id,
           coalesce(o.measurement_count, 0) AS measurement_count,
           o.latest_value,
           o.latest_measured_at,
           o.latest_measurement_id
    FROM indicator_definitions i
    JOIN action_measurement_plans p
      ON p.id = i.measurement_plan_id AND p.organization_id = i.organization_id
    LEFT JOIN LATERAL (
      SELECT mr.id, mr.value, mr.measured_at
      FROM measurement_records mr
      WHERE mr.indicator_definition_id = i.id
        AND mr.organization_id = i.organization_id
        AND mr.measurement_kind = 'baseline'
        AND {_EFFECTIVE}
      ORDER BY mr.recorded_at DESC
      LIMIT 1
    ) b ON true
    LEFT JOIN LATERAL (
      SELECT count(*) AS measurement_count,
             (array_agg(
                mr.id ORDER BY mr.measured_at DESC, mr.recorded_at DESC
              ))[1] AS latest_measurement_id,
             (array_agg(
                mr.value ORDER BY mr.measured_at DESC, mr.recorded_at DESC
              ))[1] AS latest_value,
             max(mr.measured_at) AS latest_measured_at
      FROM measurement_records mr
      WHERE mr.indicator_definition_id = i.id
        AND mr.organization_id = i.organization_id
        AND mr.measurement_kind = 'observation'
        AND {_EFFECTIVE}
    ) o ON true
    WHERE i.organization_id = :org
      AND i.status = 'active'
"""


def _facts_from_row(row, *, links: int, verified: int) -> IndicatorFacts:
    return IndicatorFacts(
        code=row.code,
        name=row.name,
        unit_label=unit_label(row.unit_kind, row.custom_unit_label, row.currency_code),
        direction=row.direction,
        baseline_value=row.baseline_value,
        baseline_at=row.baseline_at,
        baseline_unavailable_reason=row.baseline_unavailable_reason,
        target_value=row.target_value,
        target_min=row.target_min,
        target_max=row.target_max,
        target_due_at=row.target_due_at,
        measurement_frequency_days=row.measurement_frequency_days,
        latest_value=row.latest_value,
        latest_measured_at=row.latest_measured_at,
        measurement_count=int(row.measurement_count or 0),
        activated_at=row.activated_at,
        evidence_link_count=links,
        verified_evidence_count=verified,
    )


def _evaluation_out(
    row, facts: IndicatorFacts, ev, *, owner_name: str | None
) -> TargetEvaluationOut:
    return TargetEvaluationOut(
        indicator_definition_id=row.id,
        indicator_code=facts.code,
        indicator_name=facts.name,
        unit_kind=row.unit_kind,
        unit_label=facts.unit_label,
        decimal_places=int(row.decimal_places),
        direction=facts.direction,
        state=ev.state,
        baseline_status=ev.baseline_status,
        substantiation=ev.substantiation,
        baseline_value=facts.baseline_value,
        baseline_at=facts.baseline_at,
        target_value=facts.target_value,
        target_min=facts.target_min,
        target_max=facts.target_max,
        target_due_at=facts.target_due_at,
        latest_value=facts.latest_value,
        latest_measured_at=facts.latest_measured_at,
        latest_measurement_id=row.latest_measurement_id,
        measurement_count=facts.measurement_count,
        evidence_link_count=facts.evidence_link_count,
        verified_evidence_count=facts.verified_evidence_count,
        next_measurement_due_at=ev.next_measurement_due_at,
        is_measurement_overdue=ev.is_measurement_overdue,
        owner_membership_id=row.owner_membership_id,
        owner_display_name=owner_name,
        headline=ev.headline,
        what_to_do_next=ev.what_to_do_next,
    )


def _evaluate(
    conn: Connection,
    org_id: UUID,
    *,
    where: str,
    params: dict,
    now: datetime | None = None,
) -> list[tuple]:
    """(row, facts, evaluation) per active indicator, evidence loaded in batch."""
    moment = now or _now()
    rows = conn.execute(
        text(f"{_INDICATOR_FACTS_SQL} {where} ORDER BY i.code"),
        {"org": org_id, **params},
    ).all()
    counts = _evidence_counts(
        conn, org_id, [r.latest_measurement_id for r in rows]
    )
    out = []
    for row in rows:
        links, verified = counts.get(row.latest_measurement_id, (0, 0))
        facts = _facts_from_row(row, links=links, verified=verified)
        out.append((row, facts, evaluation.evaluate_indicator(facts, moment)))
    return out


def evaluate_plan(
    conn: Connection, org_id: UUID, plan_id: UUID, *, now: datetime | None = None
) -> list[tuple]:
    return _evaluate(
        conn,
        org_id,
        where="AND i.measurement_plan_id = :pid",
        params={"pid": plan_id},
        now=now,
    )


_POSTURE_HEADLINE = {
    MeasurementPosture.not_planned.value: (
        "Ainda não há como provar que esta ação funcionou.",
        "Crie um plano de medição com pelo menos um indicador para acompanhar o "
        "resultado.",
    ),
    MeasurementPosture.awaiting_baseline.value: (
        "Falta o ponto de partida dos indicadores.",
        "Registre a linha de base (ou o motivo de não existir) para ativar o plano.",
    ),
    MeasurementPosture.awaiting_measurement.value: (
        "O plano está de pé, mas ainda não há medição depois da ação.",
        "Registre a primeira medição para saber se o resultado mudou.",
    ),
    MeasurementPosture.overdue.value: (
        "Há medição atrasada neste plano.",
        "Registre a medição pendente antes de decidir sobre a eficácia.",
    ),
    MeasurementPosture.on_time.value: (
        "As medições estão em dia.",
        "Continue acompanhando até a data-alvo dos indicadores.",
    ),
}


def _evaluations_out(conn: Connection, org_id: UUID, triples: list[tuple]):
    labels = _owner_labels(org_id, [row.owner_membership_id for row, _f, _e in triples])
    return [
        _evaluation_out(
            row,
            facts,
            ev,
            owner_name=(labels.get(row.owner_membership_id) or (None, None))[0],
        )
        for row, facts, ev in triples
    ]


def get_action_plan_summary(
    ctx: OrgContext, action_plan_id: UUID
) -> MeasurementSummaryOut:
    """Everything the board and the closure screen need, in one read."""
    require_role(ctx, *_READ_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        _fetch_action_plan_context(conn, ctx.organization_id, action_plan_id)
        plan_row = conn.execute(
            text(
                f"""
                SELECT {_PLAN_COLS}
                FROM action_measurement_plans
                WHERE organization_id = :org AND action_plan_id = :apid
                ORDER BY (status <> 'closed') DESC, created_at DESC
                LIMIT 1
                """
            ),
            {"org": ctx.organization_id, "apid": action_plan_id},
        ).first()
        if plan_row is None:
            headline, next_step = _POSTURE_HEADLINE[
                MeasurementPosture.not_planned.value
            ]
            return MeasurementSummaryOut(
                action_plan_id=action_plan_id,
                plan=None,
                measurement_posture=MeasurementPosture.not_planned.value,
                target_posture=TargetPosture.unknown.value,
                substantiation=SubstantiationLevel.none.value,
                headline=headline,
                what_to_do_next=next_step,
            )
        triples = evaluate_plan(conn, ctx.organization_id, plan_row.id)
        plan = _plan_out_with_counts(conn, ctx.organization_id, plan_row)
        evaluations_out = _evaluations_out(conn, ctx.organization_id, triples)

    evaluations = [ev for _row, _facts, ev in triples]
    posture = evaluation.measurement_posture(evaluations)
    headline, next_step = _POSTURE_HEADLINE[posture]
    return MeasurementSummaryOut(
        action_plan_id=action_plan_id,
        plan=plan,
        measurement_posture=posture,
        target_posture=evaluation.target_posture(evaluations),
        substantiation=evaluation.overall_substantiation(evaluations),
        baseline_status=evaluation.overall_baseline_status(evaluations),
        indicator_count=len(evaluations),
        overdue_indicator_count=sum(
            1 for e in evaluations if e.is_measurement_overdue
        ),
        evaluations=evaluations_out,
        headline=headline,
        what_to_do_next=next_step,
    )


def postures_by_action_plan(
    conn: Connection,
    org_id: UUID,
    action_plan_ids: list[UUID],
    *,
    now: datetime | None = None,
) -> dict[UUID, tuple[str, str, int]]:
    """(measurement_posture, target_posture, indicator_count) per ActionPlan.

    One query for the whole board — the execution board must never fan out per
    card to answer "is this action being measured?".
    """
    if not action_plan_ids:
        return {}
    triples = _evaluate(
        conn,
        org_id,
        where="AND p.action_plan_id = ANY(:ids) AND p.status <> 'closed'",
        params={"ids": action_plan_ids},
        now=now,
    )
    grouped: dict[UUID, list] = {}
    for row, _facts, ev in triples:
        grouped.setdefault(row.action_plan_id, []).append(ev)
    return {
        plan_id: (
            evaluation.measurement_posture(evs),
            evaluation.target_posture(evs),
            len(evs),
        )
        for plan_id, evs in grouped.items()
    }


def measurement_ids_for_case(
    conn: Connection, org_id: UUID, case_id: UUID, measurement_ids: list[UUID]
) -> set[UUID]:
    """Measurement ids from `measurement_ids` that belong to this case's chain."""
    if not measurement_ids:
        return set()
    rows = conn.execute(
        text(
            """
            SELECT mr.id
            FROM measurement_records mr
            JOIN action_measurement_plans amp
              ON amp.id = mr.measurement_plan_id
              AND amp.organization_id = mr.organization_id
            WHERE mr.organization_id = :org
              AND mr.id = ANY(:ids)
              AND amp.improvement_case_id = :cid
            """
        ),
        {"org": org_id, "ids": measurement_ids, "cid": case_id},
    ).all()
    return {r.id for r in rows}


def summarize_case_measurements(
    conn: Connection, org_id: UUID, case_id: UUID, *, now: datetime | None = None
) -> tuple[str, str, str, list]:
    """(measurement_posture, target_posture, substantiation, evaluations) for a case."""
    triples = _evaluate(
        conn,
        org_id,
        where="AND p.improvement_case_id = :cid",
        params={"cid": case_id},
        now=now,
    )
    evaluations = [ev for _row, _facts, ev in triples]
    return (
        evaluation.measurement_posture(evaluations),
        evaluation.target_posture(evaluations),
        evaluation.overall_substantiation(evaluations),
        _evaluations_out(conn, org_id, triples),
    )
