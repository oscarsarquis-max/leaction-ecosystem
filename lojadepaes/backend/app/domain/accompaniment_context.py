from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import quote

from app.domain.marketplace_links import sanitize_plain_text

ALLOWED_CATEGORIES = {
    "vinhos": "Vinhos",
    "queijos": "Queijos",
    "frios": "Frios",
    "azeites": "Azeites",
    "cervejas": "Cervejas",
    "batatas": "Batatas",
}

CATEGORY_ALIASES = {
    "vinho": "vinhos",
    "vinhos": "vinhos",
    "queijo": "queijos",
    "queijos": "queijos",
    "frio": "frios",
    "frios": "frios",
    "embutido": "frios",
    "presunto": "frios",
    "azeite": "azeites",
    "azeites": "azeites",
    "cerveja": "cervejas",
    "cervejas": "cervejas",
    "batata": "batatas",
    "batatas": "batatas",
}

WINE_STYLES = {
    "tinto": ("tinto", "cabernet", "malbec", "merlot", "syrah", "shiraz", "pinot", "tempranillo"),
    "branco": ("branco", "chardonnay", "sauvignon", "verde", "alvarinho", "arinto", "riesling"),
    "rose": ("rose", "rosé", "rosado"),
    "espumante": ("espumante", "prosecco", "brut", "cava", "champagne"),
}

WINE_STYLE_LABELS = {
    "tinto": "vinho tinto",
    "branco": "vinho branco",
    "rose": "vinho rosé",
    "espumante": "espumante",
}

DISH_TOKENS = {
    "leitao": ("leitao", "leitão"),
    "porco": ("porco", "pernil"),
    "salada": ("salada", "saladas"),
    "frios": ("mesa de frios", "tabua de frios", "tábua de frios", "embutidos", "charcutaria"),
    "sardinha": ("sardinha", "sardinhas"),
    "camarao": ("camarao", "camarão", "camaroes", "camarões"),
    "lagosta": ("lagosta", "lagostas"),
    "peixe": ("peixe grelhado", "peixes grelhados", "peixe", "peixes"),
    "hamburguer": ("hamburguer", "hambúrguer", "hamburger", "burger"),
}

DISH_LABELS = {
    "leitao": "leitão",
    "porco": "porco",
    "salada": "saladas",
    "frios": "mesa de frios",
    "peixe": "peixe",
    "sardinha": "sardinhas",
    "camarao": "camarão",
    "lagosta": "lagosta",
    "hamburguer": "hambúrguer",
}

MEAL_COMPLEMENTS = {
    "leitao": ("vinhos", "queijos", "azeites"),
    "porco": ("vinhos", "queijos", "azeites"),
    "salada": ("azeites",),
    "frios": ("queijos", "frios", "azeites"),
    "peixe": ("vinhos", "azeites"),
    "sardinha": ("vinhos", "azeites"),
    "camarao": ("vinhos", "azeites"),
    "lagosta": ("vinhos", "azeites"),
    "hamburguer": ("cervejas", "batatas"),
}

TABLE_ASK = (
    "acompanhamento",
    "acompanhar",
    "para a mesa",
    "para servir",
    "o que servir",
    "como servir",
    "sugere",
    "sugestao",
    "sugestão",
    "combinacao",
    "combinação",
    "combina",
    "combinar",
    "para acompanhar",
    "o que beber",
    "para beber",
    "e para beber",
    "que bebidas",
    "completar a mesa",
    "mostre os acompanhamentos",
    "mostra os acompanhamentos",
)
GUIDE_SCORE_ASK = (
    "avaliacao",
    "avaliação",
    "tem nota",
    "que nota",
    "pontuacao",
    "pontuação",
    "quantos pontos",
    "guia descorchados",
    "guia adega",
)

SUPPORT_ONLY = (
    "pagamento",
    "pagar",
    "pix",
    "cartao",
    "cartão",
    "endereco",
    "endereço",
    "meu pedido",
    "encomenda",
    "fidelidade",
    "carimbo",
)

