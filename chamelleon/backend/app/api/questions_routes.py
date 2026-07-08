"""Rotas de gestão administrativa do catálogo de questões do framework publicado.

CRUD restrito a sysadmin. Leads e o fluxo de diagnóstico consomem o catálogo via
GET /api/assessment/questions (somente leitura).
"""

from flask import Blueprint, jsonify, request

from app.core.middlewares import require_tenant_context
from app.core.rbac import ROLE_SYSADMIN, require_auth, require_role
from app.services.assessment_service import AssessmentService

questions_bp = Blueprint("questions", __name__)


@questions_bp.get("/admin-catalog")
@require_auth
@require_role(ROLE_SYSADMIN)
def list_questions_admin_catalog():
    try:
        service = AssessmentService()
        catalog = service.list_questions_catalog_admin()
        return jsonify({"status": "ok", **catalog}), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        return jsonify({"error": "Erro ao listar catálogo global de questões."}), 500


@questions_bp.get("")
@require_tenant_context
@require_auth
@require_role(ROLE_SYSADMIN)
def list_questions():
    try:
        service = AssessmentService()
        items = service.list_questions_catalog()
        return jsonify({"status": "ok", "items": items, "total": len(items)}), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        return jsonify({"error": "Erro ao listar questões."}), 500


@questions_bp.post("")
@require_tenant_context
@require_auth
@require_role(ROLE_SYSADMIN)
def create_question():
    payload = request.get_json(silent=True) or {}
    try:
        service = AssessmentService()
        result = service.create_question(payload)
        return jsonify({"status": "ok", **result}), 201
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        return jsonify({"error": "Erro ao criar questão."}), 500


@questions_bp.put("/<question_id>")
@require_tenant_context
@require_auth
@require_role(ROLE_SYSADMIN)
def update_question(question_id: str):
    payload = request.get_json(silent=True) or {}
    try:
        service = AssessmentService()
        result = service.update_question(question_id, payload)
        return jsonify({"status": "ok", **result}), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404
    except Exception:
        return jsonify({"error": "Erro ao atualizar questão."}), 500


@questions_bp.delete("/<question_id>")
@require_tenant_context
@require_auth
@require_role(ROLE_SYSADMIN)
def delete_question(question_id: str):
    try:
        service = AssessmentService()
        result = service.delete_question(question_id)
        return jsonify({"status": "ok", **result}), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404
    except Exception:
        return jsonify({"error": "Erro ao remover questão."}), 500
