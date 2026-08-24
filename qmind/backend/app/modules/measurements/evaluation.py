"""Target evaluation — pure Decimal logic, no database, no clock of its own.

The rules here decide whether an action *proved* it worked. They deliberately
never conclude "effective" on their own: a met target is an input to the human
efficacy decision, never a substitute for it.

Two concepts are kept strictly apart, because conflating them was the central
defect of the first ISOI-008 draft:

`baseline_status`
    Do we know where the indicator started? A baseline is either recorded, or
    its absence is justified in writing, or it is simply missing.

`substantiation`
    Is the current reading backed by a document a third party could inspect?
    This is answered **only** by the evidence attached to the effective
    measurement record. A baseline number is not evidence of anything: someone
    typing "48.5" into a form does not make 48.5 true. So substantiation never
    looks at the baseline, at the target, or at whether the target was met.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from app.schemas.enums import (
    RANGE_DIRECTIONS,
    BaselineStatus,
    IndicatorDirection,
    MeasurementPosture,
    SubstantiationLevel,
    TargetEvaluationState,
    TargetPosture,
)


@dataclass(frozen=True)
class IndicatorFacts:
    """Everything the evaluation needs about one indicator."""

    code: str
    name: str
    unit_label: str
    direction: str
    baseline_value: Decimal | None
    baseline_at: datetime | None
    baseline_unavailable_reason: str | None
    target_value: Decimal | None
    target_min: Decimal | None
    target_max: Decimal | None
    target_due_at: datetime | None
    measurement_frequency_days: int | None
    latest_value: Decimal | None
    latest_measured_at: datetime | None
    measurement_count: int
    activated_at: datetime | None = None
    # Evidence attached to the *effective* measurement record, batch-loaded by
    # the caller. `verified_evidence_count` only counts evidences an auditor
    # could actually open: approved, and neither superseded nor on the way out.
    evidence_link_count: int = 0
    verified_evidence_count: int = 0


@dataclass(frozen=True)
class Evaluation:
    state: str
    baseline_status: str
    substantiation: str
    next_measurement_due_at: datetime | None
    is_measurement_overdue: bool
    headline: str
    what_to_do_next: str


def has_target(facts: IndicatorFacts) -> bool:
    return (
        facts.target_value is not None
        or facts.target_min is not None
        or facts.target_max is not None
    )


def target_rule_is_complete_for(
    *,
    direction: str,
    target_value: Decimal | None,
    target_min: Decimal | None,
    target_max: Decimal | None,
) -> bool:
    """Can this target ever produce a verdict?

    A range needs both bounds; a direction needs its single target. An
    indicator whose rule is incomplete can be drafted, but it cannot be part
    of an active plan: it would collect numbers nobody can judge.
    """
    if direction in RANGE_DIRECTIONS:
        return target_min is not None and target_max is not None
    return target_value is not None


def target_rule_is_complete(facts: IndicatorFacts) -> bool:
    return target_rule_is_complete_for(
        direction=facts.direction,
        target_value=facts.target_value,
        target_min=facts.target_min,
        target_max=facts.target_max,
    )


def baseline_status_of(
    *, baseline_value: Decimal | None, baseline_unavailable_reason: str | None
) -> str:
    if baseline_value is not None:
        return BaselineStatus.recorded.value
    if (baseline_unavailable_reason or "").strip():
        return BaselineStatus.unavailable_justified.value
    return BaselineStatus.missing.value


def baseline_status(facts: IndicatorFacts) -> str:
    return baseline_status_of(
        baseline_value=facts.baseline_value,
        baseline_unavailable_reason=facts.baseline_unavailable_reason,
    )


def baseline_is_settled(facts: IndicatorFacts) -> bool:
    """A baseline is settled when we know it, or we documented why we cannot."""
    return baseline_status(facts) != BaselineStatus.missing.value


def substantiation_from_evidence(
    *, evidence_link_count: int, verified_evidence_count: int
) -> str:
    """The only source of truth for substantiation: attached evidence.

    * `none`     — nothing is attached, so nothing is proven.
    * `partial`  — something is attached but it is not usable proof yet (still
                   in quarantine, rejected, superseded or on its way to
                   disposal).
    * `verified` — at least one attached evidence is approved and still valid.
    """
    if verified_evidence_count > 0:
        return SubstantiationLevel.verified.value
    if evidence_link_count > 0:
        return SubstantiationLevel.partial.value
    return SubstantiationLevel.none.value


def _target_satisfied(facts: IndicatorFacts, value: Decimal) -> bool | None:
    """None when there is nothing to compare against."""
    direction = facts.direction
    if direction in RANGE_DIRECTIONS:
        if facts.target_min is None or facts.target_max is None:
            return None
        return facts.target_min <= value <= facts.target_max
    if facts.target_value is None:
        return None
    if direction == IndicatorDirection.higher_is_better.value:
        return value >= facts.target_value
    if direction == IndicatorDirection.lower_is_better.value:
        return value <= facts.target_value
    return None


def _moving_the_right_way(facts: IndicatorFacts, value: Decimal) -> bool | None:
    if facts.baseline_value is None:
        return None
    if facts.direction == IndicatorDirection.higher_is_better.value:
        return value > facts.baseline_value
    if facts.direction == IndicatorDirection.lower_is_better.value:
        return value < facts.baseline_value
    return None


def next_measurement_due_at(facts: IndicatorFacts) -> datetime | None:
    """When the next reading is expected — by cadence, else by the target date."""
    if facts.measurement_frequency_days:
        anchor = facts.latest_measured_at or facts.activated_at
        if anchor is None:
            return None
        return anchor + timedelta(days=int(facts.measurement_frequency_days))
    return facts.target_due_at


def measurement_is_overdue(facts: IndicatorFacts, now: datetime) -> bool:
    """Without a cadence, only a never-measured indicator can fall behind:
    an indicator already measured has nothing scheduled to miss."""
    due_at = next_measurement_due_at(facts)
    if due_at is None:
        return False
    if facts.measurement_frequency_days:
        return now > due_at
    return facts.measurement_count == 0 and now > due_at


def _unit_suffix(facts: IndicatorFacts) -> str:
    return f" {facts.unit_label}".rstrip()


def evaluate_indicator(facts: IndicatorFacts, now: datetime) -> Evaluation:
    due_at = next_measurement_due_at(facts)
    overdue = measurement_is_overdue(facts, now)
    base_status = baseline_status(facts)
    substantiation = substantiation_from_evidence(
        evidence_link_count=facts.evidence_link_count,
        verified_evidence_count=facts.verified_evidence_count,
    )

    def build(state: str, headline: str, what_next: str) -> Evaluation:
        return Evaluation(
            state=state,
            baseline_status=base_status,
            substantiation=substantiation,
            next_measurement_due_at=due_at,
            is_measurement_overdue=overdue,
            headline=headline,
            what_to_do_next=what_next,
        )

    if base_status == BaselineStatus.missing.value:
        return build(
            TargetEvaluationState.awaiting_baseline.value,
            f"{facts.name}: falta o ponto de partida.",
            "Registre o valor atual do indicador (linha de base) ou explique "
            "por que ele não pode ser medido hoje.",
        )

    if facts.measurement_count == 0 or facts.latest_value is None:
        return build(
            TargetEvaluationState.awaiting_measurement.value,
            f"{facts.name}: ainda sem medição depois da ação.",
            "Registre a primeira medição após a implementação para saber se "
            "o resultado mudou.",
        )

    value = facts.latest_value
    satisfied = _target_satisfied(facts, value)
    reading = f"{value}{_unit_suffix(facts)}"

    if satisfied is None:
        return build(
            TargetEvaluationState.inconclusive.value,
            f"{facts.name}: última medição {reading}, sem meta definida.",
            "Defina a meta do indicador para que a medição possa dizer se o "
            "resultado é suficiente.",
        )

    if satisfied:
        return build(
            TargetEvaluationState.target_met.value,
            f"{facts.name}: meta atingida ({reading}).",
            _next_step_for_met(substantiation),
        )

    deadline_passed = facts.target_due_at is not None and now > facts.target_due_at
    if not deadline_passed:
        trend = _moving_the_right_way(facts, value)
        return build(
            TargetEvaluationState.on_track.value,
            f"{facts.name}: caminhando para a meta ({reading})."
            if trend
            else f"{facts.name}: ainda distante da meta ({reading}).",
            "Continue medindo até a data-alvo antes de concluir sobre eficácia.",
        )

    return build(
        TargetEvaluationState.target_not_met.value,
        f"{facts.name}: meta não atingida no prazo ({reading}).",
        "Analise por que o resultado não mudou como esperado antes de decidir "
        "sobre a eficácia da ação.",
    )


def _next_step_for_met(substantiation: str) -> str:
    """A met target with nothing behind it is a claim, not a result."""
    if substantiation == SubstantiationLevel.none.value:
        return (
            "Anexe o documento que comprova esta medição (relatório, extração, "
            "planilha assinada) antes de levar o resultado para a decisão de "
            "eficácia."
        )
    if substantiation == SubstantiationLevel.partial.value:
        return (
            "O comprovante desta medição ainda não foi aprovado. Conclua a "
            "verificação do arquivo antes de usar o resultado como prova."
        )
    return (
        "Leve este resultado para a decisão de eficácia — a meta atingida "
        "é uma evidência, não a conclusão."
    )


_POSTURE_ORDER = (
    MeasurementPosture.awaiting_baseline.value,
    MeasurementPosture.overdue.value,
    MeasurementPosture.awaiting_measurement.value,
    MeasurementPosture.on_time.value,
)


def measurement_posture(evaluations: list[Evaluation]) -> str:
    """Worst signal wins: the board must surface the thing that needs attention."""
    if not evaluations:
        return MeasurementPosture.not_planned.value
    seen: set[str] = set()
    for ev in evaluations:
        if ev.state == TargetEvaluationState.awaiting_baseline.value:
            seen.add(MeasurementPosture.awaiting_baseline.value)
        elif ev.is_measurement_overdue:
            seen.add(MeasurementPosture.overdue.value)
        elif ev.state == TargetEvaluationState.awaiting_measurement.value:
            seen.add(MeasurementPosture.awaiting_measurement.value)
        else:
            seen.add(MeasurementPosture.on_time.value)
    for posture in _POSTURE_ORDER:
        if posture in seen:
            return posture
    return MeasurementPosture.on_time.value


def target_posture(evaluations: list[Evaluation]) -> str:
    met = any(e.state == TargetEvaluationState.target_met.value for e in evaluations)
    not_met = any(
        e.state == TargetEvaluationState.target_not_met.value for e in evaluations
    )
    if met and not_met:
        return TargetPosture.mixed.value
    if met:
        return TargetPosture.met.value
    if not_met:
        return TargetPosture.not_met.value
    return TargetPosture.unknown.value


def overall_substantiation(evaluations: list[Evaluation]) -> str:
    """The plan is only as substantiated as its weakest indicator."""
    if not evaluations:
        return SubstantiationLevel.none.value
    levels = {e.substantiation for e in evaluations}
    if SubstantiationLevel.none.value in levels:
        return SubstantiationLevel.none.value
    if SubstantiationLevel.partial.value in levels:
        return SubstantiationLevel.partial.value
    return SubstantiationLevel.verified.value


_BASELINE_ORDER = (
    BaselineStatus.missing.value,
    BaselineStatus.unavailable_justified.value,
    BaselineStatus.recorded.value,
)


def overall_baseline_status(evaluations: list[Evaluation]) -> str:
    """Weakest baseline wins, for the same reason substantiation does."""
    if not evaluations:
        return BaselineStatus.missing.value
    seen = {e.baseline_status for e in evaluations}
    for status in _BASELINE_ORDER:
        if status in seen:
            return status
    return BaselineStatus.missing.value
