"""Carrega regras de curadoria da base de dados (com fallback do seed)."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from app.database.models import MarketplaceCuration
from app.database.seed import DEFAULT_CURATION_ROWS, get_default_row

logger = logging.getLogger(__name__)

CURATED_CATEGORY_IDS = frozenset({"formacao", "equipamentos", "software"})


@dataclass
class CurationRules:
    category_id: str
    search_terms: list[str] = field(default_factory=list)
    positive_keywords: list[str] = field(default_factory=list)
    negative_keywords: list[str] = field(default_factory=list)

    @property
    def has_curated_search(self) -> bool:
        return bool(self.search_terms)


class CurationRepository:
    @staticmethod
    def list_all() -> list[dict]:
        from app.database import DB_AVAILABLE, db

        if not DB_AVAILABLE or db is None:
            return [dict(row) for row in DEFAULT_CURATION_ROWS]

        rows = MarketplaceCuration.query.order_by(MarketplaceCuration.id).all()
        if rows:
            return [row.to_dict() for row in rows]
        return [dict(row) for row in DEFAULT_CURATION_ROWS]

    @staticmethod
    def get_by_id(curation_id: str) -> MarketplaceCuration | None:
        from app.database import db

        return db.session.get(MarketplaceCuration, curation_id)

    @staticmethod
    def update_by_id(curation_id: str, payload: dict):
        from app.database import DB_AVAILABLE, db

        if not DB_AVAILABLE or db is None or MarketplaceCuration is None:
            raise RuntimeError("Banco de dados indisponível para atualizar curadoria.")

        row = db.session.get(MarketplaceCuration, curation_id)
        if row is None:
            row = MarketplaceCuration(id=curation_id)
            db.session.add(row)

        if "search_terms" in payload:
            row.search_terms = _normalize_list(payload["search_terms"])
        if "positive_keywords" in payload:
            row.positive_keywords = _normalize_list(payload["positive_keywords"])
        if "negative_keywords" in payload:
            row.negative_keywords = _normalize_list(payload["negative_keywords"])

        db.session.commit()
        return row

    @staticmethod
    def load_for_category(category_id: str) -> CurationRules:
        from app.database import DB_AVAILABLE, db

        if not DB_AVAILABLE or db is None or MarketplaceCuration is None:
            return _build_rules_from_seed(category_id)

        try:
            global_row = db.session.get(MarketplaceCuration, "global")
            category_row = (
                db.session.get(MarketplaceCuration, category_id)
                if category_id in CURATED_CATEGORY_IDS
                else None
            )
            return _build_rules(category_id, category_row, global_row)
        except Exception as exc:
            logger.warning("Curadoria via DB indisponível (%s) — usando seed local.", exc)
            return _build_rules_from_seed(category_id)


def _build_rules(
    category_id: str,
    category_row: MarketplaceCuration | None,
    global_row: MarketplaceCuration | None,
) -> CurationRules:
    if category_row is None and global_row is None:
        return _build_rules_from_seed(category_id)

    search_terms = _row_list(category_row, "search_terms")
    positive_keywords = _row_list(category_row, "positive_keywords")

    negative_keywords = _row_list(global_row, "negative_keywords")
    if category_row:
        negative_keywords = _merge_unique(
            negative_keywords,
            _row_list(category_row, "negative_keywords"),
        )

    if category_row is None and category_id in CURATED_CATEGORY_IDS:
        seed = get_default_row(category_id)
        if seed:
            search_terms = search_terms or list(seed.get("search_terms") or [])
            positive_keywords = positive_keywords or list(
                seed.get("positive_keywords") or []
            )

    if global_row is None:
        seed_global = get_default_row("global")
        if seed_global:
            negative_keywords = negative_keywords or list(
                seed_global.get("negative_keywords") or []
            )

    return CurationRules(
        category_id=category_id,
        search_terms=search_terms,
        positive_keywords=positive_keywords,
        negative_keywords=negative_keywords,
    )


def _build_rules_from_seed(category_id: str) -> CurationRules:
    global_seed = get_default_row("global") or {}
    category_seed = get_default_row(category_id) if category_id in CURATED_CATEGORY_IDS else {}

    return CurationRules(
        category_id=category_id,
        search_terms=list(category_seed.get("search_terms") or []),
        positive_keywords=list(category_seed.get("positive_keywords") or []),
        negative_keywords=_merge_unique(
            list(global_seed.get("negative_keywords") or []),
            list(category_seed.get("negative_keywords") or []),
        ),
    )


def _row_list(row: MarketplaceCuration | None, attr: str) -> list[str]:
    if row is None:
        return []
    value = getattr(row, attr, None)
    return _normalize_list(value)


def _normalize_list(value) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _merge_unique(*groups: list[str]) -> list[str]:
    seen: set[str] = set()
    merged: list[str] = []
    for group in groups:
        for item in group:
            key = item.casefold()
            if key in seen:
                continue
            seen.add(key)
            merged.append(item)
    return merged
