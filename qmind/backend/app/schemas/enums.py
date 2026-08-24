"""Domain state-machine enums — OpenAPI + runtime validation (domain-docs-v0)."""

from __future__ import annotations

from enum import Enum


class AssessmentStatus(str, Enum):
    draft = "draft"
    planned = "planned"
    in_progress = "in_progress"
    analysis = "analysis"
    actions = "actions"
    report = "report"
    closed = "closed"
    cancelled = "cancelled"


class AssessmentType(str, Enum):
    diagnosis = "diagnosis"
    internal_audit = "internal_audit"
    external_audit = "external_audit"
    certification_prep = "certification_prep"
    other = "other"


class FindingStatus(str, Enum):
    draft = "draft"
    in_review = "in_review"
    approved = "approved"
    rejected = "rejected"
    withdrawn = "withdrawn"
    discarded = "discarded"


class FindingType(str, Enum):
    conformity = "conformity"
    nonconformity = "nonconformity"
    opportunity = "opportunity"
    observation = "observation"


class EvidenceStatus(str, Enum):
    upload_pending = "upload_pending"
    quarantined = "quarantined"
    rejected = "rejected"
    approved = "approved"
    superseded = "superseded"
    pending_disposal = "pending_disposal"
    disposed = "disposed"


class EvidenceClassification(str, Enum):
    public = "public"
    internal = "internal"
    confidential = "confidential"
    restricted = "restricted"


class InterviewStatus(str, Enum):
    planned = "planned"
    confirmed = "confirmed"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"


class InterviewMode(str, Enum):
    onsite = "onsite"
    remote = "remote"
    hybrid = "hybrid"


class EvidenceLinkTargetType(str, Enum):
    requirement = "requirement"
    question = "question"
    finding = "finding"
    action_item = "action_item"
    interview = "interview"
    answer = "answer"
    action_check_in = "action_check_in"
    action_impediment = "action_impediment"
    measurement_record = "measurement_record"
    outcome_observation = "outcome_observation"
    improvement_case = "improvement_case"


class MeasurementPlanStatus(str, Enum):
    draft = "draft"
    active = "active"
    closed = "closed"


class IndicatorDirection(str, Enum):
    """What "better" means for this indicator.

    `within_range` wants the value inside the band; `maintain_range` wants it to
    stay where it already is and treats leaving the band as the failure. They
    evaluate identically but say different things to the reader, which is why
    both exist.
    """

    higher_is_better = "higher_is_better"
    lower_is_better = "lower_is_better"
    within_range = "within_range"
    maintain_range = "maintain_range"


# The first draft of ISOI-008 named directions after the arithmetic. Callers
# built against it keep working; the canonical value is always the new one.
INDICATOR_DIRECTION_ALIASES = {
    "increase_is_better": IndicatorDirection.higher_is_better,
    "decrease_is_better": IndicatorDirection.lower_is_better,
    "stay_within_range": IndicatorDirection.within_range,
}

RANGE_DIRECTIONS = frozenset(
    {IndicatorDirection.within_range.value, IndicatorDirection.maintain_range.value}
)


class IndicatorValueType(str, Enum):
    """Only decimal for now: an indicator is audit evidence and must be exact."""

    decimal = "decimal"


class IndicatorUnitKind(str, Enum):
    percentage = "percentage"
    count = "count"
    currency = "currency"
    ratio = "ratio"
    score = "score"
    duration_minutes = "duration_minutes"
    duration_hours = "duration_hours"
    duration_days = "duration_days"
    dimensionless = "dimensionless"
    custom = "custom"


class IndicatorStatus(str, Enum):
    active = "active"
    superseded = "superseded"
    retired = "retired"


class MeasurementKind(str, Enum):
    """A baseline is a measurement; it is just the first one."""

    baseline = "baseline"
    observation = "observation"


class MeasurementRecordStatus(str, Enum):
    """Derived, never stored: a reading is superseded once a correction exists."""

    active = "active"
    superseded = "superseded"


class BaselineStatus(str, Enum):
    """Whether we know where the indicator started."""

    missing = "missing"
    unavailable_justified = "unavailable_justified"
    recorded = "recorded"


class TargetEvaluationState(str, Enum):
    not_planned = "not_planned"
    awaiting_baseline = "awaiting_baseline"
    awaiting_measurement = "awaiting_measurement"
    on_track = "on_track"
    target_met = "target_met"
    target_not_met = "target_not_met"
    inconclusive = "inconclusive"


class SubstantiationLevel(str, Enum):
    none = "none"
    partial = "partial"
    verified = "verified"


class MeasurementPosture(str, Enum):
    not_planned = "not_planned"
    awaiting_baseline = "awaiting_baseline"
    awaiting_measurement = "awaiting_measurement"
    on_time = "on_time"
    overdue = "overdue"


class TargetPosture(str, Enum):
    unknown = "unknown"
    met = "met"
    not_met = "not_met"
    mixed = "mixed"


class MaturityStatus(str, Enum):
    draft = "draft"
    in_review = "in_review"
    approved = "approved"
    rejected = "rejected"
    superseded = "superseded"
    discarded = "discarded"


class Applicability(str, Enum):
    applicable = "applicable"
    not_applicable = "not_applicable"
    insufficient_info = "insufficient_info"


class ActionPlanStatus(str, Enum):
    draft = "draft"
    active = "active"
    completed = "completed"
    cancelled = "cancelled"


class ActionItemStatus(str, Enum):
    open = "open"
    in_progress = "in_progress"
    implemented = "implemented"
    validated = "validated"
    done = "done"
    cancelled = "cancelled"
    ineffective = "ineffective"
    ineffective_closed = "ineffective_closed"


class ActionKind(str, Enum):
    correction = "correction"
    corrective_action = "corrective_action"
    improvement = "improvement"


class ReportStatus(str, Enum):
    draft = "draft"
    in_review = "in_review"
    published = "published"
    archived = "archived"
    superseded = "superseded"
    discarded = "discarded"


class JobStatus(str, Enum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    cancelled = "cancelled"


class OrganizationStatus(str, Enum):
    active = "active"
    suspended = "suspended"
    closed = "closed"


class MembershipStatus(str, Enum):
    invited = "invited"
    active = "active"
    revoked = "revoked"
    expired = "expired"


class EvolutionCategory(str, Enum):
    direction_governance = "direction_governance"
    planning_risks = "planning_risks"
    people_resources = "people_resources"
    operations_customers = "operations_customers"
    measurement_decisions = "measurement_decisions"
    correction_improvement = "correction_improvement"


class EvolutionPriority(str, Enum):
    now = "now"
    next_cycle = "next_cycle"
    future = "future"
    investigate = "investigate"


class EvolutionConfidence(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


class EvolutionImpact(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


class EvolutionEffort(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


class EvolutionSuggestionStatus(str, Enum):
    proposed = "proposed"
    accepted = "accepted"
    dismissed = "dismissed"
    converted_to_action = "converted_to_action"
    superseded = "superseded"


class EvolutionGenerationMode(str, Enum):
    preliminary = "preliminary"
    analysis_ready = "analysis_ready"


class EvolutionPackageStatus(str, Enum):
    active = "active"
    superseded = "superseded"
