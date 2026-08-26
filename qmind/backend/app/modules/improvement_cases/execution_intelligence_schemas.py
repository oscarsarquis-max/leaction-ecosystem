"""Core-owned mirrors of QMind OI Execution Intelligence V1 contracts."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints, field_validator, model_validator

from app.modules.oi.schemas import EnvelopeMetadata, SourceRef, StrictModel

NonEmptyStr = Annotated[str, StringConstraints(min_length=1, strip_whitespace=True)]
ActionStatus = Literal[
    "open", "in_progress", "implemented", "validated", "done", "cancelled",
    "ineffective", "ineffective_closed",
]
PlanStatus = Literal["draft", "active", "completed", "cancelled"]
MeasurementPosture = Literal[
    "not_planned", "awaiting_baseline", "awaiting_measurement", "on_time", "overdue"
]
TargetPosture = Literal["unknown", "met", "not_met", "mixed"]
BaselineStatus = Literal["missing", "recorded", "unavailable_justified"]
Substantiation = Literal["none", "partial", "verified"]
ResultDirection = Literal["improved", "unchanged", "worsened", "not_yet_measured"]
IndicatorDirection = Literal[
    "higher_is_better", "lower_is_better", "within_range", "maintain_range"
]
IsoBasis = Literal["6.2.2", "8.1", "9.1.1", "10.2.1", "10.3"]


def _aware(value: datetime | None, field_name: str) -> datetime | None:
    if value is not None and (value.tzinfo is None or value.tzinfo.utcoffset(value) is None):
        raise ValueError(f"{field_name} must be timezone-aware (prefer UTC)")
    return value


class ExecutionCaseFacts(StrictModel):
    status: NonEmptyStr = Field(max_length=80)
    problem_statement: str | None = Field(default=None, max_length=4000)
    impact_statement: str | None = Field(default=None, max_length=4000)
    related_process: str | None = Field(default=None, max_length=4000)
    latest_problem_analysis_ref: str | None = Field(default=None, max_length=200)


class ExecutionPlanFacts(StrictModel):
    plan_ref: NonEmptyStr = Field(max_length=200)
    status: PlanStatus
    window_start: datetime | None = None
    window_end: datetime | None = None

    @field_validator("window_start", "window_end")
    @classmethod
    def aware_dates(cls, value: datetime | None, info: Any) -> datetime | None:
        return _aware(value, info.field_name)

    @model_validator(mode="after")
    def ordered_window(self) -> ExecutionPlanFacts:
        if self.window_start and self.window_end and self.window_end < self.window_start:
            raise ValueError("window_end must be >= window_start")
        return self


class ExecutionActionFacts(StrictModel):
    action_ref: NonEmptyStr = Field(max_length=200)
    label: NonEmptyStr = Field(max_length=300)
    status: ActionStatus
    owner_assigned: bool
    sprint_ref: str | None = Field(default=None, max_length=200)
    sprint_status: str | None = Field(default=None, max_length=80)
    created_at: datetime
    started_at: datetime | None = None
    due_at: datetime | None = None
    completed_at: datetime | None = None
    last_check_in_at: datetime | None = None
    check_in_count: int = Field(default=0, ge=0)
    progress_percent: int | None = Field(default=None, ge=0, le=100)
    active_impediment_count: int = Field(default=0, ge=0)
    oldest_active_impediment_hours: int | None = Field(default=None, ge=0)
    open_dependency_count: int = Field(default=0, ge=0)
    overdue_dependency_count: int = Field(default=0, ge=0)
    evidence_count: int = Field(default=0, ge=0)
    approved_evidence_count: int = Field(default=0, ge=0)
    is_overdue: bool = False
    is_terminal: bool
    claims_execution: bool

    @field_validator("created_at", "started_at", "due_at", "completed_at", "last_check_in_at")
    @classmethod
    def aware_dates(cls, value: datetime | None, info: Any) -> datetime | None:
        return _aware(value, info.field_name)


class ExecutionFacts(StrictModel):
    plan: ExecutionPlanFacts | None = None
    actions: list[ExecutionActionFacts] = Field(default_factory=list)

    @model_validator(mode="after")
    def unique_actions(self) -> ExecutionFacts:
        refs = [x.action_ref for x in self.actions]
        if len(refs) != len(set(refs)):
            raise ValueError("action_ref values must be unique")
        return self


class MeasurementPlanFacts(StrictModel):
    plan_ref: NonEmptyStr = Field(max_length=200)
    status: PlanStatus


class MeasurementIndicatorFacts(StrictModel):
    indicator_ref: NonEmptyStr = Field(max_length=200)
    plan_ref: NonEmptyStr = Field(max_length=200)
    name: NonEmptyStr = Field(max_length=300)
    unit: NonEmptyStr = Field(max_length=80)
    direction: IndicatorDirection
    target_value: str | None = Field(default=None, pattern=r"^-?\d+(\.\d+)?$")
    target_min: str | None = Field(default=None, pattern=r"^-?\d+(\.\d+)?$")
    target_max: str | None = Field(default=None, pattern=r"^-?\d+(\.\d+)?$")
    baseline_value: str | None = Field(default=None, pattern=r"^-?\d+(\.\d+)?$")
    baseline_at: datetime | None = None
    latest_value: str | None = Field(default=None, pattern=r"^-?\d+(\.\d+)?$")
    latest_measured_at: datetime | None = None
    measurement_posture: MeasurementPosture
    target_posture: TargetPosture
    baseline_status: BaselineStatus
    is_measurement_overdue: bool = False
    next_measurement_due_at: datetime | None = None
    substantiation: Substantiation
    comparable_reading_count: int = Field(default=0, ge=0)

    @field_validator("baseline_at", "latest_measured_at", "next_measurement_due_at")
    @classmethod
    def aware_dates(cls, value: datetime | None, info: Any) -> datetime | None:
        return _aware(value, info.field_name)


class MeasurementFacts(StrictModel):
    plans: list[MeasurementPlanFacts] = Field(default_factory=list)
    indicators: list[MeasurementIndicatorFacts] = Field(default_factory=list)

    @model_validator(mode="after")
    def unique_refs(self) -> MeasurementFacts:
        plans = [x.plan_ref for x in self.plans]
        indicators = [x.indicator_ref for x in self.indicators]
        if len(plans) != len(set(plans)):
            raise ValueError("measurement plan_ref values must be unique")
        if len(indicators) != len(set(indicators)):
            raise ValueError("indicator_ref values must be unique")
        return self


class OutcomeFacts(StrictModel):
    result_direction: ResultDirection
    observed_at: datetime
    observation_summary: NonEmptyStr = Field(max_length=4000)
    measurement_basis_summary: NonEmptyStr = Field(max_length=4000)
    linked_measurement_count: int = Field(default=0, ge=0)

    @field_validator("observed_at")
    @classmethod
    def aware_observed_at(cls, value: datetime) -> datetime:
        return _aware(value, "observed_at")  # type: ignore[return-value]


class ExecutionIntelligenceInput(StrictModel):
    schema_version: Literal["1.0"]
    core_organization_id: UUID
    improvement_case_id: UUID
    request_id: NonEmptyStr
    correlation_id: NonEmptyStr
    captured_at: datetime
    source: SourceRef
    case: ExecutionCaseFacts
    execution: ExecutionFacts
    measurement: MeasurementFacts
    outcome: OutcomeFacts | None = None
    fact_refs: list[NonEmptyStr] = Field(min_length=1)
    metadata: EnvelopeMetadata | None = None

    @field_validator("captured_at")
    @classmethod
    def aware_captured_at(cls, value: datetime) -> datetime:
        return _aware(value, "captured_at")  # type: ignore[return-value]

    @field_validator("fact_refs")
    @classmethod
    def unique_fact_refs(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("fact_refs must be unique")
        return value


SignalCategory = Literal[
    "flow", "schedule", "blocker", "dependency", "evidence", "measurement", "outcome"
]
SignalLevel = Literal["information", "watch", "attention"]
SignalCode = Literal[
    "execution_not_started", "execution_progress_observed", "action_overdue",
    "execution_stale", "active_impediment", "open_dependency", "ownership_gap",
    "execution_evidence_gap", "measurement_baseline_gap", "measurement_overdue",
    "result_unsubstantiated", "target_met_awaiting_human_review",
    "target_not_met_attention", "outcome_measurement_tension",
    "result_observation_missing",
]
InterpretabilityStatus = Literal["insufficient_facts", "interpretable"]
ExecutionPosture = Literal[
    "insufficient_information", "not_started", "progressing", "attention_required",
    "stalled", "awaiting_result_evaluation", "result_observed",
]


class ExecutionSignal(StrictModel):
    code: SignalCode
    category: SignalCategory
    level: SignalLevel
    title: NonEmptyStr = Field(max_length=300)
    interpretation: NonEmptyStr = Field(max_length=4000)
    supporting_fact_refs: list[NonEmptyStr] = Field(min_length=1)
    iso_basis: list[IsoBasis] = Field(min_length=1)
    recommended_next_step: NonEmptyStr = Field(max_length=4000)
    requires_human_validation: Literal[True] = True


class ExecutionIntelligenceResult(StrictModel):
    schema_version: Literal["1.0"]
    core_organization_id: UUID
    improvement_case_id: UUID
    analysis_id: UUID
    request_id: NonEmptyStr
    correlation_id: NonEmptyStr
    generated_at: datetime
    mechanism_version: Literal["execution-intelligence-rules-v1"]
    interpretability_status: InterpretabilityStatus
    execution_posture: ExecutionPosture
    interpretation_summary: NonEmptyStr = Field(max_length=4000)
    signals: list[ExecutionSignal] = Field(default_factory=list)
    missing_information: list[NonEmptyStr] = Field(default_factory=list)
    limitations: list[NonEmptyStr] = Field(default_factory=list)

    @field_validator("generated_at")
    @classmethod
    def aware_generated_at(cls, value: datetime) -> datetime:
        return _aware(value, "generated_at")  # type: ignore[return-value]


class ExecutionIntelligenceRunOut(BaseModel):
    id: UUID
    organization_id: UUID
    improvement_case_id: UUID
    schema_version: str
    mechanism_version: str
    request_id: str
    correlation_id: str
    generated_at: datetime
    input_fingerprint: str
    input_snapshot: ExecutionIntelligenceInput
    result: ExecutionIntelligenceResult
    created_by: UUID
    created_at: datetime
    is_stale: bool = False


class ExecutionIntelligenceSummary(BaseModel):
    run_id: UUID
    generated_at: datetime
    interpretability_status: InterpretabilityStatus
    execution_posture: ExecutionPosture
    interpretation_summary: str
    signal_count: int
    is_stale: bool


def dump_jsonable(model: BaseModel) -> dict[str, Any]:
    return model.model_dump(mode="json")
