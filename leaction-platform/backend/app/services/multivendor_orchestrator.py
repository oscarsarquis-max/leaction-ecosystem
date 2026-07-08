"""Orquestrador Federated Search — agrega Mercado Livre + Amazon por categoria."""

from __future__ import annotations

import logging
import random
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from app.services.amazon_service import AmazonService
from app.services.curation_repository import CurationRepository, CurationRules
from app.services.mercadolivre_fallback import get_fallback_offers
from app.services.mercadolivre_service import MercadoLivreService, MercadoLivreServiceError

logger = logging.getLogger(__name__)

DEFAULT_LIMIT = 12
MAX_LIMIT = 24

CATEGORY_PROFILES: dict[str, dict[str, str]] = {
    "formacao": {
        "label": "Formação e Conteúdo Executivo",
        "default_query": "livros liderança transformação digital curso",
        "mercadolivre": "livros liderança transformação digital",
        "amazon": "livros liderança transformação digital educação",
    },
    "equipamentos": {
        "label": "Infraestrutura e Conectividade",
        "default_query": "switch roteador wifi automação rede corporativa",
        "mercadolivre": "equipamentos automação rede switch roteador",
        "amazon": "network switch router access point enterprise",
    },
    "software": {
        "label": "Software e Ferramentas Digitais",
        "default_query": "software gestão educacional LMS digital",
        "mercadolivre": "software gestão digital corporativo",
        "amazon": "software business management digital tools",
    },
    "geral": {
        "label": "Transformação Digital",
        "default_query": "transformação digital maturidade liderança",
        "mercadolivre": "transformação digital maturidade liderança",
        "amazon": "digital transformation leadership technology",
    },
}

CATEGORY_ALIASES: dict[str, str] = {
    "formação": "formacao",
    "education": "formacao",
    "biblioteca": "formacao",
    "executiva": "formacao",
    "equipamento": "equipamentos",
    "infra": "equipamentos",
    "infraestrutura": "equipamentos",
    "conectividade": "equipamentos",
    "apps": "software",
    "ferramentas": "software",
}

CATEGORY_FALLBACK_QUERIES: dict[str, str] = {
    "formacao": "livro liderança gestão",
    "equipamentos": "rede switch automação infra",
    "software": "software licença corporativo",
    "geral": "transformação digital maturidade",
}


