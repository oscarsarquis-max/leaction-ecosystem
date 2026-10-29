from uuid import uuid4

from app.core.config import get_settings
from app.domain.accompaniment_context import (
    build_vitrine_href,
    context_title,
    infer_suggested_query,
    parse_vitrine_query,
)
from app.domain.accompaniments import gigio_lookup, public_catalog
from app.domain.gigio.pairing import (
    EXPANSION_PROFILE_KEYS,
    infer_occasions_from_text,
    lookup_pairing_references,
    publish_authorized_pilot,
    sources_for_conversation,
)
from app.domain.gigio.pairing_match import compatible_offer_ids, match_offer_to_reference
from app.domain.gigio.service import chat
from app.domain.gigio.tools import execute_tool
from app.models.enums import EditorialStatus
from app.models.week_recipes import WeekRecipe, WeekRecipeIngredient
from sqlalchemy.orm import Session
from tests.test_prompt73 import _mock_hub, _offer
from tests.test_prompt77 import _TextOnlyGateway, _enable
from tests.test_prompt81 import _enable_pairing, _publish


def _board(db: Session, monkeypatch) -> None:
    offers = [
        _offer(id="MLBVINHO1", title="Vinho tinto da mesa", category="vinhos", link="https://www.mercadolivre.com.br/p/MLBVINHO1"),
        _offer(id="MLBVERDE1", title="Vinho Verde 750ml", category="vinhos", link="https://www.mercadolivre.com.br/p/MLBVERDE1"),
        _offer(id="MLBALBA1", title="Albariño Rias Baixas 750ml", category="vinhos", link="https://www.mercadolivre.com.br/p/MLBALBA1"),
        _offer(id="MLBLAMB1", title="Lambrusco Rosé 750ml", category="vinhos", link="https://www.mercadolivre.com.br/p/MLBLAMB1"),
        _offer(id="MLBCHAB1", title="Chablis Premier Cru 750ml", category="vinhos", link="https://www.mercadolivre.com.br/p/MLBCHAB1"),
        _offer(id="MLBQUEIJO1", title="Queijo gorgonzola", category="queijos", link="https://www.mercadolivre.com.br/p/MLBQUEIJO1"),
        _offer(
            id="MLBSALAMEQ",
            title="Salame com queijo gorgonzola 300g",
            category="queijos",
            link="https://www.mercadolivre.com.br/p/MLBSALAMEQ",
        ),
        _offer(id="MLBFRIOS1", title="Presunto cru fatiado 200g", category="frios", link="https://www.mercadolivre.com.br/p/MLBFRIOS1"),
        _offer(id="MLBAZEITE1", title="Azeite português", category="azeites", link="https://www.mercadolivre.com.br/p/MLBAZEITE1"),
    ]
    _mock_hub(monkeypatch, offers)
    _enable(monkeypatch)
    _enable_pairing(monkeypatch)


def _recipe(db: Session) -> WeekRecipe:
    recipe = WeekRecipe(
        title="Sardinhas e Homus de Grão-de-Bico Fresco (Tartine Bread)",
        slug="sardinhas-e-homus-de-grao-de-bico-fresco-tartine-bread",
        summary="Sardinhas em lata na torrada.",
        editorial_status=EditorialStatus.PUBLISHED.value,
        is_featured=True,
        method_text="Espalhe o homus sobre o pão frito e cubra com as sardinhas.",
    )
    db.add(recipe)
    db.flush()
    db.add(WeekRecipeIngredient(recipe_id=recipe.id, body="1 lata de sardinhas em azeite", sort_order=0))
    db.add(WeekRecipeIngredient(recipe_id=recipe.id, body="2 fatias de pão", sort_order=1))
    db.commit()
    return recipe


def test_expansion_publish_keeps_previous_and_excludes_drafts(db: Session) -> None:
    report = publish_authorized_pilot(db)
    keys = {item["profile_key"] for item in report if item["action"] == "published"}
    assert EXPANSION_PROFILE_KEYS <= keys
    assert "wine-churrasco-porco" in keys
    assert "wine-dao-leitao" not in keys


def test_frios_table_without_wine_gets_breads_and_cta(db: Session, monkeypatch) -> None:
    _board(db, monkeypatch)
    publish_authorized_pilot(db)
    result = chat(
        db,
        get_settings(),
        messages=[
            {
                "role": "user",
                "content": "Vou receber amigos e quero montar uma mesa de frios. Que pães e acompanhamentos você sugere?",
            }
        ],
        page={"path": "/"},
        order_token=None,
        is_admin=False,
        gateway=_TextOnlyGateway(
            "Comece pelo Pão Fermentação Natural de Trigo, que o catálogo descreve como combina com queijos e embutidos. "
            "Monte variedade de queijos e presunto. Para completar a mesa, azeite no pão. Bebida só se quiserem."
        ),
    )
    hrefs = " ".join(item["href"] for item in result["sources"])
    assert "charcuterie-board" in hrefs
    assert "vinhos-e-churrasco" not in hrefs
    assert result["cta"]
    assert "frios" in result["cta"]["href"] or "queijos" in result["cta"]["href"]
    assert "vinhos" not in result["cta"]["href"]


