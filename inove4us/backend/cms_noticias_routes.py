"""
GET /api/noticias — proxy resiliente ao Headless CMS do Action Hub.
"""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from services.hub_cms_cache import fetch_published_posts

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
