from __future__ import annotations

from fastapi import APIRouter

from app.auth.deps import OrgContextDep, PrincipalDep
from app.modules.orgs import service
from app.modules.orgs.schemas import (
    MembershipOut,
    OrgMemberOut,
    OrganizationCreate,
    OrganizationDetailOut,
    OrganizationOut,
)
from app.schemas.common import ERROR_RESPONSES, IdempotencyKeyHeader

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.post(
    "",
    response_model=OrganizationDetailOut,
    status_code=201,
    operation_id="createOrganization",
    responses={400: ERROR_RESPONSES[400], 401: ERROR_RESPONSES[401], 422: ERROR_RESPONSES[422]},
    summary="Create organization",
)
def create_organization(
    payload: OrganizationCreate,
    principal: PrincipalDep,
    _idempotency_key: IdempotencyKeyHeader = None,
) -> OrganizationDetailOut:
    return service.create_organization(principal, payload)


@router.get(
    "/me/memberships",
    response_model=list[MembershipOut],
    operation_id="listMyMemberships",
    responses={401: ERROR_RESPONSES[401]},
    summary="List memberships for current user",
)
def my_memberships(principal: PrincipalDep) -> list[MembershipOut]:
    return service.list_my_memberships(principal)


@router.get(
    "/current",
    response_model=OrganizationOut,
    operation_id="getCurrentOrganization",
    responses={401: ERROR_RESPONSES[401], 403: ERROR_RESPONSES[403], 404: ERROR_RESPONSES[404]},
    summary="Get organization from X-Organization-Id",
)
def current_organization(ctx: OrgContextDep) -> OrganizationOut:
    return service.get_current_organization(ctx)


@router.get(
    "/current/members",
    response_model=list[OrgMemberOut],
    operation_id="listCurrentOrganizationMembers",
    responses={401: ERROR_RESPONSES[401], 403: ERROR_RESPONSES[403]},
    summary="List active members of current organization (human labels)",
)
def current_organization_members(ctx: OrgContextDep) -> list[OrgMemberOut]:
    return service.list_current_org_members(ctx)
