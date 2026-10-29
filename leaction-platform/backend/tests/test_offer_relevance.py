from app.services.mercadolivre_service import MercadoLivreService
from app.services.offer_relevance import evaluate_offer
from app.services.multivendor_orchestrator import _apply_relevance, _filter_curated_titles
from app.services.curation_repository import CurationRules


def _offer(title: str, **extra):
    payload = {"id": extra.pop("id", "MLB1"), "title": title, "category": extra.get("category", "vinhos")}
    payload.update(extra)
    return payload


def test_real_wine_accepted_book_and_tie_rejected():
    wine = evaluate_offer(
        _offer("Vinho Tinto Português Alto Da Capela 2016 750ml"),
        category="vinhos",
    )
    tie = evaluate_offer(
        _offer("Vinho tinto masculino italiano, fino e estreito, 6 cm, vinho tinto, vinho da Borgonha"),
        category="vinhos",
    )
    book = evaluate_offer(
        _offer("As rosas 3drose são vinho tinto também é vinho tinto P"),
        category="vinhos",
    )
    assert wine.accepted
    assert not tie.accepted
    assert "roupa" in tie.reason or "incompat" in tie.reason
    assert not book.accepted


def test_official_domain_wins_and_conflict_loses():
    official = evaluate_offer(
        _offer("Espumante Salton Brut 750ml", provider_domain="MLB-SPARKLING_WINES"),
        category="vinhos",
    )
    book_domain = evaluate_offer(
        _offer("Guia de vinhos do ano", provider_domain="MLB-BOOKS"),
        category="vinhos",
    )
    assert official.accepted
    assert official.source == "provider_category"
    assert not book_domain.accepted
    assert book_domain.source == "provider_category"


def test_cheese_and_recipe_book():
    cheese = evaluate_offer(_offer("Queijo Canastra Curado 500g", category="queijos"), category="queijos")
    recipe = evaluate_offer(_offer("Livro de receitas com queijo e pão", category="queijos"), category="queijos")
    salame = evaluate_offer(_offer("Salame com gorgonzola fatiado 100g", category="queijos"), category="queijos")
    assert cheese.accepted
    assert not recipe.accepted
    assert not salame.accepted


def test_copa_sliced_versus_glass_and_trophy():
    sliced = evaluate_offer(_offer("Copa italiana fatiada 100g", category="frios"), category="frios")
    glass = evaluate_offer(_offer("Taça de vinho cristal 450ml", category="frios"), category="frios")
    trophy = evaluate_offer(_offer("Kit 3 Chaveiros Troféu Taça Copa Do Mundo Miniatura"), category="frios")
    cups = evaluate_offer(_offer("Copa Italiana de Campo Mikasa de 11,5 onças, conjunto de 4"), category="frios")
    assert sliced.accepted
    assert not glass.accepted
    assert not trophy.accepted
    assert not cups.accepted


def test_beer_versus_glass_and_shirt():
    beer = evaluate_offer(_offer("Cerveja Pilsen lata 350ml", category="cervejas"), category="cervejas")
    glass = evaluate_offer(_offer("Copo de cerveja tulipa 400ml", category="cervejas"), category="cervejas")
    shirt = evaluate_offer(_offer("Camiseta cerveja artesanal", category="cervejas"), category="cervejas")
    kit = evaluate_offer(_offer("Kit fabricação de cerveja caseira", category="cervejas"), category="cervejas")
    assert beer.accepted
    assert not glass.accepted
    assert not shirt.accepted
    assert not kit.accepted


def test_potato_food_versus_seed_and_chips_are_distinct():
    fry = evaluate_offer(
        _offer("Batata palito pré-frita congelada 1kg", category="batatas"),
        category="batatas",
    )
    chips = evaluate_offer(_offer("Batata chips lisa 60g", category="batatas"), category="batatas")
    seed = evaluate_offer(_offer("Semente de batata para plantio", category="batatas"), category="batatas")
    toy = evaluate_offer(_offer("Brinquedo pelúcia batata", category="batatas"), category="batatas")
    cutter = evaluate_offer(_offer("Fatiador Batata Palito Frita", category="batatas"), category="batatas")
    pillow = evaluate_offer(_offer("Almofada Divertida Batata Palito 40x40", category="batatas"), category="batatas")
    scoop = evaluate_offer(_offer("Pá Para Batata Palito Em Inox Pegador De Batata Frita", category="batatas"), category="batatas")
    assert fry.accepted
    assert chips.accepted
    assert not seed.accepted
    assert not toy.accepted
    assert not cutter.accepted
    assert not pillow.accepted
    assert not scoop.accepted


def test_oil_versus_accessory():
    oil = evaluate_offer(_offer("Azeite extra virgem português 500ml", category="azeites"), category="azeites")
    accessory = evaluate_offer(_offer("Porta azeite galheteiro inox dispenser", category="azeites"), category="azeites")
    assert oil.accepted
    assert not accessory.accepted


def test_missing_category_and_conflicting_attributes_stay_out():
    ambiguous = evaluate_offer(_offer("Kit mesa especial"), category="vinhos")
    assert not ambiguous.accepted
    assert ambiguous.decision == "review"


def test_accents_and_synonyms():
    rose = evaluate_offer(_offer("Vinho rosé português garrafa 750 ml"), category="vinhos")
    assert rose.accepted


def test_human_exception_is_auditable():
    forced = evaluate_offer(
        _offer("Item ambíguo", id="MLBEX1"),
        category="vinhos",
        decisions={"lojadepaes|vinhos|MLBEX1": {"decision": "approve", "reason": "Degustação da casa, garrafa conferida."}},
    )
    blocked = evaluate_offer(
        _offer("Vinho Tinto Touriga 750ml", id="MLBEX2"),
        category="vinhos",
        decisions={"lojadepaes|vinhos|MLBEX2": {"decision": "reject", "reason": "Fora de linha."}},
    )
    assert forced.accepted
    assert forced.source == "human"
    assert not blocked.accepted
    assert blocked.source == "human"


def test_culinary_filter_does_not_readmit_without_positives():
    rules = CurationRules(
        category_id="vinhos",
        search_terms=["vinho tinto mesa"],
        positive_keywords=["vinho"],
        negative_keywords=["livro"],
    )
    offers = [_offer("Caderno escolar azul"), _offer("Vinho tinto mesa 750ml")]
    kept = _filter_curated_titles(offers, rules, category="vinhos")
    assert [item["title"] for item in kept] == ["Vinho tinto mesa 750ml"]


def test_apply_relevance_keeps_valid_and_drops_noise():
    accepted, rejected = _apply_relevance(
        [
            _offer("Vinho Tinto Português Alto Da Capela 2016 750ml"),
            _offer("Vinho tinto masculino italiano, fino e estreito, 6 cm"),
            _offer("As rosas 3drose são vinho tinto também é vinho tinto P"),
        ],
        category="vinhos",
        origin="lojadepaes",
        decisions={},
    )
    assert len(accepted) == 1
    assert len(rejected) == 2
    assert "Alto Da Capela" in accepted[0]["title"]


def test_official_picture_prefers_largest_declared_size():
    chosen = MercadoLivreService._choose_official_picture(
        [
            {"url": "https://http2.mlstatic.com/D_small-I.jpg", "size": "250x250"},
            {"secure_url": "https://http2.mlstatic.com/D_full-I.jpg", "max_size": "1200x800"},
        ]
    )
    assert chosen["secure_url"].endswith("D_full-I.jpg")
    assert MercadoLivreService._normalize_image_url(chosen["secure_url"]).endswith("D_full-O.jpg")
