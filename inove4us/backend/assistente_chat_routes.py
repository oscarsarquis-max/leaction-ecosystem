"""
GET /api/assistente-chat — árvore do assistente (Hub CMS + fallback local).
"""

from __future__ import annotations

from flask import Blueprint, jsonify

from assistente_chat_fallback import build_fallback_tree, normalize_tree_payload
from db import CREDITO_IA_FREEMIUM_DEFAULT, FREEMIUM_AULAS_MES
from services.hub_cms_cache import fetch_assistente_chat

assistente_chat_bp = Blueprint("assistente_chat", __name__)


@assistente_chat_bp.get("/api/assistente-chat")
def get_assistente_chat():
    aulas = int(FREEMIUM_AULAS_MES)
    desafios = int(CREDITO_IA_FREEMIUM_DEFAULT)
    source = "fallback"

    raw = fetch_assistente_chat(sistema_destino="inove4us")
    tree = normalize_tree_payload(raw, aulas_mes=aulas, desafios_gratis=desafios)
    if tree is None:
        tree = build_fallback_tree(aulas_mes=aulas, desafios_gratis=desafios)
        tree["source"] = "fallback"
    else:
        tree["source"] = "hub"
        source = "hub"

    return jsonify(
        {
            "success": True,
            "source": source,
            "limits": {
                "aulas_mes": aulas,
                "desafios_gratis": desafios,
            },
            "tree": tree,
        }
    ), 200
