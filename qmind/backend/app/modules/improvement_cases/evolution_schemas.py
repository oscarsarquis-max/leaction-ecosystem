"""Schemas for OutcomeObservation and Evolution projection (ISOI-005)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.modules.actions.schemas import ActionItemOut, ActionPlanOut
from app.modules.improvement_cases.problem_schemas import (
    ImprovementCaseAnalysisRunOut,
)
from app.modules.improvement_cases.execution_intelligence_schemas import (
    ExecutionIntelligenceSummary,
)
from app.modules.improvement_cases.schemas import ImprovementCaseOut
from app.modules.measurements.schemas import TargetEvaluationOut
from app.schemas.enums import (
    MeasurementPosture,
    SubstantiationLevel,
    TargetPosture,
)

ResultDirection = Literal[
    "improved", "unchanged", "worsened", "not_yet_measured"
]
ClosureReadiness = Literal["insufficient_information", "ready_for_review"]

_MAX = 4000


def _nonblank(v: str) -> str:
    cleaned = (v or "").strip()
    if not cleaned:
        raise ValueError("must not be blank")
    return cleaned


class OutcomeObservationCreate(BaseModel):
    model_config = {"extra": "forbid"}

    result_direction: ResultDirection
    observation_statement: str = Field(min_length=1, max_length=_MAX)
    measurement_basis: str = Field(min_length=1, max_length=_MAX)
    observed_at: datetime
    measurement_record_ids: list[UUID] = Field(
        default_factory=list,
        description=(
            "Measurements that back this observation. They must belong to this "
            "improvement case through its action plans."
        ),
    )

    @field_validator("observation_statement", "measurement_basis")
    @classmethod
    def strip_required(cls, v: str) -> str:
        return _nonblank(v)

    @field_validator("observed_at")
    @classmethod
    def aware_observed_at(cls, v: datetime) -> datetime:
        if v.tzinfo is None or v.tzinfo.utcoffset(v) is None:
            raise ValueError("observed_at must be timezone-aware")
        return v


class OutcomeObservationOut(BaseModel):
    id: UUID
    organization_id: UUID
    improvement_case_id: UUID
    result_direction: ResultDirection
    observation_statement: str
    measurement_basis: str
    observed_at: datetime
    created_by: UUID
    created_at: datetime
    measurement_record_ids: list[UUID] = Field(default_factory=list)


class MeasurementSummary(BaseModel):
    """What the numbers say across every measurement plan of this case."""

    measurement_posture: MeasurementPosture
    target_posture: TargetPosture
    substantiation: SubstantiationLevel
    indicator_count: int = 0
    overdue_indicator_count: int = 0
    evaluations: list[TargetEvaluationOut] = Field(default_factory=list)


class AnalysisRunComparison(BaseModel):
    context_status_before: str
    context_status_after: str
    findings_added: list[str] = Field(default_factory=list)
    findings_removed: list[str] = Field(default_factory=list)
    findings_persisting: list[str] = Field(default_factory=list)
    missing_information_added: list[str] = Field(default_factory=list)
    missing_information_removed: list[str] = Field(default_factory=list)
    limitations_added: list[str] = Field(default_factory=list)
    limitations_removed: list[str] = Field(default_factory=list)


class AnalysisSummary(BaseModel):
    total_runs: int
    latest_run: ImprovementCaseAnalysisRunOut | None = None
    previous_run: ImprovementCaseAnalysisRunOut | None = None
    comparison: AnalysisRunComparison | None = None


class ActionStatusCount(BaseModel):
    status: str
    count: int


class ActionSummary(BaseModel):
    total: int
    by_status: list[ActionStatusCount] = Field(default_factory=list)
    overdue: int
    completed: int
    items: list[ActionItemOut] = Field(default_factory=list)
    plan: ActionPlanOut | None = None


class ImprovementCaseEvolutionOut(BaseModel):
    case: ImprovementCaseOut
    analysis_summary: AnalysisSummary
    action_summary: ActionSummary
    measurement_summary: MeasurementSummary
    latest_outcome_observation: OutcomeObservationOut | None = None
    outcome_observations: list[OutcomeObservationOut] = Field(default_factory=list)
    closure_readiness: ClosureReadiness
    closure_readiness_reason: str = ""
    execution_intelligence: ExecutionIntelligenceSummary | None = None
