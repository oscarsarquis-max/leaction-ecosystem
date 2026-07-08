"""Resolução do contexto RBAC a partir de headers (Node) ou sessão Flask."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from flask import request, session

from rbac.constants import ROLE_LED, ROLE_SYSADMIN, SYSTEM_ROLES


@dataclass(frozen=True)
class RbacContext:
    system_role: str
    id_usuario: int | None = None
    id_member: int | None = None
    id_clie: int | None = None
    id_proj: int | None = None
    id_squad: int | None = None
    email: str | None = None
    position: str | None = None
    auth_type: str = "anonymous"

    def has_role(self, *roles: str) -> bool:
        if self.system_role == ROLE_SYSADMIN:
            return True
        return self.system_role in roles

    def to_dict(self) -> dict[str, Any]:
        return {
            "system_role": self.system_role,
            "id_usuario": self.id_usuario,
            "id_member": self.id_member,
            "id_clie": self.id_clie,
            "id_proj": self.id_proj,
            "id_squad": self.id_squad,
            "email": self.email,
            "position": self.position,
            "auth_type": self.auth_type,
        }


def _int_header(name: str) -> int | None:
    raw = (request.headers.get(name) or "").strip()
    if not raw:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def resolve_rbac_context() -> RbacContext:
    """Prioridade: headers do proxy Node → sessão Flask."""
    hdr_role = (request.headers.get("X-PanelDX-System-Role") or "").strip().lower()
    if hdr_role == "admin":
        hdr_role = ROLE_SYSADMIN
    if hdr_role in SYSTEM_ROLES:
        return RbacContext(
            system_role=hdr_role,
            id_usuario=_int_header("X-PanelDX-Id-Usuario"),
            id_member=_int_header("X-PanelDX-Id-Member"),
            id_clie=_int_header("X-PanelDX-Id-Clie"),
            id_proj=_int_header("X-PanelDX-Id-Proj"),
            id_squad=_int_header("X-PanelDX-Id-Squad"),
            email=(request.headers.get("X-PanelDX-Email") or "").strip() or None,
            position=(request.headers.get("X-PanelDX-Position") or "").strip() or None,
            auth_type=(request.headers.get("X-PanelDX-Auth-Type") or "team").strip(),
        )

    stored = session.get("rbac") or {}
    role = (stored.get("system_role") or "").strip().lower()
    if role in SYSTEM_ROLES:
        return RbacContext(
            system_role=role,
            id_usuario=stored.get("id_usuario"),
            id_member=stored.get("id_member"),
            id_clie=stored.get("id_clie"),
            id_proj=stored.get("id_proj"),
            id_squad=stored.get("id_squad"),
            email=stored.get("email"),
            position=stored.get("position"),
            auth_type=stored.get("auth_type", "session"),
        )

    return RbacContext(system_role=ROLE_LED)


def store_rbac_session(ctx: RbacContext) -> None:
    session["rbac"] = ctx.to_dict()


def redirect_for_role(system_role: str) -> str:
    routes = {
        ROLE_SYSADMIN: "/admin",
        ROLE_LED: "/projeto",
        "consultor": "/portal-consultor",
        "executor": "/execucao",
    }
    return routes.get(system_role, "/projeto")
