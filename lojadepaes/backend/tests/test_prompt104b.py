"""104B: catálogo consultado primeiro; alternativa do mesmo perfil; bebida sem comida."""

from app.domain.accompaniment_context import apply_vitrine_query, infer_suggested_query
from app.domain.accompaniments import GENERIC_CTA, SUGGESTED_CTA, gigio_lookup
from app.domain.gigio.pairing import publish_authorized_pilot
from app.domain.gigio.pairing_match import catalog_match_tier, compatible_offer_ids
from app.core.config import get_settings
from sqlalchemy.orm import Session
from tests.test_prompt73 import _mock_hub, _offer
from tests.test_prompt77 import _enable
from tests.test_prompt81 import _enable_pairing


def _wine_refs() -> tuple[dict, dict]:
    product = {
        "category": "vinhos",
        "scope": "product",
        "match_hints": ["albarino", "albariño"],
        "retrieval_role": "pairing",
        "evidence_type": "pairing_recommendation",
        "verification_status": "verified",
        "editorial_status": "published",
        "identity": {"brand": "Pazos", "line": "Albariño"},
    }
    style = {
        "category": "vinhos",
        "scope": "style",
        "match_hints": ["albarino", "albariño"],
        "retrieval_role": "pairing",
        "evidence_type": "pairing_recommendation",
        "verification_status": "verified",
        "editorial_status": "published",
        "identity": {},
    }
    return product, style


def test_catalog_suggestion_precedes_style_alternative() -> None:
    product, style = _wine_refs()
    named = {
        "hub_offer_id": "Z",
        "title": "Pazos Albariño Rias Baixas 750ml",
        "category": "vinhos",
        "brand": "Pazos",
    }
    other = {"hub_offer_id": "Y", "title": "Outro Albariño 750ml", "category": "vinhos"}
    cheese = {"hub_offer_id": "Q", "title": "Queijo gorgonzola", "category": "queijos"}
    ids, tier = catalog_match_tier([named, other, cheese], [product, style])
    assert tier == "specific"
    assert ids == ["Z"]
    ids, tier = catalog_match_tier([other, cheese], [product, style])
    assert tier == "style"
    assert ids == ["Y"]
    ids, tier = catalog_match_tier([cheese], [style])
    assert ids == []
    assert tier == "none"
    assert compatible_offer_ids([named, other], [style]) == ["Z", "Y"]


def test_drinks_follow_the_reply_and_leave_food_out() -> None:
    history = [{"role": "user", "content": "Vou servir carneiro assado."}]
    wine = infer_suggested_query(
        user_text="E as bebidas?",
        reply="Um tinto encorpado acompanha o assado.",
        history=history,
    )
    assert wine.categories == ("vinhos",)
    assert wine.wine_style == "tinto"
    assert "queijos" not in wine.categories
    assert "cervejas" not in wine.categories
    both = infer_suggested_query(
        user_text="E as bebidas?",
        reply="Pode ser um tinto ou uma cerveja lager.",
        history=history,
    )
    assert set(both.categories) == {"vinhos", "cervejas"}
    assert "queijos" not in both.categories
    assert both.wine_style == "tinto"


def test_drink_preferences_replace_the_previous_cut() -> None:
    history = [{"role": "user", "content": "E as bebidas para o assado?"}]
    red = infer_suggested_query(user_text="só tinto", reply="Então o tinto.", history=history)
    assert red.categories == ("vinhos",)
    assert red.wine_style == "tinto"
    beer = infer_suggested_query(user_text="prefiro cerveja", reply="Uma lager então.", history=history)
    assert beer.categories == ("cervejas",)
    assert "vinhos" not in beer.categories
    dry = infer_suggested_query(user_text="sem álcool", reply="Água com gás.", history=history)
    assert "vinhos" not in dry.categories
    assert "cervejas" not in dry.categories
    cards = [
        {"hub_offer_id": "T", "name": "Malbec tinto 750ml", "category": "vinhos"},
        {"hub_offer_id": "C", "name": "Cava Brut Reserva", "category": "vinhos"},
        {"hub_offer_id": "B", "name": "Cerveja lager", "category": "cervejas"},
        {"hub_offer_id": "Q", "name": "Queijo gorgonzola", "category": "queijos"},
    ]
    picked = apply_vitrine_query(cards, red)
    assert [item["hub_offer_id"] for item in picked] == ["T"]


def test_unmatched_catalog_does_not_become_the_suggested_shelf(db: Session, monkeypatch) -> None:
    _enable(monkeypatch)
    _enable_pairing(monkeypatch)
    publish_authorized_pilot(db)
    _mock_hub(
        monkeypatch,
        [
            _offer(id="MLBVINHO1", title="Vinho tinto da mesa", category="vinhos", link="https://www.mercadolivre.com.br/p/MLBVINHO1"),
            _offer(id="MLBQUEIJO1", title="Queijo gorgonzola", category="queijos", link="https://www.mercadolivre.com.br/p/MLBQUEIJO1"),
        ],
    )
    empty = gigio_lookup(
        db,
        get_settings(),
        categories=["vinhos"],
        dishes=["sardinha"],
        query_text="sardinhas",
    )
    assert empty["hub_status"] == "no_match"
    assert empty["cta"] is None
    assert empty.get("cta", {}) != {"label": SUGGESTED_CTA}
    broad = gigio_lookup(
        db,
        get_settings(),
        categories=["vinhos", "azeites"],
        dishes=["sardinha"],
        query_text="sardinhas",
    )
    assert broad["cta"]["label"] == GENERIC_CTA
    assert broad["cta"]["href"] == "/acompanhar"
    assert broad["cta"]["label"] != SUGGESTED_CTA
