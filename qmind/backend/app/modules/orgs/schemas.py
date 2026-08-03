from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.enums import MembershipStatus, OrganizationStatus


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


class OrganizationDetailOut(BaseModel):
    organization: OrganizationOut
    membership: MembershipOut
