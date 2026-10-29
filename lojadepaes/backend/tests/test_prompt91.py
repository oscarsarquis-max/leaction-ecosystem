from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.domain.baker_library.access import AUTHORIZED_INITIAL_BRL, PLAN_HINT_SKU, public_plan
from app.domain.baker_library.articles import ARTICLE_VERSION, list_public_articles, public_article
from app.domain.baker_library.calculator import compute
from app.domain.baker_library.function import classify_function
from app.domain.gigio.intent import TurnDecision
from app.domain.gigio.rules import PROCESS_RULES, PROCESS_RULES_VERSION
from app.domain.gigio.service import chat
from tests.test_prompt73 import _mock_hub


def test_rules_keep_90_and_add_library() -> None:
    assert int(PROCESS_RULES_VERSION) >= 91
    assert "Onde compro um Fusca" in PROCESS_RULES
    assert "Biblioteca do Padeiro" in PROCESS_RULES
    assert "checkout de pão" in PROCESS_RULES


def test_baker_percentage_does_not_double_count_levain() -> None:
    result = compute(
        {
            "mode": "from_flour",
            "flour_g": 1000,
            "hydration_pct": 70,
            "salt_pct": 2,
            "preferment_flour_pct": 20,
            "levain_hydration_pct": 100,
            "levain_mode": "pff",
        }
    )
    assert result["totals"]["dough_g"] == 1720
    assert result["totals"]["dough_g"] != 2120
    assert result["final_mix"] == {
        "flour_g": 800,
        "water_g": 500,
        "salt_g": 20,
        "levain_g": 400,
        "extras": [],
    }
    assert result["levain"] == {"flour_g": 200, "water_g": 200, "weight_g": 400}


def test_scale_dough_to_860() -> None:
    result = compute(
        {
            "mode": "scale_dough",
            "flour_g": 1000,
            "target_dough_g": 860,
            "hydration_pct": 70,
            "salt_pct": 2,
            "preferment_flour_pct": 20,
            "levain_hydration_pct": 100,
            "levain_mode": "pff",
        }
    )
    assert result["totals"]["dough_g"] == 860
    assert result["flour_g"] == 500
    assert result["final_mix"]["levain_g"] == 200


def test_convert_levain_weight_to_pff() -> None:
    result = compute(
        {
            "mode": "convert_levain",
            "flour_g": 1000,
            "hydration_pct": 70,
            "salt_pct": 2,
            "levain_weight_g": 400,
            "levain_hydration_pct": 100,
            "levain_mode": "weight",
        }
    )
    assert result["preferment_flour_pct"] == 20
    assert result["totals"]["dough_g"] == 1720


def test_public_articles_have_sources(db) -> None:
    items = list_public_articles(db)
    assert [item["slug"] for item in items] == ["o-comeco", "as-maos-na-massa", "a-mesa"]
    começo = public_article(db, "o-comeco")
    assert começo["version"] == ARTICLE_VERSION
    assert any("Hamelman" in source["label"] for source in começo["sources"])
    assert "/biblioteca/calculadora" in começo["body_markdown"]


def test_plan_without_hub_does_not_open_checkout(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.domain.baker_library.access._fetch_catalog",
        lambda _settings: {"plans": []},
    )
    plan = public_plan(get_settings())
    assert plan["configured"] is False
    assert plan["checkout_ready"] is False
    assert plan["authorized_initial_brl"] == AUTHORIZED_INITIAL_BRL
    assert PLAN_HINT_SKU


def test_function_keeps_shop_free_on_library_route() -> None:
    page = {"path": "/biblioteca/o-comeco", "library": {"article_id": "o-comeco", "intent": "deepen"}}
    table = classify_function(page, TurnDecision("table", True, False))
    builder = classify_function(page, TurnDecision("builder", False, True))
    deepen = classify_function(page, TurnDecision("other", False, False))
    browse = classify_function({"path": "/biblioteca/o-comeco"}, TurnDecision("other", False, False))
    assert table == "atendimento"
    assert builder == "fazedor"
    assert deepen == "biblioteca"
    assert browse == "atendimento"


def test_deepen_without_authorization_does_not_call_model(db, monkeypatch) -> None:
    called = {"n": 0}

    class Boom:
        def complete(self, *_args, **_kwargs):
            called["n"] += 1
            raise AssertionError("modelo não deveria ser chamado")

    settings = get_settings()
    monkeypatch.setattr(settings, "gigio_enabled", True)
    monkeypatch.setattr(
        "app.domain.baker_library.access._fetch_catalog",
        lambda _settings: {"plans": []},
    )
    result = chat(
        db,
        settings,
        messages=[{"role": "user", "content": "Adapte esta fórmula para a minha cozinha"}],
        page={"path": "/biblioteca/o-comeco", "library": {"article_id": "o-comeco", "intent": "deepen"}},
        order_token=None,
        is_admin=False,
        gateway=Boom(),
    )
    assert called["n"] == 0
    assert result["access"]["authorized"] is False
    assert result["offer"]["checkout_ready"] is False
    assert any(token in result["reply"].casefold() for token in ("identifique", "assinatura", "plano", "biblioteca"))


def test_calculator_and_articles_api(client: TestClient) -> None:
    listed = client.get("/api/v1/biblioteca/artigos")
    assert listed.status_code == 200
    slugs = [item["slug"] for item in listed.json()["items"]]
    assert slugs == ["o-comeco", "as-maos-na-massa", "a-mesa"]
    article = client.get("/api/v1/biblioteca/artigos/o-comeco")
    assert article.status_code == 200
    assert article.json()["version"] == ARTICLE_VERSION
    calc = client.post(
        "/api/v1/biblioteca/calculadora",
        json={
            "mode": "from_flour",
            "flour_g": 1000,
            "hydration_pct": 70,
            "salt_pct": 2,
            "preferment_flour_pct": 20,
            "levain_hydration_pct": 100,
            "levain_mode": "pff",
        },
    )
    assert calc.status_code == 200
    assert calc.json()["totals"]["dough_g"] == 1720
    checkout = client.post("/api/v1/biblioteca/assinatura", json={"return_to": "/biblioteca/o-comeco"})
    assert checkout.status_code == 401


def test_shop_chat_still_free_from_library_path(db, monkeypatch) -> None:
    _mock_hub(monkeypatch, [])
    settings = get_settings()
    monkeypatch.setattr(settings, "gigio_enabled", True)
    from app.domain.gigio.fake import FakeGigioGateway

    result = chat(
        db,
        settings,
        messages=[{"role": "user", "content": "Qual o Pix do meu pedido?"}],
        page={"path": "/biblioteca/o-comeco", "library": {"article_id": "o-comeco", "intent": "deepen"}},
        order_token=None,
        is_admin=False,
        gateway=FakeGigioGateway(),
    )
    assert result["unavailable"] is False
    assert "access" not in result or result.get("access") is None
