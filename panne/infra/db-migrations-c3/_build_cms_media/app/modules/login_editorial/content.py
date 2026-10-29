"""Conteúdo estático + sanitização do schema editorial Panne."""

from __future__ import annotations

from hashlib import sha256

from app.modules.login_editorial.url_policy import (
    DEFAULT_CTA_HOSTS,
    DEFAULT_MEDIA_HOSTS,
    parse_host_allowlist,
    sanitize_cta_url,
    sanitize_image_url,
)

SCHEMA_VERSION = 1
STATIONS_NOTE = "Conteúdo editorial sanitizado. Autenticação permanece no centro."

_COLUMNS = (
    {
        "placement": "left",
        "eyebrow": "Oficina",
        "title": "O turno cabe no quadro",
        "summary": "Produção, componentes e conformidade no recorte da padaria.",
        "sections": (
            "Contexto do turno antes dos filtros.",
            "Próxima ação por estado e permissão.",
        ),
        "image": {
            "url": "/images/aprovados/horizontal-claro.png",
            "alt": "Marca Panne em fundo claro.",
        },
        "priority": 10,
    },
    {
        "placement": "right",
        "eyebrow": "Atelier",
        "title": "Ficha antes do palpite",
        "summary": "Versão e revisão humana antes de qualquer selo.",
        "sections": (
            "Ausência não é zero.",
            "Assistente orienta, não executa.",
        ),
        "image": {
            "url": "/images/aprovados/compacto-escuro.png",
            "alt": "Símbolo compacto da Panne.",
        },
        "priority": 9,
    },
)


def _plain(value: object, max_len: int) -> str:
    text = str(value or "")
    text = "".join(ch for ch in text if ch >= " " or ch in "\n\t")
    for token in ("<", ">", "javascript:", "data:"):
        if token in text.lower() and token != "\n":
            text = text.replace("<", "").replace(">", "")
    return text.strip()[:max_len]


def _hash(payload: dict) -> str:
    return sha256(repr(sorted(payload.items())).encode("utf-8")).hexdigest()[:16]


def sanitize_column(
    raw: dict,
    *,
    media_hosts: frozenset[str] | None = None,
    cta_hosts: frozenset[str] | None = None,
) -> dict | None:
    placement = raw.get("placement")
    if placement not in {"left", "right"}:
        return None
    title = _plain(raw.get("title"), 120)
    if not title:
        return None
    media = media_hosts if media_hosts is not None else DEFAULT_MEDIA_HOSTS
    ctas = cta_hosts if cta_hosts is not None else DEFAULT_CTA_HOSTS
    image = raw.get("image") if isinstance(raw.get("image"), dict) else {}
    url = sanitize_image_url(image.get("url"), media_hosts=media)
    column = {
        "schema_version": SCHEMA_VERSION,
        "placement": placement,
        "locale": "pt-BR",
        "eyebrow": _plain(raw.get("eyebrow"), 40),
        "title": title,
        "summary": _plain(raw.get("summary"), 280),
        "sections": [_plain(item, 180) for item in raw.get("sections") or [] if _plain(item, 180)][:4],
        "image": {"url": url, "alt": _plain(image.get("alt"), 120) or title},
        "priority": int(raw.get("priority") or 0),
    }
    cta = raw.get("cta") if isinstance(raw.get("cta"), dict) else None
    if cta:
        label = _plain(cta.get("label"), 40)
        href = sanitize_cta_url(cta.get("url"), cta_hosts=ctas)
        if label and href:
            column["cta"] = {"label": label, "url": href}
    column["hash"] = _hash(column)
    return column


def static_payload(
    *,
    media_hosts: frozenset[str] | None = None,
    cta_hosts: frozenset[str] | None = None,
) -> dict:
    columns = [
        sanitize_column(dict(row), media_hosts=media_hosts, cta_hosts=cta_hosts) for row in _COLUMNS
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "source": "static",
        "columns": [row for row in columns if row],
        "note": STATIONS_NOTE,
    }


def unavailable_fallback() -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "source": "fallback",
        "columns": [],
        "note": "Conteúdo editorial indisponível. O acesso permanece no centro.",
    }


def hosts_from_settings(settings) -> tuple[frozenset[str], frozenset[str]]:
    media = parse_host_allowlist(
        getattr(settings, "login_editorial_media_hosts", "") or "",
        DEFAULT_MEDIA_HOSTS,
    )
    cta = parse_host_allowlist(
        getattr(settings, "login_editorial_cta_hosts", "") or "",
        DEFAULT_CTA_HOSTS,
    )
    return media, cta
