from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.db import get_runtime_session
from app.modules.identity_organization.authorization import Principal
from app.modules.identity_organization.roles import grant_role, revoke_role
from app.modules.identity_organization.services import new_correlation_id
from app.modules.production_http.deps import (
    get_runtime_principal,
    require_correlation_id,
    require_idempotency_key,
)
from app.modules.production_http.errors import raise_domain
from app.modules.production_http.schemas import RoleGrantBody, RoleRevokeBody, envelope

router = APIRouter()


@router.post("/{membership_id}/roles")
def post_grant_role(
    organization_id: UUID,
    membership_id: UUID,
    body: RoleGrantBody,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_correlation_id: Annotated[str | None, Header()] = None,
):
    require_idempotency_key(idempotency_key)
    correlation = require_correlation_id(x_correlation_id)
    try:
        row = grant_role(
            session,
            principal,
            membership_id=membership_id,
            role=body.role,
            reason=body.reason,
            correlation_id=correlation,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise_domain(exc)
    return envelope({"id": str(row.id), "role": row.role, "revoked_at": None})


@router.post("/{membership_id}/roles/{role}/revoke")
def post_revoke_role(
    organization_id: UUID,
    membership_id: UUID,
    role: str,
    body: RoleRevokeBody,
    principal: Annotated[Principal, Depends(get_runtime_principal)],
    session: Annotated[Session, Depends(get_runtime_session)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_correlation_id: Annotated[str | None, Header()] = None,
):
    require_idempotency_key(idempotency_key)
    correlation = new_correlation_id(x_correlation_id)
    require_correlation_id(x_correlation_id)
    try:
        row = revoke_role(
            session,
            principal,
            membership_id=membership_id,
            role=role,
            reason=body.reason,
            correlation_id=correlation,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise_domain(exc)
    return envelope({"id": str(row.id), "role": row.role, "revoked": True})
