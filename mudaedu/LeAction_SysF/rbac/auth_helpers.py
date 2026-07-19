"""Helpers de autenticação RBAC."""

from __future__ import annotations

from rbac.constants import (
    ROLE_CONSULTOR,
    ROLE_EXECUTOR,
    ROLE_LED,
    ROLE_SYSADMIN,
    SYSTEM_ROLES,
)


def rbac_infer_system_role_from_team(
    *,
    role: str | None,
    position: str | None,
    email: str | None = None,
    admin_email: str | None = None,
) -> str:
    """Infere system_role inicial ao criar usuário a partir de ctdi_team (somente no cadastro)."""
    if admin_email and email and email.lower().strip() == admin_email.lower().strip():
        return ROLE_SYSADMIN

    role_up = (role or "").strip().upper()
    pos = (position or "").strip()

    if role_up in ("ADMIN", "SYSADMIN"):
        return ROLE_SYSADMIN
    if role_up == "CONSULTOR" or "consultor estratégico" in pos.lower():
        return ROLE_CONSULTOR
    if role_up == "LEAD":
        return ROLE_LED
    if "analista" in pos.lower():
        return ROLE_EXECUTOR
    return ROLE_EXECUTOR


# Alias legado
rbac_resolve_team_system_role = rbac_infer_system_role_from_team


def rbac_map_system_role_to_team_role(system_role: str | None) -> str:
    """Mapeia papel global para coluna role legada em ctdi_team."""
    mapping = {
        "sysadmin": "ADMIN",
        "consultor": "CONSULTOR",
        "led": "LEAD",
        "executor": "CLIENTE",
    }
    return mapping.get((system_role or "").strip().lower(), "CLIENTE")
