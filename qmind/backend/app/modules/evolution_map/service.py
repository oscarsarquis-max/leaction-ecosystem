"""Evolution Map service — generate/list/review deterministic suggestions."""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import text

from app.audit import write_audit
from app.auth.context import OrgContext
from app.db import tenant_connection
from app.errors import AppError
from app.modules.evolution_map.catalog import CATALOG_VERSION, rules_by_id
from app.modules.evolution_map.engine import (
    ActionItemFact,
    AssessmentFacts,
    EvidenceFact,
    FindingFact,
    GuidedAnswerFact,
    MaturityScoreFact,
    evaluate_rules,
    fingerprint_facts,
    source_snapshot,
)
from app.modules.evolution_map.schemas import (
    ConvertSuggestionToActionIn,
    ConvertSuggestionToActionOut,
    DismissSuggestionIn,
    EvolutionGenerateIn,
    EvolutionPackageOut,
    EvolutionRegenerationDiff,
    EvolutionSuggestionOut,
    InvestigateSuggestionIn,
    SourceReference,
)
from app.modules.orgs.service import require_role
from app.schemas.enums import EvolutionGenerationMode, EvolutionSuggestionStatus

_READ_ROLES = (
    "org_admin",
    "consultant_auditor",
    "quality_manager",
    "process_owner",
    "reader",
)
_REVIEW_ROLES = ("org_admin", "consultant_auditor", "quality_manager")
_GENERATE_ROLES = ("org_admin", "consultant_auditor", "quality_manager")

_PRESERVE_STATUSES = {
    EvolutionSuggestionStatus.accepted.value,
    EvolutionSuggestionStatus.dismissed.value,
    EvolutionSuggestionStatus.converted_to_action.value,
}

MAX_PRIORITY = 10

_PACKAGE_COLS = """
    id, organization_id, assessment_id, package_version, generation_mode, status,
    supersedes_id, source_fingerprint, source_snapshot, catalog_version,
    generated_by, generated_at, created_at, updated_at
"""

_SUGGESTION_COLS = """
    id, organization_id, assessment_id, package_id, package_version,
    rule_id, rule_version, category, title, observation, business_rationale,
    suggested_evolution, expected_benefit, first_step, impact, effort,
    priority, confidence, is_priority, source_references, status, dismiss_reason,
    investigate_note, generated_at, generated_by, reviewed_at, reviewed_by,
    created_at, updated_at
"""


def _parse_refs(raw: Any) -> list[SourceReference]:
    if isinstance(raw, str):
        raw = json.loads(raw)
    if not isinstance(raw, list):
        return []
    return [SourceReference.model_validate(x) for x in raw]


def _suggestion_out(
    row,
    *,
    action_item_id=None,
    action_plan_id=None,
) -> EvolutionSuggestionOut:
    rule = rules_by_id().get(row.rule_id)
    clauses = list(rule.related_clauses) if rule else []
    return EvolutionSuggestionOut(
        id=row.id,
        organization_id=row.organization_id,
        assessment_id=row.assessment_id,
        package_id=row.package_id,
        package_version=int(row.package_version),
        rule_id=row.rule_id,
        rule_version=row.rule_version,
        category=row.category,
        title=row.title,
        observation=row.observation,
        business_rationale=row.business_rationale,
        suggested_evolution=row.suggested_evolution,
        expected_benefit=row.expected_benefit,
        first_step=row.first_step,
        impact=row.impact,
        effort=row.effort,
        priority=row.priority,
        confidence=row.confidence,
        is_priority=bool(row.is_priority),
        source_references=_parse_refs(row.source_references),
        related_clauses=clauses,
        status=row.status,
        dismiss_reason=row.dismiss_reason,
        investigate_note=getattr(row, "investigate_note", None),
        action_item_id=action_item_id,
        action_plan_id=action_plan_id,
        generated_at=row.generated_at,
        generated_by=row.generated_by,
        reviewed_at=row.reviewed_at,
        reviewed_by=row.reviewed_by,
    )


def _action_links_for_suggestions(conn, org_id, suggestion_ids: list) -> dict:
    if not suggestion_ids:
        return {}
    rows = conn.execute(
        text(
            """
            SELECT id, action_plan_id, source_evolution_suggestion_id
            FROM action_items
            WHERE organization_id = :org
              AND source_evolution_suggestion_id = ANY(CAST(:ids AS uuid[]))
            """
        ),
        {"org": org_id, "ids": [str(x) for x in suggestion_ids]},
    ).all()
    return {
        r.source_evolution_suggestion_id: (r.id, r.action_plan_id) for r in rows
    }


