from app.core.config import get_settings
from app.domain.accompaniment_context import (
    apply_vitrine_query,
    infer_suggested_query,
    parse_vitrine_query,
    select_contextual_cards,
)
from app.domain.accompaniments import SUGGESTED_CTA, gigio_lookup, public_catalog
from app.domain.gigio.fake import _choose_tool
from app.domain.gigio.rules import PROCESS_RULES, PROCESS_RULES_VERSION
from app.domain.gigio.service import chat
from app.domain.offer_contract import offer_fits_contract
from sqlalchemy.orm import Session
from tests.test_prompt73 import _mock_hub, _offer
from tests.test_prompt77 import _TextOnlyGateway, _enable
from tests.test_prompt81 import _enable_pairing

HAMBURGER_Q = (
    "queremos fazer um hamburguer bem legal, com batatas e molho. "
    "que sugestao de acompanhamento vc poderia me dar? "
    "que tipo de pao vc aconselha? e que bebidas ficariam bem?"
)

HAMBURGER_REPLY = (
    "Não há pão específico de hambúrguer no catálogo publicado. "
    "Se quiser adaptar, use um pão de leite macio se estiver disponível. "
    "As batatas da proposta ficam bem palito pré-fritas ou no forno; molho à parte. "
    "Para completar a mesa, cerveja pilsen ou lager gelada."
)


def _board(db: Session, monkeypatch, extra: list | None = None) -> list:
    offers = [
        _offer(id="MLBCERV1", title="Cerveja Pilsen lata 350ml", category="cervejas", link="https://www.mercadolivre.com.br/p/MLBCERV1"),
        _offer(id="MLBCERV2", title="Cerveja IPA long neck 355ml", category="cervejas", link="https://www.mercadolivre.com.br/p/MLBCERV2"),
        _offer(id="MLBBAT1", title="Batata palito pré-frita congelada 1kg", category="batatas", link="https://www.mercadolivre.com.br/p/MLBBAT1"),
        _offer(id="MLBBAT2", title="Batata chips lisa 60g", category="batatas", link="https://www.mercadolivre.com.br/p/MLBBAT2"),
        _offer(id="MLBBAT3", title="Batata palha extrafina 100g", category="batatas", link="https://www.mercadolivre.com.br/p/MLBBAT3"),
        _offer(id="MLBQUEIJO1", title="Queijo Canastra meia cura", category="queijos", link="https://www.mercadolivre.com.br/p/MLBQUEIJO1"),
        _offer(id="MLBQUEIJO2", title="Queijo Canastra artesanal", category="queijos", link="https://www.mercadolivre.com.br/p/MLBQUEIJO2"),
        _offer(id="MLBQUEIJO3", title="Queijo Canastra da serra", category="queijos", link="https://www.mercadolivre.com.br/p/MLBQUEIJO3"),
        _offer(id="MLBVINHO1", title="Vinho tinto da mesa 750ml", category="vinhos", link="https://www.mercadolivre.com.br/p/MLBVINHO1"),
        _offer(id="MLBAZEITE1", title="Azeite português extra virgem", category="azeites", link="https://www.mercadolivre.com.br/p/MLBAZEITE1"),
        _offer(id="MLBFRIOS1", title="Presunto cru fatiado 200g", category="frios", link="https://www.mercadolivre.com.br/p/MLBFRIOS1"),
        _offer(
            id="MLBGHOST",
            title="Cerveja artesanal indisponível",
            category="cervejas",
            link="https://www.mercadolivre.com.br/p/MLBGHOST",
            availability_verified=False,
        ),
    ]
    if extra:
        offers.extend(extra)
    _mock_hub(monkeypatch, offers)
    _enable(monkeypatch)
    _enable_pairing(monkeypatch)
    return offers


def test_rules_version_is_current() -> None:
    assert int(PROCESS_RULES_VERSION) >= 87
    assert "lookup_products" in PROCESS_RULES
    assert "hambúrguer" in PROCESS_RULES.casefold() or "hamburguer" in PROCESS_RULES.casefold()
    assert "sem álcool exclui vinho e cerveja" in PROCESS_RULES.casefold()


