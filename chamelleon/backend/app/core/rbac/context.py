"""Resolução do contexto RBAC a partir de headers (MVP) ou sessão futura."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from flask import g, request

from app.core.rbac.constants import ROLE_SYSADMIN, SYSTEM_ROLES
from app.database.models import TenantUser, User, db


@dataclass(frozen=True)
class RbacContext:
    user_id: uuid.UUID
    system_role: str
    user_name: str | None = None
    user_email: str | None = None
    tenant_id: uuid.UUID | None = None

    def has_role(self, *roles: str) -> bool:
        if self.system_role == ROLE_SYSADMIN:
            return True
        return self.system_role in roles

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": str(self.user_id),
            "system_role": self.system_role,
            "user_name": self.user_name,
            "user_email": self.user_email,
            "tenant_id": str(self.tenant_id) if self.tenant_id else None,
        }


def _parse_uuid_header(name: str) -> uuid.UUID | None:
    raw = (request.headers.get(name) or "").strip()
    if not raw:
        return None
    try:
        return uuid.UUID(raw)
    except (ValueError, TypeError):
        return None


def _resolve_role_header() -> str | None:
    for header in ("X-Chamelleon-System-Role",):
        role = (request.headers.get(header) or "").strip().lower()
        if role in SYSTEM_ROLES:
            return role
    return None


def resolve_rbac_context() -> RbacContext | None:
    """Carrega utilizador e papel a partir de X-User-ID + membership no tenant."""
    user_id = _parse_uuid_header("X-User-ID")
    if not user_id:
        return None

    user = db.session.get(User, user_id)
    if not user:
        return None

    tenant_id = getattr(g, "tenant_id", None) or _parse_uuid_header("X-Tenant-ID")
    system_role = _resolve_role_header()

    membership = None
    if tenant_id:
        membership = TenantUser.query.filter_by(tenant_id=tenant_id, user_id=user_id).first()
        if membership:
            system_role = membership.role
        elif system_role not in SYSTEM_ROLES:
            membership = (
                TenantUser.query.filter_by(user_id=user_id)
                .filter(TenantUser.role.in_(tuple(SYSTEM_ROLES)))
                .first()
            )
            if membership:
                system_role = membership.role
                tenant_id = membership.tenant_id
            else:
                return None
    else:
        membership = (
            TenantUser.query.filter_by(user_id=user_id)
            .filter(TenantUser.role.in_(tuple(SYSTEM_ROLES)))
            .first()
        )
        if membership:
            system_role = membership.role
            tenant_id = membership.tenant_id

    if system_role not in SYSTEM_ROLES:
        return None

    return RbacContext(
        user_id=user_id,
        system_role=system_role,
        user_name=user.name,
        user_email=user.email,
        tenant_id=tenant_id,
    )


def apply_rbac_to_g(ctx: RbacContext) -> None:
    g.user_id = ctx.user_id
    g.system_role = ctx.system_role
    g.user_name = ctx.user_name
    g.user_email = ctx.user_email
    g.rbac = ctx
