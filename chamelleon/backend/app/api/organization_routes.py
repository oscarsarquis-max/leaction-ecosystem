"""Rotas de unidades organizacionais (filiais/escritórios/depósitos)."""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from app.core.middlewares import require_tenant_context
from app.core.rbac import ROLE_LED, ROLE_SYSADMIN, require_auth, require_role
from app.services.organizational_units_service import OrganizationalUnitsService

organization_bp = Blueprint("organization", __name__)


@organization_bp.get("/units")
@require_tenant_context
@require_auth
@require_role(ROLE_SYSADMIN, ROLE_LED)
def list_units():
    try:
        units = OrganizationalUnitsService().list_units()
        return jsonify({"status": "ok", "units": units, "total": len(units)}), 200
    except Exception:
        return jsonify({"error": "Erro ao listar unidades organizacionais."}), 500


@organization_bp.post("/units")
@require_tenant_context
@require_auth
@require_role(ROLE_SYSADMIN, ROLE_LED)
def create_unit():
    payload = request.get_json(silent=True) or {}
    try:
        unit = OrganizationalUnitsService().create_unit(payload)
        return jsonify({"status": "ok", "unit": unit}), 201
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        return jsonify({"error": "Erro ao criar unidade organizacional."}), 500


@organization_bp.put("/units/<unit_id>")
@require_tenant_context
@require_auth
@require_role(ROLE_SYSADMIN, ROLE_LED)
def update_unit(unit_id: str):
    payload = request.get_json(silent=True) or {}
    try:
        unit = OrganizationalUnitsService().update_unit(unit_id, payload)
        return jsonify({"status": "ok", "unit": unit}), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        return jsonify({"error": "Erro ao atualizar unidade organizacional."}), 500


@organization_bp.delete("/units/<unit_id>")
@require_tenant_context
@require_auth
@require_role(ROLE_SYSADMIN, ROLE_LED)
def deactivate_unit(unit_id: str):
    try:
        OrganizationalUnitsService().deactivate_unit(unit_id)
        return jsonify({"status": "ok"}), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404
    except Exception:
        return jsonify({"error": "Erro ao desativar unidade organizacional."}), 500
