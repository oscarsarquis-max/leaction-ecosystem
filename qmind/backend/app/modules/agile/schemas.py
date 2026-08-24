"""Pydantic models — Agile Action Execution Workspace (ISOI-007)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.enums import ActionItemStatus, ActionKind

SquadStatus = Literal["active", "inactive"]
AgileRole = Literal["value_owner", "facilitator", "execution_member", "stakeholder"]
MembershipStatus = Literal["active", "inactive"]
SprintStatus = Literal["planned", "active", "completed", "cancelled"]
CardPriority = Literal["critical", "high", "medium", "low"]
CheckInHealth = Literal["on_track", "attention", "blocked"]
ImpedimentSeverity = Literal["low", "medium", "high", "critical"]
ImpedimentStatus = Literal["open", "resolved", "cancelled"]
DependencyType = Literal["blocks", "relates_to"]
DependencyStatus = Literal["active", "removed"]
CeremonyType = Literal["sprint_planning", "daily_check_in", "sprint_review", "retrospective"]
BoardColumnKey = Literal[
    "backlog",
    "selected",
    "in_progress",
    "implemented",
    "validated",
    "ineffective",
    "done",
]
CarryDecisionKind = Literal["backlog"]  # sprint_id handled via UUID union in model

CHECK_IN_STALE_WINDOW_HOURS = 72
"""A card is considered without a recent check-in after this many hours."""


class SquadCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    value_owner_membership_id: UUID = Field(
        description="Active org membership that answers for the squad value stream",
    )
    purpose: str = Field(default="", max_length=2000)
    default_sprint_length_days: int = Field(default=14, ge=1, le=90)


class SquadUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    purpose: str | None = Field(default=None, max_length=2000)
    status: SquadStatus | None = None
    default_sprint_length_days: int | None = Field(default=None, ge=1, le=90)


class SquadOut(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    purpose: str
    status: SquadStatus
    default_sprint_length_days: int
    created_by: UUID
    created_at: datetime
    updated_at: datetime


class SquadMembershipCreate(BaseModel):
    membership_id: UUID
    agile_role: AgileRole


class SquadMembershipUpdate(BaseModel):
    agile_role: AgileRole | None = None
    status: MembershipStatus | None = None


class SquadMembershipOut(BaseModel):
    id: UUID
    organization_id: UUID
    squad_id: UUID
    membership_id: UUID
    agile_role: AgileRole
    status: MembershipStatus
    member_display_name: str | None = None
    member_email: str | None = None
    created_by: UUID
    created_at: datetime
    updated_at: datetime


class SprintCreate(BaseModel):
    squad_id: UUID
    name: str = Field(min_length=1, max_length=200)
    goal: str = Field(default="", max_length=2000)
    starts_at: datetime
    ends_at: datetime
    timezone: str = Field(default="America/Sao_Paulo", max_length=64)
    capacity_points: int | None = Field(default=None, gt=0)
    wip_limit_in_progress: int | None = Field(default=None, gt=0)


class SprintUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    goal: str | None = Field(default=None, max_length=2000)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    timezone: str | None = Field(default=None, max_length=64)
    capacity_points: int | None = Field(default=None, gt=0)
    wip_limit_in_progress: int | None = Field(default=None, gt=0)
    status: SprintStatus | None = None


class SprintOut(BaseModel):
    id: UUID
    organization_id: UUID
    squad_id: UUID
    name: str
    goal: str
    starts_at: datetime
    ends_at: datetime
    timezone: str
    status: SprintStatus
    capacity_points: int | None
    wip_limit_in_progress: int | None
    activation_skip_cards_rationale: str | None
    created_by: UUID
    activated_by: UUID | None
    closed_by: UUID | None
    created_at: datetime
    activated_at: datetime | None
    closed_at: datetime | None
    updated_at: datetime


class SprintActivateIn(BaseModel):
    activation_skip_cards_rationale: str | None = Field(default=None, max_length=2000)


class CarryDecisionIn(BaseModel):
    action_item_id: UUID
    decision: str = Field(
        description="backlog or target sprint UUID for carry-over",
        min_length=1,
    )


class SprintCompleteIn(BaseModel):
    carry_decisions: list[CarryDecisionIn] = Field(default_factory=list)


class SprintCardAllocateIn(BaseModel):
    action_item_id: UUID
    priority: CardPriority = "medium"
    estimate_points: int | None = Field(default=None, gt=0)
    position: int | None = Field(default=None, ge=0)


class SprintCardPositionIn(BaseModel):
    position: int = Field(ge=0)


class SprintCardRemoveIn(BaseModel):
    removal_reason: str = Field(default="", max_length=2000)


class SprintCardOut(BaseModel):
    id: UUID
    organization_id: UUID
    sprint_id: UUID
    action_item_id: UUID
    priority: CardPriority
    estimate_points: int | None
    position: int
    committed_at: datetime
    removed_at: datetime | None
    removal_reason: str | None
    carried_from_sprint_id: UUID | None
    created_by: UUID
    created_at: datetime
    updated_at: datetime


class BoardCardOut(BaseModel):
    action_item_id: UUID
    action_plan_id: UUID
    description: str
    action_kind: ActionKind
    status: ActionItemStatus
    owner_membership_id: UUID
    owner_display_name: str
    owner_email: str
    due_at: datetime
    is_overdue: bool
    priority: CardPriority | None = None
    estimate_points: int | None = None
    sprint_id: UUID | None = None
    sprint_name: str | None = None
    squad_id: UUID | None = None
    squad_name: str | None = None
    has_open_impediment: bool = False
    has_blocking_dependency: bool = False
    open_impediment_count: int = 0
    blocking_dependency_count: int = 0
    latest_check_in_at: datetime | None = None
    latest_check_in_health: CheckInHealth | None = None
    source_analysis_run_id: UUID | None = None
    source_finding_code: str | None = None
    source_analysis_is_stale: bool | None = None
    assessment_id: UUID | None = None
    improvement_case_id: UUID | None = None
    finding_id: UUID | None = None
    card_id: UUID | None = None
    position: int | None = None


class BoardColumnOut(BaseModel):
    key: BoardColumnKey
    label: str
    cards: list[BoardCardOut] = Field(default_factory=list)


class BoardOut(BaseModel):
    squad_id: UUID | None = None
    sprint_id: UUID | None = None
    active_sprint_id: UUID | None = None
    wip_limit_in_progress: int | None = None
    wip_signal: bool = False
    in_progress_count: int = 0
    columns: list[BoardColumnOut]


class BoardMoveIn(BaseModel):
    action_item_id: UUID
    target_column: BoardColumnKey
    sprint_id: UUID | None = Field(
        default=None,
        description="Required when moving to/from selected column",
    )
    impediment_override_justification: str | None = Field(default=None, max_length=2000)
    reject_reason: str | None = Field(default=None, max_length=2000)
    efficacy_fail_reason: str | None = Field(default=None, max_length=2000)


class BoardMoveOut(BaseModel):
    action_item_id: UUID
    from_column: BoardColumnKey | None
    to_column: BoardColumnKey
    item_status: ActionItemStatus
    transition_event: str | None = None


class CheckInCreate(BaseModel):
    health: CheckInHealth
    progress_note: str = Field(min_length=1, max_length=4000)
    next_step: str = Field(default="", max_length=2000)
    sprint_id: UUID | None = None
    idempotency_key: str | None = Field(default=None, max_length=128)


class CheckInOut(BaseModel):
    id: UUID
    organization_id: UUID
    action_item_id: UUID
    sprint_id: UUID | None
    health: CheckInHealth
    progress_note: str
    next_step: str
    reported_by: UUID
    reported_at: datetime


class ImpedimentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=4000)
    severity: ImpedimentSeverity = "medium"
    sprint_id: UUID | None = None
    owner_membership_id: UUID | None = None


class ImpedimentUpdate(BaseModel):
    status: ImpedimentStatus | None = None
    resolution_note: str | None = Field(default=None, max_length=4000)
    owner_membership_id: UUID | None = None
    severity: ImpedimentSeverity | None = None


class ImpedimentOut(BaseModel):
    id: UUID
    organization_id: UUID
    action_item_id: UUID
    sprint_id: UUID | None
    title: str
    description: str
    severity: ImpedimentSeverity
    status: ImpedimentStatus
    owner_membership_id: UUID | None
    opened_by: UUID
    opened_at: datetime
    resolved_by: UUID | None
    resolved_at: datetime | None
    resolution_note: str | None
    updated_at: datetime


class DependencyCreate(BaseModel):
    predecessor_action_item_id: UUID
    dependent_action_item_id: UUID
    dependency_type: DependencyType


class DependencyOut(BaseModel):
    id: UUID
    organization_id: UUID
    predecessor_action_item_id: UUID
    dependent_action_item_id: UUID
    dependency_type: DependencyType
    status: DependencyStatus = "active"
    created_by: UUID
    created_at: datetime
    removed_by: UUID | None = None
    removed_at: datetime | None = None
    removal_reason: str | None = None


class CeremonyRecordCreate(BaseModel):
    agenda_event_id: UUID
    ceremony_type: CeremonyType
    summary: str = Field(default="", max_length=8000)
    decisions: str = Field(default="", max_length=8000)
    follow_up: str = Field(default="", max_length=8000)


class CeremonyRecordOut(BaseModel):
    id: UUID
    organization_id: UUID
    sprint_id: UUID
    agenda_event_id: UUID
    ceremony_type: CeremonyType
    summary: str
    decisions: str
    follow_up: str
    recorded_by: UUID
    recorded_at: datetime
    revision: int


class SprintMetricsOut(BaseModel):
    sprint_id: UUID
    squad_id: UUID
    planned_cards: int
    completed_cards: int
    carry_over_cards: int
    in_progress_count: int
    open_impediments: int
    overdue_actions: int
    throughput: int
    goal: str
    status: SprintStatus
    average_cycle_time_hours: float | None = None
    median_cycle_time_hours: float | None = None
    oldest_in_progress_age_hours: float | None = None
    blocked_time_hours: float | None = None
    cards_without_recent_check_in: int = 0
    check_in_stale_window_hours: int = CHECK_IN_STALE_WINDOW_HOURS
    review_outcome: str | None = None
