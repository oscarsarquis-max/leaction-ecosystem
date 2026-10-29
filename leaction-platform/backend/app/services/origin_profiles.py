"""Perfis de curadoria por sistema de origem.

Seleção configurada (categorias, termos, inclusões/exclusões). Sem IA.
Origem omissa ou desconhecida nunca troca o legado de TI por alimentos.
"""

from __future__ import annotations

DEFAULT_ORIGIN = "legado"
APP_ID_HEADER = "X-ActionHub-App-Id"

# Identidade de consumidor já usada no Hub (checkout/app id) → perfil.
TRUSTED_APP_ORIGINS = {
    "lojadepaes": "lojadepaes",
}

ORIGIN_PROFILES: dict[str, dict] = {
    "legado": {
        "label": "Transformação digital",
        "categories": ("formacao", "equipamentos", "software"),
        "published": True,
    },
    "lojadepaes": {
        "label": "A Loja de Pães",
        "categories": ("vinhos", "queijos", "frios", "azeites", "cervejas", "batatas"),
        "published": True,
    },
    "educacao": {
        "label": "Educação (capacidade futura)",
        "categories": ("livros",),
        "published": False,
    },
}

CULINARY_CATEGORY_PROFILES: dict[str, dict[str, str]] = {
    "vinhos": {
        "label": "Vinhos para a mesa",
        "default_query": "vinho tinto para mesa queijo pão",
        "mercadolivre": "vinho tinto mesa",
        "amazon": "vinho tinto mesa gourmet",
    },
    "queijos": {
        "label": "Queijos",
        "default_query": "queijo canastra gorgonzola mesa",
        "mercadolivre": "queijo canastra mesa",
        "amazon": "queijo gourmet mesa",
    },
    "frios": {
        "label": "Frios e charcutaria",
        "default_query": "presunto parma salame copa mesa",
        "mercadolivre": "presunto parma mesa",
        "amazon": "charcutaria presunto gourmet",
    },
    "azeites": {
        "label": "Azeites e conservas",
        "default_query": "azeite extra virgem mesa pão",
        "mercadolivre": "azeite extra virgem",
        "amazon": "azeite extra virgem gourmet",
    },
    "cervejas": {
        "label": "Cervejas",
        "default_query": "cerveja pilsen lata mesa",
        "mercadolivre": "cerveja pilsen lata",
        "amazon": "cerveja pilsen gourmet",
    },
    "batatas": {
        "label": "Batatas",
        "default_query": "batata palito pre frita congelada",
        "mercadolivre": "batata palito pre frita congelada",
        "amazon": "batata congelada palito",
    },
    "livros": {
        "label": "Livros (educação)",
        "default_query": "livros educação didático",
        "mercadolivre": "livros educação",
        "amazon": "livros educação didáticos",
    },
}

CULINARY_ALIASES: dict[str, str] = {
    "vinho": "vinhos",
    "wine": "vinhos",
    "queijo": "queijos",
    "cheese": "queijos",
    "charcutaria": "frios",
    "embutidos": "frios",
    "azeite": "azeites",
    "conservas": "azeites",
    "cerveja": "cervejas",
    "beer": "cervejas",
    "batata": "batatas",
    "potato": "batatas",
    "books": "livros",
    "livro": "livros",
}

CULINARY_FALLBACK_QUERIES: dict[str, str] = {
    "vinhos": "vinho tinto mesa",
    "queijos": "queijo canastra mesa",
    "frios": "presunto parma mesa",
    "azeites": "azeite extra virgem",
    "cervejas": "cerveja pilsen lata",
    "batatas": "batata palito pre frita congelada",
    "livros": "livros educação",
}

AMAZON_CULINARY_INDEX: dict[str, str] = {
    "vinhos": "Gourmet",
    "queijos": "Gourmet",
    "frios": "Gourmet",
    "azeites": "Gourmet",
    "cervejas": "Gourmet",
    "batatas": "Gourmet",
    "livros": "Books",
}


def resolve_origin(*, app_id: str | None = None, query_origin: str | None = None) -> dict:
    """Mapeia identidade de servidor primeiro; query só se estiver na allowlist publicada."""
    app = (app_id or "").strip().lower()
    if app:
        mapped = TRUSTED_APP_ORIGINS.get(app)
        if mapped:
            return {"ok": True, "origin": mapped, "error": None}
        return {
            "ok": False,
            "origin": None,
            "error": "origem não reconhecida",
        }

    raw = (query_origin or "").strip().lower()
    if not raw:
        return {"ok": True, "origin": DEFAULT_ORIGIN, "error": None}

    profile = ORIGIN_PROFILES.get(raw)
    if profile is None:
        return {"ok": False, "origin": None, "error": "origem não reconhecida"}
    if not profile.get("published"):
        return {"ok": False, "origin": None, "error": "origem não publicada"}
    return {"ok": True, "origin": raw, "error": None}


def origin_categories(origin: str) -> tuple[str, ...]:
    profile = ORIGIN_PROFILES.get(origin) or ORIGIN_PROFILES[DEFAULT_ORIGIN]
    return tuple(profile["categories"])


def category_belongs_to_origin(category: str, origin: str) -> bool:
    return category in origin_categories(origin)


def list_origin_public(origin: str) -> dict:
    profile = ORIGIN_PROFILES[origin]
    return {
        "id": origin,
        "label": profile["label"],
        "categories": list(profile["categories"]),
        "mode": "configured_selection",
    }