def test_nature_rejects_beer_accessories_and_potato_nonfood() -> None:
    assert offer_fits_contract(title="Cerveja Pilsen lata 350ml", category="cervejas")
    assert not offer_fits_contract(title="Copo de cerveja tulipa 400ml", category="cervejas")
    assert not offer_fits_contract(title="Camiseta cerveja artesanal", category="cervejas")
    assert not offer_fits_contract(title="Kit fabricação de cerveja caseira", category="cervejas")
    assert offer_fits_contract(title="Batata palito pré-frita congelada 1kg", category="batatas")
    assert offer_fits_contract(title="Batata chips lisa 60g", category="batatas")
    assert not offer_fits_contract(title="Semente de batata para plantio", category="batatas")
    assert not offer_fits_contract(title="Brinquedo pelúcia batata", category="batatas")
    assert not offer_fits_contract(title="Cortador de batata palito", category="batatas")
    assert not offer_fits_contract(title="Fatiador Batata Palito Frita", category="batatas")
    assert not offer_fits_contract(title="Almofada Divertida Batata Palito 40x40", category="batatas")
    assert not offer_fits_contract(title="Pá Para Batata Palito Em Inox Pegador", category="batatas")


def test_hamburger_question_selects_beer_and_potato_not_cheese() -> None:
    query = infer_suggested_query(user_text=HAMBURGER_Q, reply=HAMBURGER_REPLY)
    assert query.dishes == ("hamburguer",)
    assert "cervejas" in query.categories
    assert "batatas" in query.categories
    assert "queijos" not in query.categories
    assert "vinhos" not in query.categories
    oil_reply = infer_suggested_query(
        user_text=HAMBURGER_Q,
        reply="Asse as batatas com azeite e alecrim. Cerveja pilsen gelada.",
    )
    assert "azeites" not in oil_reply.categories
    assert "cervejas" in oil_reply.categories
    assert "batatas" in oil_reply.categories


def test_hamburger_does_not_need_marketplace_word() -> None:
    query = infer_suggested_query(user_text=HAMBURGER_Q, reply=HAMBURGER_REPLY)
    assert "marketplace" not in HAMBURGER_Q
    assert query.useful is True


def test_followups_change_criteria_without_reusing_full_meal(db: Session, monkeypatch) -> None:
    _board(db, monkeypatch)
    history = [{"role": "user", "content": HAMBURGER_Q}]
    prefer = infer_suggested_query(
        user_text="prefiro cerveja",
        reply="Então cerveja com as batatas.",
        history=history,
    )
    assert "cervejas" in prefer.categories
    assert "batatas" in prefer.categories
    no_alcohol = infer_suggested_query(
        user_text="sem álcool",
        reply="Água, suco ou refrigerante. Sem cerveja e sem vinho.",
        history=history,
    )
    assert "cervejas" not in no_alcohol.categories
    assert "vinhos" not in no_alcohol.categories
    assert "batatas" in no_alcohol.categories
    fry = infer_suggested_query(
        user_text="quero batatas para fritar, não chips",
        reply="Então batata palito pré-frita, sem chips.",
        history=history,
    )
    assert fry.potato_form == "fritar"
    drinks = infer_suggested_query(
        user_text="só as bebidas",
        reply="Só as cervejas então.",
        history=history,
    )
    assert drinks.categories == ("cervejas",)
    assert "batatas" not in drinks.categories


def test_lookup_and_catalog_use_verified_beer_and_potato(db: Session, monkeypatch) -> None:
    _board(db, monkeypatch)
    result = chat(
        db,
        get_settings(),
        messages=[{"role": "user", "content": HAMBURGER_Q}],
        page={"path": "/"},
        order_token=None,
        is_admin=False,
        gateway=_TextOnlyGateway(HAMBURGER_REPLY),
    )
    assert result["cta"]
    assert result["cta"]["label"] == SUGGESTED_CTA
    href = result["cta"]["href"]
    assert "cervejas" in href
    assert "batatas" in href
    assert "queijos" not in href
    assert "marketplace" not in href
    lookup = gigio_lookup(
        db,
        get_settings(),
        categories=["cervejas", "batatas"],
        dishes=["hamburguer"],
        query_text=HAMBURGER_Q,
    )
    names = [item["name"] for item in lookup["items"]]
    cats = {item["category"] for item in lookup["items"]}
    assert "cervejas" in cats
    assert "batatas" in cats
    assert "queijos" not in cats
    assert "Cerveja artesanal indisponível" not in names
    assert "Queijo Canastra meia cura" not in names
    catalog = public_catalog(db, get_settings(), cats="cervejas,batatas", mesa="hamburguer")
    assert catalog["title"] == "Para o hambúrguer"
    assert catalog["context"]["title"] == "Para o hambúrguer"
    shown = [item["name"] for item in catalog["items"]]
    assert any("Cerveja" in name for name in shown)
    assert any("Batata" in name for name in shown)
    assert not any("Canastra" in name for name in shown)
    occasions = {story["occasion"] for story in catalog["stories"]}
    assert "Mesa de fim de tarde" not in occasions
    assert shown[0] not in {story["title"] for story in catalog["stories"]}


