"""Integração Amazon Product Advertising API 5.0 (plugin Marketplace — isolado)."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

# PA-API Brasil assina em us-east-1 (independente de AWS_REGION do Bedrock/S3).
DEFAULT_REGION = "us-east-1"
DEFAULT_MARKETPLACE = "www.amazon.com.br"
DEFAULT_HOST = "webservices.amazon.com"
DEFAULT_SEARCH_INDEX = "All"
REQUEST_TIMEOUT_S = 15

# Mapeamento categoria LeAction → SearchIndex Amazon (PA-API)
AMAZON_CATEGORY_INDEX: dict[str, str] = {
    "formacao": "Books",
    "equipamentos": "Electronics",
    "software": "Software",
    "geral": "All",
}


class AmazonServiceError(Exception):
    """Falha ao consultar a Product Advertising API."""


def _env(*names: str) -> str:
    for name in names:
        value = (os.getenv(name) or "").strip()
        if value:
            return value
    return ""


class AmazonService:
    """Cliente PA-API 5.0 — retorna lista vazia se credenciais ausentes."""

    def __init__(
        self,
        *,
        access_key: str | None = None,
        secret_key: str | None = None,
        partner_tag: str | None = None,
        region: str | None = None,
        marketplace: str | None = None,
        timeout_s: int = REQUEST_TIMEOUT_S,
    ) -> None:
        self.access_key = (access_key or _env("AWS_ACCESS_KEY_ID")).strip()
        self.secret_key = (secret_key or _env("AWS_SECRET_ACCESS_KEY")).strip()
        self.partner_tag = (
            partner_tag
            or _env(
                "AMAZON_PARTNER_TAG",
                "AMAZON_ASSOCIATE_TAG",
                "AWS_ASSOCIATE_TAG",
            )
        ).strip()
        self.region = (
            region
            or _env("AMAZON_REGION", "AMAZON_PAAPI_REGION")
            or DEFAULT_REGION
        ).strip()
        self.marketplace = (
            marketplace or _env("AMAZON_MARKETPLACE") or DEFAULT_MARKETPLACE
        ).strip()
        self.host = (_env("AMAZON_PAAPI_HOST") or DEFAULT_HOST).strip()
        self.timeout_s = timeout_s

    @staticmethod
    def is_configured() -> bool:
        return bool(
            _env("AWS_ACCESS_KEY_ID")
            and _env("AWS_SECRET_ACCESS_KEY")
            and _env(
                "AMAZON_PARTNER_TAG",
                "AMAZON_ASSOCIATE_TAG",
                "AWS_ASSOCIATE_TAG",
            )
        )

    @staticmethod
    def credential_status() -> dict[str, bool]:
        return {
            "aws_keys": bool(_env("AWS_ACCESS_KEY_ID") and _env("AWS_SECRET_ACCESS_KEY")),
            "partner_tag": bool(
                _env(
                    "AMAZON_PARTNER_TAG",
                    "AMAZON_ASSOCIATE_TAG",
                    "AWS_ASSOCIATE_TAG",
                )
            ),
        }

    def search_offers(
        self,
        query: str,
        *,
        category: str | None = None,
        limit: int = 12,
    ) -> list[dict[str, Any]]:
        """Busca produtos na Amazon. Sem credenciais → []."""
        if not (self.access_key and self.secret_key and self.partner_tag):
            return []

        term = (query or "").strip()
        if not term:
            return []

        safe_limit = max(1, min(int(limit or 12), 24))
        search_index = AMAZON_CATEGORY_INDEX.get(
            _normalize_category_key(category or ""),
            DEFAULT_SEARCH_INDEX,
        )

        try:
            payload = self._search_items(term, search_index, safe_limit)
            return self._parse_search_response(payload, category=category)
        except AmazonServiceError as exc:
            logger.warning("Amazon PA-API: %s", exc)
            return []
        except Exception:
            logger.exception("Erro inesperado na Amazon PA-API")
            return []

    def _search_items(self, keywords: str, search_index: str, item_count: int) -> dict[str, Any]:
        body = {
            "Keywords": keywords,
            "SearchIndex": search_index,
            "ItemCount": item_count,
            "PartnerTag": self.partner_tag,
            "PartnerType": "Associates",
            "Marketplace": self.marketplace,
            "Resources": [
                "Images.Primary.Medium",
                "Images.Primary.Large",
                "ItemInfo.Title",
                "Offers.Listings.Price",
                "DetailPageURL",
            ],
        }
        raw_body = json.dumps(body, separators=(",", ":"))
        headers = self._signed_headers("SearchItems", raw_body)
        url = f"https://{self.host}/paapi5/searchitems"

        request = urllib.request.Request(
            url,
            data=raw_body.encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_s) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:400]
            raise AmazonServiceError(f"HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise AmazonServiceError("Não foi possível contactar a Amazon PA-API") from exc

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise AmazonServiceError("Resposta JSON inválida da Amazon") from exc

        if not isinstance(data, dict):
            raise AmazonServiceError("Formato inesperado na resposta Amazon")
        if data.get("Errors"):
            msg = data["Errors"][0].get("Message", "Erro PA-API") if data["Errors"] else "Erro PA-API"
            raise AmazonServiceError(str(msg))
        return data

    def _signed_headers(self, operation: str, payload: str) -> dict[str, str]:
        """Assinatura AWS SigV4 para ProductAdvertisingAPI."""
        now = datetime.now(timezone.utc)
        amz_date = now.strftime("%Y%m%dT%H%M%SZ")
        date_stamp = now.strftime("%Y%m%d")
        service = "ProductAdvertisingAPI"
        target = f"com.amazon.paapi5.v1.ProductAdvertisingAPIv1.{operation}"

        canonical_uri = "/paapi5/searchitems"
        payload_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        canonical_headers = (
            f"content-encoding:amz-1.0\n"
            f"content-type:application/json; charset=utf-8\n"
            f"host:{self.host}\n"
            f"x-amz-date:{amz_date}\n"
            f"x-amz-target:{target}\n"
        )
        signed_headers = "content-encoding;content-type;host;x-amz-date;x-amz-target"
        canonical_request = (
            "POST\n"
            f"{canonical_uri}\n"
            "\n"
            f"{canonical_headers}\n"
            f"{signed_headers}\n"
            f"{payload_hash}"
        )

        credential_scope = f"{date_stamp}/{self.region}/{service}/aws4_request"
        string_to_sign = (
            "AWS4-HMAC-SHA256\n"
            f"{amz_date}\n"
            f"{credential_scope}\n"
            f"{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}"
        )

        signing_key = _derive_signing_key(self.secret_key, date_stamp, self.region, service)
        signature = hmac.new(
            signing_key, string_to_sign.encode("utf-8"), hashlib.sha256
        ).hexdigest()

        authorization = (
            f"AWS4-HMAC-SHA256 Credential={self.access_key}/{credential_scope}, "
            f"SignedHeaders={signed_headers}, Signature={signature}"
        )

        return {
            "Content-Encoding": "amz-1.0",
            "Content-Type": "application/json; charset=utf-8",
            "Host": self.host,
            "X-Amz-Date": amz_date,
            "X-Amz-Target": target,
            "Authorization": authorization,
        }

    def _parse_search_response(
        self,
        payload: dict[str, Any],
        *,
        category: str | None,
    ) -> list[dict[str, Any]]:
        block = payload.get("SearchResult") or payload.get("searchResult") or {}
        items = block.get("Items") or block.get("items") or []
        if not isinstance(items, list):
            return []

        cat_key = _normalize_category_key(category or "") or "geral"
        offers: list[dict[str, Any]] = []

        for item in items:
            if not isinstance(item, dict):
                continue
            formatted = self._format_item(item, category=cat_key)
            if formatted:
                offers.append(formatted)
        return offers

    def _format_item(self, item: dict[str, Any], *, category: str) -> dict[str, Any] | None:
        asin = str(item.get("ASIN") or item.get("asin") or "").strip()
        if not asin:
            return None

        title_block = item.get("ItemInfo") or item.get("itemInfo") or {}
        title_info = title_block.get("Title") or title_block.get("title") or {}
        title = str(title_info.get("DisplayValue") or title_info.get("displayValue") or "").strip()
        if not title:
            return None

        link = str(item.get("DetailPageURL") or item.get("detailPageURL") or "").strip()
        if not link:
            link = f"https://{self.marketplace}/dp/{asin}"

        images = item.get("Images") or item.get("images") or {}
        primary = images.get("Primary") or images.get("primary") or {}
        medium = primary.get("Medium") or primary.get("medium") or {}
        large = primary.get("Large") or primary.get("large") or {}
        image = (
            str(medium.get("URL") or medium.get("url") or "").strip()
            or str(large.get("URL") or large.get("url") or "").strip()
            or None
        )

        price, currency, price_label = self._extract_price(item)

        return {
            "id": f"amazon-{asin}",
            "title": title,
            "price": price,
            "currency": currency,
            "price_label": price_label,
            "image": image,
            "link": link,
            "vendor": "amazon",
            "category": category,
            "fallback": False,
        }

    @staticmethod
    def _extract_price(item: dict[str, Any]) -> tuple[float | None, str, str]:
        offers = item.get("Offers") or item.get("offers") or {}
        listings = offers.get("Listings") or offers.get("listings") or []
        if isinstance(listings, list) and listings:
            listing = listings[0] if isinstance(listings[0], dict) else {}
            price_block = listing.get("Price") or listing.get("price") or {}
            amount = price_block.get("Amount") or price_block.get("amount")
            currency = str(
                price_block.get("Currency") or price_block.get("currency") or "BRL"
            ).strip()
            try:
                value = float(amount)
                return value, currency, _format_price_label(value, currency)
            except (TypeError, ValueError):
                pass
        return None, "BRL", "Consulte"


def _normalize_category_key(raw: str) -> str:
    key = raw.strip().lower()
    aliases = {
        "formação": "formacao",
        "education": "formacao",
        "equipamento": "equipamentos",
        "infra": "equipamentos",
        "infraestrutura": "equipamentos",
        "apps": "software",
        "digital": "geral",
    }
    return aliases.get(key, key)


def _format_price_label(price: float, currency: str) -> str:
    if currency == "BRL":
        formatted = f"{price:,.2f}"
        return f"R$ {formatted.replace(',', 'X').replace('.', ',').replace('X', '.')}"
    return f"{currency} {price:.2f}"


def _derive_signing_key(secret: str, date_stamp: str, region: str, service: str) -> bytes:
    def _sign(key: bytes, msg: str) -> bytes:
        return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()

    k_date = _sign(("AWS4" + secret).encode("utf-8"), date_stamp)
    k_region = _sign(k_date, region)
    k_service = _sign(k_region, service)
    return _sign(k_service, "aws4_request")