def _enrich_suggestions(conn, org_id, sug_rows) -> list[EvolutionSuggestionOut]:
    links = _action_links_for_suggestions(
        conn, org_id, [s.id for s in sug_rows]
    )
    out: list[EvolutionSuggestionOut] = []
    for s in sug_rows:
        link = links.get(s.id)
        out.append(
            _suggestion_out(
                s,
                action_item_id=link[0] if link else None,
                action_plan_id=link[1] if link else None,
            )
        )
    return out


def _package_out(
    row,
    suggestions: list[EvolutionSuggestionOut],
    *,
    regeneration_diff: EvolutionRegenerationDiff | None = None,
) -> EvolutionPackageOut:
    snap = row.source_snapshot
    if isinstance(snap, str):
        snap = json.loads(snap)
    priority = [s for s in suggestions if s.is_priority]
    secondary = [s for s in suggestions if not s.is_priority]
    return EvolutionPackageOut(
        id=row.id,
        organization_id=row.organization_id,
        assessment_id=row.assessment_id,
        package_version=int(row.package_version),
        generation_mode=row.generation_mode,
        status=row.status,
        supersedes_id=row.supersedes_id,
        source_fingerprint=row.source_fingerprint,
        source_snapshot=snap or {},
        catalog_version=row.catalog_version,
        generated_at=row.generated_at,
        generated_by=row.generated_by,
        priority_suggestions=priority,
        secondary_suggestions=secondary,
        regeneration_diff=regeneration_diff,
    )


def _resolve_mode(
    assessment_status: str, requested: EvolutionGenerationMode | None
) -> EvolutionGenerationMode:
    if requested is not None:
        return requested
    if assessment_status in ("analysis", "actions", "report", "closed"):
        return EvolutionGenerationMode.analysis_ready
    return EvolutionGenerationMode.preliminary


