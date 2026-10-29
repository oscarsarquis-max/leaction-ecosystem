from app.domain.offer_contract import offer_fits_contract
from app.domain.marketplace_client import _parse_offer


def test_contract_keeps_real_food_and_drops_noise():
    assert offer_fits_contract(title="Vinho Tinto Português Alto Da Capela 2016 750ml", category="vinhos")
    assert not offer_fits_contract(
        title="Vinho tinto masculino italiano, fino e estreito, 6 cm, vinho tinto",
        category="vinhos",
    )
    assert not offer_fits_contract(title="As rosas 3drose são vinho tinto também é vinho tinto P", category="vinhos")
    assert offer_fits_contract(title="Queijo Canastra Curado", category="queijos")
    assert not offer_fits_contract(title="Livro de receitas com queijo", category="queijos")
    assert not offer_fits_contract(title="Salame com gorgonzola fatiado 100g", category="queijos")
    assert offer_fits_contract(title="Copa italiana fatiada 100g", category="frios")
    assert not offer_fits_contract(title="Taça de vinho cristal", category="frios")
    assert not offer_fits_contract(title="Kit 3 Chaveiros Troféu Taça Copa Do Mundo Miniatura", category="frios")
    assert not offer_fits_contract(title="Copa Italiana de Campo Mikasa de 11,5 onças, conjunto de 4", category="frios")
    assert offer_fits_contract(title="Azeite extra virgem português 500ml", category="azeites")
    assert not offer_fits_contract(title="Porta azeite galheteiro dispenser", category="azeites")


def test_parse_still_requires_official_link():
    parsed = _parse_offer(
        {
            "id": "MLB38120577",
            "title": "Vinho Tinto Português Alto Da Capela 2016 750ml",
            "category": "vinhos",
            "link": "https://www.mercadolivre.com.br/p/MLB38120577",
            "vendor": "mercadolivre",
        },
        category="vinhos",
    )
    assert parsed is not None
    assert parsed.id == "MLB38120577"
