"""Contrato de relevância da vitrine. A Loja não classifica de novo — só recusa o que foge da natureza."""

from __future__ import annotations

import unicodedata

ALLOWED_CATEGORIES = frozenset({"vinhos", "queijos", "frios", "azeites", "cervejas", "batatas"})

FORBIDDEN = (
    "livro",
    "livros",
    "ebook",
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
    "chaveiro",
    "copa do mundo",
    "bola de",
    "porta azeite",
    "galheteiro",
    "dispenser",
)

WINE_COLOR_ONLY = ("cor vinho", "tom vinho", "roses are red", "vinho tinto tambem e vinho tinto")
CLOTHING_FIT = ("masculino", "feminino", "fino e estreito", "slim fit")
WINE_DRINK = ("vinho tinto", "vinho branco", "vinho rose", "vinho rosé", "espumante", "750 ml", "750ml", "garrafa")
CHEESE = ("queijo", "canastra", "gorgonzola", "brie")
COLD_CUTS = ("presunto", "parma", "salame", "copa italiana", "copa fatiada", "fiambre")
OIL = ("azeite extra", "azeite de oliva", "extra virgem", "azeite portugues", "azeite português")
BEER = ("cerveja", "lager", "pilsen", "pilsner", "ipa", "stout", "weizen", "long neck")
POTATO = ("batata palito", "batata pre-frita", "batata pre frita", "batata congelada", "batata chips", "batata palha", "chips de batata")


def _fold(value: object) -> str:
    text = " ".join(str(value or "").split()).casefold()
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(char for char in nfkd if not unicodedata.combining(char))


def _has(hay: str, needles: tuple[str, ...]) -> bool:
    return any(_fold(item) in hay for item in needles)


def offer_fits_contract(*, title: str, category: str, domain: str = "") -> bool:
    shelf = _fold(category)
    if shelf not in ALLOWED_CATEGORIES:
        return False
    hay = _fold(f"{title} {domain}")
    if _has(hay, FORBIDDEN):
        return False
    if shelf == "vinhos":
        if _has(hay, WINE_COLOR_ONLY) and not _has(hay, ("750", "garrafa", "espumante")):
            return False
        if _has(hay, CLOTHING_FIT):
            return False
        if _has(hay, ("taca", "taça", "saca-rolhas")):
            return False
        return _has(hay, WINE_DRINK)
    if shelf == "queijos":
        if _has(hay, ("salame", "salami", "presunto", "embutido", "copa italiana", "linguica", "linguiça")):
            return False
        return _has(hay, CHEESE)
    if shelf == "frios":
        if _has(hay, ("taca", "taça", "copa do mundo", "chaveiro", "mikasa", "oncas", "de campo", "conjunto de")):
            return False
        return _has(hay, COLD_CUTS)
    if shelf == "azeites":
        if _has(hay, ("porta azeite", "dispenser", "galheteiro")):
            return False
        return _has(hay, OIL)
    if shelf == "cervejas":
        if _has(hay, ("copo de cerveja", "tulipa", "camiseta", "kit fabricacao", "kit fabricação", "livro", "growler vazio")):
            return False
        return _has(hay, BEER)
    if shelf == "batatas":
        if _has(
            hay,
            (
                "semente",
                "muda",
                "cortador",
                "fatiador",
                "descascador",
                "fritadeira",
                "brinquedo",
                "pelucia",
                "pelúcia",
                "almofada",
                "travesseiro",
                "pegador",
                "pa para",
            ),
        ):
            return False
        return _has(hay, POTATO)
    return False
