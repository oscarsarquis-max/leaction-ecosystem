"""Constantes RBAC — papéis de sistema (sysadmin, led, consultor, executor)."""

from __future__ import annotations

ROLE_SYSADMIN = "sysadmin"
ROLE_LED = "led"
ROLE_CONSULTOR = "consultor"
ROLE_EXECUTOR = "executor"
ROLE_SQUAD_MEMBER = "squad_member"

SYSTEM_ROLES = frozenset(
    {ROLE_SYSADMIN, ROLE_LED, ROLE_CONSULTOR, ROLE_EXECUTOR, ROLE_SQUAD_MEMBER}
)

ROLE_LABELS = {
    ROLE_SYSADMIN: "Administrador",
    ROLE_LED: "Lead (Gestor)",
    ROLE_CONSULTOR: "Consultor",
    ROLE_EXECUTOR: "Executor",
    ROLE_SQUAD_MEMBER: "Membro de Squad",
}
