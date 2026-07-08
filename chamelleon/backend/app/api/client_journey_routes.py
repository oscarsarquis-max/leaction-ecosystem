"""Rotas da jornada do cliente — contexto, contrato, estado (PanelDX)."""

from flask import Blueprint, g, jsonify, request

from app.core.middlewares import require_tenant_membership
from app.core.rbac.constants import ROLE_LED, ROLE_SYSADMIN
from app.core.rbac.decorators import require_auth, require_role
from app.services.client_journey_service import (
    activate_project,
    get_journey_for_tenant,
    save_client_context,
)

client_journey_bp = Blueprint("client_journey", __name__)


@client_journey_bp.get("/journey")
@require_tenant_membership
@require_auth
def get_journey():
    try:
        payload = get_journey_for_tenant(g.tenant_id)
        return jsonify({"status": "ok", "journey": payload}), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404


@client_journey_bp.put("/context")
@require_tenant_membership
@require_auth
@require_role(ROLE_LED, ROLE_SYSADMIN)
def update_context():
    payload = request.get_json(silent=True) or {}
    try:
        journey = save_client_context(g.tenant_id, payload)
        return jsonify({"status": "ok", "journey": journey}), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@client_journey_bp.post("/activate-project")
@require_tenant_membership
@require_auth
@require_role(ROLE_LED, ROLE_SYSADMIN)
def post_activate_project():
    """Ativa o projeto (contratação) — equivalente ActionHub / hasActiveProject."""
    try:
        journey = activate_project(g.tenant_id)
        return jsonify({"status": "ok", "journey": journey}), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
