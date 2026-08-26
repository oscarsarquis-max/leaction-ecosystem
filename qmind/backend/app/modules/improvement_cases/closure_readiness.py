"""Canonical closure-review readiness (Evolution is the source of truth)."""

from __future__ import annotations

from typing import Literal

from app.schemas.enums import MeasurementPosture

ClosureReadiness = Literal["insufficient_information", "ready_for_review"]

# A planned-but-unproven measurement is missing information. `not_planned` is
# deliberately absent: a case that never planned measurement is judged by the
# other gates, exactly as it was before measurement existed.
_BLOCKING_POSTURES = frozenset(
    {
        MeasurementPosture.awaiting_baseline.value,
        MeasurementPosture.awaiting_measurement.value,
        MeasurementPosture.overdue.value,
    }
)

_POSTURE_REASON = {
    MeasurementPosture.awaiting_baseline.value: (
        "Falta a linha de base de um indicador planejado."
    ),
    MeasurementPosture.awaiting_measurement.value: (
        "Um indicador planejado ainda não foi medido depois da ação."
    ),
    MeasurementPosture.overdue.value: (
        "Há medição atrasada em um indicador planejado."
    ),
}


def evaluate_closure_readiness(
    *,
    has_problem_analysis: bool,
    problem_analysis_is_stale: bool,
    action_count: int,
    has_incomplete_actions: bool,
    has_outcome: bool,
    outcome_direction: str | None,
    measurement_posture: str,
) -> tuple[ClosureReadiness, str]:
    """Readiness to *review* closure — never a verdict on efficacy.

    A met target does not close a case on its own, and a missed target does not
    fail it: both are inputs a human weighs. What blocks review is missing
    information, including a measurement that was promised and never taken.
    """
    if not has_problem_analysis:
        return "insufficient_information", "Ainda não há análise para este caso."
    if problem_analysis_is_stale:
        return (
            "insufficient_information",
            "O contexto mudou desde a última análise — rode a análise novamente.",
        )
    if action_count < 1:
        return "insufficient_information", "Nenhuma ação foi criada a partir da análise."
    if has_incomplete_actions:
        return "insufficient_information", "Há ações que ainda não foram concluídas."
    if not has_outcome:
        return (
            "insufficient_information",
            "Ninguém registrou ainda o que aconteceu com o problema.",
        )
    if outcome_direction == "not_yet_measured":
        return (
            "insufficient_information",
            "A última observação diz que o resultado ainda não foi medido.",
        )
    if measurement_posture in _BLOCKING_POSTURES:
        return "insufficient_information", _POSTURE_REASON[measurement_posture]
    return (
        "ready_for_review",
        "Ações concluídas e resultado observado: leve o caso para revisão de encerramento.",
    )