def _load_facts(
    conn, *, org_id: UUID, assessment_id: UUID, mode: EvolutionGenerationMode, status: str
) -> AssessmentFacts:
    facts = AssessmentFacts(
        assessment_id=assessment_id,
        organization_id=org_id,
        status=status,
        generation_mode=mode,
    )

    # Wizard context from guided session
    sess = conn.execute(
        text(
            """
            SELECT context
            FROM guided_sessions
            WHERE assessment_id = :aid AND organization_id = :org
            ORDER BY updated_at DESC NULLS LAST, created_at DESC
            LIMIT 1
            """
        ),
        {"aid": assessment_id, "org": org_id},
    ).first()
    if sess and sess.context:
        ctx = sess.context
        if isinstance(ctx, str):
            ctx = json.loads(ctx)
        if isinstance(ctx, dict):
            facts.context = ctx

    answers = conn.execute(
        text(
            """
            SELECT ga.id, ga.question_id, ga.question_version, ga.answer_value,
                   ga.evidence_mode, ga.provide_later, ga.description
            FROM guided_answers ga
            JOIN guided_sessions gs ON gs.id = ga.session_id
            WHERE gs.assessment_id = :aid AND ga.organization_id = :org
            """
        ),
        {"aid": assessment_id, "org": org_id},
    ).all()
    for a in answers:
        facts.answers.append(
            GuidedAnswerFact(
                answer_id=a.id,
                question_id=a.question_id,
                question_version=a.question_version or "1",
                answer_value=a.answer_value,
                evidence_mode=a.evidence_mode or "none",
                provide_later=bool(a.provide_later),
                description=a.description or "",
            )
        )

    evidences = conn.execute(
        text(
            """
            SELECT DISTINCT e.id, e.status, gae.question_id
            FROM evidences e
            LEFT JOIN guided_answer_evidences gae
              ON gae.evidence_id = e.id AND gae.organization_id = e.organization_id
            WHERE e.organization_id = :org
              AND (
                e.assessment_id = :aid
                OR gae.assessment_id = :aid
              )
            """
        ),
        {"aid": assessment_id, "org": org_id},
    ).all()
    for e in evidences:
        facts.evidences.append(
            EvidenceFact(
                evidence_id=e.id,
                status=e.status,
                linked_question_id=e.question_id,
            )
        )

    findings = conn.execute(
        text(
            """
            SELECT id, status, finding_type, title, body
            FROM findings
            WHERE assessment_id = :aid AND organization_id = :org
              AND status NOT IN ('discarded', 'withdrawn')
            """
        ),
        {"aid": assessment_id, "org": org_id},
    ).all()
    for f in findings:
        body = (f.body or "").lower()
        has_cause = any(
            k in body for k in ("causa", "porque", "por que", "root cause", "motivo raiz")
        )
        facts.findings.append(
            FindingFact(
                finding_id=f.id,
                status=f.status,
                finding_type=f.finding_type,
                title=f.title or "",
                has_cause=has_cause,
            )
        )

    items = conn.execute(
        text(
            """
            SELECT ai.id, ai.status, ai.finding_id
            FROM action_items ai
            JOIN action_plans ap ON ap.id = ai.action_plan_id
            WHERE ap.assessment_id = :aid AND ai.organization_id = :org
            """
        ),
        {"aid": assessment_id, "org": org_id},
    ).all()
    for i in items:
        facts.action_items.append(
            ActionItemFact(item_id=i.id, status=i.status, finding_id=i.finding_id)
        )

    if mode == EvolutionGenerationMode.analysis_ready:
        scores = conn.execute(
            text(
                """
                SELECT ma.id AS package_id, s.criterion_id, d.code AS dimension_code,
                       s.level, s.applicability
                FROM maturity_assessments ma
                JOIN maturity_scores s ON s.maturity_assessment_id = ma.id
                LEFT JOIN maturity_criteria c ON c.id = s.criterion_id
                LEFT JOIN maturity_dimensions d ON d.id = c.maturity_dimension_id
                WHERE ma.assessment_id = :aid
                  AND ma.organization_id = :org
                  AND ma.status = 'approved'
                """
            ),
            {"aid": assessment_id, "org": org_id},
        ).all()
        for s in scores:
            facts.maturity_scores.append(
                MaturityScoreFact(
                    maturity_assessment_id=s.package_id,
                    criterion_id=s.criterion_id,
                    dimension_code=s.dimension_code,
                    level=s.level,
                    applicability=s.applicability,
                )
            )

    return facts


