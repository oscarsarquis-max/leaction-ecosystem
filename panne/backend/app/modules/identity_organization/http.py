"""Contrato HTTP mínimo autenticado. Sem CRUD de negócio."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_runtime_session
from app.modules.identity_organization.access_tokens import (
    AccessTokenVerifier,
    TokenVerificationError,
)
from app.modules.identity_organization.authorization import (
    PERMISSION_IDENTITY_READ_ME,
    AuthorizationError,
    Principal,
    require_permission,
)
from app.modules.identity_organization.services import (
    IdentityResolutionError,
    load_principal,
    lookup_identity,
    new_correlation_id,
    parse_organization_header,
    record_audit,
)
from app.modules.identity_organization.tenant_context import apply_tenant_context

router = APIRouter()


class AssociationResponse(BaseModel):
    organization_id: UUID
    display_name: str = ""
    slug: str = ""
    roles: list[str] = Field(default_factory=list)
    status: str
    permissions: list[str]


class MeResponse(BaseModel):
    user_id: UUID
    display_name: str
    status: str
    selected_organization_id: UUID | None = None
    associations: list[AssociationResponse]
    roles: list[str]
    permissions: list[str] = Field(default_factory=list)


def get_access_token_verifier() -> AccessTokenVerifier:
    from app.modules.identity_organization.access_tokens import (
        CognitoAccessTokenVerifier,
        FakeAccessTokenVerifier,
    )

    settings = get_settings()
    if settings.auth_verifier == "cognito":
        scopes = frozenset(part for part in settings.oidc_required_scope.split() if part)
        return CognitoAccessTokenVerifier(
            settings.oidc_issuer,
            settings.oidc_client_id,
            audience=settings.oidc_audience or None,
            required_scopes=scopes,
            jwks_timeout=settings.jwks_timeout_seconds,
        )
    return FakeAccessTokenVerifier()


def _bearer(authorization: str | None, max_bytes: int) -> str:
    if authorization is None or not authorization.strip():
        raise HTTPException(status_code=401, detail="nao_autenticado")
    if len(authorization.encode("utf-8")) > max_bytes:
        raise HTTPException(status_code=401, detail="nao_autenticado")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(status_code=401, detail="nao_autenticado")
    return token.strip()


def _to_response(principal: Principal) -> MeResponse:
    associations = [
        AssociationResponse(
            organization_id=item.organization_id,
            display_name=item.organization_display_name,
            slug=item.organization_slug,
            roles=list(item.roles),
            status=item.status,
            permissions=sorted(item.permissions),
        )
        for item in principal.associations
    ]
    roles = [role for item in principal.associations for role in item.roles]
    if principal.selected is not None:
        roles = list(principal.selected.roles)
    return MeResponse(
        user_id=principal.user_id,
        display_name=principal.display_name,
        status=principal.status,
        selected_organization_id=(
            principal.selected.organization_id if principal.selected else None
        ),
        associations=associations,
        roles=roles,
        permissions=sorted(principal.permissions),
    )


@router.get("/api/v1/me", response_model=MeResponse)
def read_me(
    verifier: Annotated[AccessTokenVerifier, Depends(get_access_token_verifier)],
    session: Annotated[Session, Depends(get_runtime_session)],
    authorization: Annotated[str | None, Header()] = None,
    x_panne_organization_id: Annotated[str | None, Header()] = None,
    x_request_id: Annotated[str | None, Header()] = None,
) -> MeResponse:
    settings = get_settings()
    correlation_id = new_correlation_id(x_request_id)
    try:
        token = verifier.verify(_bearer(authorization, settings.max_authorization_header_bytes))
        requested = parse_organization_header(x_panne_organization_id)
    except TokenVerificationError as exc:
        if exc.unavailable:
            raise HTTPException(status_code=503, detail="indisponivel") from None
        raise HTTPException(status_code=401, detail="nao_autenticado") from None
    except AuthorizationError:
        raise HTTPException(status_code=403, detail="nao_autorizado") from None

    apply_tenant_context(
        session,
        organization_id=None,
        user_id=None,
        issuer=token.issuer,
        subject=token.subject,
    )
    try:
        identity = lookup_identity(session, token)
        apply_tenant_context(
            session,
            organization_id=None,
            user_id=identity.user_id,
            issuer=token.issuer,
            subject=token.subject,
        )
        principal = load_principal(session, identity, token, requested)
        apply_tenant_context(
            session,
            organization_id=(principal.selected.organization_id if principal.selected else None),
            user_id=principal.user_id,
            issuer=token.issuer,
            subject=token.subject,
        )
        require_permission(principal, PERMISSION_IDENTITY_READ_ME)
        record_audit(
            session,
            event_type="identity.authenticated",
            aggregate_type="app_user",
            aggregate_id=principal.user_id,
            organization_id=(principal.selected.organization_id if principal.selected else None),
            actor_user_id=principal.user_id,
            correlation_id=correlation_id,
            payload={"associations": len(principal.associations)},
        )
        return _to_response(principal)
    except (IdentityResolutionError, AuthorizationError):
        raise HTTPException(status_code=403, detail="nao_autorizado") from None
