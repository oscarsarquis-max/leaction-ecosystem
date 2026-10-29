from app.core.config import get_settings
from app.domain.accompaniment_context import (
    apply_vitrine_query,
    display_offer_title,
    infer_suggested_query,
    parse_vitrine_query,
    select_contextual_cards,
)
from app.domain.accompaniments import gigio_lookup, public_catalog
from app.domain.gigio.service import chat
from app.domain.marketplace_links import marketplace_price_prep
from sqlalchemy.orm import Session
from tests.test_prompt73 import _mock_hub, _offer
from tests.test_prompt77 import _TextOnlyGateway, _catalog, _enable


def test_display_title_collapses_exact_repetition() -> None:
    assert display_offer_title("Vinho Tinto Vinho Tinto Português Alto Da Capela 2016 750ml") == (
        "Vinho Tinto Português Alto Da Capela 2016 750ml"
    )
    assert display_offer_title("Queijo Canastra 500g") == "Queijo Canastra 500g"


def test_meal_ask_without_wine_word_opens_table_cta(db: Session, monkeypatch) -> None:
    _catalog(db, monkeypatch)
    _enable(monkeypatch)
    monkeypatch.setenv("LOJADEPAES_GIGIO_ENABLED", "true")
    get_settings.cache_clear()
    result = chat(
        db,
        get_settings(),
        messages=[
            {
                "role": "user",
                "content": "Vou servir leitão com saladas. Que pão e acompanhamentos você sugere?",
            }
        ],
        page={"path": "/"},
        order_token=None,
        is_admin=False,
        gateway=_TextOnlyGateway(
            "Para o leitão, um pão de crosta firme segura o suco. "
            "Para completar a mesa, um vinho, um queijo para a tábua e azeite no pão."
        ),
    )
    assert result["cta"]["label"] == "Ver acompanhamentos sugeridos"
    href = result["cta"]["href"]
    assert "mesa=leitao,salada" in href
    assert "cats=" in href
    assert "vinhos" in href
    assert "queijos" in href
    assert "tipo=tinto" not in href
    catalog = public_catalog(db, get_settings(), cats="vinhos,queijos,azeites", mesa="leitao,salada")
    assert catalog["title"] == "Sugestões para sua mesa"
    assert catalog["context"]["summary"] == "leitão e saladas"
    labels = [item["label"] for item in catalog["context"]["filters"]]
    assert labels.count("Vinhos") == 1
    assert "vinho tinto" not in labels


def test_wine_followup_keeps_meal_and_does_not_expand_cheese(db: Session, monkeypatch) -> None:
    _catalog(db, monkeypatch)
    _enable(monkeypatch)
    first = infer_suggested_query(
        user_text="Vou servir leitão com saladas. Que pão e acompanhamentos você sugere?",
        reply="Comece pelo pão de fermentação. Para completar a mesa, vinho, queijo e azeite.",
    )
    second = infer_suggested_query(
        user_text="E um vinho?",
        reply="Um vinho de corpo médio acompanha o leitão. Sugestão do Gigio, sem prova certificada.",
        history=[
            {
                "role": "user",
                "content": "Vou servir leitão com saladas. Que pão e acompanhamentos você sugere?",
            }
        ],
    )
    assert "queijos" in first.categories
    assert second.categories == ("vinhos",)
    assert second.dishes == ("leitao", "salada")
    assert second.wine_style == ""
    lookup = gigio_lookup(
        db,
        get_settings(),
        categories=second.categories,
        dishes=second.dishes,
    )
    assert lookup["available"] is True
    assert "cats=vinhos" in lookup["cta"]["href"]
    assert "queijos" not in lookup["cta"]["href"]
    assert "mesa=leitao,salada" in lookup["cta"]["href"]


def test_cheese_followup_and_exclusions(db: Session, monkeypatch) -> None:
    _catalog(db, monkeypatch)
    _enable(monkeypatch)
    cheese = infer_suggested_query(
        user_text="Um queijo também faria sentido?",
        reply="Na tábua, ao lado, não sobre o porco. Sugestão do Gigio.",
        history=[{"role": "user", "content": "Vou servir leitão com saladas."}],
    )
    assert cheese.categories == ("queijos",)
    only_wine = infer_suggested_query(
        user_text="Só vinho, sem queijo",
        reply="Fico só no vinho para esta mesa.",
        history=[{"role": "user", "content": "leitão com saladas"}],
    )
    assert only_wine.categories == ("vinhos",)
    no_alcohol = infer_suggested_query(
        user_text="sem álcool",
        reply="Sem vinho. Azeite no pão e um queijo na tábua.",
        history=[{"role": "user", "content": "leitão com saladas, acompanhamentos"}],
    )
    assert "vinhos" not in no_alcohol.categories
    assert "queijos" in no_alcohol.categories


def test_story_header_is_not_the_first_product_name(db: Session, monkeypatch) -> None:
    _catalog(db, monkeypatch)
    _enable(monkeypatch)
    payload = public_catalog(db, get_settings(), cats="vinhos")
    assert payload["title"] == "Sugestões para sua mesa"
    for story in payload["stories"]:
        names = {item["name"] for item in story["items"]}
        assert story["title"] not in names
    assert payload["items"][0]["name"] != payload["stories"][0]["title"]


def test_contextual_selection_does_not_pad_to_twelve(db: Session, monkeypatch) -> None:
    extras = [
        _offer(id=f"MLBVINHO{index}", title=f"Vinho da casa {index} 750ml", category="vinhos")
        for index in range(2, 14)
    ]
    _mock_hub(monkeypatch, [_offer(id="MLBVINHO1", title="Vinho da casa 1 750ml", category="vinhos"), *extras])
    _enable(monkeypatch)
    payload = public_catalog(db, get_settings(), cats="vinhos")
    assert 0 < len(payload["items"]) <= 3


def test_sparkling_is_not_red_wine() -> None:
    cards = [
        {"hub_offer_id": "1", "name": "Espumante brut 750ml", "category": "vinhos", "description": ""},
        {"hub_offer_id": "2", "name": "Vinho tinto da mesa 750ml", "category": "vinhos", "description": ""},
    ]
    query = parse_vitrine_query(cats="vinhos", tipo="tinto")
    matched = apply_vitrine_query(cards, query)
    assert [item["name"] for item in matched] == ["Vinho tinto da mesa 750ml"]


def test_price_preposition_is_no_for_mercado_livre() -> None:
    assert marketplace_price_prep("mercadolivre") == "no"
    assert marketplace_price_prep("amazon") == "na"


def test_select_contextual_keeps_few_correct_items() -> None:
    cards = [
        {"hub_offer_id": "w1", "name": "Vinho A", "category": "vinhos"},
        {"hub_offer_id": "w2", "name": "Vinho B", "category": "vinhos"},
        {"hub_offer_id": "w3", "name": "Vinho C", "category": "vinhos"},
        {"hub_offer_id": "w4", "name": "Vinho D", "category": "vinhos"},
        {"hub_offer_id": "q1", "name": "Queijo A", "category": "queijos"},
    ]
    picked = select_contextual_cards(cards, parse_vitrine_query(cats="vinhos,queijos"))
    assert [item["hub_offer_id"] for item in picked] == ["w1", "w2", "w3", "q1"]