def get_active_package(ctx: OrgContext, assessment_id: UUID) -> EvolutionPackageOut | None:
    require_role(ctx, *_READ_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        assessment = conn.execute(
            text(
                """
                SELECT id FROM assessments
                WHERE id = :id AND organization_id = :org
                """
            ),
            {"id": assessment_id, "org": ctx.organization_id},
        ).first()
        if assessment is None:
            raise AppError("not_found", "Assessment not found", status_code=404)
        row = conn.execute(
            text(
                f"""
                SELECT {_PACKAGE_COLS}
                FROM evolution_suggestion_packages
                WHERE assessment_id = :aid AND organization_id = :org AND status = 'active'
                """
            ),
            {"aid": assessment_id, "org": ctx.organization_id},
        ).first()
        if row is None:
            return None
        sug_rows = conn.execute(
            text(
                f"""
                SELECT {_SUGGESTION_COLS}
                FROM evolution_suggestions
                WHERE package_id = :pid AND organization_id = :org
                ORDER BY is_priority DESC, priority, title
                """
            ),
            {"pid": row.id, "org": ctx.organization_id},
        ).all()
        suggestions = _enrich_suggestions(conn, ctx.organization_id, sug_rows)
    return _package_out(row, suggestions)


def get_suggestion(ctx: OrgContext, suggestion_id: UUID) -> EvolutionSuggestionOut:
    require_role(ctx, *_READ_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        row = conn.execute(
            text(
                f"""
                SELECT {_SUGGESTION_COLS}
                FROM evolution_suggestions
                WHERE id = :id AND organization_id = :org
                """
            ),
            {"id": suggestion_id, "org": ctx.organization_id},
        ).first()
        if row is None:
            raise AppError("not_found", "Suggestion not found", status_code=404)
        suggestions = _enrich_suggestions(conn, ctx.organization_id, [row])
    return suggestions[0]


def generate_package(
    ctx: OrgContext, assessment_id: UUID, payload: EvolutionGenerateIn | None = None
) -> EvolutionPackageOut:
    require_role(ctx, *_GENERATE_ROLES)
    payload = payload or EvolutionGenerateIn()

    with tenant_connection(ctx.organization_id) as conn:
        assessment = conn.execute(
            text(
                """
                SELECT id, status FROM assessments
                WHERE id = :id AND organization_id = :org
                """
            ),
            {"id": assessment_id, "org": ctx.organization_id},
        ).first()
        if assessment is None:
            raise AppError("not_found", "Assessment not found", status_code=404)

        mode = _resolve_mode(assessment.status, payload.mode)
        if mode == EvolutionGenerationMode.analysis_ready and assessment.status in (
            "draft",
            "planned",
        ):
            raise AppError(
                "generation_not_allowed",
                "analysis_ready exige avaliação em análise ou fase posterior",
                status_code=409,
            )

        facts = _load_facts(
            conn,
            org_id=ctx.organization_id,
            assessment_id=assessment_id,
            mode=mode,
            status=assessment.status,
        )
        fp = fingerprint_facts(facts)
        snap = source_snapshot(facts)

        active = conn.execute(
            text(
                f"""
                SELECT {_PACKAGE_COLS}
                FROM evolution_suggestion_packages
                WHERE assessment_id = :aid AND organization_id = :org AND status = 'active'
                FOR UPDATE
                """
            ),
            {"aid": assessment_id, "org": ctx.organization_id},
        ).first()

        if active and active.source_fingerprint == fp and active.generation_mode == mode.value:
            # Idempotent return
            sug_rows = conn.execute(
                text(
                    f"""
                    SELECT {_SUGGESTION_COLS}
                    FROM evolution_suggestions
                    WHERE package_id = :pid AND organization_id = :org
                    ORDER BY is_priority DESC, priority, title
                    """
                ),
                {"pid": active.id, "org": ctx.organization_id},
            ).all()
            suggestions = _enrich_suggestions(conn, ctx.organization_id, sug_rows)
            conn.commit()
            return _package_out(active, suggestions)

        preserved: dict[str, Any] = {}
        previous_rule_ids: set[str] = set()
        if active:
            prev_all = conn.execute(
                text(
                    f"""
                    SELECT {_SUGGESTION_COLS}
                    FROM evolution_suggestions
                    WHERE package_id = :pid AND organization_id = :org
                    """
                ),
                {"pid": active.id, "org": ctx.organization_id},
            ).all()
            previous_rule_ids = {p.rule_id for p in prev_all}
            for p in prev_all:
                if p.status in _PRESERVE_STATUSES:
                    preserved[p.rule_id] = p

        candidates = evaluate_rules(facts)
        # Keep preserved rules even if not rematched (carry forward)
        for rule_id, prow in preserved.items():
            if not any(c.rule.rule_id == rule_id for c in candidates):
                # synthetic carry — will copy fields from preserved row
                pass

        version_no = 1
        if active:
            version_no = int(active.package_version) + 1
            conn.execute(
                text(
                    """
                    UPDATE evolution_suggestion_packages
                    SET status = 'superseded', updated_at = now()
                    WHERE id = :id AND organization_id = :org
                    """
                ),
                {"id": active.id, "org": ctx.organization_id},
            )
            conn.execute(
                text(
                    """
                    UPDATE evolution_suggestions
                    SET status = CASE
                          WHEN status IN ('accepted', 'dismissed', 'converted_to_action')
                            THEN status
                          ELSE 'superseded'
                        END,
                        updated_at = now()
                    WHERE package_id = :pid AND organization_id = :org
                      AND status = 'proposed'
                    """
                ),
                {"pid": active.id, "org": ctx.organization_id},
            )

        package_id = uuid4()
        conn.execute(
            text(
                f"""
                INSERT INTO evolution_suggestion_packages (
                  id, organization_id, assessment_id, package_version, generation_mode,
                  status, supersedes_id, source_fingerprint, source_snapshot,
                  catalog_version, generated_by
                ) VALUES (
                  :id, :org, :aid, :ver, :mode,
                  'active', :sup, :fp, CAST(:snap AS jsonb),
                  :cat, :by
                )
                """
            ),
            {
                "id": package_id,
                "org": ctx.organization_id,
                "aid": assessment_id,
                "ver": version_no,
                "mode": mode.value,
                "sup": active.id if active else None,
                "fp": fp,
                "snap": json.dumps(snap),
                "cat": CATALOG_VERSION,
                "by": ctx.membership_id,
            },
        )

        # Merge candidates with preserved statuses
        ranked = candidates
        priority_ids: set[str] = set()
        for i, c in enumerate(ranked):
            if i < MAX_PRIORITY:
                priority_ids.add(c.rule.rule_id)

        inserted_rules: set[str] = set()
        for c in ranked:
            prev = preserved.get(c.rule.rule_id)
            status = prev.status if prev else "proposed"
            dismiss_reason = prev.dismiss_reason if prev else None
            reviewed_at = prev.reviewed_at if prev else None
            reviewed_by = prev.reviewed_by if prev else None
            sid = uuid4()
            conn.execute(
                text(
                    """
                    INSERT INTO evolution_suggestions (
                      id, organization_id, assessment_id, package_id, package_version,
                      rule_id, rule_version, category, title, observation,
                      business_rationale, suggested_evolution, expected_benefit, first_step,
                      impact, effort, priority, confidence, is_priority,
                      source_references, status, dismiss_reason,
                      generated_by, reviewed_at, reviewed_by
                    ) VALUES (
                      :id, :org, :aid, :pid, :ver,
                      :rid, :rv, :cat, :title, :obs,
                      :br, :se, :eb, :fs,
                      :impact, :effort, :pri, :conf, :is_pri,
                      CAST(:refs AS jsonb), :st, :dr,
                      :by, :rat, :rby
                    )
                    """
                ),
                {
                    "id": sid,
                    "org": ctx.organization_id,
                    "aid": assessment_id,
                    "pid": package_id,
                    "ver": version_no,
                    "rid": c.rule.rule_id,
                    "rv": c.rule.version,
                    "cat": c.rule.category.value,
                    "title": c.rule.title,
                    "obs": c.observation,
                    "br": c.rule.business_rationale,
                    "se": c.rule.suggested_evolution,
                    "eb": c.rule.expected_benefit,
                    "fs": c.rule.first_step,
                    "impact": c.rule.impact.value,
                    "effort": c.rule.effort.value,
                    "pri": c.priority.value,
                    "conf": c.confidence.value,
                    "is_pri": c.rule.rule_id in priority_ids,
                    "refs": json.dumps(
                        [r.model_dump(mode="json") for r in c.source_references]
                    ),
                    "st": status,
                    "dr": dismiss_reason,
                    "by": ctx.membership_id,
                    "rat": reviewed_at,
                    "rby": reviewed_by,
                },
            )
            inserted_rules.add(c.rule.rule_id)

        # Carry preserved rules not rematched (still visible in new package)
        for rule_id, prow in preserved.items():
            if rule_id in inserted_rules:
                continue
            conn.execute(
                text(
                    """
                    INSERT INTO evolution_suggestions (
                      id, organization_id, assessment_id, package_id, package_version,
                      rule_id, rule_version, category, title, observation,
                      business_rationale, suggested_evolution, expected_benefit, first_step,
                      impact, effort, priority, confidence, is_priority,
                      source_references, status, dismiss_reason,
                      generated_by, reviewed_at, reviewed_by
                    ) VALUES (
                      :id, :org, :aid, :pid, :ver,
                      :rid, :rv, :cat, :title, :obs,
                      :br, :se, :eb, :fs,
                      :impact, :effort, :pri, :conf, false,
                      CAST(:refs AS jsonb), :st, :dr,
                      :by, :rat, :rby
                    )
                    """
                ),
                {
                    "id": uuid4(),
                    "org": ctx.organization_id,
                    "aid": assessment_id,
                    "pid": package_id,
                    "ver": version_no,
                    "rid": prow.rule_id,
                    "rv": prow.rule_version,
                    "cat": prow.category,
                    "title": prow.title,
                    "obs": prow.observation,
                    "br": prow.business_rationale,
                    "se": prow.suggested_evolution,
                    "eb": prow.expected_benefit,
                    "fs": prow.first_step,
                    "impact": prow.impact,
                    "effort": prow.effort,
                    "pri": prow.priority,
                    "conf": prow.confidence,
                    "refs": json.dumps(
                        prow.source_references
                        if isinstance(prow.source_references, list)
                        else json.loads(prow.source_references or "[]")
                    ),
                    "st": prow.status,
                    "dr": prow.dismiss_reason,
                    "by": ctx.membership_id,
                    "rat": prow.reviewed_at,
                    "rby": prow.reviewed_by,
                },
            )

        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="evolution_map.generate",
            resource_type="evolution_suggestion_package",
            resource_id=package_id,
            metadata={
                "assessment_id": str(assessment_id),
                "generation_mode": mode.value,
                "package_version": version_no,
                "priority_count": min(MAX_PRIORITY, len(ranked)),
                "total_candidates": len(ranked),
                "fingerprint": fp,
                "supersedes_id": str(active.id) if active else None,
            },
        )
        conn.commit()

    out = get_active_package(ctx, assessment_id)
    assert out is not None
    if previous_rule_ids or preserved:
        new_ids = {s.rule_id for s in out.priority_suggestions + out.secondary_suggestions}
        out.regeneration_diff = EvolutionRegenerationDiff(
            new_rule_ids=sorted(new_ids - previous_rule_ids),
            retained_rule_ids=sorted(new_ids & previous_rule_ids),
            superseded_rule_ids=sorted(previous_rule_ids - new_ids),
            preserved_accepted_rule_ids=sorted(
                rid
                for rid, prow in preserved.items()
                if prow.status
                in (
                    EvolutionSuggestionStatus.accepted.value,
                    EvolutionSuggestionStatus.converted_to_action.value,
                )
            ),
        )
    return out


def accept_suggestion(ctx: OrgContext, suggestion_id: UUID) -> EvolutionSuggestionOut:
    require_role(ctx, *_REVIEW_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        row = conn.execute(
            text(
                f"""
                SELECT {_SUGGESTION_COLS}
                FROM evolution_suggestions
                WHERE id = :id AND organization_id = :org
                FOR UPDATE
                """
            ),
            {"id": suggestion_id, "org": ctx.organization_id},
        ).first()
        if row is None:
            raise AppError("not_found", "Suggestion not found", status_code=404)
        if row.status in ("dismissed", "converted_to_action", "superseded"):
            raise AppError(
                "invalid_transition",
                f"Cannot accept suggestion in status {row.status}",
                status_code=409,
            )
        if row.status == "accepted":
            return get_suggestion(ctx, suggestion_id)
        conn.execute(
            text(
                """
                UPDATE evolution_suggestions
                SET status = 'accepted',
                    reviewed_at = now(),
                    reviewed_by = :by,
                    updated_at = now()
                WHERE id = :id AND organization_id = :org
                """
            ),
            {"id": suggestion_id, "org": ctx.organization_id, "by": ctx.membership_id},
        )
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="evolution_suggestion.accept",
            resource_type="evolution_suggestion",
            resource_id=suggestion_id,
            from_status=row.status,
            to_status="accepted",
            metadata={"rule_id": row.rule_id},
        )
        conn.commit()
    return get_suggestion(ctx, suggestion_id)


def dismiss_suggestion(
    ctx: OrgContext, suggestion_id: UUID, payload: DismissSuggestionIn
) -> EvolutionSuggestionOut:
    require_role(ctx, *_REVIEW_ROLES)
    reason = payload.reason.strip()
    if len(reason) < 3:
        raise AppError("validation_error", "dismiss reason required", status_code=422)
    with tenant_connection(ctx.organization_id) as conn:
        row = conn.execute(
            text(
                f"""
                SELECT {_SUGGESTION_COLS}
                FROM evolution_suggestions
                WHERE id = :id AND organization_id = :org
                FOR UPDATE
                """
            ),
            {"id": suggestion_id, "org": ctx.organization_id},
        ).first()
        if row is None:
            raise AppError("not_found", "Suggestion not found", status_code=404)
        if row.status in ("converted_to_action", "superseded"):
            raise AppError(
                "invalid_transition",
                f"Cannot dismiss suggestion in status {row.status}",
                status_code=409,
            )
        conn.execute(
            text(
                """
                UPDATE evolution_suggestions
                SET status = 'dismissed',
                    dismiss_reason = :reason,
                    reviewed_at = now(),
                    reviewed_by = :by,
                    updated_at = now()
                WHERE id = :id AND organization_id = :org
                """
            ),
            {
                "id": suggestion_id,
                "org": ctx.organization_id,
                "by": ctx.membership_id,
                "reason": reason,
            },
        )
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="evolution_suggestion.dismiss",
            resource_type="evolution_suggestion",
            resource_id=suggestion_id,
            from_status=row.status,
            to_status="dismissed",
            metadata={"rule_id": row.rule_id, "has_reason": True},
        )
        conn.commit()
    return get_suggestion(ctx, suggestion_id)


