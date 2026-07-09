"""Motor de recomendação contextual — overlap SQL de tags (sem IA em runtime).

Fluxo:
  1) Sprints ativas do PanelDX trazem `tags` já persistidas na criação (IA).
  2) Produtos do ActionHub (`marketplace_products.tags`) fazem interseção (&&).
  3) Prateleiras genéricas continuam via MultivendorOrchestrator (live/fallback).
"""

from __future__ import annotations

import logging
import os
from typing import Any

import requests
from sqlalchemy import text

from app.services.multivendor_orchestrator import MultivendorOrchestrator

logger = logging.getLogger(__name__)

ACTIVE_SPRINT_STATUSES = frozenset(
    {
        "em_andamento",
        "ativa",
        "planejada_backlog",
        "planejada",
        "em_analise",
        "em analise",
    }
)

CANONICAL_TAGS = frozenset({"formacao", "equipamentos", "software"})


def _paneldx_base_url() -> str:
    return (
        os.getenv("PANELDX_API_INTERNAL_URL")
        or os.getenv("PANELDX_FLASK_URL")
        or "http://127.0.0.1:5002"
    ).rstrip("/")


def _normalize_tags(raw: Any) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        raw = [raw]
    if not isinstance(raw, (list, tuple)):
        return []
    out: list[str] = []
    seen: set[str] = set()
    for item in raw:
        tag = str(item or "").strip().lower().replace(" ", "_").replace("-", "_")
        aliases = {
            "formação": "formacao",
            "formacao": "formacao",
            "equipamento": "equipamentos",
            "equipamentos": "equipamentos",
            "infra": "equipamentos",
            "infraestrutura": "equipamentos",
            "software": "software",
            "sistemas": "software",
        }
        tag = aliases.get(tag, tag)
        if tag in CANONICAL_TAGS and tag not in seen:
            seen.add(tag)
            out.append(tag)
    return out


def fetch_panel_dx_sprints(*, id_matu: int | None = None, id_clie: int | None = None) -> list[dict]:
    """Busca sprints ativas/priorizadas no PanelDX (tags já persistidas)."""
    base = _paneldx_base_url()

    if id_clie and not id_matu:
        try:
            resp = requests.get(
                f"{base}/api/sprints/blocos-pipeline",
                params={"id_clie": id_clie},
                timeout=10,
            )
            if resp.ok:
                data = resp.json() if resp.content else {}
                items = data.get("items") if isinstance(data, dict) else None
                if isinstance(items, list):
                    mapped: list[dict] = []
                    for item in items:
                        if not isinstance(item, dict):
                            continue
                        mapped.append(
                            {
                                "id_sprn": item.get("id_sprn"),
                                "name_sprn": item.get("nome") or item.get("name_sprn"),
                                "desc_sprn": item.get("desc") or item.get("desc_sprn"),
                                "stat_sprn": item.get("stat_sprn") or "em_andamento",
                                "name_bloc_text": item.get("bloco_nome") or item.get("block_key"),
                                "tags": _normalize_tags(item.get("tags")),
                            }
                        )
                    if mapped:
                        return mapped
        except Exception as exc:
            logger.warning("Falha pipeline sprints id_clie=%s: %s", id_clie, exc)

    matu = id_matu
    if not matu:
        return []

    try:
        resp = requests.get(
            f"{base}/api/ctdi_sprn",
            params={"id_matu": matu},
            timeout=10,
        )
        resp.raise_for_status()
        rows = resp.json()
        if not isinstance(rows, list):
            return []
    except Exception as exc:
        logger.warning("Falha ao buscar sprints PanelDX id_matu=%s: %s", matu, exc)
        return []

    active: list[dict] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        status = str(row.get("stat_sprn") or "").strip().lower().replace(" ", "_")
        if status in ACTIVE_SPRINT_STATUSES or status.replace("_", " ") in ACTIVE_SPRINT_STATUSES:
            row = dict(row)
            row["tags"] = _normalize_tags(row.get("tags"))
            active.append(row)
    return active


def collect_sprint_tags(sprints: list[dict]) -> list[str]:
    """Une tags persistidas das sprints ativas (ordem estável)."""
    ordered: list[str] = []
    seen: set[str] = set()
    for sprint in sprints:
        for tag in _normalize_tags(sprint.get("tags")):
            if tag not in seen:
                seen.add(tag)
                ordered.append(tag)
    return ordered


