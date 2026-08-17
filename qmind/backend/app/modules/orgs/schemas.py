from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.enums import MembershipStatus, OrganizationStatus

BusinessModel = Literal[
    "",
    "b2b",
    "b2c",
    "b2b2c",
    "services",
    "manufacturing",
    "mixed",
    "other",
]
EmployeeRange = Literal[
    "",
    "1-10",
    "11-50",
    "51-200",
    "201-500",
    "501-1000",
    "1000+",
]
CertificationStatus = Literal[
    "unknown",
    "none",
    "in_progress",
    "certified",
    "expired",
    "not_applicable",
]
QualityStructure = Literal[
    "unknown",
    "none",
    "informal",
    "formal_partial",
    "formal",
]


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200, examples=["Acme Diagnóstico Ltda"])
    timezone: str = Field(default="America/Sao_Paulo", max_length=64, examples=["America/Sao_Paulo"])


class OrganizationOut(BaseModel):
    id: UUID
    name: str
    status: OrganizationStatus
    timezone: str
    created_at: datetime


class MembershipOut(BaseModel):
    id: UUID
    organization_id: UUID
    organization_name: str
    roles: list[str]
    status: MembershipStatus


class OrgMemberOut(BaseModel):
    membership_id: UUID
    email: str
    display_name: str | None = None
    roles: list[str]
    status: MembershipStatus


class OrganizationDetailOut(BaseModel):
    organization: OrganizationOut
    membership: MembershipOut


class OrganizationProfileOut(BaseModel):
    organization_id: UUID
    trade_name: str
    legal_name: str
    summary: str
    industry: str
    business_model: BusinessModel
    employee_range: EmployeeRange
    unit_count: int | None = None
    certification_status: CertificationStatus
    quality_structure: QualityStructure
    created_at: datetime
    updated_at: datetime


class OrganizationProfilePatch(BaseModel):
    """Partial update — organization_id and timestamps are not accepted."""

    model_config = ConfigDict(extra="forbid")

    trade_name: str | None = Field(default=None, max_length=200)
    legal_name: str | None = Field(default=None, max_length=200)
    summary: str | None = Field(default=None, max_length=4000)
    industry: str | None = Field(default=None, max_length=200)
    business_model: BusinessModel | None = None
    employee_range: EmployeeRange | None = None
    unit_count: int | None = Field(default=None, ge=0)
    certification_status: CertificationStatus | None = None
    quality_structure: QualityStructure | None = None
