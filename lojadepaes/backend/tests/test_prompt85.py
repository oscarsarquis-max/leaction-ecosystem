from app.core.config import get_settings
from app.domain.accompaniment_context import infer_suggested_query
from app.domain.accompaniments import (
    ALTERNATIVES_CTA,
    GENERIC_CTA,
    HUB_NOTICE,
    SUGGESTED_CTA,
    gigio_lookup,
)
from app.domain.gigio.pairing import publish_authorized_pilot
from app.domain.gigio.rules import PROCESS_RULES_VERSION
from app.domain.gigio.service import chat
from app.domain.gigio.tools import execute_tool
from sqlalchemy.orm import Session
from tests.test_prompt73 import _mock_hub, _offer
from tests.test_prompt77 import _TextOnlyGateway, _enable
from tests.test_prompt81 import _enable_pairing
from tests.test_prompt84 import _recipe


def _board(db: Session, monkeypatch, extra: list | None = None) -> None:
    offers = [
        _offer(id="MLBVINHO1", title="Vinho tinto da mesa", category="vinhos", link="https://www.mercadolivre.com.br/p/MLBVINHO1"),
        _offer(id="MLBCAVA1", title="Cava Brut Reserva 750ml", category="vinhos", link="https://www.mercadolivre.com.br/p/MLBCAVA1"),
        _offer(id="MLBVERDE1", title="Vinho Verde 750ml", category="vinhos", link="https://www.mercadolivre.com.br/p/MLBVERDE1"),
        _offer(id="MLBAZEITE1", title="Azeite português", category="azeites", link="https://www.mercadolivre.com.br/p/MLBAZEITE1"),
        _offer(id="MLBQUEIJO1", title="Queijo gorgonzola", category="queijos", link="https://www.mercadolivre.com.br/p/MLBQUEIJO1"),
        _offer(id="MLBFRIOS1", title="Presunto cru fatiado 200g", category="frios", link="https://www.mercadolivre.com.br/p/MLBFRIOS1"),
        _offer(id="MLBLAMB1", title="Lambrusco Rosé 750ml", category="vinhos", link="https://www.mercadolivre.com.br/p/MLBLAMB1"),
    ]
    if extra:
        offers.extend(extra)
    _mock_hub(monkeypatch, offers)
    _enable(monkeypatch)
    _enable_pairing(monkeypatch)


def test_rules_version_is_current() -> None:
    assert int(PROCESS_RULES_VERSION) >= 87


def test_sardine_pairing_ask_opens_meal_complements() -> None:
    query = infer_suggested_query(
        user_text="O que combina com a receita de sardinhas com homus de vocês?",
        reply="A receita não certifica vinho. Se quiser bebida, a Wine Folly trata sardinha como peixe intenso.",
    )
    assert query.dishes == ("sardinha",)
    assert "azeites" in query.categories
    assert infer_suggested_query(
        user_text="O Sacramentos Sabina Entre Serras 2025 tem avaliação?",
        reply="O Descorchados atribui 95 pontos a este rótulo.",
    ).useful is False


def test_sardine_recipe_beer_mention_does_not_open_beer_shelf() -> None:
    query = infer_suggested_query(
        user_text="O que combina com a receita de sardinhas com homus de vocês?",
        reply="A receita menciona cerveja gelada. Se quiser bebida, a Wine Folly trata sardinha como peixe intenso.",
    )
    assert "cervejas" not in query.categories
    assert "azeites" in query.categories


def test_sardine_accompaniment_keeps_source_recipe_and_cta(db: Session, monkeypatch) -> None:
    _board(db, monkeypatch)
    publish_authorized_pilot(db)
    recipe = _recipe(db)
    found = execute_tool(
        "lookup_recipes",
        {"q": "sardinhas homus"},
        session=db,
        settings=get_settings(),
        order_reference=None,
        order_token=None,
        is_admin=False,
    )
    assert any(item["slug"] == recipe.slug for item in found["items"])
    result = chat(
        db,
        get_settings(),
        messages=[{"role": "user", "content": "O que combina com a receita de sardinhas com homus de vocês?"}],
        page={"path": "/"},
        order_token=None,
        is_admin=False,
        gateway=_TextOnlyGateway(
            "A receita publicada é Sardinhas e Homus de Grão-de-Bico Fresco. "
            "A receita não certifica vinho. Se quiser bebida, a Wine Folly trata sardinha como peixe intenso."
        ),
    )
    hrefs = " ".join(item["href"] for item in result["sources"])
    assert "wine-with-fish-pairing-guide" in hrefs
    assert result["cta"]
    assert result["cta"]["label"] == SUGGESTED_CTA
    assert "mesa=sardinha" in result["cta"]["href"]
    assert "azeites" in result["cta"]["href"]
    assert "MLBVINHO1" not in result["cta"]["href"]
    assert "MLBCAVA1" in result["cta"]["href"] or "MLBLAMB1" in result["cta"]["href"] or "MLBAZEITE1" in result["cta"]["href"]


