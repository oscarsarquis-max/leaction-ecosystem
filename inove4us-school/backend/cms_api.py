"""GET /api/cms/site — Micro-CMS do Action Hub (colunas da página /acesso)."""
from __future__ import annotations

import os
from typing import Any

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


def _hub_media_base() -> str:
    """Origem pública das imagens CMS (/images/...). Preferir Hub FE (com rewrite) ou gateway."""
    return (
        os.environ.get("ACTION_HUB_MEDIA_BASE_URL")
        or os.environ.get("ACTION_HUB_PUBLIC_URL")
        or os.environ.get("ACTION_HUB_API_URL")
        or os.environ.get("HUB_API_URL")
        or "http://127.0.0.1:4001"
    ).strip().rstrip("/")


def _absolutize_cms_media_url(url: Any) -> str:
    raw = str(url or "").strip()
    if not raw:
        return ""
    if raw.startswith(("http://", "https://", "data:")):
        return raw
    if raw.startswith("/images/"):
        return f"{_hub_media_base()}{raw}"
    if raw.startswith("images/"):
        return f"{_hub_media_base()}/{raw}"
    return raw


def _rewrite_block_media(block: Any) -> Any:
    if not isinstance(block, dict):
        return block
    out = dict(block)
    for key in ("image_url", "image_path"):
        if key in out:
            out[key] = _absolutize_cms_media_url(out.get(key))
    # Garante que FE (image_url || image_path) ache a URL absoluta.
    media = _absolutize_cms_media_url(out.get("image_url") or out.get("image_path"))
    if media:
        out["image_url"] = media
        out["image_path"] = media
    return out


def absolutize_landing_media(landing: dict[str, Any]) -> dict[str, Any]:
    """Converte /images/... relativo do Hub em URL absoluta para o browser do School."""
    out = dict(landing)
    if "coluna1" in out:
        out["coluna1"] = _rewrite_block_media(out.get("coluna1"))
    if "hero_cta" in out:
        out["hero_cta"] = _rewrite_block_media(out.get("hero_cta"))
    columns = out.get("columns")
    if isinstance(columns, list):
        out["columns"] = [_rewrite_block_media(col) for col in columns]
    return out


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
    landing = absolutize_landing_media(landing)
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