def test_no_meat_and_no_alcohol_respected(db: Session, monkeypatch) -> None:
    _board(db, monkeypatch)
    publish_authorized_pilot(db)
    query = infer_suggested_query(
        user_text="Mesa de frios sem carne e sem álcool, o que servir com o pão?",
        reply="Queijos, azeite e pão. Sem embutidos e sem vinho.",
    )
    assert "frios" not in query.categories
    assert "vinhos" not in query.categories
    assert "queijos" in query.categories
    result = chat(
        db,
        get_settings(),
        messages=[{"role": "user", "content": "Mesa de frios sem carne e sem álcool. O que servir?"}],
        page={"path": "/"},
        order_token=None,
        is_admin=False,
        gateway=_TextOnlyGateway("Queijos e azeite no pão. Sem embutidos e sem vinho."),
    )
    href = (result.get("cta") or {}).get("href") or ""
    cats = ""
    if "cats=" in href:
        cats = href.split("cats=", 1)[1].split("&", 1)[0]
    assert "frios" not in cats.split(",")
    assert "vinhos" not in cats.split(",")
    assert "vinhos" not in href
    assert "MLBFRIOS1" not in href
    assert "MLBSALAMEQ" not in href
    assert "MLBVINHO1" not in href


def test_followup_only_cheese_preserves_previous_link(db: Session, monkeypatch) -> None:
    _board(db, monkeypatch)
    publish_authorized_pilot(db)
    first = infer_suggested_query(
        user_text="Quero uma mesa de frios com acompanhamentos.",
        reply="Queijos, embutidos e azeite.",
    )
    second = infer_suggested_query(
        user_text="quero somente queijos",
        reply="Então só queijos.",
        history=[{"role": "user", "content": "Quero uma mesa de frios com acompanhamentos."}],
    )
    assert build_vitrine_href(first) != build_vitrine_href(second)
    assert second.categories == ("queijos",)
    assert "frios" not in second.categories


def test_wrong_nature_and_generic_wine_are_excluded() -> None:
    salame = {"hub_offer_id": "X", "title": "Salame com queijo gorgonzola 300g", "category": "queijos"}
    generic = {"hub_offer_id": "Y", "title": "Vinho Tinto 750ml", "category": "vinhos"}
    specific = {"hub_offer_id": "Z", "title": "Albariño Rias Baixas 750ml", "category": "vinhos"}
    cheese_ref = {
        "category": "queijos",
        "scope": "style",
        "match_hints": ["gorgonzola"],
        "retrieval_role": "pairing",
        "evidence_type": "pairing_recommendation",
        "verification_status": "verified",
        "editorial_status": "published",
    }
    wine_ref = {
        "category": "vinhos",
        "scope": "style",
        "match_hints": ["albarino", "albariño"],
        "retrieval_role": "pairing",
        "evidence_type": "pairing_recommendation",
        "verification_status": "verified",
        "editorial_status": "published",
    }
    assert match_offer_to_reference(salame, cheese_ref)["correspondence"] == "none"
    assert compatible_offer_ids([generic, specific], [wine_ref]) == ["Z"]


def test_hub_down_keeps_advice(db: Session, monkeypatch) -> None:
    _enable(monkeypatch)
    _enable_pairing(monkeypatch)
    _publish(db, "board-mesa-frios")
    from tests.test_prompt73 import _mock_hub as mock

    mock(monkeypatch, [], ok=False)
    result = chat(
        db,
        get_settings(),
        messages=[{"role": "user", "content": "Como monto uma mesa de frios?"}],
        page={"path": "/"},
        order_token=None,
        is_admin=False,
        gateway=_TextOnlyGateway(
            "Varie queijos e embutidos e use o pão como base, segundo a Wine Folly. Sem oferta compatível agora."
        ),
    )
    assert result["sources"]
    assert result["cta"] is None


def test_order_question_has_no_pairing_or_forced_cta(db: Session, monkeypatch) -> None:
    _board(db, monkeypatch)
    publish_authorized_pilot(db)
    result = chat(
        db,
        get_settings(),
        messages=[{"role": "user", "content": "Como acompanho o pagamento do meu pedido?"}],
        page={"path": "/"},
        order_token=None,
        is_admin=False,
        gateway=_TextOnlyGateway("O pagamento segue o fluxo do pedido. Não preciso sugerir vinho."),
    )
    assert result["sources"] == []
    assert result["cta"] is None


def test_previous_pilot_does_not_leak(db: Session, monkeypatch) -> None:
    _enable_pairing(monkeypatch)
    publish_authorized_pilot(db)
    pork = lookup_pairing_references(db, enabled=True, categories=["vinhos"], query="churrasco de porco e linguica")
    cheese = lookup_pairing_references(db, enabled=True, categories=["vinhos"], query="tabua de queijos")
    fish = lookup_pairing_references(db, enabled=True, categories=["vinhos"], query="peixe grelhado")
    assert [item["profile_key"] for item in pork["references"]] == ["wine-churrasco-porco"]
    assert [item["profile_key"] for item in cheese["references"]] == ["wine-queijo-tabua"]
    assert [item["profile_key"] for item in fish["references"]] == ["wine-peixe-grelhado"]


