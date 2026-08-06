"""Integração desacoplada com a API do Mercado Livre (plugin Marketplace)."""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from app.services.ml_oauth_service import ML_API_BASE_URL, get_valid_access_token

logger = logging.getLogger(__name__)

DEFAULT_SITE = "MLB"
DEFAULT_QUERY = "transformação digital maturidade liderança educação corporativa"
DEFAULT_LIMIT = 12
MAX_LIMIT = 24
# Antes forçava 20 resultados e enriquecia listing 1-a-1 (N+1). Agora respeita o limit.
API_SEARCH_MIN_LIMIT = int(os.getenv("ML_API_SEARCH_MIN_LIMIT", "6"))
# 3s era insuficiente — /products/search costuma levar 4–6s e a vitrine caía em fallback sem foto.
REQUEST_TIMEOUT_S = float(os.getenv("ML_REQUEST_TIMEOUT_S", "12"))
# Enrich /products/{id}/items costuma 404 e só atrasa; catálogo já traz picture.
LISTING_ENRICH_MAX = int(os.getenv("ML_LISTING_ENRICH_MAX", "0"))
LISTING_ENRICH_WORKERS = int(os.getenv("ML_LISTING_ENRICH_WORKERS", "4"))

BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

PLATFORM_SEARCH_TERMS = (
    "transformação digital",
    "maturidade digital",
    "liderança educacional",
    "gestão educacional",
    "inovação corporativa",
)


class MercadoLivreServiceError(Exception):
    """Falha ao consultar ofertas do Mercado Livre."""


