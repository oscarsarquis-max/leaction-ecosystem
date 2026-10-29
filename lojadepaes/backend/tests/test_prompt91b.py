from app.core.config import get_settings
from app.domain.baker_library.access import (
    AUTHORIZED_COMPLEMENTARY_BRL,
    AUTHORIZED_INITIAL_BRL,
    COMPLEMENTARY_HINT_SKU,
    PLAN_HINT_SKU,
    public_plan,
)
from app.domain.baker_library.credits import remember_operation, recovered_reply
from app.domain.gigio.fake import FakeGigioGateway
from app.domain.gigio.gateway import ChatResponse
from app.domain.gigio.intent import TurnDecision
from app.domain.baker_library.function import classify_function
from app.domain.gigio.rules import PROCESS_RULES, PROCESS_RULES_VERSION
from app.domain.gigio.service import chat
from tests.test_prompt73 import _mock_hub


def _reply(text: str) -> ChatResponse:
    return ChatResponse(
        text=text,
        tool_use=[],
        stop_reason="end_turn",
        input_tokens=8,
        output_tokens=20,
        latency_ms=4,
        provider="fake",
        model_id="fake",
        region="local",
    )


def test_rules_keep_90_and_state_monthly_credits() -> None:
    assert int(PROCESS_RULES_VERSION) >= 91
    assert "Onde compro um Fusca" in PROCESS_RULES
    assert "Usar 1 crédito" in PROCESS_RULES
    assert "R$ 19,00" in PROCESS_RULES
    assert "R$ 10,00" in PROCESS_RULES
    assert "checkout de pão" in PROCESS_RULES


def test_public_plan_shows_both_authorized_prices(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.domain.baker_library.access._fetch_catalog",
        lambda _settings: {"plans": []},
    )
    plan = public_plan(get_settings())
    assert plan["configured"] is False
    assert plan["checkout_ready"] is False
    assert plan["authorized_initial_brl"] == AUTHORIZED_INITIAL_BRL
    assert plan["authorized_complementary_brl"] == AUTHORIZED_COMPLEMENTARY_BRL
    assert plan["principal"]["credits"] == 20
    assert plan["complementary"]["credits"] == 10
    assert plan["accumulate"] is False
    assert PLAN_HINT_SKU
    assert COMPLEMENTARY_HINT_SKU


def test_public_plan_enables_checkout_when_hub_catalog_is_live(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.domain.baker_library.access._fetch_catalog",
        lambda _settings: {
            "plans": [
                {
                    "id": "prod-principal",
                    "sku": PLAN_HINT_SKU,
                    "name": "Principal da Biblioteca",
                    "type": "plan",
                    "price": 19,
                    "currency": "BRL",
                    "credits": 20,
                    "checkout_mode": "subscription",
                    "recurring": True,
                    "meta_json": {
                        "periodicidade": "mensal",
                        "checkout_mode": "subscription",
                        "creditos": 20,
                        "direitos": {"assinatura": True, "biblioteca": True},
                    },
                },
                {
                    "id": "prod-pack",
                    "sku": COMPLEMENTARY_HINT_SKU,
                    "name": "Pacote adicional de consultas de IA",
                    "type": "credit_pack",
                    "price": 10,
                    "currency": "BRL",
                    "credits": 10,
                    "checkout_mode": "hub_brick",
                    "recurring": False,
                    "meta_json": {
                        "creditos": 10,
                        "direitos": {"papel": "pacote_avulso"},
                    },
                },
            ]
        },
    )
    plan = public_plan(get_settings())
    assert plan["configured"] is True
    assert plan["checkout_ready"] is True
    assert plan["principal"]["price"] == 19
    assert plan["principal"]["credits"] == 20
    assert plan["principal"]["checkout_ready"] is True
    assert plan["pack"]["price"] == 10
    assert plan["pack"]["credits"] == 10
    assert plan["pack"]["period"] == "avulso"
    assert plan["pack"]["checkout_ready"] is True
    assert plan["pack"]["optional"] is True
    assert plan["plans_href"].endswith("/loja") or "/loja?" in plan["plans_href"]


def test_deepen_without_conscious_send_does_not_call_model_or_reserve(db, monkeypatch) -> None:
    called = {"model": 0, "reserve": 0}

    class Boom:
        def complete(self, *_args, **_kwargs):
            called["model"] += 1
            raise AssertionError("modelo não deveria ser chamado")

    monkeypatch.setattr(
        "app.domain.gigio.service.access_for_account",
        lambda *_a, **_k: {
            "authorized": True,
            "identified": True,
            "credits": 20,
            "balance_source": "hub",
            "exhausted": False,
            "plan": public_plan(get_settings()),
        },
    )

    def _reserve(*_a, **_k):
        called["reserve"] += 1
        raise AssertionError("reserva não deveria ocorrer sem Usar 1 crédito")

    monkeypatch.setattr("app.domain.gigio.service.reserve_credit", _reserve)
    settings = get_settings()
    monkeypatch.setattr(settings, "gigio_enabled", True)
    result = chat(
        db,
        settings,
        messages=[{"role": "user", "content": "Adapte esta fórmula para a minha cozinha"}],
        page={"path": "/biblioteca/o-comeco", "library": {"article_id": "o-comeco", "intent": "deepen"}},
        order_token=None,
        is_admin=False,
        gateway=Boom(),
        spend_credit=False,
    )
    assert called == {"model": 0, "reserve": 0}
    assert result["access"]["needs_confirm"] is True
    assert "Usar 1 crédito" in result["reply"]


