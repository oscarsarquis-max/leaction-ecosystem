"""Rotas administrativas — gestão global de utilizadores (sysadmin)."""

from flask import Blueprint, jsonify, request

from app.core.rbac import ROLE_SYSADMIN, require_auth, require_role
from app.services.admin_users_service import AdminUsersService

admin_users_bp = Blueprint("admin_users", __name__)


@admin_users_bp.get("/users")
@require_auth
@require_role(ROLE_SYSADMIN)
def list_users():
    try:
        service = AdminUsersService()
        users = service.list_users(
            search=request.args.get("q") or request.args.get("busca"),
            system_role=(request.args.get("system_role") or request.args.get("role") or "").strip().lower()
            or None,
            tenant_id=request.args.get("tenant_id"),
            include_inactive=request.args.get("incluir_inativos", "1") == "1",
        )
        return jsonify({"status": "ok", "users": users, "total": len(users)}), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        return jsonify({"error": "Erro ao listar utilizadores."}), 500


@admin_users_bp.get("/users/tenant-options")
@require_auth
@require_role(ROLE_SYSADMIN)
def tenant_options():
    try:
        service = AdminUsersService()
        tenants = service.list_tenant_options()
        return jsonify({"status": "ok", "tenants": tenants}), 200
    except Exception:
        return jsonify({"error": "Erro ao listar empresas."}), 500


@admin_users_bp.get("/users/<user_id>/access")
@require_auth
@require_role(ROLE_SYSADMIN)
def user_access(user_id: str):
    try:
        service = AdminUsersService()
        data = service.get_user_access(user_id)
        return jsonify({"status": "ok", **data}), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404
    except Exception:
        return jsonify({"error": "Erro ao consultar acesso."}), 500


@admin_users_bp.post("/users")
@require_auth
@require_role(ROLE_SYSADMIN)
def create_user():
    payload = request.get_json(silent=True) or {}
    try:
        service = AdminUsersService()
        result = service.create_user(payload)
        return jsonify({"status": "ok", **result}), 201
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        return jsonify({"error": "Erro ao criar utilizador."}), 500


@admin_users_bp.put("/users/<user_id>")
@require_auth
@require_role(ROLE_SYSADMIN)
def update_user(user_id: str):
    payload = request.get_json(silent=True) or {}
    try:
        service = AdminUsersService()
        result = service.update_user(user_id, payload)
        return jsonify({"status": "ok", **result}), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        return jsonify({"error": "Erro ao atualizar utilizador."}), 500


@admin_users_bp.delete("/users/<user_id>")
@require_auth
@require_role(ROLE_SYSADMIN)
def deactivate_user(user_id: str):
    try:
        service = AdminUsersService()
        result = service.deactivate_user(user_id)
        return jsonify({"status": "ok", **result}), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404
    except Exception:
        return jsonify({"error": "Erro ao desativar utilizador."}), 500


@admin_users_bp.post("/users/<user_id>/regenerate-code")
@require_auth
@require_role(ROLE_SYSADMIN)
def regenerate_code(user_id: str):
    try:
        service = AdminUsersService()
        result = service.regenerate_lead_code(user_id)
        return jsonify({"status": "ok", **result}), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        return jsonify({"error": "Erro ao reenviar código."}), 500
