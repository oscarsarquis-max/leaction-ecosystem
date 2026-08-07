"""Deterministic matching engine — facts in, ranked suggestions out (no LLM)."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from app.modules.evolution_map.catalog import (
    CATALOG_VERSION,
    EvolutionRule,
    RULES,
    default_confidence_for_rule,
)
from app.modules.evolution_map.schemas import SourceReference
from app.schemas.enums import (
    EvolutionConfidence,
    EvolutionGenerationMode,
    EvolutionPriority,
)


@dataclass
class GuidedAnswerFact:
    answer_id: UUID | None
    question_id: str
    question_version: str
    answer_value: str | None
    evidence_mode: str
    provide_later: bool
    description: str = ""


@dataclass
class EvidenceFact:
    evidence_id: UUID
    status: str
    linked_question_id: str | None = None


@dataclass
class FindingFact:
    finding_id: UUID
    status: str
    finding_type: str
    title: str
    has_cause: bool = False


@dataclass
class ActionItemFact:
    item_id: UUID
    status: str
    finding_id: UUID | None = None


@dataclass
class MaturityScoreFact:
    maturity_assessment_id: UUID
    criterion_id: UUID | None
    dimension_code: str | None
    level: int | None
    applicability: str | None


@dataclass
class AssessmentFacts:
    assessment_id: UUID
    organization_id: UUID
    status: str
    generation_mode: EvolutionGenerationMode
    context: dict[str, Any] = field(default_factory=dict)
    answers: list[GuidedAnswerFact] = field(default_factory=list)
    evidences: list[EvidenceFact] = field(default_factory=list)
    findings: list[FindingFact] = field(default_factory=list)
    action_items: list[ActionItemFact] = field(default_factory=list)
    maturity_scores: list[MaturityScoreFact] = field(default_factory=list)


@dataclass
class CandidateSuggestion:
    rule: EvolutionRule
    observation: str
    confidence: EvolutionConfidence
    priority: EvolutionPriority
    source_references: list[SourceReference]
    score: float


_THEME_RE = re.compile(r"(CTX|LDR|GOV|POL|RSK|PLN|OBJ|CHG|OPS|PRD|SVC|CUS|HR|CMP|TRN|PPL|DOC|INF|REC|SUP|PUR|EXT|SAT|FBK|NPS|AUD|INT|CHK)", re.I)


def question_themes(question_id: str) -> set[str]:
    return {m.group(1).upper() for m in _THEME_RE.finditer(question_id)}


def fingerprint_facts(facts: AssessmentFacts) -> str:
    payload = {
        "mode": facts.generation_mode.value,
        "status": facts.status,
        "answers": sorted(
            [
                {
                    "q": a.question_id,
                    "v": a.question_version,
                    "a": a.answer_value,
                    "em": a.evidence_mode,
                    "pl": a.provide_later,
                }
                for a in facts.answers
            ],
            key=lambda x: (x["q"], x["v"]),
        ),
        "evidences": sorted(
            [{"id": str(e.evidence_id), "st": e.status} for e in facts.evidences],
            key=lambda x: x["id"],
        ),
        "findings": sorted(
            [
                {
                    "id": str(f.finding_id),
                    "st": f.status,
                    "t": f.finding_type,
                    "cause": f.has_cause,
                }
                for f in facts.findings
            ],
            key=lambda x: x["id"],
        ),
        "actions": sorted(
            [{"id": str(a.item_id), "st": a.status} for a in facts.action_items],
            key=lambda x: x["id"],
        ),
        "maturity": sorted(
            [
                {
                    "d": m.dimension_code,
                    "lvl": m.level,
                    "app": m.applicability,
                }
                for m in facts.maturity_scores
            ],
            key=lambda x: (x["d"] or "", x["lvl"] or 0),
        ),
        "context_keys": sorted(facts.context.keys()),
        "catalog": CATALOG_VERSION,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def source_snapshot(facts: AssessmentFacts) -> dict[str, Any]:
    return {
        "generation_mode": facts.generation_mode.value,
        "assessment_status": facts.status,
        "answer_count": len(facts.answers),
        "evidence_count": len(facts.evidences),
        "finding_count": len(facts.findings),
        "action_item_count": len(facts.action_items),
        "maturity_score_count": len(facts.maturity_scores),
        "catalog_version": CATALOG_VERSION,
        # IDs only — never document bodies or signed URLs
        "evidence_ids": [str(e.evidence_id) for e in facts.evidences[:50]],
        "finding_ids": [str(f.finding_id) for f in facts.findings[:50]],
    }


def _theme_match(rule: EvolutionRule, qid: str) -> bool:
    if not rule.question_themes:
        return True
    themes = question_themes(qid)
    return bool(themes.intersection({t.upper() for t in rule.question_themes}))


def _priority_for(
    rule: EvolutionRule, confidence: EvolutionConfidence, *, urgent: bool
) -> EvolutionPriority:
    if confidence == EvolutionConfidence.low and rule.base_priority != EvolutionPriority.investigate:
        return EvolutionPriority.investigate
    if urgent and rule.impact.value == "high":
        return EvolutionPriority.now
    return rule.base_priority


def _score(rule: EvolutionRule, confidence: EvolutionConfidence, priority: EvolutionPriority) -> float:
    impact_w = {"high": 3.0, "medium": 2.0, "low": 1.0}[rule.impact.value]
    conf_w = {"high": 1.2, "medium": 1.0, "low": 0.7}[confidence.value]
    pri_w = {"now": 1.4, "next_cycle": 1.1, "future": 0.8, "investigate": 0.9}[priority.value]
    effort_w = {"low": 1.15, "medium": 1.0, "high": 0.85}[rule.effort.value]
    return impact_w * conf_w * pri_w * effort_w


def evaluate_rules(facts: AssessmentFacts) -> list[CandidateSuggestion]:
    out: list[CandidateSuggestion] = []
    pending_ev = [e for e in facts.evidences if e.status in ("upload_pending", "quarantined", "pending_disposal")]
    rejected_ev = [e for e in facts.evidences if e.status == "rejected"]
    later_answers = [a for a in facts.answers if a.provide_later or a.evidence_mode == "provide_later"]

    for rule in RULES:
        kind = str(rule.conditions.get("kind", ""))
        refs: list[SourceReference] = []
        matched = False
        has_evidence = False
        has_finding = False
        urgent = False
        observation = rule.observation

        if kind == "guided_answer_value":
            wanted = set(rule.conditions.get("answer_values") or [])
            hits = [
                a
                for a in facts.answers
                if a.answer_value in wanted and _theme_match(rule, a.question_id)
            ]
            if hits:
                matched = True
                for a in hits[:5]:
                    refs.append(
                        SourceReference(
                            kind="guided_answer",
                            id=str(a.answer_id) if a.answer_id else None,
                            question_id=a.question_id,
                            question_version=a.question_version,
                            detail=a.answer_value,
                        )
                    )
                observation = (
                    f"{rule.observation} "
                    f"Ex.: pergunta {hits[0].question_id} respondida como '{hits[0].answer_value}'."
                )

        elif kind == "evidence_pending":
            if pending_ev or later_answers:
                matched = True
                urgent = True
                for e in pending_ev[:5]:
                    refs.append(
                        SourceReference(
                            kind="evidence",
                            id=str(e.evidence_id),
                            detail=e.status,
                        )
                    )
                    has_evidence = True
                for a in later_answers[:3]:
                    refs.append(
                        SourceReference(
                            kind="guided_answer",
                            id=str(a.answer_id) if a.answer_id else None,
                            question_id=a.question_id,
                            question_version=a.question_version,
                            detail="provide_later",
                        )
                    )

        elif kind == "evidence_rejected":
            if rejected_ev:
                matched = True
                urgent = True
                has_evidence = True
                for e in rejected_ev[:5]:
                    refs.append(
                        SourceReference(
                            kind="evidence",
                            id=str(e.evidence_id),
                            detail="rejected",
                        )
                    )

        elif kind == "context_objectives_incomplete":
            objectives = facts.context.get("objectives") or facts.context.get("quality_objectives")
            if isinstance(objectives, list) and objectives:
                incomplete = [
                    o
                    for o in objectives
                    if isinstance(o, dict)
                    and (not o.get("owner") and not o.get("responsible") or not o.get("due_at") and not o.get("deadline"))
                ]
                if incomplete or any(
                    isinstance(o, dict) and not (o.get("owner") or o.get("responsible"))
                    for o in objectives
                ):
                    matched = True
                    refs.append(
                        SourceReference(
                            kind="wizard_context",
                            detail="objectives_incomplete",
                            label="objetivos",
                        )
                    )
            elif facts.context.get("has_objectives") is False:
                matched = True
                refs.append(SourceReference(kind="wizard_context", detail="objectives_missing"))

        elif kind == "context_risks_without_action":
            risks = facts.context.get("risks") or []
            if isinstance(risks, list) and risks:
                bare = [
                    r
                    for r in risks
                    if isinstance(r, dict) and not (r.get("action") or r.get("treatment") or r.get("mitigation"))
                ]
                if bare:
                    matched = True
                    refs.append(
                        SourceReference(
                            kind="wizard_context",
                            detail="risks_without_action",
                            label=f"{len(bare)} risco(s)",
                        )
                    )

        elif kind == "context_processes_untracked":
            processes = facts.context.get("processes") or []
            if isinstance(processes, list) and len(processes) >= 1:
                untracked = [
                    p
                    for p in processes
                    if isinstance(p, dict)
                    and not (p.get("kpi") or p.get("indicator") or p.get("owner") or p.get("monitored"))
                ]
                if untracked or len(processes) >= 2:
                    # If processes listed but no monitoring hints in answers either
                    ops_answers = [
                        a
                        for a in facts.answers
                        if question_themes(a.question_id).intersection({"OPS", "PRD"})
                        and a.answer_value in ("partial", "no", "unknown")
                    ]
                    if untracked or ops_answers:
                        matched = True
                        refs.append(
                            SourceReference(
                                kind="wizard_context",
                                detail="processes_untracked",
                                label=f"{len(processes)} processo(s)",
                            )
                        )
                        for a in ops_answers[:2]:
                            refs.append(
                                SourceReference(
                                    kind="guided_answer",
                                    id=str(a.answer_id) if a.answer_id else None,
                                    question_id=a.question_id,
                                    question_version=a.question_version,
                                    detail=a.answer_value,
                                )
                            )

        elif kind == "competence_undemonstrated":
            hits = [
                a
                for a in facts.answers
                if _theme_match(rule, a.question_id)
                and a.answer_value in ("partial", "no", "unknown")
            ]
            if hits:
                matched = True
                for a in hits[:4]:
                    refs.append(
                        SourceReference(
                            kind="guided_answer",
                            id=str(a.answer_id) if a.answer_id else None,
                            question_id=a.question_id,
                            question_version=a.question_version,
                            detail=a.answer_value,
                        )
                    )

        elif kind == "documented_info_uncontrolled":
            hits = [
                a
                for a in facts.answers
                if _theme_match(rule, a.question_id)
                and a.answer_value in ("partial", "no", "unknown")
            ]
            if hits:
                matched = True
                for a in hits[:4]:
                    refs.append(
                        SourceReference(
                            kind="guided_answer",
                            id=str(a.answer_id) if a.answer_id else None,
                            question_id=a.question_id,
                            question_version=a.question_version,
                            detail=a.answer_value,
                        )
                    )

        elif kind == "supplier_unevaluated":
            hits = [
                a
                for a in facts.answers
                if _theme_match(rule, a.question_id)
                and a.answer_value in ("partial", "no", "unknown")
            ]
            if hits:
                matched = True
                for a in hits[:4]:
                    refs.append(
                        SourceReference(
                            kind="guided_answer",
                            id=str(a.answer_id) if a.answer_id else None,
                            question_id=a.question_id,
                            question_version=a.question_version,
                            detail=a.answer_value,
                        )
                    )

        elif kind == "customer_satisfaction_untracked":
            hits = [
                a
                for a in facts.answers
                if _theme_match(rule, a.question_id)
                and a.answer_value in ("partial", "no", "unknown")
            ]
            stakeholders = facts.context.get("stakeholders") or []
            if hits or (
                isinstance(stakeholders, list)
                and stakeholders
                and not any(
                    isinstance(s, dict) and (s.get("satisfaction") or s.get("feedback"))
                    for s in stakeholders
                )
            ):
                matched = True
                for a in hits[:3]:
                    refs.append(
                        SourceReference(
                            kind="guided_answer",
                            id=str(a.answer_id) if a.answer_id else None,
                            question_id=a.question_id,
                            question_version=a.question_version,
                            detail=a.answer_value,
                        )
                    )
                if stakeholders:
                    refs.append(
                        SourceReference(
                            kind="wizard_context",
                            detail="stakeholders_without_satisfaction",
                        )
                    )

        elif kind == "internal_audit_ineffective":
            hits = [
                a
                for a in facts.answers
                if _theme_match(rule, a.question_id)
                and a.answer_value in ("partial", "no", "unknown")
            ]
            ncs = [f for f in facts.findings if f.status == "approved" and f.finding_type == "nonconformity"]
            if hits or ncs:
                matched = True
                for a in hits[:3]:
                    refs.append(
                        SourceReference(
                            kind="guided_answer",
                            id=str(a.answer_id) if a.answer_id else None,
                            question_id=a.question_id,
                            question_version=a.question_version,
                            detail=a.answer_value,
                        )
                    )
                for f in ncs[:2]:
                    has_finding = True
                    refs.append(
                        SourceReference(
                            kind="finding",
                            id=str(f.finding_id),
                            label=f.title[:80],
                            detail=f.finding_type,
                        )
                    )

        elif kind == "finding_cause_missing":
            if facts.generation_mode == EvolutionGenerationMode.analysis_ready:
                weak = [
                    f
                    for f in facts.findings
                    if f.status in ("approved", "in_review") and not f.has_cause
                ]
                if weak:
                    matched = True
                    urgent = True
                    has_finding = True
                    for f in weak[:5]:
                        refs.append(
                            SourceReference(
                                kind="finding",
                                id=str(f.finding_id),
                                label=f.title[:80],
                                detail="cause_missing",
                            )
                        )

        elif kind == "action_efficacy_unverified":
            if facts.generation_mode == EvolutionGenerationMode.analysis_ready:
                weak = [
                    a
                    for a in facts.action_items
                    if a.status in ("implemented", "in_progress")
                ]
                if weak:
                    matched = True
                    urgent = True
                    for a in weak[:5]:
                        refs.append(
                            SourceReference(
                                kind="action_item",
                                id=str(a.item_id),
                                detail=a.status,
                            )
                        )

        elif kind == "maturity_low_dimension":
            if facts.generation_mode == EvolutionGenerationMode.analysis_ready:
                max_level = int(rule.conditions.get("max_level") or 2)
                lows = [
                    m
                    for m in facts.maturity_scores
                    if m.applicability == "applicable"
                    and m.level is not None
                    and m.level <= max_level
                ]
                if lows:
                    matched = True
                    for m in lows[:5]:
                        refs.append(
                            SourceReference(
                                kind="maturity_score",
                                id=str(m.maturity_assessment_id),
                                detail=f"level={m.level}",
                                label=m.dimension_code,
                            )
                        )

        if not matched or not refs:
            continue

        confidence = default_confidence_for_rule(
            rule, has_evidence=has_evidence, has_finding=has_finding
        )
        if kind == "guided_answer_value" and rule.conditions.get("answer_values") == ["partial"]:
            confidence = EvolutionConfidence.medium if has_evidence else EvolutionConfidence.medium
        if kind == "guided_answer_value" and rule.conditions.get("answer_values") == ["unknown"]:
            confidence = EvolutionConfidence.low
            if not has_evidence:
                urgent = False

        priority = _priority_for(rule, confidence, urgent=urgent)
        out.append(
            CandidateSuggestion(
                rule=rule,
                observation=observation.strip(),
                confidence=confidence,
                priority=priority,
                source_references=refs,
                score=_score(rule, confidence, priority),
            )
        )

    # Deduplicate by rule_id keeping highest score
    best: dict[str, CandidateSuggestion] = {}
    for c in out:
        prev = best.get(c.rule.rule_id)
        if prev is None or c.score > prev.score:
            best[c.rule.rule_id] = c
    ranked = sorted(best.values(), key=lambda c: (-c.score, c.rule.rule_id))
    return ranked