def investigate_suggestion(
    ctx: OrgContext, suggestion_id: UUID, payload: InvestigateSuggestionIn | None = None
) -> EvolutionSuggestionOut:
    require_role(ctx, *_REVIEW_ROLES)
    payload = payload or InvestigateSuggestionIn()
    with tenant_connection(ctx.organization_id) as conn:
        row = conn.execute(
            text(
                f"""
                SELECT {_SUGGESTION_COLS}
                FROM evolution_suggestions
                WHERE id = :id AND organization_id = :org
                FOR UPDATE
                """
            ),
            {"id": suggestion_id, "org": ctx.organization_id},
        ).first()
        if row is None:
            raise AppError("not_found", "Suggestion not found", status_code=404)
        if row.status not in ("proposed", "accepted"):
            raise AppError(
                "invalid_transition",
                f"Cannot mark investigate from status {row.status}",
                status_code=409,
            )
        note = (payload.missing_information or payload.note or "").strip()
        if len(note) < 3:
            raise AppError(
                "validation_error",
                "Informe qual informação está faltando para aprofundar",
                status_code=422,
            )
        conn.execute(
            text(
                """
                UPDATE evolution_suggestions
                SET priority = 'investigate',
                    investigate_note = :note,
                    reviewed_at = now(),
                    reviewed_by = :by,
                    updated_at = now()
                WHERE id = :id AND organization_id = :org
                """
            ),
            {
                "id": suggestion_id,
                "org": ctx.organization_id,
                "by": ctx.membership_id,
                "note": note,
            },
        )
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="evolution_suggestion.investigate",
            resource_type="evolution_suggestion",
            resource_id=suggestion_id,
            metadata={
                "rule_id": row.rule_id,
                "note_present": True,
            },
        )
        conn.commit()
    return get_suggestion(ctx, suggestion_id)


