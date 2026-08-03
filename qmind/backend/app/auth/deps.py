"""FastAPI dependencies: principal + organization context."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header
from sqlalchemy import text

from app.auth.cognito import decode_cognito_access_token
from app.auth.context import OrgContext, Principal
from app.config import Settings, get_settings
from app.db import admin_connection
from app.errors import AppError


def _upsert_user(idp_sub: str, email: str, display_name: str | None) -> UUID:
    with admin_connection() as conn:
        row = conn.execute(
            text(
                """
                INSERT INTO users (idp_sub, email, display_name, status)
                VALUES (:sub, :email, :name, 'active')
                ON CONFLICT (idp_sub) DO UPDATE
                  SET email = EXCLUDED.email,
                      display_name = COALESCE(EXCLUDED.display_name, users.display_name),
                      updated_at = now()
                RETURNING id
                """
            ),
            {"sub": idp_sub, "email": email, "name": display_name},
        ).one()
        conn.commit()
        return row.id


def get_principal(
    authorization: Annotated[str | None, Header()] = None,
    x_dev_user_sub: Annotated[str | None, Header()] = None,
    x_dev_user_email: Annotated[str | None, Header()] = None,
    settings: Settings = Depends(get_settings),
) -> Principal:
    if settings.auth_mode == "dev":
        # Belt-and-suspenders: Settings also rejects ENVIRONMENT=prod + AUTH_MODE=dev at boot.
        if settings.environment == "prod":
            raise AppError("auth_forbidden", "Dev auth is forbidden in production", status_code=500)
        if not x_dev_user_sub or not x_dev_user_email:
            raise AppError(
                "unauthorized",
                "Dev auth requires X-Dev-User-Sub and X-Dev-User-Email",
                status_code=401,
            )
        user_id = _upsert_user(x_dev_user_sub, x_dev_user_email, None)
        return Principal(user_id=user_id, idp_sub=x_dev_user_sub, email=x_dev_user_email)

    if not authorization or not authorization.lower().startswith("bearer "):
        raise AppError("unauthorized", "Bearer token required", status_code=401)
    token = authorization.split(" ", 1)[1].strip()
    claims = decode_cognito_access_token(token, settings)
    sub = claims["sub"]
    email = claims.get("email") or claims.get("username") or f"{sub}@cognito.local"
    user_id = _upsert_user(sub, str(email), claims.get("name"))
    return Principal(user_id=user_id, idp_sub=sub, email=str(email))


def get_org_context(
    principal: Annotated[Principal, Depends(get_principal)],
    x_organization_id: Annotated[UUID | None, Header(alias="X-Organization-Id")] = None,
) -> OrgContext:
    """Active org comes from membership lookup — never trust body alone (ADR-002/006)."""
    if x_organization_id is None:
        raise AppError(
            "organization_required",
            "X-Organization-Id header required for this operation",
            status_code=400,
        )
    with admin_connection() as conn:
        row = conn.execute(
            text(
                """
                SELECT id, roles
                FROM memberships
                WHERE organization_id = :org
                  AND user_id = :user
                  AND status = 'active'
                  AND (valid_to IS NULL OR valid_to > now())
                """
            ),
            {"org": x_organization_id, "user": principal.user_id},
        ).first()
    if row is None:
        raise AppError(
            "forbidden_organization",
            "No active membership for the requested organization",
            status_code=403,
        )
    roles = tuple(row.roles or ())
    return OrgContext(
        principal=principal,
        organization_id=x_organization_id,
        membership_id=row.id,
        roles=roles,
    )


PrincipalDep = Annotated[Principal, Depends(get_principal)]
OrgContextDep = Annotated[OrgContext, Depends(get_org_context)]
