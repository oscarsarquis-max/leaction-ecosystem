"""Contexto HTTP autenticado. Sem conexão administrativa."""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_runtime_session
from app.modules.identity_organization.access_tokens import (
    AccessTokenVerifier,
    TokenVerificationError,
)
from app.modules.identity_organization.authorization import AuthorizationError, Principal
from app.modules.identity_organization.http import get_access_token_verifier
from app.modules.identity_organization.services import (
    IdentityResolutionError,
    load_principal,
    lookup_identity,
    new_correlation_id,
)
from app.modules.identity_organization.tenant_context import apply_tenant_context
from app.modules.production_http.errors import public_error

bearer_scheme = HTTPBearer(auto_error=False)
MAX_TEXT = 200
MAX_NOTES = 2000
MAX_PAGE = 50
DEFAULT_PAGE = 20


def _bearer_token(
    authorization: str | None,
    credentials: HTTPAuthorizationCredentials | None,
) -> str:
    settings = get_settings()
    raw = authorization
    if credentials is not None:
        raw = f"Bearer {credentials.credentials}"
    if raw is None or not raw.strip():
        raise HTTPException(status_code=401, detail=public_error("nao_autenticado"))
    if len(raw.encode("utf-8")) > settings.max_authorization_header_bytes:
        raise HTTPException(status_code=401, detail=public_error("nao_autenticado"))
    scheme, _, token = raw.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(status_code=401, detail=public_error("nao_autenticado"))
    return token.strip()


def parse_if_match(value: str | None, *, required: bool) -> int | None:
    if value is None or not value.strip():
        if required:
            raise HTTPException(status_code=400, detail=public_error("etag_obrigatorio"))
        return None
    raw = value.strip()
    if raw.startswith("W/"):
        raw = raw[2:].strip()
    raw = raw.strip('"')
    try:
        return int(raw)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=public_error("contrato_invalido")) from exc


def require_idempotency_key(value: str | None) -> UUID:
    if value is None or not value.strip():
        raise HTTPException(status_code=400, detail=public_error("idempotencia_obrigatoria"))
    try:
        return UUID(value.strip())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=public_error("contrato_invalido")) from exc


def require_correlation_id(value: str | None) -> UUID:
    if value is None or not value.strip():
        raise HTTPException(status_code=400, detail=public_error("correlacao_obrigatoria"))
    try:
        return UUID(value.strip())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=public_error("contrato_invalido")) from exc


def get_runtime_principal(
    organization_id: UUID,
    session: Annotated[Session, Depends(get_runtime_session)],
    verifier: Annotated[AccessTokenVerifier, Depends(get_access_token_verifier)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)] = None,
    authorization: Annotated[str | None, Header()] = None,
    x_correlation_id: Annotated[str | None, Header()] = None,
) -> Principal:
    try:
        token = verifier.verify(_bearer_token(authorization, credentials))
    except TokenVerificationError as exc:
        if exc.unavailable:
            raise HTTPException(status_code=503, detail=public_error("indisponivel")) from None
        raise HTTPException(status_code=401, detail=public_error("nao_autenticado")) from None
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
        principal = load_principal(session, identity, token, organization_id)
    except (IdentityResolutionError, AuthorizationError):
        raise HTTPException(status_code=403, detail=public_error("nao_autorizado")) from None
    if principal.selected is None or principal.selected.organization_id != organization_id:
        raise HTTPException(status_code=403, detail=public_error("organizacao_divergente"))
    apply_tenant_context(
        session,
        organization_id=organization_id,
        user_id=principal.user_id,
        issuer=token.issuer,
        subject=token.subject,
    )
    if x_correlation_id:
        new_correlation_id(x_correlation_id)
    return principal
