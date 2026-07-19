"""Rotas HTTP eSIM — webhook e API de backlog."""

from __future__ import annotations

import sys

from flask import Blueprint, jsonify, request

from integrations.esim.observability import esim_log_webhook_rate_limited
from integrations.esim.processor import esim_processar_webhook
from integrations.esim.rate_limit import esim_verificar_rate_limit_webhook
from integrations.esim.repository import esim_consumir_backlog_item, esim_listar_backlog_pendente

esim_bp = Blueprint("esim", __name__)


def _esim_client_key_webhook() -> str:
    forwarded = (request.headers.get("X-Forwarded-For") or "").split(",")[0].strip()
    return forwarded or (request.remote_addr or "unknown")


def _esim_executar_webhook():
    permitido, retry_after = esim_verificar_rate_limit_webhook(_esim_client_key_webhook())
    if not permitido:
        esim_log_webhook_rate_limited(_esim_client_key_webhook(), retry_after)
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "Rate limit excedido no webhook eSIM.",
                    "retry_after_s": retry_after,
                }
            ),
            429,
        )

    try:
        body = request.get_json(silent=True)
        result = esim_processar_webhook(body, dict(request.headers))
        status = result.pop("http_status", 200)
        return jsonify(result), status
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500


@esim_bp.route("/api/webhooks/esim", methods=["POST"])
def esim_webhook_ingestao():
    """Ingestão de telemetria eSIM (rota canônica)."""
    return _esim_executar_webhook()


@esim_bp.route("/api/webhooks/basemobile", methods=["POST"])
def esim_webhook_basemobile_alias():
    """Alias legado — Base Mobile."""
    return _esim_executar_webhook()


@esim_bp.route("/api/esim/mesa-backlog", methods=["GET"])
def esim_api_mesa_backlog():
    """Backlog preditivo eSIM — consumível pela Mesa Org."""
    id_clie = request.args.get("id_clie")
    id_matu = request.args.get("id_matu")
    if not id_clie:
        return jsonify({"status": "error", "message": "id_clie é obrigatório"}), 400
    try:
        items = esim_listar_backlog_pendente(int(id_clie), int(id_matu) if id_matu else None)
        return jsonify({"status": "success", "origem": "telemetria", "data": items}), 200
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500


@esim_bp.route("/api/basemobile/mesa-backlog", methods=["GET"])
def esim_api_mesa_backlog_basemobile_alias():
    """Alias legado — Base Mobile."""
    return esim_api_mesa_backlog()


@esim_bp.route("/api/esim/mesa-backlog/consumir", methods=["POST"])
def esim_api_consumir_backlog():
    """Marca item do backlog eSIM como consumido."""
    data = request.get_json(silent=True) or {}
    id_item = data.get("id_item")
    id_nota = data.get("id_nota") or data.get("id_nota_mesa")

    if id_item is None and id_nota is None:
        return jsonify({"status": "error", "message": "Informe id_item ou id_nota."}), 400

    try:
        id_item_int = int(id_item) if id_item is not None else None
        id_nota_int = int(id_nota) if id_nota is not None else None
        result = esim_consumir_backlog_item(id_item=id_item_int, id_nota=id_nota_int)
        if result.get("consumidos", 0) == 0:
            return jsonify({"status": "success", "message": "Nenhum item pendente encontrado.", **result}), 200
        return jsonify({"status": "success", "message": "Backlog eSIM marcado como consumido.", **result}), 200
    except (TypeError, ValueError):
        return jsonify({"status": "error", "message": "id_item/id_nota deve ser numérico."}), 400
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500


@esim_bp.route("/api/basemobile/mesa-backlog/consumir", methods=["POST"])
def esim_api_consumir_backlog_basemobile_alias():
    """Alias legado — Base Mobile."""
    return esim_api_consumir_backlog()


def register_esim_routes(flask_app) -> None:
    """Registra rotas eSIM no app Flask principal."""
    flask_app.register_blueprint(esim_bp)
    from integrations.esim.admin_routes import register_esim_admin_routes
    register_esim_admin_routes(flask_app)
    print("✅ eSIM: POST /api/webhooks/esim registrado.", file=sys.stderr)


def register_basemobile_routes(flask_app) -> None:
    """Alias legado — redireciona para register_esim_routes."""
    register_esim_routes(flask_app)
