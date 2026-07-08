"""Busca pública no Mercado Livre — extrai ofertas reais (imagem do vendor) do HTML de /ofertas."""

from __future__ import annotations

import json
import logging
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
OFERTAS_BASE = "https://www.mercadolivre.com.br/ofertas"
ML_PICTURE_BASE = "https://http2.mlstatic.com/D_Q_NP_2X_{picture_id}-AB.webp"


class MercadoLivrePublicSearchError(Exception):
    """Falha ao obter ofertas públicas do Mercado Livre."""


def search_public_offers(query: str, *, limit: int = 12, timeout_s: int = 15) -> list[dict[str, Any]]:
    """Busca ofertas via página pública /ofertas?q= (sem OAuth)."""
    term = (query or "").strip()
    if not term:
        return []

    params = urllib.parse.urlencode({"q": term})
    url = f"{OFERTAS_BASE}?{params}"
    html = _fetch_html(url, timeout_s=timeout_s)

    offers = _parse_organic_items(html, limit=limit)
    if offers:
        return offers

    offers = _parse_loose_items(html, limit=limit)
    return offers


def _fetch_html(url: str, *, timeout_s: int) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "pt-BR,pt;q=0.9",
            "User-Agent": USER_AGENT,
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_s) as response:
            return response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        logger.error("Erro ao consultar Mercado Livre: HTTP %s", exc.code)
        raise MercadoLivrePublicSearchError(
            f"Mercado Livre retornou HTTP {exc.code} na busca pública"
        ) from exc
    except urllib.error.URLError as exc:
        raise MercadoLivrePublicSearchError(
            "Não foi possível contactar o Mercado Livre"
        ) from exc


def _parse_organic_items(html: str, *, limit: int) -> list[dict[str, Any]]:
    """Extrai cards ORGANIC_ITEM embutidos no HTML Nordic/polycard."""
    offers: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for match in re.finditer(r'"type":"ORGANIC_ITEM"', html):
        chunk = html[match.start() : match.start() + 6000]

        item_match = re.search(r'"metadata":\{[^}]*"id":"(MLB\d+)"', chunk)
        url_match = re.search(r'"url":"((?:\\.|[^"\\])*)"', chunk)
        pic_match = re.search(r'"pictures":\[\{"id":"([^"]+)"', chunk)
        title_match = re.search(
            r'"type":"title".*?"text":"((?:\\.|[^"\\])*)"',
            chunk,
            re.DOTALL,
        )
        price_match = re.search(
            r'"current_price":\{"value":([0-9.]+)',
            chunk,
        ) or re.search(r'"price":\{"value":([0-9.]+)', chunk)

        if not item_match or not url_match or not title_match:
            continue

        item_id = item_match.group(1)
        if item_id in seen_ids:
            continue

        raw_url = _decode_json_string(url_match.group(1))
        link = raw_url if raw_url.startswith("http") else f"https://{raw_url.lstrip('/')}"

        frag_match = re.search(r'"url_fragments":"((?:\\.|[^"\\])*)"', chunk)
        if frag_match:
            fragments = _decode_json_string(frag_match.group(1))
            if fragments:
                link = f"{link}{fragments if fragments.startswith('#') else '#' + fragments}"

        title = _decode_json_string(title_match.group(1)).strip()
        if not title:
            continue

        picture_id = pic_match.group(1) if pic_match else ""
        image = build_picture_url(picture_id) if picture_id else None

        price = None
        price_label = "Consulte"
        if price_match:
            try:
                price = float(price_match.group(1))
                price_label = _format_brl(price)
            except ValueError:
                pass

        seen_ids.add(item_id)
        offers.append(
            {
                "id": item_id,
                "title": title,
                "price": price,
                "currency": "BRL",
                "price_label": price_label,
                "image": image,
                "link": link,
                "fallback": False,
                "vendor": "mercadolivre",
            }
        )
        if len(offers) >= limit:
            break

    return offers


def _decode_json_string(raw: str) -> str:
    try:
        return json.loads(f'"{raw}"')
    except json.JSONDecodeError:
        return raw.replace("\\u002F", "/").replace("\\/", "/")


def _parse_loose_items(html: str, *, limit: int) -> list[dict[str, Any]]:
    """Fallback leve — pares img alt + link quando JSON polycard não está presente."""
    offers: list[dict[str, Any]] = []
    pattern = re.compile(
        r'href="(https://www\.mercadolivre\.com\.br/[^"]+/p/MLB[^"]*)"[^>]*>.*?'
        r'src="(https://http2\.mlstatic\.com/D_[^"]+)"[^>]*alt="([^"]{8,})"',
        re.DOTALL,
    )
    for match in pattern.finditer(html):
        link, image, title = match.groups()
        if "acessibilidade" in link or "addresses" in link:
            continue
        offers.append(
            {
                "id": _id_from_link(link),
                "title": title.strip(),
                "price": None,
                "currency": "BRL",
                "price_label": "Consulte",
                "image": image.replace("http://", "https://"),
                "link": link,
                "fallback": False,
                "vendor": "mercadolivre",
            }
        )
        if len(offers) >= limit:
            break
    return offers


def build_picture_url(picture_id: str) -> str:
    return ML_PICTURE_BASE.format(picture_id=picture_id)


def _id_from_link(link: str) -> str:
    match = re.search(r"(MLB\d+)", link)
    return match.group(1) if match else link


def _format_brl(price: float) -> str:
    formatted = f"{price:,.2f}"
    return f"R$ {formatted.replace(',', 'X').replace('.', ',').replace('X', '.')}"