def test_sardine_cta_without_model_calling_lookup(db: Session, monkeypatch) -> None:
    _board(db, monkeypatch)
    publish_authorized_pilot(db)
    result = chat(
        db,
        get_settings(),
        messages=[{"role": "user", "content": "Sugestões de acompanhamento para sardinhas com homus"}],
        page={"path": "/"},
        order_token=None,
        is_admin=False,
        gateway=_TextOnlyGateway("Pão frito, homus e sardinhas. Bebida só se quiser, segundo a Wine Folly."),
    )
    assert result["cta"]["label"] == SUGGESTED_CTA
    assert "acompanhar" in result["cta"]["href"]


def test_no_alcohol_followup_does_not_reuse_wine_cta(db: Session, monkeypatch) -> None:
    _board(db, monkeypatch)
    publish_authorized_pilot(db)
    first = chat(
        db,
        get_settings(),
        messages=[{"role": "user", "content": "O que combina com a receita de sardinhas com homus?"}],
        page={"path": "/"},
        order_token=None,
        is_admin=False,
        gateway=_TextOnlyGateway("Receita publicada. Se quiser, um Cava seco segundo a Wine Folly."),
    )
    second = chat(
        db,
        get_settings(),
        messages=[
            {"role": "user", "content": "O que combina com a receita de sardinhas com homus?"},
            {"role": "assistant", "content": first["reply"], "cta": first["cta"]},
            {"role": "user", "content": "Agora sem álcool."},
        ],
        page={"path": "/"},
        order_token=None,
        is_admin=False,
        gateway=_TextOnlyGateway("Então pão, homus e azeite, sem vinho."),
    )
    assert second["cta"] is None
    assert second["access"]["deepen_offer"] is True
    assert second["access"]["charged"] is False
    assert "MLBCAVA1" not in (second.get("reply") or "")
    assert first["cta"]["href"]


def test_style_without_guide_score_can_open_cta(db: Session, monkeypatch) -> None:
    _board(db, monkeypatch)
    publish_authorized_pilot(db)
    result = chat(
        db,
        get_settings(),
        messages=[{"role": "user", "content": "Qual vinho combina com peixe grelhado?"}],
        page={"path": "/"},
        order_token=None,
        is_admin=False,
        gateway=_TextOnlyGateway("O tipo e o preparo mudam a escolha, segundo a Wine Folly. Vinho Verde é uma via para peixe magro."),
    )
    assert result["cta"]["label"] == SUGGESTED_CTA
    assert "95" not in (result["sources"][0].get("score_line") or "")
    assert "MLBVERDE1" in result["cta"]["href"]


def test_missing_evaluated_label_uses_alternatives_without_score_transfer(db: Session, monkeypatch) -> None:
    _board(db, monkeypatch)
    publish_authorized_pilot(db)
    result = chat(
        db,
        get_settings(),
        messages=[
            {
                "role": "user",
                "content": "Quero acompanhar o peixe grelhado com o Sacramentos Sabina Entre Serras 2025. O que há na vitrine?",
            }
        ],
        page={"path": "/"},
        order_token=None,
        is_admin=False,
        gateway=_TextOnlyGateway(
            "Esse rótulo recebeu 95 pontos no Descorchados, safra 2025. "
            "Não está neste anúncio. Há brancos de estilo compatível com peixe magro."
        ),
    )
    assert result["cta"]["label"] == ALTERNATIVES_CTA
    assert "MLBVERDE1" in result["cta"]["href"]
    assert "Sacramentos" not in result["cta"]["href"]
    assert any(item.get("retrieval_role") == "evaluation" for item in result["sources"])
    assert all("95" not in (item.get("title") or "") or item.get("retrieval_role") == "evaluation" for item in result["sources"])


