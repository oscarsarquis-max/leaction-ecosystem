"""Decorator @require_role para rotas Flask."""

from __future__ import annotations

from functools import wraps
from typing import Callable

from flask import jsonify

from rbac.context import resolve_rbac_context


def require_role(*roles: str) -> Callable:
    """Exige um dos papéis listados (sysadmin sempre passa)."""

    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args, **kwargs):
            ctx = resolve_rbac_context()
            if not ctx.has_role(*roles):
                return jsonify({
                    "success": False,
                    "status": "error",
                    "error": "Acesso negado para o seu perfil.",
                    "required_roles": list(roles),
                    "current_role": ctx.system_role,
                }), 403
            return fn(*args, **kwargs)

        return wrapper

    return decorator
