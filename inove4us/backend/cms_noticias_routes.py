"""
GET /api/noticias — proxy resiliente ao Headless CMS do Action Hub.
GET /api/cms/site — Micro-CMS (landing) por config_key (padrão inove4us).
"""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from services.hub_cms_cache import fetch_published_posts, fetch_site_cms

cms_noticias_bp = Blueprint("cms_noticias", __name__)


@cms_noticias_bp.get("/api/noticias")
def list_noticias():
    sistema = (request.args.get("sistema_destino") or "inove4us").strip() or "inove4us"
    try:
        limit = int(request.args.get("limit") or "5")
    except (TypeError, ValueError):
        limit = 5
    limit = max(1, min(limit, 50))

    posts = fetch_published_posts(sistema_destino=sistema, limit=limit)
    # Sempre 200 — degradação silenciosa (cache ou [])
    return jsonify(posts), 200


@cms_noticias_bp.get("/api/cms/site")
def get_site_cms():
    """Landing Micro-CMS do Hub (colunas /acesso). Sem gestão no satélite."""
    config_key = (request.args.get("config_key") or "inove4us").strip() or "inove4us"
    data = fetch_site_cms(config_key=config_key)
    landing = data.get("landing_page_data") if isinstance(data, dict) else None
    if not isinstance(landing, dict):
        landing = {}
    return (
        jsonify(
            {
                "success": True,
                "config_key": data.get("config_key") or config_key,
                "landing_page_data": landing,
                "source": "hub" if landing else "empty",
            }
        ),
        200,
    )
