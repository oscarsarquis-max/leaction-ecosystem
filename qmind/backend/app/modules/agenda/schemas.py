from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

EventType = Literal[
    "interview", "meeting", "visit", "reminder", "milestone", "deadline", "other"
]
EventStatus = Literal["scheduled", "completed", "cancelled"]


class AgendaEventCreate(BaseModel):
    assessment_id: UUID | None = None
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)
    event_type: EventType
    starts_at: datetime
    ends_at: datetime | None = None
    timezone: str = Field(default="America/Sao_Paulo", max_length=64)
    owner_membership_id: UUID | None = None
    participant_membership_ids: list[UUID] = Field(default_factory=list)
    location_or_link: str = Field(default="", max_length=500)
    guidance: str = Field(default="", max_length=2000)
    related_action: str = Field(default="", max_length=200)


class AgendaEventUpdate(BaseModel):
    assessment_id: UUID | None = None
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    event_type: EventType | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    timezone: str | None = Field(default=None, max_length=64)
    owner_membership_id: UUID | None = None
    participant_membership_ids: list[UUID] | None = None
    location_or_link: str | None = Field(default=None, max_length=500)
    guidance: str | None = Field(default=None, max_length=2000)
    related_action: str | None = Field(default=None, max_length=200)
    status: EventStatus | None = None


class AgendaEventOut(BaseModel):
    id: UUID
    organization_id: UUID
    assessment_id: UUID | None
    assessment_label: str | None = None
    title: str
    description: str
    event_type: EventType
    starts_at: datetime
    ends_at: datetime | None
    timezone: str
    owner_membership_id: UUID | None
    owner_label: str | None = None
    participant_membership_ids: list[UUID]
    location_or_link: str
    status: EventStatus
    guidance: str
    related_action: str
    source_kind: str | None = None
    source_id: UUID | None = None
    is_auto: bool
    is_overdue: bool = False
    primary_action_label: str
    primary_action_href: str | None = None
    why_it_matters: str
    preparation: str
    created_at: datetime
    updated_at: datetime


class AgendaDaySummary(BaseModel):
    date: str  # YYYY-MM-DD in org timezone
    count: int
    has_overdue: bool = False


class AgendaBoardOut(BaseModel):
    timezone: str
    selected_date: str
    next_up: AgendaEventOut | None
    today: list[AgendaEventOut]
    selected_day: list[AgendaEventOut]
    overdue: list[AgendaEventOut]
    in_progress_assessments: list[dict]
    month_markers: list[AgendaDaySummary]