class MultivendorOrchestrator:
    """Agrega buscas multivendor com mapeamento por categoria LeAction."""

    def __init__(
        self,
        *,
        mercadolivre: MercadoLivreService | None = None,
        amazon: AmazonService | None = None,
    ) -> None:
        self.mercadolivre = mercadolivre or MercadoLivreService()
        self.amazon = amazon or AmazonService()

    @staticmethod
    def list_categories() -> list[dict[str, str]]:
        return [
            {"id": key, "label": profile["label"]}
            for key, profile in CATEGORY_PROFILES.items()
            if key != "geral"
        ]

    def search_all_vendors(
        self,
        query: str | None = None,
        *,
        category: str | None = None,
        limit: int = DEFAULT_LIMIT,
    ) -> dict[str, Any]:
        safe_limit = max(1, min(int(limit or DEFAULT_LIMIT), MAX_LIMIT))
        cat_key = resolve_category_key(category)
        profile = CATEGORY_PROFILES.get(cat_key, CATEGORY_PROFILES["geral"])
        curation = CurationRepository.load_for_category(cat_key)

        user_query = (query or "").strip()
        amazon_query = user_query or profile["amazon"]
        has_curated_category = curation.has_curated_search

        if has_curated_category:
            curated_terms = _curated_ml_search_terms(curation.search_terms)
            effective_query = curated_terms[0] if curated_terms else profile["default_query"]
        else:
            effective_query = user_query or profile["default_query"]

        amazon_configured = AmazonService.is_configured()
        if amazon_configured:
            ml_limit = max(1, (safe_limit + 1) // 2)
            amazon_limit = max(1, safe_limit // 2)
        else:
            ml_limit = safe_limit
            amazon_limit = 0

        ml_offers: list[dict[str, Any]] = []
        amazon_offers: list[dict[str, Any]] = []
        vendor_errors: list[str] = []
        used_fallback = False

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = {
                pool.submit(
                    self._search_mercadolivre,
                    cat_key,
                    ml_limit,
                    curation,
                    user_query=user_query,
                ): "mercadolivre",
            }
            if amazon_limit > 0:
                futures[
                    pool.submit(
                        self._search_amazon,
                        amazon_query,
                        cat_key,
                        amazon_limit,
                    )
                ] = "amazon"
            for future in as_completed(futures):
                vendor_name = futures[future]
                try:
                    result = future.result()
                    if vendor_name == "mercadolivre":
                        ml_offers = _filter_curated_titles(result, curation)[:safe_limit]
                    else:
                        amazon_offers = result
                except Exception as exc:
                    logger.warning("Vendor %s falhou: %s", vendor_name, exc)
                    vendor_errors.append(f"{vendor_name}: {exc}")

        if not ml_offers:
            ml_offers = _fallback_offers_for_category(
                cat_key,
                user_query or effective_query,
                safe_limit,
            )
            used_fallback = bool(ml_offers)

        merged = _interleave_offers(ml_offers, amazon_offers, limit=safe_limit)

        sources = []
        if ml_offers:
            sources.append("mercadolivre")
        if amazon_offers:
            sources.append("amazon")

        notice = None
        if not merged:
            notice = _build_empty_notice(
                ml_configured=True,
                amazon_configured=AmazonService.is_configured(),
                vendor_errors=vendor_errors,
            )
        elif used_fallback:
            notice = (
                "Vitrine curada LeAction — a busca live do Mercado Livre não retornou "
                "produtos relevantes para esta categoria."
            )
        elif not AmazonService.is_configured():
            notice = (
                "Amazon não configurada — exibindo apenas Mercado Livre. "
                "Defina AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY e AMAZON_PARTNER_TAG."
            )

        return {
            "status": "ok",
            "source": "federated" if len(sources) > 1 else (sources[0] if sources else "unavailable"),
            "sources": sources,
            "live": bool(merged) and not used_fallback,
            "category": cat_key,
            "category_label": profile["label"],
            "query": effective_query,
            "count": len(merged),
            "offers": merged,
            "notice": notice,
            "vendors": {
                "mercadolivre": {
                    "count": len(ml_offers),
                    "active": bool(ml_offers),
                    "fallback": used_fallback,
                },
                "amazon": {
                    "count": len(amazon_offers),
                    "configured": AmazonService.is_configured(),
                    "active": bool(amazon_offers),
                },
            },
        }

    def _search_mercadolivre(
        self,
        category: str,
        limit: int,
        curation: CurationRules,
        *,
        user_query: str = "",
    ) -> list[dict[str, Any]]:
        if curation.has_curated_search:
            search_terms = _curated_ml_search_terms(curation.search_terms)
            if user_query:
                search_terms = [user_query] + [
                    term for term in search_terms if _fold_text(term) != _fold_text(user_query)
                ]
        else:
            profile = CATEGORY_PROFILES.get(category, CATEGORY_PROFILES["geral"])
            fallback = user_query or profile["mercadolivre"]
            search_terms = [fallback]

        per_term_limit = max(8, limit * 3)
        seen_links: set[str] = set()
        collected: list[dict[str, Any]] = []

        for term in search_terms:
            if len(collected) >= limit:
                break
            try:
                result = self.mercadolivre.search_offers_with_meta(
                    term,
                    limit=per_term_limit,
                )
            except MercadoLivreServiceError as exc:
                logger.warning("Mercado Livre (termo=%r): %s", term, exc)
                continue

            for offer in result.get("offers") or []:
                if len(collected) >= limit:
                    break
                title = str(offer.get("title") or "")
                if not _passes_curation_filters(title, curation, strict_positive=True):
                    continue
                normalized = _normalize_mercadolivre_offer(offer, category=category)
                link = str(normalized.get("link") or "")
                if link and link in seen_links:
                    continue
                if link:
                    seen_links.add(link)
                collected.append(normalized)

            if not curation.has_curated_search and not collected:
                for offer in result.get("offers") or []:
                    if len(collected) >= limit:
                        break
                    title = str(offer.get("title") or "")
                    if not _passes_curation_filters(title, curation, strict_positive=False):
                        continue
                    normalized = _normalize_mercadolivre_offer(offer, category=category)
                    link = str(normalized.get("link") or "")
                    if link and link in seen_links:
                        continue
                    if link:
                        seen_links.add(link)
                    collected.append(normalized)

        if len(collected) < limit and curation.has_curated_search:
            for term in search_terms:
                if len(collected) >= limit:
                    break
                try:
                    result = self.mercadolivre.search_offers_with_meta(
                        term,
                        limit=per_term_limit,
                    )
                except MercadoLivreServiceError as exc:
                    logger.warning("Mercado Livre relaxado (termo=%r): %s", term, exc)
                    continue

                for offer in result.get("offers") or []:
                    if len(collected) >= limit:
                        break
                    title = str(offer.get("title") or "")
                    if not _passes_curation_filters(title, curation, strict_positive=False):
                        continue
                    normalized = _normalize_mercadolivre_offer(offer, category=category)
                    link = str(normalized.get("link") or "")
                    if link and link in seen_links:
                        continue
                    if link:
                        seen_links.add(link)
                    collected.append(normalized)

        return collected[:limit]

    def _search_amazon(
        self,
        query: str,
        category: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        return self.amazon.search_offers(query, category=category, limit=limit)


def resolve_category_key(raw: str | None) -> str:
    key = (raw or "").strip().lower()
    if not key:
        return "geral"
    return CATEGORY_ALIASES.get(key, key if key in CATEGORY_PROFILES else "geral")


def _fold_text(value: str) -> str:
    lowered = value.lower()
    nfkd = unicodedata.normalize("NFKD", lowered)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _title_blocked(title: str, negative_keywords: list[str]) -> bool:
    if not negative_keywords:
        return False
    folded = _fold_text(title)
    return any(_fold_text(keyword) in folded for keyword in negative_keywords)


def _title_allowed(title: str, positive_keywords: list[str]) -> bool:
    if not positive_keywords:
        return True
    folded = _fold_text(title)
    return any(_fold_text(keyword) in folded for keyword in positive_keywords)


def _passes_curation_filters(
    title: str,
    curation: CurationRules,
    *,
    strict_positive: bool,
) -> bool:
    if _title_blocked(title, curation.negative_keywords):
        return False
    if strict_positive and curation.positive_keywords:
        return _title_allowed(title, curation.positive_keywords)
    return True


def _curated_ml_search_terms(search_terms: list[str]) -> list[str]:
    terms = list(search_terms)
    random.shuffle(terms)
    return terms


def _filter_curated_titles(
    offers: list[dict[str, Any]],
    curation: CurationRules,
) -> list[dict[str, Any]]:
    filtered = [
        offer
        for offer in offers
        if _passes_curation_filters(str(offer.get("title") or ""), curation, strict_positive=True)
    ]
    if filtered:
        return filtered
    return [
        offer
        for offer in offers
        if _passes_curation_filters(str(offer.get("title") or ""), curation, strict_positive=False)
    ]


def _fallback_offers_for_category(
    category: str,
    query: str,
    limit: int,
) -> list[dict[str, Any]]:
    if category in CATEGORY_FALLBACK_QUERIES:
        fallback_query = CATEGORY_FALLBACK_QUERIES[category]
    else:
        fallback_query = query or CATEGORY_FALLBACK_QUERIES.get("geral", "digital")
    raw = get_fallback_offers(fallback_query, limit=limit)
    offers: list[dict[str, Any]] = []
    for offer in raw:
        normalized = _normalize_mercadolivre_offer(offer, category=category)
        normalized["fallback"] = True
        offers.append(normalized)
    return offers


def _normalize_mercadolivre_offer(offer: dict[str, Any], *, category: str) -> dict[str, Any]:
    item_id = str(offer.get("id") or "")
    return {
        "id": item_id if item_id.startswith("ML") else f"ml-{item_id}",
        "title": str(offer.get("title") or "").strip(),
        "price": offer.get("price"),
        "currency": offer.get("currency") or "BRL",
        "price_label": offer.get("price_label") or "Consulte",
        "image": offer.get("image"),
        "link": offer.get("link"),
        "vendor": "mercadolivre",
        "category": category,
        "fallback": bool(offer.get("fallback", False)),
    }


def _interleave_offers(
    first: list[dict[str, Any]],
    second: list[dict[str, Any]],
    *,
    limit: int,
) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen_links: set[str] = set()
    max_len = max(len(first), len(second))

    for i in range(max_len):
        for bucket in (first, second):
            if i < len(bucket):
                offer = bucket[i]
                link = str(offer.get("link") or "")
                if link and link in seen_links:
                    continue
                if link:
                    seen_links.add(link)
                merged.append(offer)
                if len(merged) >= limit:
                    return merged
    return merged


def _build_empty_notice(
    *,
    ml_configured: bool,
    amazon_configured: bool,
    vendor_errors: list[str],
) -> str:
    parts = ["Nenhuma oferta encontrada nos vendors."]
    if not amazon_configured:
        parts.append(
            "Amazon: configure AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY e AMAZON_PARTNER_TAG."
        )
    if vendor_errors:
        parts.append("Detalhes: " + "; ".join(vendor_errors[:2]))
    return " ".join(parts)
