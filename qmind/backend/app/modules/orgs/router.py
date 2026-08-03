from __future__ import annotations

from fastapi import APIRouter

from app.auth.deps import OrgContextDep, PrincipalDep
from app.modules.orgs import service
from app.modules.orgs.schemas import (
    MembershipOut,
    OrganizationCreate,
    OrganizationDetailOut,
    OrganizationOut,
)

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.post("", response_model=OrganizationDetailOut, status_code=201)
def create_organization(payload: OrganizationCreate, principal: PrincipalDep) -> OrganizationDetailOut:
    return service.create_organization(principal, payload)


@router.get("/me/memberships", response_model=list[MembershipOut])
def my_memberships(principal: PrincipalDep) -> list[MembershipOut]:
    return service.list_my_memberships(principal)


@router.get("/current", response_model=OrganizationOut)
def current_organization(ctx: OrgContextDep) -> OrganizationOut:
    return service.get_current_organization(ctx)