def test_no_match_and_hub_failure_are_distinct(db: Session, monkeypatch) -> None:
    _enable(monkeypatch)
    _enable_pairing(monkeypatch)
    publish_authorized_pilot(db)
    _mock_hub(
        monkeypatch,
        [_offer(id="MLBVINHO1", title="Vinho tinto da mesa", category="vinhos", link="https://www.mercadolivre.com.br/p/MLBVINHO1")],
    )
    empty = gigio_lookup(
        db,
        get_settings(),
        categories=["vinhos", "azeites"],
        dishes=["sardinha"],
        query_text="sardinhas",
    )
    assert empty["cta"]["label"] == GENERIC_CTA
    assert empty["cta"]["href"] == "/acompanhar"
    assert empty["hub_status"] == "no_match"
    _mock_hub(monkeypatch, [], ok=False)
    down = chat(
        db,
        get_settings(),
        messages=[{"role": "user", "content": "O que combina com a receita de sardinhas com homus?"}],
        page={"path": "/"},
        order_token=None,
        is_admin=False,
        gateway=_TextOnlyGateway("A Wine Folly trata sardinha como peixe intenso. Sem vitrine agora."),
    )
    assert down["sources"]
    assert down["cta"] is None
    assert down["notice"] == HUB_NOTICE


def test_stale_hub_snapshot_refreshes_missing_oil_shelf(db: Session, monkeypatch) -> None:
    _enable(monkeypatch)
    _enable_pairing(monkeypatch)
    publish_authorized_pilot(db)
    stale = [
        _offer(id="MLBVINHO1", title="Vinho tinto da mesa", category="vinhos", link="https://www.mercadolivre.com.br/p/MLBVINHO1"),
    ]
    warm = stale + [
        _offer(id="MLBAZEITE1", title="Azeite português extra virgem 500ml", category="azeites", link="https://www.mercadolivre.com.br/p/MLBAZEITE1"),
    ]
    state = {"refresh": False}

    def _fetch(_settings, **kwargs):
        state["refresh"] = bool(kwargs.get("refresh"))
        return {"ok": True, "offers": warm if kwargs.get("refresh") else stale, "error": None}

    monkeypatch.setattr("app.domain.marketplace_client.fetch_hub_profile_catalog", _fetch)
    monkeypatch.setattr("app.domain.accompaniments.marketplace_client.fetch_hub_profile_catalog", _fetch)
    result = gigio_lookup(
        db,
        get_settings(),
        categories=["vinhos", "azeites"],
        dishes=["sardinha"],
        query_text="O que combina com a receita de sardinhas com homus?",
    )
    assert state["refresh"] is True
    assert result["cta"]["label"] == SUGGESTED_CTA
    assert "MLBAZEITE1" in result["cta"]["href"]
    assert "MLBVINHO1" not in result["cta"]["href"]


def test_previous_tables_and_operations_stay(db: Session, monkeypatch) -> None:
    _board(db, monkeypatch)
    publish_authorized_pilot(db)
    pork = chat(
        db,
        get_settings(),
        messages=[{"role": "user", "content": "Vou fazer churrasco de porco e linguiça. Qual vinho?"}],
        page={"path": "/"},
        order_token=None,
        is_admin=False,
        gateway=_TextOnlyGateway("Lambrusco ou Cabernet Franc no churrasco, segundo a Evino."),
    )
    cheese = chat(
        db,
        get_settings(),
        messages=[{"role": "user", "content": "Qual vinho combina com a tábua de queijos?"}],
        page={"path": "/"},
        order_token=None,
        is_admin=False,
        gateway=_TextOnlyGateway("Brancos, brut ou Chardonnay como curinga da tábua, segundo a Evino."),
    )
    frios = chat(
        db,
        get_settings(),
        messages=[{"role": "user", "content": "Vou receber amigos e quero montar uma mesa de frios. Que pães e acompanhamentos você sugere?"}],
        page={"path": "/"},
        order_token=None,
        is_admin=False,
        gateway=_TextOnlyGateway("Varie queijos e embutidos. Pão como base. Azeite no pão. Bebida só se quiserem."),
    )
    pay = chat(
        db,
        get_settings(),
        messages=[{"role": "user", "content": "Como acompanho o pagamento do meu pedido?"}],
        page={"path": "/"},
        order_token=None,
        is_admin=False,
        gateway=_TextOnlyGateway("O pagamento segue o fluxo do pedido."),
    )
    assert "vinhos-e-churrasco" in " ".join(item["href"] for item in pork["sources"])
    assert pork["cta"]
    assert "MLBLAMB1" in pork["cta"]["href"]
    assert "queijos-como-harmonizar" in " ".join(item["href"] for item in cheese["sources"])
    assert cheese["cta"]
    assert "charcuterie-board" in " ".join(item["href"] for item in frios["sources"])
    assert frios["cta"]
    assert "vinhos" not in (frios["cta"]["href"] or "")
    assert pay["cta"] is None
    assert pay["sources"] == []
