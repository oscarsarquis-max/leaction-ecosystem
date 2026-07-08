"""Rotas do plugin Marketplace — exposição federada multivendor."""

from __future__ import annotations

import logging

from flask import Blueprint, jsonify, request

from app.services.amazon_service import AmazonService
from app.services.mercadolivre_auth import is_ml_api_configured
from app.services.ml_oauth_service import (
    has_persisted_or_env_tokens,
    is_oauth_app_configured,
    oauth_setup_info,
)
from app.services.mercadolivre_service import DEFAULT_LIMIT, MAX_LIMIT
from app.services.multivendor_orchestrator import MultivendorOrchestrator

logger = logging.getLogger(__name__)

marketplace_bp = Blueprint("marketplace", __name__)


@marketplace_bp.get("/offers")
def list_marketplace_offers():
    """
    GET /api/marketplace/offers
    Query params: q (termo), category (formacao|equipamentos|software), limit (1–24).
    """
    query = (request.args.get("q") or "").strip() or None
    category = (request.args.get("category") or "").strip() or None
    limit_raw = request.args.get("limit", type=int)
    limit = limit_raw if limit_raw is not None else DEFAULT_LIMIT
    limit = max(1, min(limit, MAX_LIMIT))

    orchestrator = MultivendorOrchestrator()
    try:
        result = orchestrator.search_all_vendors(
            query,
            category=category,
            limit=limit,
        )
        return jsonify(result), 200
    except Exception:
        logger.exception("Falha inesperada no marketplace federado")
        return (
            jsonify(
                {
                    "status": "error",
                    "error": "Erro interno ao agregar ofertas multivendor",
                    "offers": [],
                    "count": 0,
                }
            ),
            500,
        )


@marketplace_bp.get("/categories")
def list_marketplace_categories():
    """Catálogo de categorias de Transformação Digital suportadas pelo agregador."""
    return jsonify(
        {
            "status": "ok",
            "categories": MultivendorOrchestrator.list_categories(),
        }
    ), 200


@marketplace_bp.get("/health")
def marketplace_health():
    """Healthcheck isolado do plugin (não interfere no gateway)."""
    ml_oauth = oauth_setup_info()
    return (
        jsonify(
            {
                "status": "ok",
                "plugin": "marketplace",
                "mode": "federated",
                "ml_configured": is_ml_api_configured(),
                "ml_oauth_app": is_oauth_app_configured(),
                "ml_tokens_ready": has_persisted_or_env_tokens(),
                "ml_redirect_uri_https": ml_oauth.get("redirect_uri_https"),
                "ml_redirect_uri": ml_oauth.get("redirect_uri"),
                "amazon_configured": AmazonService.is_configured(),
                "amazon_credentials": AmazonService.credential_status(),
            }
        ),
        200,
    )
