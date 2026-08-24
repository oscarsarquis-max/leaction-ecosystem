"""Pydantic models — action measurement plans and indicators (ISOI-008 rev001).

Every numeric value is a `Decimal`. Floats are forbidden here: an indicator is
audit evidence, and 0.1 + 0.2 must not become 0.30000000000000004 in a report.

Two shapes deserve a note:

* `IndicatorReviseIn` distinguishes *unset* from *null*. "Do not touch the
  target date" and "there is no target date any more" are different
  instructions, and a partial update that cannot tell them apart will silently
  erase fields the user never mentioned. The distinction is read from
  `model_fields_set`, never from the value alone.
* `MeasurementPlanCreate` still accepts `purpose`. The field was renamed to
  `objective` because a measurement plan has to say what it must *achieve*, not
  what it is *about*; the old name keeps working so no caller breaks.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.enums import (
    INDICATOR_DIRECTION_ALIASES,
    RANGE_DIRECTIONS,
    BaselineStatus,
    IndicatorDirection,
    IndicatorStatus,
    IndicatorUnitKind,
    IndicatorValueType,
    MeasurementKind,
    MeasurementPlanStatus,
    MeasurementPosture,
    MeasurementRecordStatus,
    SubstantiationLevel,
    TargetEvaluationState,
    TargetPosture,
)

_MAX_TEXT = 4000
_MAX_DECIMAL_PLACES = 8

# Legacy free-text units seen in the field, mapped onto the closed enumeration.
_LEGACY_UNIT_KINDS: dict[str, IndicatorUnitKind] = {
    "%": IndicatorUnitKind.percentage,
    "pct": IndicatorUnitKind.percentage,
    "percent": IndicatorUnitKind.percentage,
    "percentual": IndicatorUnitKind.percentage,
    "min": IndicatorUnitKind.duration_minutes,
    "minuto": IndicatorUnitKind.duration_minutes,
    "minutos": IndicatorUnitKind.duration_minutes,
    "minutes": IndicatorUnitKind.duration_minutes,
    "h": IndicatorUnitKind.duration_hours,
    "hora": IndicatorUnitKind.duration_hours,
    "horas": IndicatorUnitKind.duration_hours,
    "hours": IndicatorUnitKind.duration_hours,
    "d": IndicatorUnitKind.duration_days,
    "dia": IndicatorUnitKind.duration_days,
    "dias": IndicatorUnitKind.duration_days,
    "day": IndicatorUnitKind.duration_days,
    "days": IndicatorUnitKind.duration_days,
}


def _nonblank(value: str) -> str:
    cleaned = (value or "").strip()
    if not cleaned:
        raise ValueError("must not be blank")
    return cleaned


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        raise ValueError("must be timezone-aware")
    return value


def _resolve_direction(value) -> IndicatorDirection | None:
    """Accept the withdrawn ISOI-008 direction names as aliases."""
    if value is None or isinstance(value, IndicatorDirection):
        return value
    text = str(value)
    if text in INDICATOR_DIRECTION_ALIASES:
        return INDICATOR_DIRECTION_ALIASES[text]
    return IndicatorDirection(text)


def _unit_from_legacy(unit: str | None) -> tuple[IndicatorUnitKind, str | None]:
    cleaned = (unit or "").strip()
    if not cleaned:
        return IndicatorUnitKind.dimensionless, None
    mapped = _LEGACY_UNIT_KINDS.get(cleaned.lower())
    if mapped is not None:
        return mapped, None
    return IndicatorUnitKind.custom, cleaned


def unit_label(
    unit_kind: str, custom_unit_label: str | None, currency_code: str | None
) -> str:
    """Human-readable unit for headlines and charts."""
    labels = {
        IndicatorUnitKind.percentage.value: "%",
        IndicatorUnitKind.count.value: "un",
        IndicatorUnitKind.ratio.value: "x",
        IndicatorUnitKind.score.value: "pts",
        IndicatorUnitKind.duration_minutes.value: "min",
        IndicatorUnitKind.duration_hours.value: "h",
        IndicatorUnitKind.duration_days.value: "dias",
        IndicatorUnitKind.dimensionless.value: "",
    }
    if unit_kind == IndicatorUnitKind.currency.value:
        return currency_code or ""
    if unit_kind == IndicatorUnitKind.custom.value:
        return (custom_unit_label or "").strip()
    return labels.get(unit_kind, "")


class _UnitFields(BaseModel):
    """Unit shape shared by create and revise."""

    unit_kind: IndicatorUnitKind | None = None
    custom_unit_label: str | None = Field(default=None, max_length=60)
    currency_code: str | None = Field(default=None, min_length=3, max_length=3)
    decimal_places: int | None = Field(default=None, ge=0, le=_MAX_DECIMAL_PLACES)

    @field_validator("currency_code")
    @classmethod
    def upper_currency(cls, v: str | None) -> str | None:
        if v is None:
            return None
        code = v.strip().upper()
        if not code.isalpha() or len(code) != 3:
            raise ValueError("currency_code must be an ISO-4217 alphabetic code")
        return code


def _assert_unit_coherent(
    unit_kind: IndicatorUnitKind,
    custom_unit_label: str | None,
    currency_code: str | None,
) -> None:
    if unit_kind == IndicatorUnitKind.custom and not (custom_unit_label or "").strip():
        raise ValueError("custom_unit_label is required when unit_kind is custom")
    if unit_kind == IndicatorUnitKind.currency and not currency_code:
        raise ValueError("currency_code is required when unit_kind is currency")
    if unit_kind != IndicatorUnitKind.currency and currency_code:
        raise ValueError("currency_code only applies when unit_kind is currency")


def _assert_target_coherent(
    direction: IndicatorDirection,
    target_value: Decimal | None,
    target_min: Decimal | None,
    target_max: Decimal | None,
) -> None:
    if direction.value in RANGE_DIRECTIONS:
        if target_value is not None:
            raise ValueError(f"{direction.value} uses target_min/target_max, not target_value")
        if target_min is not None and target_max is not None and target_max < target_min:
            raise ValueError("target_max must be >= target_min")
        return
    if target_min is not None or target_max is not None:
        raise ValueError(f"{direction.value} uses target_value, not target_min/target_max")


def _assert_percentage_bounds(
    unit_kind: IndicatorUnitKind, values: dict[str, Decimal | None]
) -> None:
    if unit_kind != IndicatorUnitKind.percentage:
        return
    for field, value in values.items():
        if value is not None and not (Decimal(0) <= value <= Decimal(100)):
            raise ValueError(f"{field} must be between 0 and 100 for a percentage")


# --- measurement plans ---------------------------------------------------


class MeasurementPlanCreate(BaseModel):
    model_config = {"extra": "forbid"}

    action_plan_id: UUID
    objective: str = Field(default="", max_length=_MAX_TEXT)
    owner_membership_id: UUID | None = None
    review_cadence_days: int | None = Field(default=None, gt=0, le=3650)
    next_review_at: datetime | None = None
    purpose: str | None = Field(
        default=None,
        max_length=_MAX_TEXT,
        deprecated=True,
        description="Deprecated alias for `objective`.",
    )

    @field_validator("next_review_at")
    @classmethod
    def aware_review(cls, v: datetime | None) -> datetime | None:
        return _aware(v)

    @model_validator(mode="after")
    def fold_legacy_purpose(self) -> "MeasurementPlanCreate":
        legacy = self.__dict__.get("purpose") or ""
        if not self.objective.strip() and legacy.strip():
            object.__setattr__(self, "objective", legacy.strip())
        return self


class MeasurementPlanUpdate(BaseModel):
    """Only the fields actually present in the request are applied."""

    model_config = {"extra": "forbid"}

    objective: str | None = Field(default=None, max_length=_MAX_TEXT)
    owner_membership_id: UUID | None = None
    review_cadence_days: int | None = Field(default=None, gt=0, le=3650)
    next_review_at: datetime | None = None
    purpose: str | None = Field(
        default=None,
        max_length=_MAX_TEXT,
        deprecated=True,
        description="Deprecated alias for `objective`.",
    )

    @field_validator("next_review_at")
    @classmethod
    def aware_review(cls, v: datetime | None) -> datetime | None:
        return _aware(v)

    def provided(self, field: str) -> bool:
        if field == "objective" and "purpose" in self.model_fields_set:
            return True
        return field in self.model_fields_set

    def objective_value(self) -> str | None:
        if "objective" in self.model_fields_set:
            return (self.objective or "").strip()
        if "purpose" in self.model_fields_set:
            return (self.__dict__.get("purpose") or "").strip()
        return None


class MeasurementPlanCloseIn(BaseModel):
    model_config = {"extra": "forbid"}

    closure_reason: str = Field(min_length=1, max_length=_MAX_TEXT)

    @field_validator("closure_reason")
    @classmethod
    def strip_reason(cls, v: str) -> str:
        return _nonblank(v)


class MeasurementPlanOut(BaseModel):
    id: UUID
    organization_id: UUID
    action_plan_id: UUID
    assessment_id: UUID | None = None
    improvement_case_id: UUID | None = None
    objective: str
    owner_membership_id: UUID | None = None
    owner_display_name: str | None = None
    owner_email: str | None = None
    review_cadence_days: int | None = None
    next_review_at: datetime | None = None
    status: MeasurementPlanStatus
    activated_by: UUID | None = None
    activated_at: datetime | None = None
    closed_by: UUID | None = None
    closed_at: datetime | None = None
    closure_reason: str | None = None
    created_by: UUID
    created_at: datetime
    updated_at: datetime
    indicator_count: int = 0
    active_indicator_count: int = 0


# --- indicators ----------------------------------------------------------


class IndicatorCreate(_UnitFields):
    model_config = {"extra": "forbid"}

    code: str = Field(min_length=1, max_length=60)
    name: str = Field(min_length=1, max_length=200)
    question: str = Field(default="", max_length=_MAX_TEXT)
    owner_membership_id: UUID | None = None
    direction: IndicatorDirection
    baseline_value: Decimal | None = None
    baseline_at: datetime | None = None
    baseline_unavailable_reason: str | None = Field(default=None, max_length=_MAX_TEXT)
    target_value: Decimal | None = None
    target_min: Decimal | None = None
    target_max: Decimal | None = None
    target_due_at: datetime | None = None
    measurement_frequency_days: int | None = Field(default=None, gt=0, le=3650)
    data_source: str = Field(default="", max_length=_MAX_TEXT)
    collection_method: str = Field(default="", max_length=_MAX_TEXT)
    unit: str | None = Field(
        default=None,
        max_length=60,
        deprecated=True,
        description="Deprecated free-text unit; use unit_kind/custom_unit_label.",
    )

    @field_validator("code")
    @classmethod
    def clean_code(cls, v: str) -> str:
        return _nonblank(v).upper()

    @field_validator("name")
    @classmethod
    def clean_name(cls, v: str) -> str:
        return _nonblank(v)

    @field_validator("direction", mode="before")
    @classmethod
    def accept_direction_alias(cls, v):
        return _resolve_direction(v)

    @field_validator("baseline_at", "target_due_at")
    @classmethod
    def aware_datetimes(cls, v: datetime | None) -> datetime | None:
        return _aware(v)

    @model_validator(mode="after")
    def check_shape(self) -> "IndicatorCreate":
        kind = self.unit_kind
        label = self.custom_unit_label
        if kind is None:
            kind, legacy_label = _unit_from_legacy(self.__dict__.get("unit"))
            label = label or legacy_label
        object.__setattr__(self, "unit_kind", kind)
        object.__setattr__(self, "custom_unit_label", label)
        if self.decimal_places is None:
            object.__setattr__(self, "decimal_places", 2)
        _assert_unit_coherent(kind, label, self.currency_code)
        _assert_target_coherent(
            self.direction, self.target_value, self.target_min, self.target_max
        )
        _assert_percentage_bounds(
            kind,
            {
                "target_value": self.target_value,
                "target_min": self.target_min,
                "target_max": self.target_max,
                "baseline_value": self.baseline_value,
            },
        )
        if self.baseline_value is None and self.baseline_at is not None:
            raise ValueError("baseline_at requires baseline_value")
        # A draft may be saved without a baseline or a reason for its absence:
        # teams routinely define the indicator before they can pull the number.
        # The plan cannot be activated until one of the two exists.
        return self


class IndicatorReviseIn(_UnitFields):
    """Revising an indicator that already has data creates a new version.

    Absent fields are left alone; fields explicitly set to `null` are cleared.
    """

    model_config = {"extra": "forbid"}

    revision_reason: str = Field(min_length=1, max_length=_MAX_TEXT)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    question: str | None = Field(default=None, max_length=_MAX_TEXT)
    owner_membership_id: UUID | None = None
    direction: IndicatorDirection | None = None
    baseline_unavailable_reason: str | None = Field(default=None, max_length=_MAX_TEXT)
    target_value: Decimal | None = None
    target_min: Decimal | None = None
    target_max: Decimal | None = None
    target_due_at: datetime | None = None
    measurement_frequency_days: int | None = Field(default=None, gt=0, le=3650)
    data_source: str | None = Field(default=None, max_length=_MAX_TEXT)
    collection_method: str | None = Field(default=None, max_length=_MAX_TEXT)
    unit: str | None = Field(
        default=None,
        max_length=60,
        deprecated=True,
        description="Deprecated free-text unit; use unit_kind/custom_unit_label.",
    )

    @field_validator("revision_reason")
    @classmethod
    def strip_reason(cls, v: str) -> str:
        return _nonblank(v)

    @field_validator("direction", mode="before")
    @classmethod
    def accept_direction_alias(cls, v):
        return _resolve_direction(v)

    @field_validator("target_due_at")
    @classmethod
    def aware_datetimes(cls, v: datetime | None) -> datetime | None:
        return _aware(v)

    @model_validator(mode="after")
    def fold_legacy_unit(self) -> "IndicatorReviseIn":
        if "unit" in self.model_fields_set and "unit_kind" not in self.model_fields_set:
            kind, label = _unit_from_legacy(self.__dict__.get("unit"))
            object.__setattr__(self, "unit_kind", kind)
            if label is not None:
                object.__setattr__(self, "custom_unit_label", label)
            self.model_fields_set.add("unit_kind")
            if label is not None:
                self.model_fields_set.add("custom_unit_label")
        return self

    def provided(self, field: str) -> bool:
        return field in self.model_fields_set


class IndicatorRetireIn(BaseModel):
    model_config = {"extra": "forbid"}

    retired_reason: str = Field(min_length=1, max_length=_MAX_TEXT)

    @field_validator("retired_reason")
    @classmethod
    def strip_reason(cls, v: str) -> str:
        return _nonblank(v)


class IndicatorOut(BaseModel):
    """The baseline block is a read-only projection.

    The baseline itself lives in `measurement_records` as the indicator's first
    reading; it is echoed here so a form can show "started at X" without a
    second request. Writing to it is done by recording a baseline measurement,
    never by patching the definition.
    """

    id: UUID
    organization_id: UUID
    measurement_plan_id: UUID
    code: str
    name: str
    question: str
    owner_membership_id: UUID | None = None
    owner_display_name: str | None = None
    owner_email: str | None = None
    value_type: IndicatorValueType = IndicatorValueType.decimal
    unit_kind: IndicatorUnitKind
    custom_unit_label: str | None = None
    currency_code: str | None = None
    decimal_places: int
    unit_label: str
    direction: IndicatorDirection
    baseline_status: BaselineStatus
    baseline_value: Decimal | None = None
    baseline_at: datetime | None = None
    baseline_measurement_id: UUID | None = None
    baseline_unavailable_reason: str | None = None
    target_value: Decimal | None = None
    target_min: Decimal | None = None
    target_max: Decimal | None = None
    target_due_at: datetime | None = None
    measurement_frequency_days: int | None = None
    data_source: str
    collection_method: str
    status: IndicatorStatus
    version: int
    lineage_id: UUID
    supersedes_indicator_id: UUID | None = None
    revision_reason: str | None = None
    retired_reason: str | None = None
    created_by: UUID
    created_at: datetime
    updated_at: datetime
    measurement_count: int = 0
    latest_value: Decimal | None = None
    latest_measured_at: datetime | None = None


# --- measurement records -------------------------------------------------


class MeasurementRecordCreate(BaseModel):
    model_config = {"extra": "forbid"}

    indicator_definition_id: UUID
    value: Decimal
    measured_at: datetime
    measurement_kind: MeasurementKind = MeasurementKind.observation
    window_start: datetime | None = None
    window_end: datetime | None = None
    note: str = Field(default="", max_length=_MAX_TEXT)
    collection_method: str = Field(default="", max_length=_MAX_TEXT)
    evidence_ids: list[UUID] = Field(
        default_factory=list,
        max_length=20,
        description=(
            "Already-authorized evidences to attach to this reading. A reading "
            "with no evidence is recorded, but it is not substantiated."
        ),
    )
    idempotency_key: str | None = Field(default=None, max_length=128)

    @field_validator("measured_at", "window_start", "window_end")
    @classmethod
    def aware_datetimes(cls, v: datetime | None) -> datetime | None:
        return _aware(v)

    @model_validator(mode="after")
    def check_window(self) -> "MeasurementRecordCreate":
        if (
            self.window_start is not None
            and self.window_end is not None
            and self.window_end < self.window_start
        ):
            raise ValueError("window_end must be >= window_start")
        return self


class MeasurementCorrectionIn(BaseModel):
    """A correction never rewrites a value — it records a superseding one."""

    model_config = {"extra": "forbid"}

    value: Decimal
    correction_reason: str = Field(min_length=1, max_length=_MAX_TEXT)
    measured_at: datetime | None = None
    note: str = Field(default="", max_length=_MAX_TEXT)
    evidence_ids: list[UUID] = Field(default_factory=list, max_length=20)
    idempotency_key: str | None = Field(default=None, max_length=128)

    @field_validator("correction_reason")
    @classmethod
    def strip_reason(cls, v: str) -> str:
        return _nonblank(v)

    @field_validator("measured_at")
    @classmethod
    def aware_measured_at(cls, v: datetime | None) -> datetime | None:
        return _aware(v)


class MeasurementRecordOut(BaseModel):
    id: UUID
    organization_id: UUID
    measurement_plan_id: UUID
    indicator_definition_id: UUID
    measurement_kind: MeasurementKind
    value: Decimal
    measured_at: datetime
    window_start: datetime | None = None
    window_end: datetime | None = None
    note: str
    collection_method: str
    status: MeasurementRecordStatus
    supersedes_measurement_id: UUID | None = None
    superseded_by_measurement_id: UUID | None = None
    correction_reason: str | None = None
    evidence_link_count: int = 0
    verified_evidence_count: int = 0
    substantiation: SubstantiationLevel = SubstantiationLevel.none
    recorded_by: UUID
    recorded_at: datetime


# --- projections ---------------------------------------------------------


class TargetEvaluationOut(BaseModel):
    """What the numbers say about one indicator, in plain language."""

    indicator_definition_id: UUID
    indicator_code: str
    indicator_name: str
    unit_kind: IndicatorUnitKind
    unit_label: str
    decimal_places: int
    direction: IndicatorDirection
    state: TargetEvaluationState
    baseline_status: BaselineStatus
    substantiation: SubstantiationLevel
    baseline_value: Decimal | None = None
    baseline_at: datetime | None = None
    target_value: Decimal | None = None
    target_min: Decimal | None = None
    target_max: Decimal | None = None
    target_due_at: datetime | None = None
    latest_value: Decimal | None = None
    latest_measured_at: datetime | None = None
    latest_measurement_id: UUID | None = None
    measurement_count: int = 0
    evidence_link_count: int = 0
    verified_evidence_count: int = 0
    next_measurement_due_at: datetime | None = None
    is_measurement_overdue: bool = False
    owner_membership_id: UUID | None = None
    owner_display_name: str | None = None
    headline: str
    what_to_do_next: str


class MeasurementSummaryOut(BaseModel):
    action_plan_id: UUID
    plan: MeasurementPlanOut | None = None
    measurement_posture: MeasurementPosture
    target_posture: TargetPosture
    substantiation: SubstantiationLevel
    baseline_status: BaselineStatus = BaselineStatus.missing
    indicator_count: int = 0
    overdue_indicator_count: int = 0
    evaluations: list[TargetEvaluationOut] = Field(default_factory=list)
    headline: str
    what_to_do_next: str
