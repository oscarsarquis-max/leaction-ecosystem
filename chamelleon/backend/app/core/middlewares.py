"""Middlewares de contexto — Tenant, Framework e RBAC."""

from __future__ import annotations

import uuid
from functools import wraps
from typing import Any, Callable

from flask import g, jsonify, request

from app.core.rbac.context import apply_rbac_to_g, resolve_rbac_context
from app.core.tenant_framework_resolver import resolve_framework_for_tenant
from app.database.models import db


def load_tenant_context() -> None:
    """Carrega tenant e framework ativo no contexto global da requisição (`g`)."""
    tenant_header = request.headers.get("X-Tenant-ID")
    if not tenant_header:
        return

    try:
        tenant_uuid = uuid.UUID(str(tenant_header).strip())
    except (ValueError, TypeError):
        return

    g.tenant_id = tenant_uuid

    framework = resolve_framework_for_tenant(tenant_uuid)
    if framework:
        g.framework_id = framework.id
        g.framework_metadata = framework.rules_metadata

    ctx = resolve_rbac_context()
    if ctx:
        apply_rbac_to_g(ctx)


def require_tenant_membership(f: Callable[..., Any]) -> Callable[..., Any]:
    """Exige tenant autenticado — não exige framework ativo (ex.: /auth/me após remoção de catálogo)."""

    @wraps(f)
    def decorated(*args: Any, **kwargs: Any):
        if not getattr(g, "tenant_id", None):
            return jsonify({"error": "Contexto de tenant ausente."}), 403
        return f(*args, **kwargs)

    return decorated


def require_tenant_context(f: Callable[..., Any]) -> Callable[..., Any]:
    """Exige `g.tenant_id` e `g.framework_id` — uso em rotas protegidas."""

    @wraps(f)
    def decorated(*args: Any, **kwargs: Any):
        if not getattr(g, "tenant_id", None) or not getattr(g, "framework_id", None):
            return jsonify(
                {
                    "error": (
                        "Nenhum framework ativo vinculado ao seu tenant. "
                        "O administrador precisa publicar o framework do setor no Builder."
                    ),
                    "code": "framework_unavailable",
                }
            ), 403
        return f(*args, **kwargs)

    return decorated