ONLY_WINE = ("so vinho", "só vinho", "somente vinho", "apenas vinho", "e um vinho", "e vinho")
ONLY_CHEESE = ("somente queijo", "somente queijos", "so queijo", "só queijo", "apenas queijo", "quero somente queijos")
NO_ALCOHOL = (
    "sem alcool",
    "sem álcool",
    "sem vinho",
    "sem cerveja",
    "nao quero vinho",
    "não quero vinho",
    "nao quero cerveja",
    "não quero cerveja",
)
NO_CHEESE = ("sem queijo", "nao quero queijo", "não quero queijo")
NO_MEAT = ("sem carne", "sem embutido", "sem embutidos")
NO_CHIPS = ("nao chips", "não chips", "sem chips", "nao quero chips", "não quero chips")
ASKS_WINE = ("vinho", "vinhos", "espumante")
ASKS_BEER = ("cerveja", "cervejas")
ASKS_CHEESE = ("queijo", "queijos")
ONLY_DRINKS = (
    "so as bebidas",
    "só as bebidas",
    "somente as bebidas",
    "apenas as bebidas",
    "so cerveja",
    "só cerveja",
    "somente cerveja",
)
POTATO_FORMS = {
    "fritar": ("pre-frita", "pre frita", "congelada", "palito", "para fritar", "corte"),
    "chips": ("chips", "snack"),
    "palha": ("batata palha", "palha"),
}
BEER_STYLES = {
    "lager": ("lager",),
    "pilsen": ("pilsen", "pilsner"),
    "ipa": ("ipa",),
    "stout": ("stout",),
}
BEER_STYLE_LABELS = {
    "lager": "lager",
    "pilsen": "pilsen",
    "ipa": "IPA",
    "stout": "stout",
}
POTATO_FORM_LABELS = {
    "fritar": "para fritar",
    "chips": "chips",
    "palha": "batata palha",
}

MAX_CONTEXTUAL_PER_CATEGORY = 3
MAX_CONTEXTUAL_ITEMS = 8


