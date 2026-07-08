"""Seed inicial das regras de curadoria — migrado do orquestrador hardcoded."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

DEFAULT_CURATION_ROWS: list[dict] = [
    {
        "id": "global",
        "search_terms": [],
        "positive_keywords": [],
        "negative_keywords": [
            "gamer",
            "jogo",
            "ps5",
            "xbox",
            "nintendo",
            "tv",
            "televisão",
            "televisao",
            "smart tv",
            "brinquedo",
            "pelúcia",
            "pelucia",
            "infantil",
        ],
    },
    {
        "id": "formacao",
        "search_terms": [
            "livro liderança",
            "livro transformação digital",
            "livro gestão de ti",
            "livro governança corporativa",
            "livro inovação estratégia",
        ],
        "positive_keywords": [
            "livro",
            "ebook",
            "curso",
            "apostila",
            "guia",
            "handbook",
            "gestao",
            "gestão",
            "lideranca",
            "liderança",
            "governanca",
            "governança",
            "inovacao",
            "inovação",
            "management",
        ],
        "negative_keywords": [],
    },
    {
        "id": "equipamentos",
        "search_terms": [
            "roteador corporativo cisco",
            "switch rede ubiquiti",
            "servidor rack dell",
            "access point corporativo",
            "firewall hardware",
        ],
        "positive_keywords": [
            "roteador",
            "router",
            "switch",
            "servidor",
            "server",
            "access point",
            "firewall",
            "rack",
            "cisco",
            "ubiquiti",
            "dell",
            "tp-link",
            "unifi",
        ],
        "negative_keywords": [],
    },
    {
        "id": "software",
        "search_terms": [
            "licença microsoft 365",
            "antivirus corporativo endpoint",
            "windows server licença",
            "kaspersky endpoint",
        ],
        "positive_keywords": [
            "licenca",
            "licença",
            "software",
            "microsoft",
            "365",
            "office",
            "windows server",
            "antivirus",
            "endpoint",
            "kaspersky",
        ],
        "negative_keywords": [],
    },
]


def seed_curation_if_empty() -> int:
    """Popula regras padrão quando a tabela está vazia."""
    from app.database import DB_AVAILABLE, db
    from app.database.models import MarketplaceCuration

    if not DB_AVAILABLE or db is None or MarketplaceCuration is None:
        return 0

    if MarketplaceCuration.query.count() > 0:
        return 0

    for row in DEFAULT_CURATION_ROWS:
        db.session.add(
            MarketplaceCuration(
                id=row["id"],
                search_terms=list(row["search_terms"]),
                positive_keywords=list(row["positive_keywords"]),
                negative_keywords=list(row["negative_keywords"]),
            )
        )

    db.session.commit()
    logger.info("Seed marketplace_curation: %d regras inseridas.", len(DEFAULT_CURATION_ROWS))
    return len(DEFAULT_CURATION_ROWS)


def get_default_row(curation_id: str) -> dict | None:
    for row in DEFAULT_CURATION_ROWS:
        if row["id"] == curation_id:
            return row
    return None
