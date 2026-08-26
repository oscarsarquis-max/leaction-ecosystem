"""Read-model contracts for the ISO Intelligence Cockpit (ISOI-010)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.improvement_cases.execution_intelligence_schemas import (
    ExecutionPosture,
    SignalCategory,
    SignalLevel,
)
from app.modules.improvement_cases.schemas import ImprovementCaseStatus
from app.schemas.enums import MeasurementPosture, SubstantiationLevel, TargetPosture

CockpitPriorityBand = Literal[
    "immediate_attention",
    "attention",
    "follow_up",
    "on_course",
    "completed_or_observed",
]
IntelligenceFreshness = Literal["current", "stale", "never_analyzed"]
ActivityWindowDays = Literal[7, 30, 90]
_ACTIVITY_WINDOWS = frozenset({7, 30, 90})


def parse_activity_window_days(value: int | str) -> ActivityWindowDays:
    """Coerce query-string ints to ActivityWindowDays (FastAPI Literal quirk)."""
    raw = int(value) if not isinstance(value, int) else value
    if raw not in _ACTIVITY_WINDOWS:
        raise ValueError("activity_window_days must be 7, 30, or 90")
    return raw  # type: ignore[return-value]
ActivityEventType = Literal[
    "check_in_recorded",
    "impediment_opened",
    "impediment_resolved",
    "measurement_recorded",
    "measurement_corrected",
    "outcome_observed",
    "execution_intelligence_run",
    "case_status_changed",
    "action_status_changed",
]
ClosureReadiness = Literal["insufficient_information", "ready_for_review"]
ResultDirection = Literal["improved", "unchanged", "worsened", "not_yet_measured"]

PROBLEM_LABEL_MAX = 200

PRIORITY_BAND_LABELS: dict[CockpitPriorityBand, str] = {
    "immediate_attention": "Atenção imediata",
    "attention": "Atenção",
    "follow_up": "Acompanhamento",
    "on_course": "No rumo",
    "completed_or_observed": "Concluído ou observado",
}

PRIORITY_REASON_LABELS: dict[str, str] = {
    "ei_current_stalled": "Execution Intelligence atual indica execução parada",
    "overdue_action_with_active_impediment": "Ação vencida com impedimento ativo",
    "overdue_dependency_with_overdue_action": "Dependência vencida combinada com ação vencida",
    "ei_current_attention_required": "Execution Intelligence atual exige atenção",
    "overdue_action": "Há ação vencida",
    "active_impediment": "Há impedimento ativo",
    "active_dependency": "Há dependência aberta",
    "measurement_overdue": "Medição atrasada",
    "target_not_met": "Meta não atingida",
    "target_mixed": "Metas mistas (atingidas e não atingidas)",
    "claims_execution_without_approved_evidence": (
        "Execução declarada sem evidência aprovada"
    ),
    "current_oi_attention_signal": "Sinal OI atual de nível atenção",
    "ei_stale": "Execution Intelligence desatualizada",
    "ei_never_analyzed": "Execution Intelligence nunca executada",
    "awaiting_result_evaluation": "Aguardando avaliação de resultado",
    "awaiting_baseline": "Aguardando linha de base",
    "awaiting_measurement": "Aguardando medição",
    "stale_check_in": "Sem check-in recente",
    "pending_human_observation": "Observação humana pendente",
    "ei_current_progressing": "Execution Intelligence atual indica progresso",
    "active_without_alerts": "Execução ativa sem alertas objetivos",
    "outcome_observed": "Resultado observado",
    "case_closed": "Caso fechado",
}


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LabeledCount(StrictModel):
    code: str
    label: str
    count: int = Field(ge=0)
    unit: str = "cases"


class CockpitCoverage(StrictModel):
    analyzed_count: int = Field(ge=0)
    included_count: int = Field(ge=0)
    excluded_count: int = Field(default=0, ge=0)
    complete: bool = True


class CockpitScopeOut(StrictModel):
    organization_id: UUID
    case_status_filter: list[ImprovementCaseStatus] | None = None
    activity_window_days: ActivityWindowDays = 30


class CaseTotalsOut(StrictModel):
    total: int = Field(ge=0)
    active: int = Field(ge=0)
    reviewing: int = Field(ge=0)
    closed: int = Field(ge=0)
    ready_for_review: int = Field(ge=0)
    unit: str = "cases"


class ExecutionTotalsOut(StrictModel):
    active_actions: int = Field(ge=0)
    completed_actions: int = Field(ge=0)
    overdue_actions: int = Field(ge=0)
    blocked_cases: int = Field(ge=0)
    active_impediments: int = Field(ge=0)
    open_dependencies: int = Field(ge=0)
    overdue_dependencies: int = Field(ge=0)
    actions_without_recent_check_in: int = Field(ge=0)
    unit_actions: str = "actions"
    unit_cases: str = "cases"


class EvidenceTotalsOut(StrictModel):
    claims_execution_actions: int = Field(ge=0)
    with_approved_evidence: int = Field(ge=0)
    without_approved_evidence: int = Field(ge=0)
    unit: str = "actions"


class MeasurementTotalsOut(StrictModel):
    by_measurement_posture: list[LabeledCount] = Field(default_factory=list)
    by_target_posture: list[LabeledCount] = Field(default_factory=list)
    by_substantiation: list[LabeledCount] = Field(default_factory=list)
    overdue_indicators: int = Field(ge=0)
    unit_cases: str = "cases"
    unit_indicators: str = "indicators"


class IntelligenceCoverageOut(StrictModel):
    current: int = Field(ge=0)
    stale: int = Field(ge=0)
    never_analyzed: int = Field(ge=0)
    unit: str = "cases"


class SignalCountOut(StrictModel):
    category: SignalCategory | None = None
    level: SignalLevel | None = None
    count: int = Field(ge=0)
    unit: str = "signals"


class PriorityReasonOut(StrictModel):
    code: str
    label: str


class CockpitCaseItemOut(StrictModel):
    case_id: UUID
    problem_label: str
    related_process: str | None = None
    case_status: ImprovementCaseStatus
    priority_band: CockpitPriorityBand
    priority_band_label: str
    priority_reasons: list[PriorityReasonOut] = Field(default_factory=list)
    action_count: int = Field(ge=0)
    completed_action_count: int = Field(ge=0)
    overdue_action_count: int = Field(ge=0)
    active_impediment_count: int = Field(ge=0)
    open_dependency_count: int = Field(ge=0)
    overdue_dependency_count: int = Field(ge=0)
    last_activity_at: datetime | None = None
    oldest_due_at: datetime | None = None
    measurement_posture: MeasurementPosture
    target_posture: TargetPosture
    substantiation: SubstantiationLevel
    outcome_result_direction: ResultDirection | None = None
    outcome_observed_at: datetime | None = None
    execution_posture: ExecutionPosture | None = None
    intelligence_generated_at: datetime | None = None
    intelligence_mechanism_version: str | None = None
    intelligence_signal_count: int = Field(default=0, ge=0)
    intelligence_freshness: IntelligenceFreshness
    intelligence_freshness_label: str
    closure_readiness: ClosureReadiness
    closure_readiness_reason: str = ""
    current_attention_signal_count: int = Field(default=0, ge=0)


class CockpitActivityItemOut(StrictModel):
    event_type: ActivityEventType
    event_type_label: str
    occurred_at: datetime
    summary: str
    case_id: UUID | None = None
    action_item_id: UUID | None = None


class CockpitSummaryOut(StrictModel):
    as_of: datetime
    scope: CockpitScopeOut
    case_totals: CaseTotalsOut
    priority_distribution: list[LabeledCount] = Field(default_factory=list)
    execution: ExecutionTotalsOut
    evidence: EvidenceTotalsOut
    measurement: MeasurementTotalsOut
    intelligence_coverage: IntelligenceCoverageOut
    execution_posture_distribution_current: list[LabeledCount] = Field(
        default_factory=list
    )
    execution_posture_distribution_stale: list[LabeledCount] = Field(
        default_factory=list
    )
    signals_current: list[SignalCountOut] = Field(default_factory=list)
    signals_stale: list[SignalCountOut] = Field(default_factory=list)
    recent_activity: list[CockpitActivityItemOut] = Field(default_factory=list)
    coverage: CockpitCoverage


class CockpitCasesPageOut(StrictModel):
    as_of: datetime
    items: list[CockpitCaseItemOut] = Field(default_factory=list)
    limit: int = Field(ge=1, le=100)
    next_cursor: str | None = None
    coverage: CockpitCoverage


class CockpitActivityPageOut(StrictModel):
    as_of: datetime
    activity_window_days: ActivityWindowDays
    items: list[CockpitActivityItemOut] = Field(default_factory=list)
    limit: int = Field(ge=1, le=100)
    next_cursor: str | None = None
    coverage: CockpitCoverage
