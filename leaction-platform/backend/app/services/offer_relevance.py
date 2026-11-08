"""Validação de natureza do produto para prateleiras culinárias.

Etapas separadas: recuperação de candidatos (orquestrador), validação de
categoria/natureza (este módulo), exceções humanas auditáveis e ordenação
posterior. Sem IA. Produto ambíguo não entra na recomendação publicada.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass

CULINARY_CATEGORIES = frozenset({"vinhos", "queijos", "frios", "azeites", "cervejas", "batatas"})

ALLOWED_DOMAINS = {
    "vinhos": frozenset(
        {
            "MLB-WINES",
            "MLB-RED_WINES",
            "MLB-WHITE_WINES",
            "MLB-ROSE_WINES",
            "MLB-SPARKLING_WINES",
            "MLB-DESSERT_WINES",
            "MLB-FORTIFIED_WINES",
        }
    ),
    "queijos": frozenset({"MLB-CHEESES", "MLB-FRESH_CHEESES", "MLB-CURED_CHEESES"}),
    "frios": frozenset(
        {
            "MLB-HAMS",
            "MLB-COLD_CUTS",
            "MLB-SAUSAGES",
            "MLB-SALAMIS",
            "MLB-CURED_MEATS",
        }
    ),
    "azeites": frozenset({"MLB-OLIVE_OILS", "MLB-OILS", "MLB-GOURMET_OILS"}),
    "cervejas": frozenset({"MLB-BEERS", "MLB-BEER", "MLB-ALCOHOLIC_BEVERAGES"}),
    "batatas": frozenset(
        {
            "MLB-POTATOES",
            "MLB-FROZEN_POTATOES",
            "MLB-FROZEN_FOOD",
            "MLB-FROZEN_VEGETABLES",
            "MLB-SNACKS",
            "MLB-POTATO_CHIPS",
        }
    ),
}

BLOCKED_DOMAINS = frozenset(
    {
        "MLB-BOOKS",
        "MLB-E_BOOKS",
        "MLB-MAGAZINES",
        "MLB-TIES",
        "MLB-NECKTIES",
        "MLB-CLOTHING",
        "MLB-SHIRTS",
        "MLB-PANTS",
        "MLB-DRESSES",
        "MLB-FOOTWEAR",
        "MLB-WATCHES",
        "MLB-JEWELRY",
        "MLB-POSTERS",
        "MLB-WALL_DECOR",
        "MLB-STICKERS",
        "MLB-KEYCHAINS",
        "MLB-TOYS",
        "MLB-VIDEO_GAMES",
        "MLB-SPORTS",
        "MLB-SOCCER",
        "MLB-GLASSES",
        "MLB-WINE_GLASSES",
        "MLB-CORKSCREWS",
        "MLB-KITCHEN_UTENSILS",
    }
)

FORBIDDEN_NATURES = (
    "livro",
    "livros",
    "ebook",
    "e-book",
    "revista",
    "poema",
    "poesia",
    "3drose",
    "poster",
    "pôster",
    "quadro",
    "adesivo",
    "gravata",
    "camisa",
    "camiseta",
    "cinto",
    "meia",
    "sapato",
    "tenis",
    "tênis",
    "relogio",
    "relógio",
    "pulseira",
    "colar",
    "brinco",
    "chaveiro",
    "bola de",
    "copa do mundo",
    "trofeu",
    "troféu",
    "gamer",
    "headset",
    "peruca",
    "batom",
    "guardanapo",
)

WINE_COLOR_ONLY = (
    "cor vinho",
    "tom vinho",
    "vinho tinto tambem e vinho tinto",
    "roses are red",
)

WINE_BEVERAGE = (
    "vinho tinto",
    "vinho branco",
    "vinho rose",
    "vinho rosé",
    "espumante",
    "prosecco",
    "750 ml",
    "750ml",
    "garrafa",
)

CHEESE_FOOD = (
    "queijo",
    "canastra",
    "gorgonzola",
    "brie",
    "camembert",
    "mussarela",
    "muçarela",
    "parmesao",
    "parmesão",
)

CHARCUTERIE_FOOD = (
    "presunto",
    "parma",
    "salame",
    "salami",
    "fiambre",
    "copa italiana",
    "copa fatiada",
    "copa iberic",
    "copa cru",
)

OIL_FOOD = (
    "azeite extra",
    "azeite de oliva",
    "azeite portugues",
    "azeite português",
    "extra virgem",
    "virgem extra",
)

BEER_DRINK = (
    "cerveja",
    "lager",
    "pilsen",
    "pilsner",
    "ipa",
    "stout",
    "weizen",
    "witbier",
    "long neck",
    "lata 350",
    "lata 473",
    "garrafa 600",
)

POTATO_FOOD = (
    "batata palito",
    "batata pre-frita",
    "batata pre frita",
    "batata congelada",
    "batata chips",
    "batata palha",
    "chips de batata",
)

CLOTHING_FIT = (
    "masculino",
    "feminino",
    "slim fit",
    "fino e estreito",
    "cm,",
    "tamanho p",
    "tamanho m",
    "tamanho g",
)

UTENSIL_AS_FOOD = (
    "taca",
    "taça",
    "copo de vinho",
    "saca-rolhas",
    "sacarolhas",
    "porta azeite",
    "dispenser",
    "galheteiro",
    "forma de queijo",
    "rechaud",
    "réchaud",
)


@dataclass(frozen=True)
class RelevanceDecision:
    accepted: bool
    decision: str
    reason: str
    source: str


def fold_text(value: object) -> str:
    text = " ".join(str(value or "").replace("\x00", " ").split()).casefold()
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(char for char in nfkd if not unicodedata.combining(char))


def _contains_any(hay: str, needles: tuple[str, ...] | frozenset[str]) -> str:
    for needle in needles:
        token = fold_text(needle)
        if token and token in hay:
            return needle
    return ""


def evaluate_offer(
    offer: dict,
    *,
    category: str,
    origin: str = "lojadepaes",
    decisions: dict[str, dict] | None = None,
) -> RelevanceDecision:
    """Valida se a oferta é da natureza pedida. Não inventa classificação."""
    shelf = fold_text(category)
    if shelf not in CULINARY_CATEGORIES:
        return RelevanceDecision(True, "skip", "Categoria fora do perfil culinário — sem filtro de natureza.", "profile")

    offer_id = str(offer.get("id") or "").strip()
    exception = (decisions or {}).get(f"{origin}|{shelf}|{offer_id}")
    if exception:
        accepted = exception.get("decision") == "approve"
        return RelevanceDecision(
            accepted,
            "approve" if accepted else "reject",
            str(exception.get("reason") or "Exceção editorial auditável."),
            "human",
        )

    title = fold_text(offer.get("title") or offer.get("name"))
    domain = fold_text(offer.get("provider_domain") or offer.get("domain_id")).replace("_", "-").upper().replace(" ", "")
    domain_norm = str(offer.get("provider_domain") or offer.get("domain_id") or "").strip().upper()
    product_type = fold_text(
        f"{offer.get('product_type') or ''} {offer.get('provider_category') or ''} {offer.get('category_name') or ''}"
    )
    hay = f"{title} {product_type}"

    if domain_norm in BLOCKED_DOMAINS or _contains_any(fold_text(domain_norm), BLOCKED_DOMAINS):
        return RelevanceDecision(
            False,
            "reject",
            f"Categoria oficial do provedor incompatível ({domain_norm}).",
            "provider_category",
        )

    allowed = ALLOWED_DOMAINS.get(shelf, frozenset())
    if domain_norm in allowed:
        forbidden = _forbidden_hit(hay, shelf)
        if forbidden:
            return RelevanceDecision(
                False,
                "reject",
                f"Categoria oficial de {shelf}, mas o título indica {forbidden}.",
                "conflict",
            )
        return RelevanceDecision(True, "accept", f"Categoria oficial do provedor ({domain_norm}).", "provider_category")

    forbidden = _forbidden_hit(hay, shelf)
    if forbidden:
        return RelevanceDecision(
            False,
            "reject",
            f"Natureza incompatível com {shelf}: {forbidden}.",
            "nature",
        )

    if shelf == "vinhos" and _contains_any(hay, WINE_COLOR_ONLY) and not _contains_any(hay, ("750", "garrafa", "espumante")):
        return RelevanceDecision(False, "reject", "Menção a vinho só como cor ou tema, não como bebida.", "nature")

    if not _has_food_marker(hay, shelf):
        return RelevanceDecision(
            False,
            "review",
            "Sem categoria oficial nem marcador de alimento/bebida suficiente — fica de fora da recomendação.",
            "ambiguous",
        )
    if shelf == "batatas" and _contains_any(hay, ("batata palito",)) and not _contains_any(
        hay,
        ("kg", "600g", "400g", "500g", "1kg", "congelad", "pre-frita", "pre frita", "chips", "palha", "mccain", "pacote", "forno"),
    ):
        return RelevanceDecision(
            False,
            "reject",
            "Título com batata palito sem formato alimentício comprovado.",
            "nature",
        )

    return RelevanceDecision(True, "accept", f"Marcadores de {shelf} no título, sem natureza conflitante.", "nature")


def _forbidden_hit(hay: str, shelf: str) -> str:
    hit = _contains_any(hay, FORBIDDEN_NATURES)
    if hit:
        return hit
    if shelf == "vinhos" and _contains_any(hay, CLOTHING_FIT) and _contains_any(hay, ("vinho", "tinto", "branco")):
        return "roupa ou acessório com cor de vinho"
    if shelf == "vinhos" and _contains_any(hay, UTENSIL_AS_FOOD):
        return "utensílio, não a bebida"
    if shelf == "frios" and _contains_any(
        hay,
        ("taca", "taça", "copa do mundo", "chaveiro", "bola de", "mikasa", "oncas", "onças", "de campo", "conjunto de"),
    ):
        return "objeto homônimo, não o frio"
    if shelf == "queijos" and _contains_any(
        hay,
        ("livro", "forma de", "silicone", "salame", "salami", "presunto", "embutido", "copa italiana", "linguica", "linguiça"),
    ):
        return "embutido, acessório ou publicação, não o queijo"
    if shelf == "azeites" and _contains_any(hay, ("porta azeite", "dispenser", "galheteiro", "spray vazio")):
        return "acessório, não o azeite"
    if shelf == "cervejas" and _contains_any(
        hay,
        (
            "copo de cerveja",
            "tulipa",
            "caneca",
            "camiseta",
            "camisa",
            "kit fabricacao",
            "kit fabricação",
            "fabrica de cerveja",
            "fábrica de cerveja",
            "livro",
            "growler vazio",
        ),
    ):
        return "acessório, copo, kit ou publicação, não a bebida"
    if shelf == "batatas" and _contains_any(
        hay,
        (
            "semente",
            "mudas",
            "cortador",
            "fatiador",
            "descascador",
            "fritadeira",
            "brinquedo",
            "pelucia",
            "pelúcia",
            "almofada",
            "travesseiro",
            "utensilio",
            "utensílio",
            "pegador",
            "pa para",
            "pá para",
        ),
    ):
        return "semente, utensílio ou brinquedo, não o alimento"
    return ""


def _has_food_marker(hay: str, shelf: str) -> bool:
    if shelf == "vinhos":
        return bool(_contains_any(hay, WINE_BEVERAGE))
    if shelf == "queijos":
        return bool(_contains_any(hay, CHEESE_FOOD))
    if shelf == "frios":
        return bool(_contains_any(hay, CHARCUTERIE_FOOD))
    if shelf == "azeites":
        return bool(_contains_any(hay, OIL_FOOD))
    if shelf == "cervejas":
        return bool(_contains_any(hay, BEER_DRINK))
    if shelf == "batatas":
        return bool(_contains_any(hay, POTATO_FOOD))
    return False


def public_offer(offer: dict) -> dict:
    hidden = {"relevance_decision", "relevance_reason", "relevance_source"}
    return {key: value for key, value in offer.items() if key not in hidden}
