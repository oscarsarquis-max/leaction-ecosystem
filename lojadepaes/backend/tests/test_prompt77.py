from app.core.config import get_settings
from app.domain.accompaniment_context import infer_suggested_query
from app.domain.accompaniments import gigio_lookup, public_catalog
from app.domain.gigio.fake import FakeGigioGateway
from app.domain.gigio.gateway import ChatResponse
from app.domain.gigio.service import chat
from app.domain.gigio.tools import execute_tool
from sqlalchemy.orm import Session
from tests.test_prompt73 import _mock_hub, _offer


def _enable(monkeypatch, *, public=True, gigio=True) -> None:
    monkeypatch.setenv("LOJADEPAES_PUBLIC_ACCOMPANIMENTS_ENABLED", "true" if public else "false")
    monkeypatch.setenv("LOJADEPAES_GIGIO_ACCOMPANIMENTS_ENABLED", "true" if gigio else "false")
    get_settings.cache_clear()


def _catalog(db: Session, monkeypatch) -> list:
    wine = _offer(id="MLBVINHO1", title="Vinho tinto da mesa", category="vinhos", link="https://www.mercadolivre.com.br/p/MLBVINHO1")
    cheese = _offer(id="MLBQUEIJO1", title="Queijo gorgonzola", category="queijos", link="https://www.mercadolivre.com.br/p/MLBQUEIJO1")
    oil = _offer(id="MLBAZEITE1", title="Azeite português", category="azeites", link="https://www.mercadolivre.com.br/p/MLBAZEITE1")
    _mock_hub(monkeypatch, [wine, cheese, oil])
    return [wine, cheese, oil]


def test_context_keeps_wine_and_cheese_out_of_oil(db: Session, monkeypatch) -> None:
    _catalog(db, monkeypatch)
    _enable(monkeypatch)
    filtered = public_catalog(db, get_settings(), cats="vinhos,queijos")
    names = [item["name"] for item in filtered["items"]]
    assert names == ["Vinho tinto da mesa", "Queijo gorgonzola"]
    assert filtered["context"]["active"] is True
    assert filtered["context"]["empty"] is False
    assert "azeite" not in " ".join(names).casefold()


def test_invalid_ids_do_not_swap_in_unrelated_items(db: Session, monkeypatch) -> None:
    _catalog(db, monkeypatch)
    _enable(monkeypatch)
    empty = public_catalog(db, get_settings(), ids="NAOEXISTE")
    assert empty["enabled"] is True
    assert empty["items"] == []
    assert empty["context"]["empty"] is True
    assert empty["context"]["clear_href"] == "/acompanhar"


def test_unknown_category_is_not_a_silent_generic_catalog(db: Session, monkeypatch) -> None:
    _catalog(db, monkeypatch)
    _enable(monkeypatch)
    generic = public_catalog(db, get_settings(), cats="embalagens")
    assert generic["context"]["active"] is False
    assert len(generic["items"]) == 3


def test_gigio_builds_contextual_cta_and_keeps_previous_link(db: Session, monkeypatch) -> None:
    _catalog(db, monkeypatch)
    _enable(monkeypatch)
    first = gigio_lookup(db, get_settings(), categories=["vinhos", "queijos"], wine_style="tinto")
    assert first["available"] is True
    assert first["cta"]["label"] == "Ver acompanhamentos sugeridos"
    assert "cats=vinhos,queijos" in first["cta"]["href"]
    assert "tipo=tinto" in first["cta"]["href"]
    assert first["cta"]["href"].startswith("/acompanhar?")
    names = {item["name"] for item in first["items"]}
    assert "Azeite português" not in names
    second = gigio_lookup(db, get_settings(), categories=["queijos"])
    assert second["cta"]["href"] != first["cta"]["href"]
    assert "vinhos" not in second["cta"]["href"]
    assert first["cta"]["href"] == first["story_href"]


def test_gigio_flag_off_has_no_cta(db: Session, monkeypatch) -> None:
    _catalog(db, monkeypatch)
    _enable(monkeypatch, gigio=False)
    off = execute_tool(
        "lookup_accompaniments",
        {"categories": ["vinhos"]},
        session=db,
        settings=get_settings(),
        order_reference=None,
        order_token=None,
        is_admin=False,
    )
    assert off["available"] is False
    assert off["cta"] is None


