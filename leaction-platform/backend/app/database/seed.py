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


# Catálogo curado para match SQL (tags persistidas) — espelha fallback B2B.
DEFAULT_CATALOG_PRODUCTS: list[dict] = [
    {
        "id": "catalog-formacao-1",
        "title": "Liderança em Tempos de Transformação Digital",
        "price": 79.9,
        "price_label": "R$ 79,90",
        "image": "/marketplace/placeholders/livro.svg",
        "link": "https://lista.mercadolivre.com.br/livros-lideranca-transformacao-digital",
        "category": "formacao",
        "tags": ["formacao"],
    },
    {
        "id": "catalog-formacao-2",
        "title": "Gestão Estratégica e Inovação Corporativa",
        "price": 92.5,
        "price_label": "R$ 92,50",
        "image": "/marketplace/placeholders/gestao.svg",
        "link": "https://lista.mercadolivre.com.br/livros-gestao-estrategica",
        "category": "formacao",
        "tags": ["formacao"],
    },
    {
        "id": "catalog-formacao-3",
        "title": "Transformação Digital para Executivos",
        "price": 68.0,
        "price_label": "R$ 68,00",
        "image": "/marketplace/placeholders/digital.svg",
        "link": "https://lista.mercadolivre.com.br/livros-transformacao-digital",
        "category": "formacao",
        "tags": ["formacao"],
    },
    {
        "id": "catalog-formacao-4",
        "title": "Curso Online — Maturidade Digital Organizacional",
        "price": 197.0,
        "price_label": "R$ 197,00",
        "image": "/marketplace/placeholders/digital.svg",
        "link": "https://lista.mercadolivre.com.br/curso-maturidade-digital",
        "category": "formacao",
        "tags": ["formacao"],
    },
    {
        "id": "catalog-equip-1",
        "title": "Switch Gerenciável Gigabit — Infraestrutura de Rede",
        "price": 489.9,
        "price_label": "R$ 489,90",
        "image": "/marketplace/placeholders/rede.svg",
        "link": "https://lista.mercadolivre.com.br/switch-gerenciavel-gigabit",
        "category": "equipamentos",
        "tags": ["equipamentos"],
    },
    {
        "id": "catalog-equip-2",
        "title": "Roteador Wi-Fi 6 Empresarial",
        "price": 629.0,
        "price_label": "R$ 629,00",
        "image": "/marketplace/placeholders/rede.svg",
        "link": "https://lista.mercadolivre.com.br/roteador-wifi-6-empresarial",
        "category": "equipamentos",
        "tags": ["equipamentos"],
    },
    {
        "id": "catalog-equip-3",
        "title": "Access Point Corporativo Dual Band",
        "price": 399.9,
        "price_label": "R$ 399,90",
        "image": "/marketplace/placeholders/rede.svg",
        "link": "https://lista.mercadolivre.com.br/access-point-corporativo",
        "category": "equipamentos",
        "tags": ["equipamentos"],
    },
    {
        "id": "catalog-equip-4",
        "title": "Notebook Profissional — Produtividade Digital",
        "price": 3299.0,
        "price_label": "R$ 3.299,00",
        "image": "/marketplace/placeholders/equipamento.svg",
        "link": "https://lista.mercadolivre.com.br/notebook-profissional",
        "category": "equipamentos",
        "tags": ["equipamentos"],
    },
    {
        "id": "catalog-sw-1",
        "title": "Microsoft 365 Business — Licença Anual",
        "price": 899.0,
        "price_label": "R$ 899,00",
        "image": "/marketplace/placeholders/digital.svg",
        "link": "https://lista.mercadolivre.com.br/microsoft-365-business",
        "category": "software",
        "tags": ["software"],
    },
    {
        "id": "catalog-sw-2",
        "title": "Antivírus Corporativo Endpoint Protection",
        "price": 249.9,
        "price_label": "R$ 249,90",
        "image": "/marketplace/placeholders/digital.svg",
        "link": "https://lista.mercadolivre.com.br/antivirus-corporativo-endpoint",
        "category": "software",
        "tags": ["software"],
    },
    {
        "id": "catalog-sw-3",
        "title": "Windows Server — Licença Standard",
        "price": 1899.0,
        "price_label": "R$ 1.899,00",
        "image": "/marketplace/placeholders/digital.svg",
        "link": "https://lista.mercadolivre.com.br/windows-server-licenca",
        "category": "software",
        "tags": ["software"],
    },
    {
        "id": "catalog-sw-4",
        "title": "Ferramentas de Gestão e Produtividade Digital",
        "price": 159.0,
        "price_label": "R$ 159,00",
        "image": "/marketplace/placeholders/digital.svg",
        "link": "https://lista.mercadolivre.com.br/software-gestao-corporativa",
        "category": "software",
        "tags": ["software"],
    },
]


def seed_catalog_products_if_empty() -> int:
    """Popula catálogo da vitrine quando a tabela está vazia."""
    from app.database import DB_AVAILABLE, db
    from app.database.models import MarketplaceProduct

    if not DB_AVAILABLE or db is None or MarketplaceProduct is None:
        return 0

    if MarketplaceProduct.query.count() > 0:
        return 0

    for row in DEFAULT_CATALOG_PRODUCTS:
        db.session.add(
            MarketplaceProduct(
                id=row["id"],
                title=row["title"],
                price=row.get("price"),
                price_label=row.get("price_label"),
                image=row.get("image"),
                link=row["link"],
                vendor="catalog",
                category=row.get("category"),
                tags=list(row.get("tags") or []),
                active=True,
            )
        )

    db.session.commit()
    logger.info("Seed marketplace_products: %d itens inseridos.", len(DEFAULT_CATALOG_PRODUCTS))
    return len(DEFAULT_CATALOG_PRODUCTS)


def get_default_row(curation_id: str) -> dict | None:
    for row in DEFAULT_CURATION_ROWS:
        if row["id"] == curation_id:
            return row
    return None