def test_unverified_and_stale_ids_stay_out(db: Session, monkeypatch) -> None:
    _board(db, monkeypatch)
    ghost = public_catalog(db, get_settings(), ids="MLBGHOST")
    assert ghost["items"] == []
    assert ghost["context"]["empty"] is True
    missing = gigio_lookup(db, get_settings(), categories=["cervejas"], ids=["MLBGHOST"])
    assert missing["available"] is False or all(item["id"] != "MLBGHOST" for item in missing["items"])


def test_fry_form_excludes_chips(db: Session, monkeypatch) -> None:
    _board(db, monkeypatch)
    catalog = public_catalog(db, get_settings(), cats="batatas", forma="fritar")
    names = " ".join(item["name"] for item in catalog["items"]).casefold()
    assert "pré-frita" in names or "pre-frita" in names or "congelada" in names
    assert "chips" not in names
    assert "palha" not in names


def test_select_does_not_let_one_category_monopolize() -> None:
    cards = [
        *[{"name": f"Queijo {i}", "category": "queijos"} for i in range(6)],
        {"name": "Cerveja Pilsen lata 350ml", "category": "cervejas"},
        {"name": "Batata palito pré-frita congelada 1kg", "category": "batatas"},
    ]
    picked = select_contextual_cards(cards, parse_vitrine_query(cats="cervejas,batatas,queijos"))
    cats = [item["category"] for item in picked]
    assert "cervejas" in cats
    assert "batatas" in cats
    assert cats[0] == "cervejas"


def test_no_alcohol_drops_beer_from_results(db: Session, monkeypatch) -> None:
    _board(db, monkeypatch)
    result = chat(
        db,
        get_settings(),
        messages=[
            {"role": "user", "content": HAMBURGER_Q},
            {"role": "assistant", "content": HAMBURGER_REPLY},
            {"role": "user", "content": "sem álcool"},
        ],
        page={"path": "/"},
        order_token=None,
        is_admin=False,
        gateway=_TextOnlyGateway("Água ou suco. Sem cerveja e sem vinho. As batatas continuam."),
    )
    assert result["cta"] is None
    assert result["access"]["deepen_offer"] is True
    assert result["access"]["charged"] is False


def test_operational_question_has_no_culinary_cta(db: Session, monkeypatch) -> None:
    _board(db, monkeypatch)
    result = chat(
        db,
        get_settings(),
        messages=[{"role": "user", "content": "Como acompanho meu pedido LP-123?"}],
        page={"path": "/"},
        order_token=None,
        is_admin=False,
        gateway=_TextOnlyGateway("Use o link protegido que você recebeu."),
    )
    assert result["cta"] is None


def test_hamburger_fake_consults_catalog_for_bread() -> None:
    tool = _choose_tool(HAMBURGER_Q)
    assert tool is not None
    assert tool["name"] == "lookup_products"


def test_partial_miss_notice_is_honest(db: Session, monkeypatch) -> None:
    _mock_hub(
        monkeypatch,
        [
            _offer(id="MLBCERV1", title="Cerveja Pilsen lata 350ml", category="cervejas", link="https://www.mercadolivre.com.br/p/MLBCERV1"),
            _offer(id="MLBQUEIJO1", title="Queijo Canastra meia cura", category="queijos", link="https://www.mercadolivre.com.br/p/MLBQUEIJO1"),
        ],
    )
    _enable(monkeypatch)
    _enable_pairing(monkeypatch)
    lookup = gigio_lookup(
        db,
        get_settings(),
        categories=["cervejas", "batatas"],
        dishes=["hamburguer"],
        query_text=HAMBURGER_Q,
    )
    assert lookup["available"] is True
    assert "cervejas" in (lookup.get("notice") or "")
    assert "batatas" in (lookup.get("notice") or "")
    names = [item["name"] for item in lookup["items"]]
    assert not any("Canastra" in name for name in names)


def test_apply_beer_style_keeps_other_categories() -> None:
    cards = [
        {"name": "Cerveja Pilsen lata 350ml", "category": "cervejas"},
        {"name": "Cerveja IPA long neck 355ml", "category": "cervejas"},
        {"name": "Batata palito pré-frita congelada 1kg", "category": "batatas"},
    ]
    picked = apply_vitrine_query(cards, parse_vitrine_query(cats="cervejas,batatas", beer_style="pilsen"))
    names = [item["name"] for item in picked]
    assert "Cerveja Pilsen lata 350ml" in names
    assert "Cerveja IPA long neck 355ml" not in names
    assert "Batata palito pré-frita congelada 1kg" in names
