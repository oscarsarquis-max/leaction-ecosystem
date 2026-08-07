from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.agenda.schemas import PlanActivityKind
from app.modules.interviews.schemas import InterviewOut


MeetingKind = Literal["opening_meeting", "closing_meeting", "additional_meeting"]

MilestoneKind = Literal[
    "milestone_preparation_done",
    "milestone_plan_approved",
    "milestone_field_start",
    "milestone_field_done",
    "milestone_analysis_done",
    "milestone_report_due",
    "milestone_closure_due",
    "milestone_custom",
]

ScheduleItemKind = Literal["interview", "meeting", "milestone"]


class ScheduleMeetingCreate(BaseModel):
    kind: MeetingKind
    objective: str = Field(default="", max_length=4000)
    participant_membership_ids: list[UUID] = Field(default_factory=list)
    starts_at: datetime
    duration_minutes: int = Field(default=60, ge=1, le=24 * 60)
    location_or_link: str = Field(default="", max_length=500)
    preparation: str = Field(default="", max_length=4000)
    owner_membership_id: UUID | None = None
    title: str | None = Field(default=None, max_length=200)
    outside_period_justification: str = Field(default="", max_length=2000)
    timezone: str | None = Field(default=None, max_length=64)


class ScheduleMeetingUpdate(BaseModel):
    objective: str | None = Field(default=None, max_length=4000)
    participant_membership_ids: list[UUID] | None = None
    starts_at: datetime | None = None
    duration_minutes: int | None = Field(default=None, ge=1, le=24 * 60)
    location_or_link: str | None = Field(default=None, max_length=500)
    preparation: str | None = Field(default=None, max_length=4000)
    owner_membership_id: UUID | None = None
    title: str | None = Field(default=None, max_length=200)
    outside_period_justification: str | None = Field(default=None, max_length=2000)
    status: Literal["scheduled", "completed", "cancelled", "waived"] | None = None
    waiver_reason: str | None = Field(default=None, max_length=2000)
    timezone: str | None = Field(default=None, max_length=64)


class ScheduleMilestoneCreate(BaseModel):
    kind: MilestoneKind
    title: str | None = Field(default=None, max_length=200)
    notes: str = Field(default="", max_length=4000)
    occurs_at: datetime
    owner_membership_id: UUID | None = None
    outside_period_justification: str = Field(default="", max_length=2000)
    timezone: str | None = Field(default=None, max_length=64)


class ScheduleMilestoneUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=4000)
    occurs_at: datetime | None = None
    owner_membership_id: UUID | None = None
    outside_period_justification: str | None = Field(default=None, max_length=2000)
    status: Literal["scheduled", "completed", "cancelled"] | None = None
    timezone: str | None = Field(default=None, max_length=64)


class ScheduleItemOut(BaseModel):
    kind: ScheduleItemKind
    id: UUID
    title: str
    status: str
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    timezone: str = "America/Sao_Paulo"
    location_or_link: str = ""
    preparation: str = ""
    objective: str = ""
    process_name: str = ""
    owner_membership_id: UUID | None = None
    participant_membership_ids: list[UUID] = Field(default_factory=list)
    plan_activity_kind: PlanActivityKind | None = None
    interview_id: UUID | None = None
    agenda_event_id: UUID | None = None
    primary_action_label: str = ""
    primary_action_href: str | None = None
    next_action: str = ""


class OverlapWarning(BaseModel):
    message: str
    membership_id: UUID | None = None
    item_ids: list[UUID] = Field(default_factory=list)


class SchedulePending(BaseModel):
    key: str
    label: str
    blocking: bool = True


class AuditPlanScheduleOut(BaseModel):
    assessment_id: UUID
    organization_id: UUID
    timezone: str
    agenda_href: str = "/assessments"
    items: list[ScheduleItemOut] = Field(default_factory=list)
    interviews: list[InterviewOut] = Field(default_factory=list)
    overlaps: list[OverlapWarning] = Field(default_factory=list)
    pendings: list[SchedulePending] = Field(default_factory=list)
    next_action: str = ""
    has_opening_meeting: bool = False
    has_closing_meeting: bool = False
