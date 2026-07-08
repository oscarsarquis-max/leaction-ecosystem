"""Pesquisa web para o Estúdio de Criação — wrapper sobre ddgs com fallbacks."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

try:
    from ddgs import DDGS
except ImportError:
    from duckduckgo_search import DDGS  # noqa: F401 — legado

SECTOR_ALIASES: dict[str, str] = {
    "telecom": "telecomunicações",
    "telecoms": "telecomunicações",
    "telecomunicacao": "telecomunicações",
    "telecomunicacoes": "telecomunicações",
    "telco": "telecomunicações",
    "educacao": "educação",
    "education": "educação",
    "edu": "educação",
    "ensino": "educação",
    "saude": "saúde",
    "health": "saúde",
    "healthcare": "saúde",
    "varejo": "varejo",
    "retail": "varejo",
    "industria": "indústria",
    "manufatura": "indústria",
}

FALLBACK_SNIPPETS: dict[str, list[dict[str, str]]] = {
    "telecomunicações": [
        {
            "query": "fallback",
            "title": "TM Forum — Digital Maturity Model",
            "url": "https://www.tmforum.org/",
            "snippet": (
                "Modelos de maturidade digital para operadoras: OSS/BSS, experiência "
                "do cliente, automação de rede e monetização de dados."
            ),
        },
        {
            "query": "fallback",
            "title": "GSMA — Industry Transformation",
            "url": "https://www.gsma.com/",
            "snippet": (
                "Transformação digital em telecom: 5G, edge computing, plataformas "
                "digitais e novos modelos de negócio para operadoras."
            ),
        },
        {
            "query": "fallback",
            "title": "ITU — Digital Transformation",
            "url": "https://www.itu.int/",
            "snippet": (
                "Governança, infraestrutura crítica e políticas de conectividade "
                "para o setor de telecomunicações global."
            ),
        },
    ],
}


def normalize_sector_name(sector_name: str) -> str:
    key = (sector_name or "").strip().lower()
    return SECTOR_ALIASES.get(key, sector_name.strip())


def build_search_queries(sector_name: str) -> list[str]:
    sector = normalize_sector_name(sector_name)
    return [
        f"maturidade digital {sector}",
        f"transformação digital {sector}",
        f"boas práticas governança TI {sector}",
        f"OSS BSS plataformas digitais {sector}",
        f"{sector} digital transformation maturity",
        f"{sector} industry operational excellence technology",
    ]


def _normalize_hit(hit: dict[str, Any], query: str) -> dict[str, str] | None:
    url = (hit.get("href") or hit.get("link") or hit.get("url") or "").strip()
    if not url:
        return None

    snippet = (hit.get("body") or hit.get("snippet") or "").strip()
    title = (hit.get("title") or hit.get("source") or "Referência").strip()

    return {
        "query": query,
        "title": title[:200],
        "url": url,
        "snippet": snippet[:600],
    }


def search_sector_references(sector_name: str, *, max_results: int = 12) -> list[dict[str, str]]:
    """Busca referências web combinando text + news; usa fallback setorial se necessário."""
    sector = normalize_sector_name(sector_name)
    queries = build_search_queries(sector_name)
    collected: list[dict[str, str]] = []
    seen_urls: set[str] = set()

    try:
        with DDGS() as ddgs:
            for query in queries:
                if len(collected) >= max_results:
                    break

                for method_name in ("text", "news"):
                    try:
                        method = getattr(ddgs, method_name)
                        hits = method(query, max_results=5)
                    except TypeError:
                        try:
                            hits = method(keywords=query, max_results=5)
                        except Exception:
                            continue
                    except Exception as exc:
                        logger.warning("Busca %s falhou para '%s': %s", method_name, query, exc)
                        continue

                    for hit in hits or []:
                        normalized = _normalize_hit(hit, query)
                        if not normalized or normalized["url"] in seen_urls:
                            continue
                        seen_urls.add(normalized["url"])
                        collected.append(normalized)
                        if len(collected) >= max_results:
                            break
    except Exception as exc:
        logger.error("Motor de busca indisponível: %s", exc)

    if not collected:
        fallback_key = sector.lower()
        for key, snippets in FALLBACK_SNIPPETS.items():
            if key in fallback_key or fallback_key in key:
                collected.extend(snippets)
                break

    return collected[:max_results]
