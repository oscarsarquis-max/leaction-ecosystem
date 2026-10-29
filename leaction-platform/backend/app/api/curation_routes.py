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
        from app.services.marketplace_resilience import offers_cache, vitrine_cache

        offers_cache.clear()
        vitrine_cache.clear()
        return jsonify({"status": "ok", "rule": row.to_dict()}), 200
    except Exception:
        logger.exception("Falha ao atualizar curadoria id=%s", curation_id)
        return (
            jsonify({"status": "error", "error": "Erro ao atualizar regra de curadoria"}),
            500,
        )


@curation_bp.get("/diagnosis")
def diagnosis_offers():
    """Diagnóstico editorial: aceites e rejeições com motivo legível. Sem dados pessoais."""
    from app.services.multivendor_orchestrator import MultivendorOrchestrator
    from app.services.origin_profiles import resolve_origin

    origin = (request.args.get("origin") or "lojadepaes").strip().lower()
    resolved = resolve_origin(query_origin=origin)
    if not resolved["ok"]:
        return jsonify({"status": "error", "error": resolved["error"]}), 400
    category = (request.args.get("category") or "vinhos").strip().lower()
    limit = min(max(request.args.get("limit", default=12, type=int) or 12, 1), 24)
    result = MultivendorOrchestrator().search_all_vendors(
        None,
        category=category,
        origin=resolved["origin"],
        limit=limit,
        diagnose=True,
    )
    rejected = (result.get("diagnosis") or {}).get("rejected_offers") or []
    return jsonify(
        {
            "status": "ok",
            "origin": resolved["origin"],
            "category": category,
            "accepted": [
                {
                    "id": item.get("id"),
                    "title": item.get("title"),
                    "reason": item.get("relevance_reason"),
                    "source": item.get("relevance_source"),
                    "domain": item.get("provider_domain"),
                }
                for item in result.get("offers") or []
            ],
            "rejected": [
                {
                    "id": item.get("id"),
                    "title": item.get("title"),
                    "reason": item.get("relevance_reason"),
                    "source": item.get("relevance_source"),
                    "domain": item.get("provider_domain"),
                }
                for item in rejected
            ],
        }
    )


@curation_bp.put("/decisions")
def put_offer_decision():
    payload = request.get_json(silent=True) or {}
    offer_id = str(payload.get("offer_id") or "").strip()
    origin = str(payload.get("origin") or "lojadepaes").strip().lower()
    category = str(payload.get("category") or "").strip().lower()
    decision = str(payload.get("decision") or "").strip().lower()
    reason = str(payload.get("reason") or "").strip()
    if not offer_id or not category or decision not in {"approve", "reject"} or not reason:
        return jsonify({"status": "error", "error": "Informe offer_id, category, decision e reason."}), 400
    try:
        from app.services.marketplace_resilience import offers_cache, vitrine_cache
        from app.services.offer_decisions import upsert_decision

        row = upsert_decision(
            offer_id=offer_id,
            origin=origin,
            category=category,
            decision=decision,
            reason=reason[:400],
        )
        offers_cache.clear()
        vitrine_cache.clear()
        return jsonify({"status": "ok", "decision": row}), 200
    except RuntimeError as exc:
        return jsonify({"status": "error", "error": str(exc)}), 503
