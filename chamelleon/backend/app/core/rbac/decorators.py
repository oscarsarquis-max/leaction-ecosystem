"""Decorators RBAC — @require_auth e @require_role (sysadmin sempre passa)."""

from __future__ import annotations

from functools import wraps
from typing import Any, Callable

from flask import g, jsonify

from app.core.rbac.constants import ROLE_SYSADMIN
from app.core.rbac.context import resolve_rbac_context


def require_auth(f: Callable[..., Any]) -> Callable[..., Any]:
    """Exige utilizador autenticado via X-User-ID (+ membership no tenant quando aplicável)."""

    @wraps(f)
    def decorated(*args: Any, **kwargs: Any):
        if not getattr(g, "user_id", None) or not getattr(g, "system_role", None):
            ctx = resolve_rbac_context()
            if not ctx:
                return jsonify(
                    {
                        "error": "Autenticação necessária. Envie X-User-ID e membership válido.",
                        "code": "auth_required",
                    }
                ), 401
            from app.core.rbac.context import apply_rbac_to_g

            apply_rbac_to_g(ctx)

        return f(*args, **kwargs)

    return decorated


def require_role(*roles: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Exige um dos papéis listados (sysadmin sempre passa)."""

    def decorator(f: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(f)
        def wrapper(*args: Any, **kwargs: Any):
            if not getattr(g, "system_role", None):
                ctx = resolve_rbac_context()
                if not ctx:
                    return jsonify(
                        {
                            "error": "Autenticação necessária.",
                            "code": "auth_required",
                        }
                    ), 401
                from app.core.rbac.context import apply_rbac_to_g

                apply_rbac_to_g(ctx)

            rbac = getattr(g, "rbac", None)
            if g.system_role == ROLE_SYSADMIN:
                return f(*args, **kwargs)
            if rbac and rbac.has_role(*roles):
                return f(*args, **kwargs)
            if g.system_role in roles:
                return f(*args, **kwargs)

            return jsonify(
                {
                    "error": "Acesso negado para o seu perfil.",
                    "code": "forbidden",
                    "required_roles": list(roles),
                    "current_role": g.system_role,
                }
            ), 403

        return wrapper

    return decorator