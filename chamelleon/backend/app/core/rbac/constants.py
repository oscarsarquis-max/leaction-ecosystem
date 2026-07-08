"""Constantes RBAC — papéis de sistema (sysadmin, led, consultor, executor)."""

from __future__ import annotations

ROLE_SYSADMIN = "sysadmin"
ROLE_LED = "led"
ROLE_CONSULTOR = "consultor"
ROLE_EXECUTOR = "executor"

SYSTEM_ROLES = frozenset({ROLE_SYSADMIN, ROLE_LED, ROLE_CONSULTOR, ROLE_EXECUTOR})

ROLE_LABELS = {
    ROLE_SYSADMIN: "Administrador",
    ROLE_LED: "Lead (Gestor)",
    ROLE_CONSULTOR: "Consultor",
    ROLE_EXECUTOR: "Executor",
}
