"""HTML do post. nh3 tira o que não está na lista; iframe só de YouTube e Vimeo."""

from __future__ import annotations

import re
from urllib.parse import urlparse

import nh3

TAGS = {
    "p",
    "h2",
    "h3",
    "a",
    "img",
    "figure",
    "figcaption",
    "blockquote",
    "ul",
    "ol",
    "li",
    "strong",
    "em",
    "video",
    "audio",
    "source",
    "iframe",
}

ATTRIBUTES = {
    "a": {"href", "title"},
    "img": {"src", "alt"},
    "iframe": {"src", "title", "allow", "allowfullscreen"},
    "video": {"src", "controls"},
    "audio": {"src", "controls"},
    "source": {"src", "type"},
}

CLASSES = {
    "a": {"card-link"},
    "figure": {"wide", "desenho", "audio", "swatch-aroma", "swatch-toque", "swatch-sabor"},
    "ul": {"galeria"},
    "li": {"swatch-aroma", "swatch-toque", "swatch-sabor"},
}

_IFRAME = re.compile(r"<iframe\b[^>]*>.*?</iframe>", re.IGNORECASE | re.DOTALL)
_SRC = re.compile(r"""src=["']([^"']+)["']""", re.IGNORECASE)


def embed_ok(url: str) -> bool:
    parsed = urlparse(url.strip())
    if parsed.scheme not in {"http", "https"}:
        return False
    host = (parsed.hostname or "").lower()
    path = parsed.path or ""
    if host in {"www.youtube.com", "youtube.com", "www.youtube-nocookie.com", "youtube-nocookie.com"}:
        return path.startswith("/embed/")
    if host == "player.vimeo.com":
        return path.startswith("/video/")
    return False


def _keep_attribute(tag: str, attr: str, value: str) -> str | None:
    if tag == "iframe" and attr == "src" and not embed_ok(value):
        return None
    return value


def _drop_bad_iframes(html: str) -> str:
    def replace(match: re.Match) -> str:
        tag = match.group(0)
        found = _SRC.search(tag)
        if found and embed_ok(found.group(1)):
            return tag
        return ""

    return _IFRAME.sub(replace, html)


def clean(html: str) -> str:
    if not html:
        return ""
    cleaned = nh3.clean(
        html,
        tags=TAGS,
        attributes=ATTRIBUTES,
        attribute_filter=_keep_attribute,
        allowed_classes=CLASSES,
        url_schemes={"http", "https"},
        link_rel="noopener noreferrer",
        strip_comments=True,
    )
    return _drop_bad_iframes(cleaned)