def test_deepen_confirms_once_and_recovers_without_new_debit(db, monkeypatch) -> None:
    calls = {"model": 0, "reserve": 0, "confirm": 0}

    class Once:
        def complete(self, *_args, **_kwargs):
            calls["model"] += 1
            return _reply("Reduza 20 g de água e observe o ponto de véu.")

    monkeypatch.setattr(
        "app.domain.gigio.service.access_for_account",
        lambda *_a, **_k: {
            "authorized": True,
            "identified": True,
            "credits": 20,
            "balance_source": "hub",
            "exhausted": False,
            "complementary_eligible": True,
            "plan": public_plan(get_settings()),
        },
    )
    monkeypatch.setattr(
        "app.domain.gigio.service.reserve_credit",
        lambda *_a, **_k: calls.__setitem__("reserve", calls["reserve"] + 1) or {"ok": True, "status": "reserved", "credits": 19},
    )
    monkeypatch.setattr(
        "app.domain.gigio.service.confirm_credit",
        lambda *_a, **_k: calls.__setitem__("confirm", calls["confirm"] + 1) or {"ok": True, "status": "confirmed", "credits": 19},
    )
    settings = get_settings()
    monkeypatch.setattr(settings, "gigio_enabled", True)
    account = type("A", (), {"id": 1, "email": "cliente@example.com"})()
    first = chat(
        db,
        settings,
        messages=[{"role": "user", "content": "Como adapto a hidratação?"}],
        page={"path": "/biblioteca/o-comeco", "library": {"article_id": "o-comeco", "intent": "deepen"}},
        order_token=None,
        is_admin=False,
        gateway=Once(),
        account=account,
        spend_credit=True,
        operation_id="op-91b-1",
    )
    assert first["unavailable"] is False
    assert first["access"]["charged"] is True
    assert calls == {"model": 1, "reserve": 1, "confirm": 1}
    replay = chat(
        db,
        settings,
        messages=[{"role": "user", "content": "Como adapto a hidratação?"}],
        page={"path": "/biblioteca/o-comeco", "library": {"article_id": "o-comeco", "intent": "deepen"}},
        order_token=None,
        is_admin=False,
        gateway=Once(),
        account=account,
        spend_credit=True,
        operation_id="op-91b-1",
    )
    assert replay["reply"] == first["reply"]
    assert calls == {"model": 1, "reserve": 1, "confirm": 1}


def test_failed_deepen_releases_and_shop_stays_free(db, monkeypatch) -> None:
    calls = {"reserve": 0, "release": 0, "confirm": 0}

    class Empty:
        def complete(self, *_args, **_kwargs):
            return _reply("")

    monkeypatch.setattr(
        "app.domain.gigio.service.access_for_account",
        lambda *_a, **_k: {
            "authorized": True,
            "identified": True,
            "credits": 5,
            "balance_source": "hub",
            "exhausted": False,
            "plan": public_plan(get_settings()),
        },
    )
    monkeypatch.setattr(
        "app.domain.gigio.service.reserve_credit",
        lambda *_a, **_k: calls.__setitem__("reserve", calls["reserve"] + 1) or {"ok": True, "status": "reserved", "credits": 4},
    )
    monkeypatch.setattr(
        "app.domain.gigio.service.release_credit",
        lambda *_a, **_k: calls.__setitem__("release", calls["release"] + 1) or {"ok": True, "status": "released", "credits": 5},
    )
    monkeypatch.setattr(
        "app.domain.gigio.service.confirm_credit",
        lambda *_a, **_k: calls.__setitem__("confirm", calls["confirm"] + 1) or {"ok": True},
    )
    settings = get_settings()
    monkeypatch.setattr(settings, "gigio_enabled", True)
    account = type("A", (), {"id": 2, "email": "cliente@example.com"})()
    result = chat(
        db,
        settings,
        messages=[{"role": "user", "content": "Explique esta fórmula"}],
        page={"path": "/biblioteca/o-comeco", "library": {"article_id": "o-comeco", "intent": "deepen"}},
        order_token=None,
        is_admin=False,
        gateway=Empty(),
        account=account,
        spend_credit=True,
        operation_id="op-91b-fail",
    )
    assert result["unavailable"] is True
    assert result["access"]["charged"] is False
    assert calls == {"reserve": 1, "release": 1, "confirm": 0}

    _mock_hub(monkeypatch, [])
    shop = chat(
        db,
        settings,
        messages=[{"role": "user", "content": "Qual o Pix do meu pedido?"}],
        page={"path": "/biblioteca/o-comeco", "library": {"article_id": "o-comeco", "intent": "deepen"}},
        order_token=None,
        is_admin=False,
        gateway=FakeGigioGateway(),
        spend_credit=False,
    )
    assert shop["unavailable"] is False
    assert shop.get("access") is None or shop.get("access", {}).get("charged") is None
    assert classify_function(
        {"path": "/biblioteca/o-comeco", "library": {"article_id": "o-comeco", "intent": "deepen"}},
        TurnDecision("table", True, False),
    ) == "atendimento"


def test_local_operation_does_not_create_balance(db) -> None:
    settings = get_settings()
    account = type("A", (), {"id": 3, "email": "cliente@example.com"})()
    remember_operation(
        db,
        settings,
        account,
        "op-rec",
        "confirmed",
        {"reply": "Já respondi esta consulta.", "unavailable": False},
    )
    stored = recovered_reply(db, "op-rec")
    assert stored is not None
    assert stored["reply"].startswith("Já respondi")
