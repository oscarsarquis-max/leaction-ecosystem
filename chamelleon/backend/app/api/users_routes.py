"""Alias REST de utilizadores no escopo do tenant — POST /api/users com site_id."""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from app.core.middlewares import require_tenant_context
from app.core.rbac import ROLE_LED, ROLE_SYSADMIN, require_auth, require_role
from app.services.operational_users_service import OperationalUsersService

users_bp = Blueprint("users_api", __name__)


@users_bp.get("/users")
@require_tenant_context
@require_auth
@require_role(ROLE_SYSADMIN, ROLE_LED)
def list_users():
    try:
        users = OperationalUsersService().list_users()
        return jsonify({"status": "ok", "users": users, "total": len(users)}), 200
    except Exception:
        return jsonify({"error": "Erro ao listar utilizadores."}), 500


@users_bp.post("/users")
@require_tenant_context
@require_auth
@require_role(ROLE_SYSADMIN, ROLE_LED)
def create_user():
    """Cria utilizador no tenant; aceita ``site_id`` / ``operational_site_id`` opcional."""
    payload = request.get_json(silent=True) or {}
    if "site_id" in payload and "operational_site_id" not in payload:
        payload = {**payload, "operational_site_id": payload.get("site_id")}
    try:
        result = OperationalUsersService().create_user(payload)
        return jsonify({"status": "ok", **result}), 201
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        return jsonify({"error": "Erro ao criar utilizador."}), 500