def _fold(value: object, *, limit: int = 80) -> str:
    text = sanitize_plain_text(value, limit=limit).casefold()
    return (
        text.replace("á", "a")
        .replace("à", "a")
        .replace("ã", "a")
        .replace("â", "a")
        .replace("é", "e")
        .replace("ê", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ô", "o")
        .replace("õ", "o")
        .replace("ú", "u")
        .replace("ç", "c")
    )


def normalize_category(raw: object) -> str:
    text = _fold(raw)
    if not text:
        return ""
    if text in ALLOWED_CATEGORIES:
        return text
    for alias, canon in CATEGORY_ALIASES.items():
        if text == alias or text.endswith(alias) or alias in text.split():
            return canon
    return ""


def normalize_wine_style(raw: object) -> str:
    text = _fold(raw)
    if text in WINE_STYLES:
        return text
    if text in {"ros", "rosado"}:
        return "rose"
    return ""


def normalize_dish(raw: object) -> str:
    text = _fold(raw)
    if text in DISH_TOKENS:
        return text
    for dish, tokens in DISH_TOKENS.items():
        if text == dish or text in tokens:
            return dish
    return ""


def display_offer_title(title: str) -> str:
    """Remove repetição exata acidental. Não reescreve marca, safra nem volume."""
    words = [part for part in str(title or "").split() if part]
    if len(words) < 2:
        return " ".join(words)
    changed = True
    while changed and len(words) >= 2:
        changed = False
        for length in range(min(len(words) // 2, 6), 0, -1):
            rebuilt: list[str] = []
            index = 0
            collapsed = False
            while index < len(words):
                phrase = words[index : index + length]
                nxt = words[index + length : index + 2 * length]
                same = (
                    len(phrase) == length
                    and len(nxt) == length
                    and [item.casefold() for item in phrase] == [item.casefold() for item in nxt]
                )
                if same:
                    rebuilt.extend(phrase)
                    index += 2 * length
                    collapsed = True
                else:
                    rebuilt.append(words[index])
                    index += 1
            if collapsed:
                words = rebuilt
                changed = True
                break
    return " ".join(words)


def story_display_title(item: dict) -> str:
    name = str(item.get("name") or "").strip()
    custom = str(item.get("story_title") or "").strip()
    occasion = str(item.get("occasion") or "").strip() or "Sugestões"
    if custom and custom.casefold() != name.casefold():
        return custom
    return occasion


def _split_csv(raw: object) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, (list, tuple, set)):
        parts = [str(item) for item in raw]
    else:
        parts = str(raw).replace("|", ",").split(",")
    return [part.strip() for part in parts if str(part).strip()]


@dataclass(frozen=True)
class VitrineQuery:
    categories: tuple[str, ...] = ()
    wine_style: str = ""
    beer_style: str = ""
    potato_form: str = ""
    bread_slug: str = ""
    offer_ids: tuple[str, ...] = ()
    dishes: tuple[str, ...] = ()

    @property
    def useful(self) -> bool:
        return bool(
            self.categories
            or self.wine_style
            or self.beer_style
            or self.potato_form
            or self.offer_ids
            or self.bread_slug
            or self.dishes
        )

    @property
    def has_meal(self) -> bool:
        return bool(self.dishes)


def parse_vitrine_query(
    *,
    cats: object = "",
    tipo: object = "",
    pao: object = "",
    ids: object = "",
    mesa: object = "",
    categories: object = None,
    wine_style: object = "",
    beer_style: object = "",
    potato_form: object = "",
    forma: object = "",
    slug: object = "",
    dishes: object = None,
) -> VitrineQuery:
    found: list[str] = []
    for raw in _split_csv(categories if categories not in (None, "") else cats):
        canon = normalize_category(raw)
        if canon and canon not in found:
            found.append(canon)
    style = normalize_wine_style(wine_style or tipo)
    beer = _fold(beer_style)
    if beer not in BEER_STYLES:
        beer = ""
    form = _fold(potato_form or forma)
    if form not in POTATO_FORMS:
        form = ""
    bread = sanitize_plain_text(slug or pao, limit=80)
    offer_ids: list[str] = []
    for raw in _split_csv(ids):
        offer_id = sanitize_plain_text(raw, limit=80)
        if offer_id and offer_id not in offer_ids:
            offer_ids.append(offer_id)
    meal: list[str] = []
    for raw in _split_csv(dishes if dishes not in (None, "") else mesa):
        dish = normalize_dish(raw)
        if dish and dish not in meal:
            meal.append(dish)
    return VitrineQuery(
        categories=tuple(found),
        wine_style=style,
        beer_style=beer,
        potato_form=form,
        bread_slug=bread,
        offer_ids=tuple(offer_ids[:24]),
        dishes=tuple(meal[:6]),
    )


def build_vitrine_href(query: VitrineQuery) -> str:
    if not query.useful:
        return "/acompanhar"
    parts: list[str] = []
    if query.categories:
        parts.append("cats=" + ",".join(query.categories))
    if query.wine_style:
        parts.append(f"tipo={query.wine_style}")
    if query.beer_style:
        parts.append(f"cerveja={query.beer_style}")
    if query.potato_form:
        parts.append(f"forma={query.potato_form}")
    if query.dishes:
        parts.append("mesa=" + ",".join(query.dishes))
    if query.bread_slug:
        parts.append("pao=" + quote(query.bread_slug, safe="-"))
    if query.offer_ids:
        parts.append("ids=" + ",".join(query.offer_ids[:12]))
    return "/acompanhar?" + "&".join(parts)


def _matches_wine_style(card: dict, style: str) -> bool:
    tokens = WINE_STYLES.get(style) or ()
    hay = _fold(f"{card.get('name') or ''} {card.get('description') or ''}")
    if style == "tinto" and any(token in hay for token in WINE_STYLES["espumante"]):
        return False
    return any(token in hay for token in tokens)


def apply_vitrine_query(cards: list[dict], query: VitrineQuery) -> list[dict]:
    picked = list(cards)
    if query.offer_ids:
        by_id = {str(item.get("hub_offer_id") or ""): item for item in picked}
        picked = [by_id[offer_id] for offer_id in query.offer_ids if offer_id in by_id]
    if query.categories:
        picked = [item for item in picked if item.get("category") in query.categories]
    if query.wine_style:
        refined = []
        for item in picked:
            if item.get("category") == "vinhos":
                if _matches_wine_style(item, query.wine_style):
                    refined.append(item)
            else:
                refined.append(item)
        picked = refined
    if query.beer_style:
        tokens = BEER_STYLES.get(query.beer_style) or ()
        picked = [
            item
            for item in picked
            if item.get("category") != "cervejas" or any(token in _fold(f"{item.get('name') or ''} {item.get('description') or ''}") for token in tokens)
        ]
    if query.potato_form:
        tokens = POTATO_FORMS.get(query.potato_form) or ()
        exclude_chips = query.potato_form == "fritar"
        refined = []
        for item in picked:
            if item.get("category") != "batatas":
                refined.append(item)
                continue
            hay = _fold(f"{item.get('name') or ''} {item.get('description') or ''}")
            if exclude_chips and any(token in hay for token in POTATO_FORMS["chips"] + POTATO_FORMS["palha"]):
                continue
            if any(token in hay for token in tokens):
                refined.append(item)
        picked = refined
    if query.bread_slug:
        related = [
            item
            for item in picked
            if query.bread_slug in {str(slug) for slug in item.get("related_product_slugs") or []}
        ]
        if related:
            picked = related
    return picked


def select_contextual_cards(cards: list[dict], query: VitrineQuery) -> list[dict]:
    if not query.useful:
        return list(cards)
    grouped: dict[str, list[dict]] = {}
    appearance: list[str] = []
    for item in cards:
        key = str(item.get("category") or "_")
        if key not in grouped:
            grouped[key] = []
            appearance.append(key)
        if len(grouped[key]) < MAX_CONTEXTUAL_PER_CATEGORY:
            grouped[key].append(item)
    order = [cat for cat in query.categories if cat in grouped]
    for key in appearance:
        if key not in order:
            order.append(key)
    picked: list[dict] = []
    for key in order:
        picked.extend(grouped[key])
        if len(picked) >= MAX_CONTEXTUAL_ITEMS:
            return picked[:MAX_CONTEXTUAL_ITEMS]
    return picked


def meal_summary(query: VitrineQuery) -> str:
    labels = [DISH_LABELS[dish] for dish in query.dishes if dish in DISH_LABELS]
    if not labels:
        return ""
    if len(labels) == 1:
        return labels[0]
    return " e ".join([", ".join(labels[:-1]), labels[-1]])


def context_title(
    query: VitrineQuery,
    *,
    bread_name: str | None = None,
    used_bread: bool = False,
    raw_text: str = "",
) -> str:
    dishes = set(query.dishes)
    folded = _fold(raw_text, limit=400)
    if "hamburguer" in dishes:
        return "Para o hambúrguer"
    if "sardinha" in dishes and ("homus" in folded or "receita" in folded):
        return "Para acompanhar sardinhas com homus"
    if "sardinha" in dishes:
        return "Para acompanhar as sardinhas"
    if "frios" in dishes:
        return "Para sua mesa de frios"
    if "camarao" in dishes:
        return "Para acompanhar o camarão"
    if "lagosta" in dishes:
        return "Para acompanhar a lagosta"
    if "peixe" in dishes:
        return "Para acompanhar o peixe"
    if query.has_meal or used_bread:
        return "Sugestões para sua mesa"
    if query.categories or query.wine_style or query.offer_ids:
        return "Sugestões para sua mesa"
    return "Acompanhamentos sugeridos"


def context_filters(query: VitrineQuery, *, bread_name: str | None = None, used_bread: bool = False) -> list[dict[str, str]]:
    filters: list[dict[str, str]] = []
    seen: set[str] = set()
    if used_bread and bread_name:
        filters.append({"key": "pao", "label": bread_name})
        seen.add(bread_name.casefold())
    for dish in query.dishes:
        label = DISH_LABELS.get(dish, dish)
        if label.casefold() not in seen:
            filters.append({"key": "mesa", "label": label})
            seen.add(label.casefold())
    if query.wine_style:
        label = WINE_STYLE_LABELS[query.wine_style]
        if label.casefold() not in seen:
            filters.append({"key": "tipo", "label": label})
            seen.add(label.casefold())
            seen.add("vinhos")
    if query.beer_style:
        label = BEER_STYLE_LABELS[query.beer_style]
        if label.casefold() not in seen:
            filters.append({"key": "cerveja", "label": label})
            seen.add(label.casefold())
            seen.add("cervejas")
    if query.potato_form:
        label = POTATO_FORM_LABELS[query.potato_form]
        if label.casefold() not in seen:
            filters.append({"key": "forma", "label": label})
            seen.add(label.casefold())
    for category in query.categories:
        if category == "vinhos" and query.wine_style:
            continue
        label = ALLOWED_CATEGORIES[category]
        if label.casefold() not in seen:
            filters.append({"key": "cats", "label": label})
            seen.add(label.casefold())
    return filters


def describe_context(
    query: VitrineQuery,
    cards: list[dict],
    *,
    bread_name: str | None = None,
    raw_text: str = "",
) -> dict:
    used_bread = bool(
        query.bread_slug
        and any(query.bread_slug in {str(slug) for slug in item.get("related_product_slugs") or []} for item in cards)
    )
    summary = meal_summary(query)
    if used_bread and bread_name:
        summary = f"{bread_name} com {summary}" if summary else bread_name
    return {
        "active": query.useful,
        "empty": query.useful and not cards,
        "title": context_title(query, bread_name=bread_name, used_bread=used_bread, raw_text=raw_text),
        "summary": summary or None,
        "filters": context_filters(query, bread_name=bread_name, used_bread=used_bread),
        "clear_href": "/acompanhar",
        "href": build_vitrine_href(query),
        "bread_name": bread_name if used_bread else None,
    }


def infer_categories_from_text(text: str) -> list[str]:
    folded = _fold(text, limit=2000)
    found: list[str] = []
    for alias, canon in (
        ("vinho", "vinhos"),
        ("queijo", "queijos"),
        ("frio", "frios"),
        ("presunto", "frios"),
        ("azeite", "azeites"),
        ("cerveja", "cervejas"),
        ("batata", "batatas"),
    ):
        if alias in folded and canon not in found:
            found.append(canon)
    return found


def infer_wine_style_from_text(text: str) -> str:
    folded = _fold(text, limit=2000)
    for style, tokens in WINE_STYLES.items():
        if any(token in folded for token in tokens):
            return style
    return ""


def infer_dishes_from_text(text: str) -> list[str]:
    folded = _fold(text, limit=2000)
    found: list[str] = []
    for dish, tokens in DISH_TOKENS.items():
        if any(token in folded for token in tokens) and dish not in found:
            found.append(dish)
    seafood = {"sardinha", "camarao", "lagosta"}
    if seafood & set(found) and "peixe" in found:
        found = [item for item in found if item != "peixe"]
    return found


def infer_exclusions_from_text(text: str) -> set[str]:
    folded = _fold(text, limit=2000)
    excluded: set[str] = set()
    if any(token in folded for token in NO_ALCOHOL):
        excluded.add("vinhos")
        excluded.add("cervejas")
    if any(token in folded for token in NO_CHEESE):
        excluded.add("queijos")
    if any(token in folded for token in NO_MEAT):
        excluded.add("frios")
    return excluded


def _asks_table(text: str) -> bool:
    folded = _fold(text, limit=2000)
    return any(token in folded for token in TABLE_ASK)


def _is_support_turn(text: str) -> bool:
    folded = _fold(text, limit=2000)
    if _asks_table(folded) or infer_dishes_from_text(folded) or infer_categories_from_text(folded):
        return False
    return any(token in folded for token in SUPPORT_ONLY)


def _asks_only_wine(text: str) -> bool:
    folded = _fold(text, limit=2000)
    if any(token in folded for token in ONLY_WINE):
        return True
    has_wine = any(token in folded for token in ASKS_WINE)
    has_other = any(token in folded for token in (*ASKS_CHEESE, "azeite", "frio", "presunto", "cerveja", "batata"))
    return has_wine and not has_other and not _asks_table(folded)


def _asks_only_cheese(text: str) -> bool:
    folded = _fold(text, limit=2000)
    return any(token in folded for token in ONLY_CHEESE)


def _asks_only_drinks(text: str) -> bool:
    folded = _fold(text, limit=2000)
    return any(token in folded for token in ONLY_DRINKS)


def _asks_drinks(text: str) -> bool:
    """Pedido de bebida. Pão, queijo ou batata na mesma frase mantêm a refeição."""
    if _asks_only_drinks(text):
        return True
    folded = _fold(text, limit=2000)
    if not any(token in folded for token in ("bebida", "para beber", "o que beber", "que beber")):
        return False
    if any(token in folded for token in ("pao", "pão", "queijo", "batata", "frios", "azeite", "presunto")):
        return False
    return True


def _styles_in(text: str) -> list[str]:
    folded = _fold(text, limit=2000)
    return [style for style, tokens in WINE_STYLES.items() if any(token in folded for token in tokens)]


def infer_potato_form_from_text(text: str) -> str:
    folded = _fold(text, limit=2000)
    if any(token in folded for token in NO_CHIPS) or ("fritar" in folded and "chips" in folded):
        return "fritar"
    if "batata palha" in folded:
        return "palha"
    if "chips" in folded and "fritar" not in folded:
        return "chips"
    if "fritar" in folded or "pre-frita" in folded or "congelada" in folded:
        return "fritar"
    return ""


def infer_beer_style_from_text(text: str) -> str:
    folded = _fold(text, limit=2000)
    for style, tokens in BEER_STYLES.items():
        if any(token in folded for token in tokens):
            return style
    return ""


def _prior_user_text(history: list[dict] | None) -> str:
    if not history:
        return ""
    parts = [str(item.get("content") or "") for item in history if item.get("role") == "user"]
    return " ".join(parts)


def _is_guide_score_turn(text: str) -> bool:
    folded = _fold(text, limit=2000)
    if not any(token in folded for token in GUIDE_SCORE_ASK):
        return False
    if _asks_table(folded) or infer_dishes_from_text(folded):
        return False
    return True


def infer_suggested_query(
    *,
    user_text: str = "",
    reply: str = "",
    history: list[dict] | None = None,
) -> VitrineQuery:
    if _is_support_turn(user_text):
        return VitrineQuery()
    if _is_guide_score_turn(user_text):
        return VitrineQuery()
    prior = _prior_user_text(history)
    conversation = f"{prior} {user_text}".strip()
    current_dishes = infer_dishes_from_text(user_text)
    dishes = current_dishes or infer_dishes_from_text(conversation)
    excluded = infer_exclusions_from_text(conversation)
    user_cats = infer_categories_from_text(user_text)
    reply_cats = infer_categories_from_text(reply)
    if "azeites" in reply_cats and "azeites" not in user_cats and not dishes:
        reply_cats = [item for item in reply_cats if item != "azeites"]
    categories: list[str] = []
    for item in [*user_cats, *reply_cats]:
        if item not in categories:
            categories.append(item)
    only_wine = _asks_only_wine(user_text)
    if _asks_only_cheese(user_text):
        categories = ["queijos"]
        return parse_vitrine_query(categories=categories, wine_style="", dishes=dishes)
    if _asks_drinks(user_text):
        drink_cats: list[str] = []
        for item in (*user_cats, *reply_cats):
            if item in {"vinhos", "cervejas"} and item not in excluded and item not in drink_cats:
                drink_cats.append(item)
        if (_styles_in(user_text) or _styles_in(reply)) and "vinhos" not in excluded and "vinhos" not in drink_cats:
            drink_cats.append("vinhos")
        folded_user = _fold(user_text, limit=2000)
        if any(token in folded_user for token in ("prefiro cerveja", "so cerveja", "só cerveja", "somente cerveja")):
            drink_cats = [] if "cervejas" in excluded else ["cervejas"]
        if any(token in folded_user for token in ("so tinto", "só tinto", "somente tinto", "apenas tinto")):
            drink_cats = [] if "vinhos" in excluded else ["vinhos"]
        if not drink_cats:
            return VitrineQuery()
        style = ""
        if "vinhos" in drink_cats and "vinhos" not in excluded:
            user_styles = _styles_in(user_text)
            reply_styles = _styles_in(reply)
            if any(token in folded_user for token in ("so tinto", "só tinto", "somente tinto", "apenas tinto")):
                style = "tinto"
            elif len(user_styles) == 1:
                style = user_styles[0]
            elif len(reply_styles) == 1:
                style = reply_styles[0]
        return parse_vitrine_query(
            categories=drink_cats,
            wine_style=style,
            beer_style=infer_beer_style_from_text(user_text) if "cervejas" in drink_cats else "",
            potato_form="",
            dishes=dishes,
        )
    if only_wine:
        categories = [item for item in categories if item == "vinhos"] or ["vinhos"]
        if "queijos" not in reply_cats:
            categories = [item for item in categories if item != "queijos"]
    elif dishes and (_asks_table(user_text) or _asks_table(conversation)) and not reply_cats and not user_cats:
        for dish in dishes:
            for category in MEAL_COMPLEMENTS.get(dish, ("vinhos", "queijos", "azeites")):
                if category not in categories:
                    categories.append(category)
    elif dishes and _asks_table(user_text) and not only_wine:
        for dish in dishes:
            for category in MEAL_COMPLEMENTS.get(dish, ("vinhos", "queijos", "azeites")):
                if category not in categories:
                    categories.append(category)
    if "hamburguer" in dishes and not only_wine:
        for category in MEAL_COMPLEMENTS["hamburguer"]:
            if category not in categories and category not in excluded:
                categories.append(category)
    categories = [item for item in categories if item not in excluded]
    folded_user = _fold(user_text, limit=2000)
    folded_reply = _fold(reply, limit=2000)
    folded_meal = _fold(f"{conversation} {reply}", limit=2000)
    if "hamburguer" in dishes and any(token in folded_meal for token in ("bebida", "cerveja")):
        if "cervejas" not in categories and "cervejas" not in excluded:
            categories.append("cervejas")
    if "hamburguer" in dishes and "batata" in folded_meal:
        if "batatas" not in categories and "batatas" not in excluded:
            categories.append("batatas")
    if "hamburguer" in dishes and "queijo" not in folded_user and "queijo" not in folded_reply:
        categories = [item for item in categories if item != "queijos"]
    seafood = {"sardinha", "camarao", "lagosta", "peixe"}
    if seafood & set(dishes) and "cerveja" not in folded_user:
        categories = [item for item in categories if item != "cervejas"]
    if "hamburguer" in dishes:
        meal_keep = {"cervejas", "batatas"}
        if "queijo" in folded_user or "queijo" in folded_reply:
            meal_keep.add("queijos")
        if any(token in folded_user for token in ASKS_WINE):
            meal_keep.add("vinhos")
        if "azeite" in folded_user:
            meal_keep.add("azeites")
        categories = [item for item in categories if item in meal_keep]
    if "frios" in dishes and not any(token in folded_user for token in ASKS_WINE):
        categories = [item for item in categories if item != "vinhos"]
    user_style = infer_wine_style_from_text(user_text)
    style = user_style if user_style and "vinhos" not in excluded else ""
    if any(token in folded_user for token in ("so tinto", "só tinto", "somente tinto", "apenas tinto")) and "vinhos" not in excluded:
        categories = ["vinhos"]
        style = "tinto"
    elif any(token in folded_user for token in ("prefiro cerveja",)) and "cervejas" not in excluded and "hamburguer" not in dishes:
        categories = ["cervejas"]
    beer = infer_beer_style_from_text(user_text) if "cervejas" not in excluded else ""
    potato = infer_potato_form_from_text(conversation)
    return parse_vitrine_query(
        categories=categories,
        wine_style=style,
        beer_style=beer,
        potato_form=potato,
        dishes=dishes,
    )


def inactive_context() -> dict:
    return {
        "active": False,
        "empty": False,
        "title": None,
        "summary": None,
        "filters": [],
        "clear_href": "/acompanhar",
        "href": "/acompanhar",
        "bread_name": None,
    }
