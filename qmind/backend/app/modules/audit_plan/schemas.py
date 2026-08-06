from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


PlanStatus = Literal["draft", "ready", "amended"]
Modality = Literal[
    "diagnosis",
    "internal_audit",
    "external_audit",
    "certification_prep",
    "other",
]
FieldSource = Literal["preparation", "manual", "assessment"]


class AuditPlanCriteria(BaseModel):
    iso9001_2015: bool = True
    internal_processes: bool = True
    legal_contractual: bool = False
    legal_contractual_text: str = ""
    additional_text: str = ""


class AuditPlanSite(BaseModel):
    name: str = ""
    location: str = ""
    notes: str = ""
    from_preparation: bool = False


class AuditPlanProcess(BaseModel):
    name: str = ""
    owner: str = ""
    notes: str = ""
    from_preparation: bool = False
    """If set, process needs no interview (justified coverage)."""
    interview_justification: str = ""


class OrgRepresentative(BaseModel):
    name: str = ""
    role: str = ""
    notes: str = ""


class ReadinessItem(BaseModel):
    key: str
    label: str
    done: bool
    blocking: bool = True


class AuditPlanReadiness(BaseModel):
    ready: bool
    completed_count: int
    pending_count: int
    percent: int
    items: list[ReadinessItem] = Field(default_factory=list)
    next_action: str = ""
    blockers: list[str] = Field(default_factory=list)


class AuditPlanOut(BaseModel):
    id: UUID
    organization_id: UUID
    assessment_id: UUID
    objective: str = ""
    modality: Modality = "diagnosis"
    modality_label: str = ""
    scope_text: str = ""
    criteria: AuditPlanCriteria = Field(default_factory=AuditPlanCriteria)
    sites: list[AuditPlanSite] = Field(default_factory=list)
    processes: list[AuditPlanProcess] = Field(default_factory=list)
    lead_membership_id: UUID | None = None
    team_membership_ids: list[UUID] = Field(default_factory=list)
    org_representatives: list[OrgRepresentative] = Field(default_factory=list)
    planned_start: date | None = None
    planned_end: date | None = None
    preparation_notes: str = ""
    risks_notes: str = ""
    plan_status: PlanStatus = "draft"
    field_sources: dict[str, str] = Field(default_factory=dict)
    last_amendment_reason: str = ""
    readiness: AuditPlanReadiness
    editable: bool = False
    requires_amendment_reason: bool = False
    updated_by_user_id: UUID | None = None
    created_at: datetime
    updated_at: datetime


class AuditPlanPatch(BaseModel):
    objective: str | None = None
    modality: Modality | None = None
    scope_text: str | None = None
    criteria: AuditPlanCriteria | None = None
    sites: list[AuditPlanSite] | None = None
    processes: list[AuditPlanProcess] | None = None
    lead_membership_id: UUID | None = None
    team_membership_ids: list[UUID] | None = None
    org_representatives: list[OrgRepresentative] | None = None
    planned_start: date | None = None
    planned_end: date | None = None
    preparation_notes: str | None = None
    risks_notes: str | None = None
    # Optimistic concurrency — reject if stale.
    expected_updated_at: datetime | None = None
    # Required when assessment is planned (after ready) or when amending in field.
    amendment_reason: str | None = None


class AuditPlanReadyIn(BaseModel):
    expected_updated_at: datetime | None = None


class AuditPlanRefreshIn(BaseModel):
    """Fill empty fields from Wizard/preparation. Never overwrites manual fields."""

    confirm_overwrite_preparation: bool = False
