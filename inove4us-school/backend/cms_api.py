"""GET /api/cms/site — Micro-CMS do Action Hub (colunas da página /acesso)."""
from __future__ import annotations

from flask import Blueprint, jsonify, request

from hub_cms_cache import fetch_site_cms

bp = Blueprint("cms", __name__)

DEFAULT_CONFIG_KEY = "inove4us-school"

# Fallback local quando o Hub está offline — espelha o default do Hub (inove4us-school).
_LOCAL_FALLBACK_LANDING = {
    "hero": {
        "leaction_title": "inove4us School",
        "subtitle": "Governança pedagógica da escola",
        "description": (
            "Metodologias, PEI e calendário em um só lugar — "
            "para gestores, secretaria e neuropedagogas."
        ),
    },
    "columns": [
        {
            "title": "O que é o inove4us School",
            "description": (
                "Torre de Controle B2B: a escola governa o método; "
                "os professores executam no inove4us."
            ),
            "visible": True,
            "pill_text": "Instituição",
            "bg_color_start": "#062e28",
            "bg_color_end": "#0f6b5c",
            "pill_bg_color": "#0c574b",
        },
        {
            "title": "Como entrar",
            "description": (
                "Acesso com e-mail e senha do gestor. Zonas administrativo, "
                "operacional e pedagógico conforme o perfil."
            ),
            "visible": True,
            "bg_color_start": "#0a453c",
            "bg_color_end": "#0f6b5c",
            "pill_text": "Acesso",
            "pill_bg_color": "#0c574b",
        },
    ],
    "coluna1": {
        "pill_text": "Instituição",
        "title": "O que é o inove4us School",
        "subtitle": (
            "Torre de Controle B2B: a escola governa o método; "
            "os professores executam no inove4us."
        ),
        "visible": True,
        "bg_color_start": "#062e28",
        "bg_color_end": "#0f6b5c",
        "pill_bg_color": "#0c574b",
        "button_bg_color": "#0f6b5c",
    },
}


@bp.get("/api/cms/site")
def get_site_cms():
    """Landing Micro-CMS do Hub. Sem gestão local no School."""
    config_key = (request.args.get("config_key") or DEFAULT_CONFIG_KEY).strip() or DEFAULT_CONFIG_KEY
    data = fetch_site_cms(config_key=config_key)
    landing = data.get("landing_page_data") if isinstance(data, dict) else None
    if not isinstance(landing, dict):
        landing = {}
    source = "hub" if landing else "empty"
    if not landing:
        landing = dict(_LOCAL_FALLBACK_LANDING)
        source = "fallback"
    return (
        jsonify(
            {
                "success": True,
                "config_key": data.get("config_key") or config_key,
                "landing_page_data": landing,
                "source": source,
            }
        ),
        200,
    )