def test_chat_attaches_vitrine_cta_below_reply(db: Session, monkeypatch) -> None:
    _catalog(db, monkeypatch)
    _enable(monkeypatch)
    monkeypatch.setenv("LOJADEPAES_GIGIO_ENABLED", "true")
    monkeypatch.setenv("LOJADEPAES_GIGIO_GATEWAY", "fake")
    get_settings.cache_clear()
    result = chat(
        db,
        get_settings(),
        messages=[{"role": "user", "content": "Como servir o pão com vinho tinto e queijo?"}],
        page={"path": "/"},
        order_token=None,
        is_admin=False,
        gateway=FakeGigioGateway(),
    )
    assert result["unavailable"] is False
    assert result["cta"]["label"] == "Ver acompanhamentos sugeridos"
    assert result["cta"]["href"].startswith("/acompanhar?")
    assert "cats=vinhos,queijos" in result["cta"]["href"]
    assert all(not item["href"].startswith("https://lista.mercadolivre") for item in result["links"])


def test_hub_down_does_not_break_common_chat(db: Session, monkeypatch) -> None:
    _mock_hub(monkeypatch, [], ok=False)
    _enable(monkeypatch)
    lookup = gigio_lookup(db, get_settings(), categories=["vinhos"])
    assert lookup["available"] is False
    assert lookup["cta"] is None
    culinary = execute_tool(
        "lookup_products",
        {"q": "pão"},
        session=db,
        settings=get_settings(),
        order_reference=None,
        order_token=None,
        is_admin=False,
    )
    assert "items" in culinary


class _TextOnlyGateway:
    def __init__(self, text: str) -> None:
        self.text = text

    def complete(self, request) -> ChatResponse:
        del request
        return ChatResponse(
            text=self.text,
            tool_use=[],
            stop_reason="end_turn",
            input_tokens=10,
            output_tokens=20,
            latency_ms=5,
            provider="fake",
            model_id="fake",
            region="local",
        )


def test_chat_attaches_cta_when_model_skips_tool(db: Session, monkeypatch) -> None:
    _catalog(db, monkeypatch)
    _enable(monkeypatch)
    monkeypatch.setenv("LOJADEPAES_GIGIO_ENABLED", "true")
    get_settings.cache_clear()
    result = chat(
        db,
        get_settings(),
        messages=[{"role": "user", "content": "Como servir um pão de fermentação natural?"}],
        page={"path": "/"},
        order_token=None,
        is_admin=False,
        gateway=_TextOnlyGateway(
            "Sirva em fatias com um fio de azeite. Como sugestão do Gigio, queijo brie e vinho tinto de corpo médio combinam com a acidez do pão."
        ),
    )
    assert result["cta"]["label"] == "Ver acompanhamentos sugeridos"
    assert "cats=vinhos,queijos" in result["cta"]["href"]
    assert "tipo=tinto" not in result["cta"]["href"]
    assert "azeites" not in result["cta"]["href"]


def test_support_question_does_not_force_vitrine_cta(db: Session, monkeypatch) -> None:
    _catalog(db, monkeypatch)
    _enable(monkeypatch)
    monkeypatch.setenv("LOJADEPAES_GIGIO_ENABLED", "true")
    get_settings.cache_clear()
    result = chat(
        db,
        get_settings(),
        messages=[{"role": "user", "content": "Como funciona o pedido e o pagamento?"}],
        page={"path": "/"},
        order_token=None,
        is_admin=False,
        gateway=_TextOnlyGateway("O pedido segue pelo calendário da Loja. Pagamento e entrega são etapas separadas."),
    )
    assert result["cta"] is None


def test_infer_suggested_query_ignores_drizzle_oil(db: Session, monkeypatch) -> None:
    del db, monkeypatch
    query = infer_suggested_query(
        user_text="Como servir o pão?",
        reply="Passe um fio de azeite e sirva com queijo e vinho tinto.",
    )
    assert query.categories == ("vinhos", "queijos")
    assert query.wine_style == ""


def test_delivery_copy_names_marketplaces(db: Session, monkeypatch) -> None:
    _catalog(db, monkeypatch)
    _enable(monkeypatch, gigio=False)
    payload = public_catalog(db, get_settings())
    assert "Mercado Livre" in payload["delivery_help"]["text"]
    assert "Amazon" in payload["delivery_help"]["text"]
    assert "informe a data" in payload["delivery_help"]["text"]
    assert "destino" not in payload["delivery_help"]["text"]
    assert payload["delivery_help"]["client_note"]
