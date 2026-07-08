"""Rotas de integração com sistemas externos (Chamelleon → Diário de Obra)."""

from functools import wraps

from flask import Blueprint, current_app, jsonify, request

from app.services import DirectiveService
from app.services.daily_goals_service import DailyGoalsService

integration_bp = Blueprint("integration", __name__, url_prefix="/api/integration")


def require_integration_auth(view):
    """Autenticação por API key — contrato desacoplado (sem acoplamento ao Chamelleon)."""

    @wraps(view)
    def wrapper(*args, **kwargs):
        expected = current_app.config.get("INTEGRATION_API_KEY") or ""
        if not expected:
            return jsonify({"error": "Integração não configurada no servidor."}), 503

        provided = (
            request.headers.get("X-Integration-Key")
            or request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
        )
        if not provided or provided != expected:
            return jsonify({"error": "Não autorizado."}), 401

        return view(*args, **kwargs)

    return wrapper


@integration_bp.post("/framework-directives")
@require_integration_auth
def receive_framework_directives():
    """
    Recebe Building Blocks operacionais (Gemba) quando um framework é aprovado no Chamelleon.

    Payload esperado (exemplo):
    {
      "tenant_id": "uuid",
      "project_id": "uuid",
      "framework_id": "telecom-v1",
      "framework_version": "1.2.0",
      "building_blocks": [ ... ],
      "gemba_focus": "campo",
      "metadata": {}
    }
    """
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "JSON inválido."}), 400

    try:
        service = DirectiveService()
        record = service.upsert_framework_directives(payload)
        return (
            jsonify(
                {
                    "status": "ok",
                    "directive_id": str(record.id),
                    "tenant_id": record.tenant_id,
                    "project_id": str(record.project_id),
                    "framework_id": record.framework_id,
                    "received_at": record.received_at.isoformat() if record.received_at else None,
                }
            ),
            201,
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        return jsonify({"error": "Erro ao persistir diretrizes."}), 500


@integration_bp.post("/daily-goals")
@require_integration_auth
def receive_daily_goals():
    """
    Recebe metas diárias (Sprint Goals) do Chamelleon e injeta nos rascunhos de RDO.

    Payload:
    {
      "tenant_id": "uuid",
      "project_id": "uuid",
      "goals": [{"date": "2026-07-08", "sprint_daily_goal": "..."}]
    }
    """
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "JSON inválido."}), 400

    try:
        result = DailyGoalsService().upsert_goals(payload)
        return jsonify({"status": "ok", **result}), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        return jsonify({"error": "Erro ao aplicar metas diárias."}), 500