def query_products_by_tag_overlap(tags: list[str], *, limit: int = 8) -> list[dict]:
    """
    SQL puro: produtos cujo array `tags` faz interseção com as tags das sprints.
      WHERE tags && :sprint_tags
    """
    if not tags:
        return []

    from app.database import DB_AVAILABLE, db
    from app.database.models import MarketplaceProduct

    if not DB_AVAILABLE or db is None or MarketplaceProduct is None:
        logger.warning("DB indisponível — recomendados contextuais vazios")
        return []

    safe_limit = max(1, min(limit, 24))
    tag_set = set(tags)

    try:
        # Overlap nativo Postgres (&&) via ANY — sem IA, indexável com GIN
        rows = (
            MarketplaceProduct.query.filter(
                MarketplaceProduct.active.is_(True),
                MarketplaceProduct.tags.overlap(tags),
            )
            .order_by(MarketplaceProduct.title.asc())
            .limit(safe_limit)
            .all()
        )
        scored = []
        for p in rows:
            overlap = tag_set.intersection(_normalize_tags(p.tags))
            scored.append((len(overlap), p))
        scored.sort(key=lambda x: (-x[0], x[1].title or ""))
        return [
            {
                **p.to_offer_dict(),
                "matched_tags": sorted(tag_set.intersection(_normalize_tags(p.tags))),
                "matched_category": p.category
                or (sorted(tag_set.intersection(_normalize_tags(p.tags))) or [None])[0],
            }
            for _, p in scored
        ]
    except Exception as exc:
        logger.warning("Falha ORM overlap (%s) — tentativa SQL raw", exc)

    try:
        rows = (
            db.session.execute(
                text(
                    """
                    SELECT id, title, price, currency, price_label, image, link,
                           vendor, category, tags
                    FROM marketplace_products
                    WHERE active = TRUE
                      AND tags && :tags
                    ORDER BY title ASC
                    LIMIT :lim
                    """
                ).bindparams(),
                {"tags": tags, "lim": safe_limit},
            )
            .mappings()
            .all()
        )
    except Exception as exc2:
        logger.exception("Falha SQL tag overlap: %s", exc2)
        return []

    offers: list[dict] = []
    for row in rows:
        product_tags = _normalize_tags(row.get("tags"))
        matched = sorted(tag_set.intersection(product_tags))
        price_val = float(row["price"]) if row.get("price") is not None else None
        label = row.get("price_label")
        if not label and price_val is not None:
            label = f"R$ {price_val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        offers.append(
            {
                "id": row["id"],
                "title": row["title"],
                "price": price_val,
                "currency": row.get("currency") or "BRL",
                "price_label": label or "Consulte",
                "image": row.get("image"),
                "link": row["link"],
                "vendor": row.get("vendor") or "catalog",
                "category": row.get("category"),
                "tags": product_tags,
                "matched_tags": matched,
                "matched_category": row.get("category") or (matched[0] if matched else None),
                "match_reason": "tag_overlap",
                "fallback": False,
            }
        )
    return offers


def build_contextual_vitrine(
    *,
    id_matu: int | None = None,
    id_clie: int | None = None,
    id_projeto: int | None = None,
    limit_per_category: int = 4,
    recommended_limit: int = 8,
) -> dict[str, Any]:
    """
    a) Sem contexto → modo genérico (prateleiras padrão).
    b/c) Com contexto → overlap SQL tags(sprints) ∩ tags(produtos).
    """
    if not id_clie and id_projeto:
        id_clie = id_projeto

    has_context = bool(id_matu or id_clie)
    orchestrator = MultivendorOrchestrator()

    # Prateleiras genéricas (live/fallback) — independentes do match contextual
    generic_shelves = []
    for cat in ("formacao", "equipamentos", "software"):
        result = orchestrator.search_all_vendors(None, category=cat, limit=limit_per_category)
        generic_shelves.append(
            {
                "category": cat,
                "category_label": result.get("category_label") or cat,
                "offers": result.get("offers") or [],
                "count": result.get("count") or 0,
                "source": result.get("source"),
            }
        )

    if not has_context:
        return {
            "status": "ok",
            "mode": "generic",
            "title": "Explore nossas Soluções",
            "subtitle": "Vitrine curada por categoria de necessidade.",
            "recommended": [],
            "sprints": [],
            "matched_categories": [],
            "sprint_tags": [],
            "shelves": generic_shelves,
        }

    sprints = fetch_panel_dx_sprints(id_matu=id_matu, id_clie=id_clie)
    sprint_tags = collect_sprint_tags(sprints)
    recommended = query_products_by_tag_overlap(sprint_tags, limit=recommended_limit)

    sprint_summaries = [
        {
            "id_sprn": sprint.get("id_sprn"),
            "nome": sprint.get("name_sprn") or sprint.get("nome"),
            "status": sprint.get("stat_sprn"),
            "bloco": sprint.get("name_bloc_text"),
            "tags": _normalize_tags(sprint.get("tags")),
        }
        for sprint in sprints
    ]

    return {
        "status": "ok",
        "mode": "contextual",
        "title": "Soluções recomendadas para suas Sprints Ativas",
        "subtitle": (
            "Itens do catálogo com tags em comum com suas sprints priorizadas (match SQL)."
            if recommended
            else (
                "Contexto recebido, mas sem overlap de tags — exibindo curadoria padrão."
                if sprint_summaries
                else "Contexto recebido, mas sem sprints ativas — exibindo curadoria padrão."
            )
        ),
        "id_matu": id_matu,
        "id_clie": id_clie,
        "recommended": recommended,
        "sprints": sprint_summaries,
        "matched_categories": sprint_tags,
        "sprint_tags": sprint_tags,
        "shelves": generic_shelves,
    }
