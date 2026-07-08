"""CRUD de curadoria B2B — plugin Marketplace isolado."""

from __future__ import annotations

import logging

from flask import Blueprint, jsonify, request

from app.services.curation_repository import CurationRepository

logger = logging.getLogger(__name__)

curation_bp = Blueprint("curation", __name__)


@curation_bp.get("/curation")
def list_curation_rules():
    """GET /api/marketplace/curation — lista todas as regras."""
    try:
        rows = CurationRepository.list_all()
        return jsonify({"status": "ok", "count": len(rows), "rules": rows}), 200
    except Exception:
        logger.exception("Falha ao listar curadoria")
        return (
            jsonify({"status": "error", "error": "Erro ao listar regras de curadoria"}),
            500,
        )


@curation_bp.put("/curation/<curation_id>")
def update_curation_rule(curation_id: str):
    """PUT /api/marketplace/curation/<id> — atualiza listas JSON de uma categoria."""
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"status": "error", "error": "JSON inválido"}), 400

    allowed_keys = {"search_terms", "positive_keywords", "negative_keywords"}
    updates = {key: payload[key] for key in allowed_keys if key in payload}
    if not updates:
        return (
            jsonify(
                {
                    "status": "error",
                    "error": "Informe ao menos um campo: search_terms, positive_keywords, negative_keywords",
                }
            ),
            400,
        )

    for key, value in updates.items():
        if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
            return (
                jsonify(
                    {
                        "status": "error",
                        "error": f"Campo '{key}' deve ser uma lista de strings",
                    }
                ),
                400,
            )

    try:
        from app.database import DB_AVAILABLE

        if not DB_AVAILABLE:
            return (
                jsonify(
                    {
                        "status": "error",
                        "error": "Banco indisponível. Instale dependências: pip install -r requirements.txt",
                    }
                ),
                503,
            )
        row = CurationRepository.update_by_id(curation_id.strip().lower(), updates)
        return jsonify({"status": "ok", "rule": row.to_dict()}), 200
    except Exception:
        logger.exception("Falha ao atualizar curadoria id=%s", curation_id)
        return (
            jsonify({"status": "error", "error": "Erro ao atualizar regra de curadoria"}),
            500,
        )
