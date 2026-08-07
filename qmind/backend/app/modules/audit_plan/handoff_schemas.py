from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.assessments.schemas import AssessmentTransitionResult
from app.modules.audit_plan.schemas import AuditPlanOut


class ConcludePlanningIn(BaseModel):
    expected_updated_at: datetime | None = None
    """If plan is still draft but checklist is complete, mark ready then transition."""
    mark_ready_if_needed: bool = True


class ConcludePlanningOut(BaseModel):
    plan: AuditPlanOut
    transition: AssessmentTransitionResult
    message: str = (
        "Planejamento concluído. A avaliação está planejada; "
        "o próximo passo é a reunião de abertura e o início da execução em campo."
    )


class StartFieldIn(BaseModel):
    expected_plan_updated_at: datetime | None = None


class StartFieldOut(BaseModel):
    transition: AssessmentTransitionResult
    redirect_href: str
    message: str = (
        "Execução em campo iniciada. Continue no painel de trabalho da avaliação."
    )


class OpeningMeetingPerformIn(BaseModel):
    actual_starts_at: datetime | None = None
    participant_membership_ids: list[UUID] | None = None
    observations: str = Field(default="", max_length=4000)
    adjustments: str = Field(default="", max_length=4000)
    pendings: str = Field(default="", max_length=4000)


class OpeningMeetingWaiveIn(BaseModel):
    waiver_reason: str = Field(min_length=8, max_length=2000)


class OpeningMeetingOut(BaseModel):
    event_id: UUID
    status: Literal["completed", "waived"]
    message: str
