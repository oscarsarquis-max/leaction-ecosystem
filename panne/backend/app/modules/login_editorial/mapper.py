"""Mapper Action Hub landing_page_data → schema fechado Panne (colunas left/right)."""

from __future__ import annotations

from hashlib import sha256
from typing import Any

from app.modules.login_editorial.content import SCHEMA_VERSION, sanitize_column

# Hero do Hub não tem slot na superfície /entrar atual — documentado como não consumido.
HERO_NOT_CONSUMED = True
# Corpo da coluna publicado no Hub. 280 cortava o texto no meio da frase.
COLUMN_BODY_MAX = 2000


def _plain(value: object, max_len: int) -> str:
    text = str(value or "")
    text = "".join(ch for ch in text if ch >= " " or ch in "\n\t")
    lower = text.lower()
    if "<" in lower or "javascript:" in lower or "data:" in lower:
        text = text.replace("<", "").replace(">", "")
    return text.strip()[:max_len]


def _column_from_banner(
    *,
    placement: str,
    banner: dict[str, Any],
    priority: int,
    media_hosts: frozenset[str] | None = None,
    cta_hosts: frozenset[str] | None = None,
) -> dict[str, Any] | None:
    if banner.get("visibility") is False or banner.get("visible") is False:
        return None
    title = _plain(banner.get("title") or banner.get("leaction_title"), 120)
    hub_body = _plain(
        banner.get("subtitle") or banner.get("description") or banner.get("summary"),
        COLUMN_BODY_MAX,
    )
    eyebrow = _plain(banner.get("pill_text") or banner.get("badge_text") or "", 40)
    image_url = _plain(banner.get("image_url") or banner.get("image_path") or "", 240)
    alt = _plain(banner.get("image_alt") or title, 120)
    cta_label = _plain(banner.get("cta_text") or banner.get("link_text") or banner.get("button_text"), 40)
    cta_url = _plain(banner.get("cta_url") or banner.get("link_url") or banner.get("button_url"), 240)
    # Coluna publicada usa só os campos do Hub. Rótulo, imagem ou texto vazios
    # permanecem vazios — não entram o rótulo, a foto nem as linhas estáticas.
    published = bool(title or hub_body or image_url)
    if not published:
        return None
    raw = {
        "placement": placement,
        "eyebrow": eyebrow,
        "title": title,
        "summary": hub_body,
        "sections": [],
        "image": {
            "url": image_url,
            "alt": alt or title,
        },
        "priority": priority,
    }
    if cta_label and cta_url:
        raw["cta"] = {"label": cta_label, "url": cta_url}
    return sanitize_column(raw, media_hosts=media_hosts, cta_hosts=cta_hosts)


def map_hub_landing_to_panne(
    landing: dict[str, Any] | None,
    *,
    static_columns: list[dict[str, Any]],
    media_hosts: frozenset[str] | None = None,
    cta_hosts: frozenset[str] | None = None,
) -> dict[str, Any] | None:
    """
    Mapeia apenas colunas laterais. Hero é ignorado (sem slot na UI Panne).
    Coluna ausente/ inválida → fallback estático daquela coluna.
    """
    if not isinstance(landing, dict):
        return None

    by_placement = {c["placement"]: c for c in static_columns if c.get("placement") in {"left", "right"}}
    columns_out: list[dict[str, Any]] = []

    coluna1 = landing.get("coluna1") if isinstance(landing.get("coluna1"), dict) else {}
    cols = landing.get("columns") if isinstance(landing.get("columns"), list) else []
    col0 = cols[0] if len(cols) > 0 and isinstance(cols[0], dict) else {}
    col1 = cols[1] if len(cols) > 1 and isinstance(cols[1], dict) else {}

    if coluna1 and col0:
        left_src = {**col0, **coluna1}
        if not left_src.get("title") and col0.get("title"):
            left_src["title"] = col0["title"]
        if not left_src.get("subtitle") and col0.get("description"):
            left_src["subtitle"] = col0["description"]
    elif coluna1:
        left_src = coluna1
    else:
        left_src = col0

    right_src = col1

    left = _column_from_banner(
        placement="left",
        banner=left_src if isinstance(left_src, dict) else {},
        priority=10,
        media_hosts=media_hosts,
        cta_hosts=cta_hosts,
    ) or by_placement.get("left")

    right = _column_from_banner(
        placement="right",
        banner=right_src if isinstance(right_src, dict) else {},
        priority=9,
        media_hosts=media_hosts,
        cta_hosts=cta_hosts,
    ) or by_placement.get("right")

    for col in (left, right):
        if col:
            columns_out.append(col)

    if not columns_out:
        return None

    digest = sha256(repr([(c.get("placement"), c.get("hash")) for c in columns_out]).encode()).hexdigest()[:12]
    return {
        "schema_version": SCHEMA_VERSION,
        "source": "hub",
        "columns": columns_out,
        "note": f"Editorial Hub mapeado (colunas; hero não consumido). v={digest}",
        "hub_hero_consumed": False,
    }