class MercadoLivreService:
    """Cliente OAuth — busca via /products/search (sites/search retorna 403 para apps atuais)."""

    # API REST global — domínio mercadolibre.com (links de produto usam mercadolivre.com.br).
    BASE_URL = ML_API_BASE_URL

    def __init__(
        self,
        *,
        site_id: str | None = None,
        default_query: str | None = None,
        timeout_s: float = REQUEST_TIMEOUT_S,
    ) -> None:
        self.site_id = (site_id or os.getenv("ML_SITE_ID") or DEFAULT_SITE).strip()
        self.default_query = (
            default_query or os.getenv("ML_DEFAULT_SEARCH_QUERY") or DEFAULT_QUERY
        ).strip()
        self.timeout_s = float(timeout_s)

    def search_offers(
        self,
        query: str | None = None,
        *,
        limit: int = DEFAULT_LIMIT,
    ) -> list[dict[str, Any]]:
        return self.search_offers_with_meta(query, limit=limit)["offers"]

    def search_offers_with_meta(
        self,
        query: str | None = None,
        *,
        limit: int = DEFAULT_LIMIT,
    ) -> dict[str, Any]:
        term = (query or self.default_query).strip() or DEFAULT_QUERY
        safe_limit = max(1, min(int(limit or DEFAULT_LIMIT), MAX_LIMIT))

        access_token = get_valid_access_token()
        if not access_token:
            logger.warning(
                "Mercado Livre OAuth indisponível (query=%r) — retornando vazio para fallback B2B",
                term,
            )
            return {
                "offers": [],
                "source": "unavailable",
                "live": False,
                "notice": (
                    "Mercado Livre não autenticado. Configure ML_APP_ID + ML_SECRET_KEY e acesse "
                    "/api/marketplace/ml/login para autorizar a busca live."
                ),
            }

        try:
            offers = self._search_live(term, safe_limit, access_token)
            if offers:
                return {
                    "offers": offers,
                    "source": "mercadolivre",
                    "live": True,
                    "notice": None,
                }
            logger.info("Busca OAuth ML sem resultados — query=%r", term)
            return {
                "offers": [],
                "source": "mercadolivre",
                "live": True,
                "notice": None,
            }
        except MercadoLivreServiceError as exc:
            logger.error("Busca OAuth ML falhou (%s) — query=%r", exc, term)
            return {
                "offers": [],
                "source": "unavailable",
                "live": False,
                "notice": str(exc),
            }

    def _search_live(
        self,
        term: str,
        limit: int,
        access_token: str,
    ) -> list[dict[str, Any]]:
        api_limit = max(limit, min(max(API_SEARCH_MIN_LIMIT, limit), 50))
        params = urllib.parse.urlencode(
            {
                "site_id": self.site_id,
                "status": "active",
                "q": term,
                "limit": api_limit,
            }
        )
        url = f"{self.BASE_URL}/products/search?{params}"
        payload = self._fetch_json(url, access_token)
        results = payload.get("results") if isinstance(payload, dict) else None
        if not isinstance(results, list):
            return []

        # Formata catálogo sem N+1; enriquecer listing só nos primeiros N (paralelo).
        candidates: list[dict[str, Any]] = []
        for product in results:
            if not isinstance(product, dict):
                continue
            base = self._format_catalog_product_base(product)
            if base:
                candidates.append(base)
            if len(candidates) >= limit:
                break

        enrich_n = max(0, min(LISTING_ENRICH_MAX, len(candidates)))
        if enrich_n <= 0:
            return candidates[:limit]

        def _enrich(idx_offer: tuple[int, dict[str, Any]]) -> tuple[int, dict[str, Any]]:
            idx, offer = idx_offer
            listing = self._fetch_best_listing(str(offer["id"]), access_token)
            if not listing:
                return idx, offer
            enriched = dict(offer)
            try:
                enriched["price"] = (
                    float(listing.get("price")) if listing.get("price") is not None else None
                )
            except (TypeError, ValueError):
                enriched["price"] = None
            enriched["currency"] = str(listing.get("currency_id") or enriched["currency"]).strip()
            item_id = str(listing.get("item_id") or "").strip()
            if item_id:
                enriched["link"] = self._item_link(item_id)
            enriched["price_label"] = self._format_price(
                enriched.get("price"), str(enriched.get("currency") or "BRL")
            )
            return idx, enriched

        workers = max(1, min(LISTING_ENRICH_WORKERS, enrich_n))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [
                pool.submit(_enrich, (i, candidates[i]))
                for i in range(enrich_n)
            ]
            for future in as_completed(futures):
                try:
                    idx, enriched = future.result()
                    candidates[idx] = enriched
                except Exception as exc:
                    logger.debug("Listing enrich falhou: %s", exc)

        return candidates[:limit]

    def _format_catalog_product_base(self, product: dict[str, Any]) -> dict[str, Any] | None:
        product_id = str(product.get("id") or "").strip()
        title = str(product.get("name") or "").strip()
        if not product_id or not title:
            return None
        currency = "BRL"
        return {
            "id": product_id,
            "title": title,
            "price": None,
            "currency": currency,
            "price_label": self._format_price(None, currency),
            "image": self._picture_from_product(product),
            "link": self._catalog_link(product_id),
            "fallback": False,
        }

    def _format_catalog_product(
        self,
        product: dict[str, Any],
        access_token: str,
    ) -> dict[str, Any] | None:
        # Mantido para compatibilidade de testes/chamadores legados.
        base = self._format_catalog_product_base(product)
        if not base:
            return None
        listing = self._fetch_best_listing(str(base["id"]), access_token)
        if not listing:
            return base
        try:
            base["price"] = (
                float(listing.get("price")) if listing.get("price") is not None else None
            )
        except (TypeError, ValueError):
            base["price"] = None
        base["currency"] = str(listing.get("currency_id") or base["currency"]).strip()
        item_id = str(listing.get("item_id") or "").strip()
        if item_id:
            base["link"] = self._item_link(item_id)
        base["price_label"] = self._format_price(base.get("price"), str(base.get("currency") or "BRL"))
        return base

    def _fetch_best_listing(
        self,
        product_id: str,
        access_token: str,
    ) -> dict[str, Any] | None:
        url = f"{self.BASE_URL}/products/{urllib.parse.quote(product_id)}/items?limit=1"
        try:
            payload = self._fetch_json(url, access_token)
        except MercadoLivreServiceError:
            return None
        results = payload.get("results") if isinstance(payload, dict) else None
        if not isinstance(results, list) or not results:
            return None
        first = results[0]
        return first if isinstance(first, dict) else None

    @staticmethod
    def platform_context_terms() -> list[str]:
        return list(PLATFORM_SEARCH_TERMS)

    def _fetch_json(self, url: str, access_token: str) -> dict[str, Any]:
        request = urllib.request.Request(
            url,
            headers={
                "Accept": "application/json",
                "Accept-Language": "pt-BR,pt;q=0.9",
                "Authorization": f"Bearer {access_token}",
                "User-Agent": BROWSER_USER_AGENT,
            },
            method="GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_s) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            logger.error("Erro ao consultar Mercado Livre: HTTP %s — %s", exc.code, url)
            if exc.code in (401, 403):
                raise MercadoLivreServiceError(
                    f"Mercado Livre retornou HTTP {exc.code} — token inválido ou sem permissão"
                ) from exc
            raise MercadoLivreServiceError(
                f"Mercado Livre retornou HTTP {exc.code}"
            ) from exc
        except urllib.error.URLError as exc:
            raise MercadoLivreServiceError(
                "Não foi possível contactar a API do Mercado Livre"
            ) from exc

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise MercadoLivreServiceError("Resposta inválida do Mercado Livre") from exc

        if not isinstance(data, dict):
            raise MercadoLivreServiceError("Formato inesperado na resposta do Mercado Livre")
        return data

    @staticmethod
    def _picture_from_product(product: dict[str, Any]) -> str | None:
        pictures = product.get("pictures")
        if not isinstance(pictures, list) or not pictures:
            return None
        first = pictures[0]
        if not isinstance(first, dict):
            return None
        return MercadoLivreService._normalize_image_url(
            str(first.get("url") or "").strip() or None
        )

    @staticmethod
    def _catalog_link(product_id: str) -> str:
        return f"https://www.mercadolivre.com.br/p/{product_id}"

    @staticmethod
    def _item_link(item_id: str) -> str:
        if len(item_id) > 3 and item_id[:3].isalpha():
            return f"https://www.mercadolivre.com.br/{item_id[:3]}-{item_id[3:]}"
        return f"https://www.mercadolivre.com.br/p/{item_id}"

    @staticmethod
    def _normalize_image_url(url: str | None) -> str | None:
        if not url:
            return None
        normalized = url.replace("http://", "https://")
        normalized = normalized.replace("-I.jpg", "-O.jpg").replace("-I.webp", "-O.webp")
        return normalized

    @staticmethod
    def _format_price(price: float | None, currency: str) -> str:
        if price is None:
            return "Consulte"
        if currency == "BRL":
            formatted = f"{price:,.2f}"
            return f"R$ {formatted.replace(',', 'X').replace('.', ',').replace('X', '.')}"
        return f"{currency} {price:.2f}"