def convert_suggestion_to_action(
    ctx: OrgContext, suggestion_id: UUID, payload: ConvertSuggestionToActionIn
) -> ConvertSuggestionToActionOut:
    """Create ActionItem + mark suggestion converted in one transaction."""
    require_role(ctx, *_REVIEW_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        row = conn.execute(
            text(
                f"""
                SELECT {_SUGGESTION_COLS}
                FROM evolution_suggestions
                WHERE id = :id AND organization_id = :org
                FOR UPDATE
                """
            ),
            {"id": suggestion_id, "org": ctx.organization_id},
        ).first()
        if row is None:
            raise AppError("not_found", "Suggestion not found", status_code=404)
        if row.status == "converted_to_action":
            raise AppError(
                "suggestion_already_converted",
                "Suggestion already converted to an action",
                status_code=409,
            )
        if row.status != "accepted":
            raise AppError(
                "suggestion_not_convertible",
                "Only accepted suggestions can be converted to actions",
                status_code=409,
            )

        assessment = conn.execute(
            text(
                """
                SELECT id, status FROM assessments
                WHERE id = :id AND organization_id = :org
                FOR UPDATE
                """
            ),
            {"id": row.assessment_id, "org": ctx.organization_id},
        ).first()
        if assessment is None:
            raise AppError("not_found", "Assessment not found", status_code=404)
        if assessment.status == "analysis":
            raise AppError(
                "actions_phase_required",
                "Abra explicitamente a fase de ações antes de converter sugestões",
                status_code=409,
            )
        if assessment.status not in ("actions", "report", "closed"):
            raise AppError(
                "phase_incompatible",
                f"Conversão exige fase de ações ou posterior (atual={assessment.status})",
                status_code=409,
            )

        existing = conn.execute(
            text(
                """
                SELECT id FROM action_items
                WHERE source_evolution_suggestion_id = :sid
                  AND organization_id = :org
                LIMIT 1
                """
            ),
            {"sid": suggestion_id, "org": ctx.organization_id},
        ).first()
        if existing is not None:
            raise AppError(
                "suggestion_already_converted",
                "This evolution suggestion already has an action item",
                status_code=409,
            )

        plan_id = payload.action_plan_id
        if plan_id is None:
            plan = conn.execute(
                text(
                    """
                    SELECT id, status FROM action_plans
                    WHERE assessment_id = :aid AND organization_id = :org
                      AND status IN ('draft', 'active')
                    ORDER BY
                      CASE status WHEN 'draft' THEN 0 ELSE 1 END,
                      created_at DESC
                    LIMIT 1
                    """
                ),
                {"aid": row.assessment_id, "org": ctx.organization_id},
            ).first()
            if plan is None:
                if not payload.create_plan_if_missing:
                    raise AppError(
                        "action_plan_required",
                        "Informe um plano de ação ou peça criação explícita",
                        status_code=422,
                    )
                plan_id = uuid4()
                conn.execute(
                    text(
                        """
                        INSERT INTO action_plans (
                          id, organization_id, assessment_id, status
                        ) VALUES (
                          :id, :org, :aid, 'draft'
                        )
                        """
                    ),
                    {
                        "id": plan_id,
                        "org": ctx.organization_id,
                        "aid": row.assessment_id,
                    },
                )
            else:
                plan_id = plan.id
        else:
            plan = conn.execute(
                text(
                    """
                    SELECT id, status, assessment_id FROM action_plans
                    WHERE id = :id AND organization_id = :org
                    FOR UPDATE
                    """
                ),
                {"id": plan_id, "org": ctx.organization_id},
            ).first()
            if plan is None:
                raise AppError("not_found", "Action plan not found", status_code=404)
            if plan.assessment_id != row.assessment_id:
                raise AppError(
                    "plan_mismatch",
                    "Action plan does not belong to this assessment",
                    status_code=422,
                )
            if plan.status not in ("draft", "active"):
                raise AppError(
                    "plan_not_editable",
                    f"Items only on draft|active plans (current={plan.status})",
                    status_code=409,
                )

        owner = conn.execute(
            text(
                """
                SELECT id FROM memberships
                WHERE id = :id AND organization_id = :org AND status = 'active'
                """
            ),
            {"id": payload.owner_membership_id, "org": ctx.organization_id},
        ).first()
        if owner is None:
            raise AppError("not_found", "Owner membership not found", status_code=404)

        efficacy = payload.efficacy_required
        if efficacy is None:
            efficacy = payload.action_kind.value == "corrective_action"

        title = (payload.title or row.title).strip()
        description = payload.description.strip()
        if title and title not in description:
            description = f"{title}\n\n{description}"

        item_id = uuid4()
        conn.execute(
            text(
                """
                INSERT INTO action_items (
                  id, organization_id, action_plan_id, finding_id,
                  source_evolution_suggestion_id, action_kind,
                  description, owner_membership_id, due_at, status, efficacy_required
                ) VALUES (
                  :id, :org, :plan, NULL,
                  :esid, :kind,
                  :desc, :owner, :due, 'open', :efficacy
                )
                """
            ),
            {
                "id": item_id,
                "org": ctx.organization_id,
                "plan": plan_id,
                "esid": suggestion_id,
                "kind": payload.action_kind.value,
                "desc": description,
                "owner": payload.owner_membership_id,
                "due": payload.due_at,
                "efficacy": efficacy,
            },
        )
        conn.execute(
            text(
                """
                UPDATE evolution_suggestions
                SET status = 'converted_to_action',
                    reviewed_at = now(),
                    reviewed_by = :by,
                    updated_at = now()
                WHERE id = :id AND organization_id = :org
                """
            ),
            {
                "id": suggestion_id,
                "org": ctx.organization_id,
                "by": ctx.membership_id,
            },
        )
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="evolution_suggestion.convert_to_action",
            resource_type="evolution_suggestion",
            resource_id=suggestion_id,
            from_status="accepted",
            to_status="converted_to_action",
            metadata={
                "rule_id": row.rule_id,
                "action_item_id": str(item_id),
                "action_plan_id": str(plan_id),
            },
        )
        conn.commit()

    suggestion = get_suggestion(ctx, suggestion_id)
    return ConvertSuggestionToActionOut(
        suggestion=suggestion,
        action_item_id=item_id,
        action_plan_id=plan_id,
    )