def test_sardine_recipe_is_identified_without_wrong_sources(db: Session, monkeypatch) -> None:
    _board(db, monkeypatch)
    publish_authorized_pilot(db)
    recipe = _recipe(db)
    tool = execute_tool(
        "lookup_recipes",
        {"q": "sardinhas homus"},
        session=db,
        settings=get_settings(),
        order_reference=None,
        order_token=None,
        is_admin=False,
    )
    assert any(item["slug"] == recipe.slug for item in tool["items"])
    result = chat(
        db,
        get_settings(),
        messages=[{"role": "user", "content": "O que combina com a receita de sardinhas com homus de vocês?"}],
        page={"path": "/"},
        order_token=None,
        is_admin=False,
        gateway=_TextOnlyGateway(
            "A receita publicada é Sardinhas e Homus de Grão-de-Bico Fresco, no Pão Fermentação Natural de Trigo. "
            "A receita não certifica vinho. Se quiser bebida, a Wine Folly trata sardinha como peixe intenso."
        ),
    )
    hrefs = " ".join(item["href"] for item in result["sources"])
    assert "wine-with-fish-pairing-guide" in hrefs
    assert "vinhos-e-churrasco" not in hrefs
    assert "queijos-como-harmonizar" not in hrefs
    catalog = public_catalog(db, get_settings(), cats="vinhos,azeites", mesa="sardinha")
    assert catalog["title"] == "Para acompanhar as sardinhas"


def test_seafood_sources_stay_in_scope(db: Session, monkeypatch) -> None:
    _enable_pairing(monkeypatch)
    publish_authorized_pilot(db)
    grilled = sources_for_conversation(db, enabled=True, user_text="Qual vinho com peixe grelhado?", reply="")
    shrimp = sources_for_conversation(db, enabled=True, user_text="Camarão com molho de limão e ervas", reply="")
    lobster = sources_for_conversation(db, enabled=True, user_text="Lagosta grelhada com manteiga", reply="")
    assert [item["href"] for item in grilled] == ["https://winefolly.com/wine-pairing/wine-with-fish-pairing-guide/"]
    assert "albarino" in " ".join(item["href"] for item in shrimp)
    assert "decanter.com" in " ".join(item["href"] for item in lobster)
    assert infer_occasions_from_text("camarão com molho") == ["camarao"]
    assert "peixe" not in infer_occasions_from_text("lagosta grelhada")
    assert "churrasco" not in infer_occasions_from_text("peixe grelhado")


def test_followup_shrimp_and_no_alcohol_updates_context(db: Session, monkeypatch) -> None:
    first = infer_suggested_query(
        user_text="O que combina com a receita de sardinhas com homus?",
        reply="A receita e, se quiser, um lambrusco.",
    )
    second = infer_suggested_query(
        user_text="Agora é camarão, sem álcool.",
        reply="Camarão com pão e azeite, sem vinho.",
        history=[{"role": "user", "content": "O que combina com a receita de sardinhas com homus?"}],
    )
    assert first.dishes == ("sardinha",)
    assert second.dishes == ("camarao",)
    assert "vinhos" not in second.categories
    assert build_vitrine_href(first) != build_vitrine_href(second)
    _enable_pairing(monkeypatch)
    publish_authorized_pilot(db)
    shrimp_sources = sources_for_conversation(
        db,
        enabled=True,
        user_text="Agora é camarão, sem álcool.",
        reply="",
        history=[{"role": "user", "content": "O que combina com a receita de sardinhas com homus?"}],
    )
    hrefs = " ".join(item["href"] for item in shrimp_sources)
    assert "albarino" not in hrefs
    assert "wine-with-fish-pairing-guide" not in hrefs
    assert "vinhos-e-churrasco" not in hrefs
    assert "queijos-como-harmonizar" not in hrefs


def test_vitrine_titles_follow_occasion() -> None:
    assert context_title(parse_vitrine_query(mesa="frios")) == "Para sua mesa de frios"
    assert context_title(parse_vitrine_query(mesa="sardinha"), raw_text="receita de sardinhas com homus") == (
        "Para acompanhar sardinhas com homus"
    )
    assert context_title(parse_vitrine_query(mesa="leitao,salada")) == "Sugestões para sua mesa"


def test_specialized_lookup_does_not_fill_generic_wine(db: Session, monkeypatch) -> None:
    _board(db, monkeypatch)
    publish_authorized_pilot(db)
    lookup = gigio_lookup(
        db,
        get_settings(),
        categories=["vinhos"],
        dishes=["camarao"],
        query_text="camarão com limão",
    )
    names = [item["name"] for item in lookup["items"]]
    assert any("Albariño" in name for name in names)
    assert all("Vinho tinto da mesa" not in name for name in names)
