"""Audit plan document — 1:1 with assessment (not a second assessment state machine)."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text

from app.audit import write_audit
from app.auth.context import OrgContext
from app.db import tenant_connection
from app.errors import AppError
from app.modules.audit_plan.schemas import (
    AuditPlanCriteria,
    AuditPlanOut,
    AuditPlanPatch,
    AuditPlanProcess,
    AuditPlanReadiness,
    AuditPlanReadyIn,
    AuditPlanRefreshIn,
    AuditPlanSite,
    OrgRepresentative,
    ReadinessItem,
)
from app.modules.orgs.service import require_role

_MUTATE_ROLES = ("org_admin", "consultant_auditor", "quality_manager")
_READ_ROLES = _MUTATE_ROLES + ("process_owner", "reader")

_MODALITY_LABELS = {
    "diagnosis": "Diagnóstico inicial",
    "internal_audit": "Auditoria interna",
    "external_audit": "Auditoria externa",
    "certification_prep": "Preparação para certificação",
    "other": "Outro",
}

_DERIVABLE_FIELDS = frozenset(
    {
        "objective",
        "modality",
        "scope_text",
        "sites",
        "processes",
        "lead_membership_id",
        "team_membership_ids",
        "criteria",
    }
)


def _modality_from_assessment_type(assessment_type: str) -> str:
    if assessment_type in _MODALITY_LABELS:
        return assessment_type
    return "other"


def _empty_criteria() -> dict[str, Any]:
    return AuditPlanCriteria().model_dump()


def _parse_json(val: Any, default: Any):
    if val is None:
        return default
    if isinstance(val, str):
        return json.loads(val)
    return val


def _criteria_has_any(c: dict[str, Any]) -> bool:
    if c.get("iso9001_2015") or c.get("internal_processes") or c.get("legal_contractual"):
        return True
    if (c.get("additional_text") or "").strip():
        return True
    if (c.get("legal_contractual_text") or "").strip():
        return True
    return False


def _process_interview_coverage(conn, org_id: UUID, assessment_id: UUID, processes: list) -> bool:
    """True when every named process has an interview or justification."""
    if not processes:
        return True
    iv_rows = conn.execute(
        text(
            """
            SELECT process_name FROM interviews
            WHERE organization_id = :org
              AND assessment_id = :aid
              AND status <> 'cancelled'
              AND coalesce(nullif(trim(process_name), ''), '') <> ''
            """
        ),
        {"org": org_id, "aid": assessment_id},
    ).all()
    covered = {(r.process_name or "").strip().lower() for r in iv_rows}
    for p in processes:
        if not isinstance(p, dict):
            continue
        name = (p.get("name") or "").strip()
        if not name:
            continue
        just = (p.get("interview_justification") or "").strip()
        if name.lower() not in covered and not just:
            return False
    return True


def _meeting_flags(conn, org_id: UUID, assessment_id: UUID) -> tuple[bool, bool]:
    rows = conn.execute(
        text(
            """
            SELECT plan_activity_kind FROM agenda_events
            WHERE organization_id = :org
              AND assessment_id = :aid
              AND status <> 'cancelled'
              AND plan_activity_kind IN ('opening_meeting', 'closing_meeting')
            """
        ),
        {"org": org_id, "aid": assessment_id},
    ).all()
    kinds = {r.plan_activity_kind for r in rows}
    return "opening_meeting" in kinds, "closing_meeting" in kinds


def compute_readiness(row, conn=None, org_id: UUID | None = None) -> AuditPlanReadiness:
    criteria = _parse_json(row.criteria, _empty_criteria())
    processes = _parse_json(row.processes, [])
    items = [
        ReadinessItem(
            key="objective",
            label="Definir objetivo",
            done=bool((row.objective or "").strip()),
        ),
        ReadinessItem(
            key="scope",
            label="Confirmar escopo",
            done=bool((row.scope_text or "").strip()),
        ),
        ReadinessItem(
            key="criteria",
            label="Informar critérios",
            done=_criteria_has_any(criteria),
        ),
        ReadinessItem(
            key="processes",
            label="Confirmar processos",
            done=len(processes) >= 1,
        ),
        ReadinessItem(
            key="lead",
            label="Escolher auditor responsável",
            done=row.lead_membership_id is not None,
        ),
        ReadinessItem(
            key="period",
            label="Informar período",
            done=row.planned_start is not None and row.planned_end is not None,
        ),
    ]
    # Date order
    if row.planned_start and row.planned_end and row.planned_end < row.planned_start:
        items.append(
            ReadinessItem(
                key="period_order",
                label="Corrigir datas (término ≥ início)",
                done=False,
            )
        )

    if conn is not None and org_id is not None:
        has_opening, has_closing = _meeting_flags(conn, org_id, row.assessment_id)
        items.append(
            ReadinessItem(
                key="opening_meeting",
                label="Definir reunião de abertura",
                done=has_opening,
            )
        )
        items.append(
            ReadinessItem(
                key="closing_meeting",
                label="Definir reunião de encerramento",
                done=has_closing,
            )
        )
        items.append(
            ReadinessItem(
                key="process_interviews",
                label="Processos com entrevistas ou justificativa",
                done=_process_interview_coverage(
                    conn, org_id, row.assessment_id, processes
                ),
            )
        )

    completed = sum(1 for i in items if i.done)
    pending = [i for i in items if not i.done]
    percent = int(round(100 * completed / len(items))) if items else 0
    blockers = [i.label for i in pending if i.blocking]
    next_action = pending[0].label if pending else "Revisar plano"
    if not pending:
        if row.plan_status == "draft":
            next_action = "Concluir Plano"
        elif row.plan_status == "amended":
            next_action = "Revisar emenda e reconfirmar o plano (Concluir Plano)"
        else:
            next_action = (
                "Concluir planejamento — formaliza a avaliação como planejada"
            )
    return AuditPlanReadiness(
        ready=len(pending) == 0,
        completed_count=completed,
        pending_count=len(pending),
        percent=percent,
        items=items,
        next_action=next_action,
        blockers=blockers,
    )


def _editable_flags(assessment_status: str, plan_status: str) -> tuple[bool, bool]:
    """Returns (editable, requires_amendment_reason)."""
    if assessment_status in ("analysis", "actions", "report", "closed", "cancelled"):
        return False, False
    if assessment_status == "in_progress":
        return True, True  # only via amend path
    if assessment_status == "planned":
        if plan_status in ("ready", "amended"):
            return True, True
        return True, False
    # draft
    return True, False


def _row_to_out(
    row,
    assessment_status: str,
    *,
    conn=None,
    org_id: UUID | None = None,
) -> AuditPlanOut:
    criteria = AuditPlanCriteria.model_validate(_parse_json(row.criteria, _empty_criteria()))
    sites = [AuditPlanSite.model_validate(x) for x in _parse_json(row.sites, [])]
    processes = [AuditPlanProcess.model_validate(x) for x in _parse_json(row.processes, [])]
    reps = [OrgRepresentative.model_validate(x) for x in _parse_json(row.org_representatives, [])]
    sources = {str(k): str(v) for k, v in (_parse_json(row.field_sources, {}) or {}).items()}
    team_ids = list(row.team_membership_ids or [])
    editable, needs_reason = _editable_flags(assessment_status, row.plan_status)
    modality = row.modality or "diagnosis"
    readiness = compute_readiness(
        row,
        conn=conn,
        org_id=org_id or row.organization_id,
    )
    return AuditPlanOut(
        id=row.id,
        organization_id=row.organization_id,
        assessment_id=row.assessment_id,
        objective=row.objective or "",
        modality=modality,
        modality_label=_MODALITY_LABELS.get(modality, modality),
        scope_text=row.scope_text or "",
        criteria=criteria,
        sites=sites,
        processes=processes,
        lead_membership_id=row.lead_membership_id,
        team_membership_ids=team_ids,
        org_representatives=reps,
        planned_start=row.planned_start,
        planned_end=row.planned_end,
        preparation_notes=row.preparation_notes or "",
        risks_notes=row.risks_notes or "",
        plan_status=row.plan_status,
        field_sources=sources,
        last_amendment_reason=row.last_amendment_reason or "",
        readiness=readiness,
        editable=editable,
        requires_amendment_reason=needs_reason,
        updated_by_user_id=row.updated_by_user_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _load_guided_context(conn, org_id: UUID, assessment_id: UUID) -> dict[str, Any]:
    row = conn.execute(
        text(
            """
            SELECT context FROM guided_sessions
            WHERE assessment_id = :aid AND organization_id = :org
            """
        ),
        {"aid": assessment_id, "org": org_id},
    ).first()
    if row is None:
        return {}
    ctx = row.context
    if isinstance(ctx, str):
        ctx = json.loads(ctx)
    return ctx or {}


def _team_ids(conn, org_id: UUID, assessment_id: UUID) -> list[UUID]:
    rows = conn.execute(
        text(
            """
            SELECT membership_id FROM assessment_team_members
            WHERE assessment_id = :aid AND organization_id = :org
            ORDER BY created_at
            """
        ),
        {"aid": assessment_id, "org": org_id},
    ).all()
    return [r.membership_id for r in rows]


def _derive_defaults(conn, org_id: UUID, assessment) -> dict[str, Any]:
    ctx = _load_guided_context(conn, org_id, assessment.id)
    qms = ctx.get("qms_scope") or {}
    profile = ctx.get("organization_profile") or {}
    scope_parts = []
    if (qms.get("description") or "").strip():
        scope_parts.append(str(qms["description"]).strip())
    if (qms.get("exclusions") or "").strip():
        scope_parts.append(f"Exclusões: {str(qms['exclusions']).strip()}")
    products = ctx.get("products_services") or []
    if products:
        names = ", ".join(
            (p.get("name") or "").strip() for p in products if (p.get("name") or "").strip()
        )
        if names:
            scope_parts.append(f"Produtos/serviços: {names}")

    trade = (profile.get("trade_name") or "").strip()
    modality = _modality_from_assessment_type(assessment.type)
    label = _MODALITY_LABELS.get(modality, "Avaliação")
    objective = ""
    if trade:
        objective = (
            f"Realizar {label.lower()} do sistema de gestão da qualidade de {trade}, "
            "com base nas informações preparadas, para organizar o percurso de avaliação."
        )
    else:
        objective = (
            f"Realizar {label.lower()} do sistema de gestão da qualidade, "
            "organizando propósito, processos e pessoas envolvidas."
        )

    sites = [
        {
            "name": (s.get("name") or "").strip(),
            "location": (s.get("location") or "").strip(),
            "notes": (s.get("notes") or "").strip(),
            "from_preparation": True,
        }
        for s in (ctx.get("sites") or [])
        if (s.get("name") or "").strip()
    ]
    processes = [
        {
            "name": (p.get("name") or "").strip(),
            "owner": (p.get("owner") or "").strip(),
            "notes": (p.get("notes") or "").strip(),
            "from_preparation": True,
        }
        for p in (ctx.get("processes") or [])
        if (p.get("name") or "").strip()
    ]
    team = _team_ids(conn, org_id, assessment.id)
    sources = {f: "preparation" for f in _DERIVABLE_FIELDS}
    sources["modality"] = "assessment"
    sources["lead_membership_id"] = "assessment"
    sources["team_membership_ids"] = "assessment"

    return {
        "objective": objective,
        "modality": modality,
        "scope_text": "\n\n".join(scope_parts),
        "criteria": _empty_criteria(),
        "sites": sites,
        "processes": processes,
        "lead_membership_id": assessment.lead_membership_id,
        "team_membership_ids": team,
        "field_sources": sources,
    }


def _assessment(conn, org_id: UUID, assessment_id: UUID, *, for_update: bool = False):
    sql = """
        SELECT id, organization_id, status, type, lead_membership_id
        FROM assessments
        WHERE id = :id AND organization_id = :org
    """
    if for_update:
        sql += " FOR UPDATE"
    row = conn.execute(text(sql), {"id": assessment_id, "org": org_id}).first()
    if row is None:
        raise AppError("not_found", "Avaliação não encontrada", status_code=404)
    return row


def _get_plan_row(conn, org_id: UUID, assessment_id: UUID, *, for_update: bool = False):
    sql = """
        SELECT * FROM assessment_audit_plans
        WHERE assessment_id = :aid AND organization_id = :org
    """
    if for_update:
        sql += " FOR UPDATE"
    return conn.execute(text(sql), {"aid": assessment_id, "org": org_id}).first()


def get_or_create(ctx: OrgContext, assessment_id: UUID) -> AuditPlanOut:
    require_role(ctx, *_READ_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        assessment = _assessment(conn, ctx.organization_id, assessment_id)
        row = _get_plan_row(conn, ctx.organization_id, assessment_id)
        if row is None:
            require_role(ctx, *_MUTATE_ROLES)
            if assessment.status in ("closed", "cancelled"):
                raise AppError(
                    "conflict",
                    "Não é possível criar plano em avaliação encerrada ou cancelada",
                    status_code=409,
                )
            derived = _derive_defaults(conn, ctx.organization_id, assessment)
            row = conn.execute(
                text(
                    """
                    INSERT INTO assessment_audit_plans (
                      organization_id, assessment_id, objective, modality, scope_text,
                      criteria, sites, processes, lead_membership_id, team_membership_ids,
                      field_sources, updated_by_user_id
                    ) VALUES (
                      :org, :aid, :obj, :mod, :scope,
                      CAST(:crit AS jsonb), CAST(:sites AS jsonb), CAST(:procs AS jsonb),
                      :lead, CAST(:team AS uuid[]), CAST(:sources AS jsonb), :uid
                    )
                    RETURNING *
                    """
                ),
                {
                    "org": ctx.organization_id,
                    "aid": assessment_id,
                    "obj": derived["objective"],
                    "mod": derived["modality"],
                    "scope": derived["scope_text"],
                    "crit": json.dumps(derived["criteria"]),
                    "sites": json.dumps(derived["sites"]),
                    "procs": json.dumps(derived["processes"]),
                    "lead": derived["lead_membership_id"],
                    "team": "{" + ",".join(str(x) for x in derived["team_membership_ids"]) + "}",
                    "sources": json.dumps(derived["field_sources"]),
                    "uid": ctx.principal.user_id,
                },
            ).one()
            write_audit(
                conn,
                organization_id=ctx.organization_id,
                actor_type="user",
                actor_user_id=ctx.principal.user_id,
                actor_membership_id=ctx.membership_id,
                action="audit_plan.create",
                resource_type="assessment_audit_plan",
                resource_id=row.id,
                metadata={
                    "assessment_id": str(assessment_id),
                    "derived_from_preparation": True,
                },
            )
            conn.commit()
        out = _row_to_out(
            row, assessment.status, conn=conn, org_id=ctx.organization_id
        )
        return out


def _check_concurrency(row, expected: datetime | None) -> None:
    if expected is None:
        return
    # Compare with second precision to tolerate serialization differences
    cur = row.updated_at
    if cur.tzinfo and expected.tzinfo is None:
        expected = expected.replace(tzinfo=cur.tzinfo)
    if abs((cur - expected).total_seconds()) > 0.5:
        raise AppError(
            "conflict",
            "O plano foi alterado por outra sessão — recarregue e tente novamente",
            status_code=409,
        )


def patch_plan(ctx: OrgContext, assessment_id: UUID, payload: AuditPlanPatch) -> AuditPlanOut:
    require_role(ctx, *_MUTATE_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        assessment = _assessment(
            conn, ctx.organization_id, assessment_id, for_update=True
        )
        row = _get_plan_row(
            conn, ctx.organization_id, assessment_id, for_update=True
        )
        if row is None:
            raise AppError("not_found", "Plano da auditoria não encontrado", status_code=404)

        editable, needs_reason = _editable_flags(assessment.status, row.plan_status)
        if not editable and assessment.status != "in_progress":
            raise AppError(
                "conflict",
                "Plano somente leitura nesta fase da avaliação",
                status_code=409,
            )
        if assessment.status == "in_progress" or needs_reason:
            reason = (payload.amendment_reason or "").strip()
            if not reason:
                raise AppError(
                    "validation_error",
                    "Informe o motivo da emenda/ajuste do plano",
                    status_code=422,
                )

        _check_concurrency(row, payload.expected_updated_at)

        sources = dict(_parse_json(row.field_sources, {}) or {})
        fields: dict[str, Any] = {}
        data = payload.model_dump(exclude_unset=True)
        data.pop("expected_updated_at", None)
        data.pop("amendment_reason", None)

        mapping = {
            "objective": "objective",
            "modality": "modality",
            "scope_text": "scope_text",
            "preparation_notes": "preparation_notes",
            "risks_notes": "risks_notes",
            "planned_start": "planned_start",
            "planned_end": "planned_end",
            "lead_membership_id": "lead_membership_id",
        }
        for key, col in mapping.items():
            if key in data:
                fields[col] = data[key]
                sources[key] = "manual"

        if "criteria" in data and data["criteria"] is not None:
            fields["criteria"] = json.dumps(
                payload.criteria.model_dump() if payload.criteria else _empty_criteria()
            )
            sources["criteria"] = "manual"
        if "sites" in data and data["sites"] is not None:
            fields["sites"] = json.dumps(
                [s.model_dump() for s in (payload.sites or [])]
            )
            sources["sites"] = "manual"
        if "processes" in data and data["processes"] is not None:
            fields["processes"] = json.dumps(
                [p.model_dump() for p in (payload.processes or [])]
            )
            sources["processes"] = "manual"
        if "org_representatives" in data and data["org_representatives"] is not None:
            fields["org_representatives"] = json.dumps(
                [r.model_dump() for r in (payload.org_representatives or [])]
            )
            sources["org_representatives"] = "manual"
        if "team_membership_ids" in data and data["team_membership_ids"] is not None:
            ids = payload.team_membership_ids or []
            fields["team_membership_ids"] = "{" + ",".join(str(x) for x in ids) + "}"
            sources["team_membership_ids"] = "manual"

        if not fields:
            out = _row_to_out(
                row, assessment.status, conn=conn, org_id=ctx.organization_id
            )
            conn.commit()
            return out

        start = fields.get("planned_start", row.planned_start)
        end = fields.get("planned_end", row.planned_end)
        if start and end and end < start:
            raise AppError(
                "validation_error",
                "Data de término deve ser igual ou posterior à data de início",
                status_code=422,
            )

        new_status = row.plan_status
        amendment_reason = row.last_amendment_reason or ""
        if needs_reason or assessment.status == "in_progress":
            new_status = "amended"
            amendment_reason = (payload.amendment_reason or "").strip()
        elif new_status == "ready" and assessment.status == "draft":
            # Editing a ready plan in draft returns to draft until re-validated
            new_status = "draft"

        params = {
            **fields,
            "field_sources": json.dumps(sources),
            "plan_status": new_status,
            "last_amendment_reason": amendment_reason,
            "uid": ctx.principal.user_id,
            "aid": assessment_id,
            "org": ctx.organization_id,
        }
        # criteria/sites/processes already JSON strings; fix CAST for jsonb cols
        sql_sets = []
        for k in fields:
            if k in ("criteria", "sites", "processes", "org_representatives"):
                sql_sets.append(f"{k} = CAST(:{k} AS jsonb)")
            elif k == "team_membership_ids":
                sql_sets.append(f"{k} = CAST(:{k} AS uuid[])")
            else:
                sql_sets.append(f"{k} = :{k}")
        sql_sets.extend(
            [
                "field_sources = CAST(:field_sources AS jsonb)",
                "plan_status = :plan_status",
                "last_amendment_reason = :last_amendment_reason",
                "updated_by_user_id = :uid",
                "updated_at = now()",
            ]
        )

        updated = conn.execute(
            text(
                f"""
                UPDATE assessment_audit_plans
                SET {", ".join(sql_sets)}
                WHERE assessment_id = :aid AND organization_id = :org
                RETURNING *
                """
            ),
            params,
        ).one()

        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="audit_plan.update",
            resource_type="assessment_audit_plan",
            resource_id=updated.id,
            metadata={
                "assessment_id": str(assessment_id),
                "fields": list(fields.keys()),
                "plan_status": new_status,
                "amendment": bool(needs_reason or assessment.status == "in_progress"),
            },
        )
        # Before commit: RLS session GUCs still apply for agenda readiness lookups.
        out = _row_to_out(
            updated, assessment.status, conn=conn, org_id=ctx.organization_id
        )
        conn.commit()
        return out


def mark_ready(ctx: OrgContext, assessment_id: UUID, payload: AuditPlanReadyIn) -> AuditPlanOut:
    """Concluir Plano: plan_status=ready. Não altera o status da avaliação."""
    require_role(ctx, *_MUTATE_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        assessment = _assessment(
            conn, ctx.organization_id, assessment_id, for_update=True
        )
        if assessment.status not in ("draft", "planned"):
            raise AppError(
                "conflict",
                "Só é possível marcar o plano como pronto em draft ou planned",
                status_code=409,
            )
        row = _get_plan_row(
            conn, ctx.organization_id, assessment_id, for_update=True
        )
        if row is None:
            raise AppError("not_found", "Plano da auditoria não encontrado", status_code=404)
        _check_concurrency(row, payload.expected_updated_at)
        readiness = compute_readiness(
            row, conn=conn, org_id=ctx.organization_id
        )
        if not readiness.ready:
            raise AppError(
                "validation_error",
                "Plano incompleto: " + "; ".join(readiness.blockers),
                status_code=422,
            )
        from_status = row.plan_status
        # Idempotent when already ready
        if from_status == "ready":
            out = _row_to_out(
                row, assessment.status, conn=conn, org_id=ctx.organization_id
            )
            conn.commit()
            return out
        updated = conn.execute(
            text(
                """
                UPDATE assessment_audit_plans
                SET plan_status = 'ready',
                    updated_by_user_id = :uid,
                    updated_at = now()
                WHERE assessment_id = :aid AND organization_id = :org
                RETURNING *
                """
            ),
            {
                "uid": ctx.principal.user_id,
                "aid": assessment_id,
                "org": ctx.organization_id,
            },
        ).one()
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="audit_plan.ready",
            resource_type="assessment_audit_plan",
            resource_id=updated.id,
            from_status=from_status,
            to_status="ready",
            metadata={
                "assessment_id": str(assessment_id),
                "reconfirm_after_amendment": from_status == "amended",
            },
        )
        # Build response before commit — after commit, SET LOCAL RLS GUCs are gone
        # and agenda_events lookups would falsely look empty.
        out = _row_to_out(
            updated, assessment.status, conn=conn, org_id=ctx.organization_id
        )
        conn.commit()
        return out


def refresh_from_preparation(
    ctx: OrgContext, assessment_id: UUID, payload: AuditPlanRefreshIn
) -> AuditPlanOut:
    """Fill empty (or still-preparation-sourced) fields from Wizard. No silent overwrite of manual."""
    require_role(ctx, *_MUTATE_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        assessment = _assessment(
            conn, ctx.organization_id, assessment_id, for_update=True
        )
        row = _get_plan_row(
            conn, ctx.organization_id, assessment_id, for_update=True
        )
        if row is None:
            raise AppError("not_found", "Plano da auditoria não encontrado", status_code=404)
        editable, needs_reason = _editable_flags(assessment.status, row.plan_status)
        if not editable:
            raise AppError("conflict", "Plano somente leitura nesta fase", status_code=409)
        if needs_reason:
            raise AppError(
                "conflict",
                "Use atualização com motivo de emenda nesta fase",
                status_code=409,
            )

        derived = _derive_defaults(conn, ctx.organization_id, assessment)
        sources = dict(_parse_json(row.field_sources, {}) or {})

        def can_fill(field: str, current_empty: bool) -> bool:
            src = sources.get(field)
            if src == "manual":
                return False
            if current_empty:
                return True
            if src in ("preparation", "assessment") and payload.confirm_overwrite_preparation:
                return True
            return False

        updates: dict[str, Any] = {}
        if can_fill("objective", not (row.objective or "").strip()):
            updates["objective"] = derived["objective"]
            sources["objective"] = "preparation"
        if can_fill("scope_text", not (row.scope_text or "").strip()):
            updates["scope_text"] = derived["scope_text"]
            sources["scope_text"] = "preparation"
        if can_fill("modality", False):
            updates["modality"] = derived["modality"]
            sources["modality"] = "assessment"
        if can_fill("sites", len(_parse_json(row.sites, [])) == 0):
            updates["sites"] = json.dumps(derived["sites"])
            sources["sites"] = "preparation"
        if can_fill("processes", len(_parse_json(row.processes, [])) == 0):
            updates["processes"] = json.dumps(derived["processes"])
            sources["processes"] = "preparation"
        if can_fill("lead_membership_id", row.lead_membership_id is None):
            updates["lead_membership_id"] = derived["lead_membership_id"]
            sources["lead_membership_id"] = "assessment"
        if can_fill("team_membership_ids", len(row.team_membership_ids or []) == 0):
            updates["team_membership_ids"] = (
                "{" + ",".join(str(x) for x in derived["team_membership_ids"]) + "}"
            )
            sources["team_membership_ids"] = "assessment"

        if not updates:
            return _row_to_out(
                row, assessment.status, conn=conn, org_id=ctx.organization_id
            )

        sql_sets = []
        for k in updates:
            if k in ("sites", "processes"):
                sql_sets.append(f"{k} = CAST(:{k} AS jsonb)")
            elif k == "team_membership_ids":
                sql_sets.append(f"{k} = CAST(:{k} AS uuid[])")
            else:
                sql_sets.append(f"{k} = :{k}")
        sql_sets.extend(
            [
                "field_sources = CAST(:field_sources AS jsonb)",
                "updated_by_user_id = :uid",
                "updated_at = now()",
            ]
        )
        params = {
            **updates,
            "field_sources": json.dumps(sources),
            "uid": ctx.principal.user_id,
            "aid": assessment_id,
            "org": ctx.organization_id,
        }
        updated = conn.execute(
            text(
                f"""
                UPDATE assessment_audit_plans
                SET {", ".join(sql_sets)}
                WHERE assessment_id = :aid AND organization_id = :org
                RETURNING *
                """
            ),
            params,
        ).one()
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="audit_plan.refresh_preparation",
            resource_type="assessment_audit_plan",
            resource_id=updated.id,
            metadata={"fields": list(updates.keys())},
        )
        conn.commit()
        return _row_to_out(
            updated, assessment.status, conn=conn, org_id=ctx.organization_id
        )
