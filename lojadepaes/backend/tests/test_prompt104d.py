"""104D: consulta livre é uma resposta; refino pede crédito e não debita antes."""

from app.domain.gigio.consult import drop_phantom_click

from app.core.config import get_settings
from app.domain.gigio.gateway import ChatResponse
from app.domain.gigio.service import chat
from sqlalchemy.orm import Session


def test_drop_phantom_click_keeps_the_answer_and_a_real_button() -> None:
    text = "Um Vinho Verde combina. Para completar a mesa, é só clicar abaixo."
    assert "abaixo" not in drop_phantom_click(text, has_cta=False)
    assert "Vinho Verde" in drop_phantom_click(text, has_cta=False)
    assert "abaixo" in drop_phantom_click(text, has_cta=True)


def _enable(monkeypatch) -> None:
    monkeypatch.setenv("LOJADEPAES_GIGIO_ENABLED", "true")
    get_settings.cache_clear()


def _reply(text: str) -> ChatResponse:
    return ChatResponse(
        text=text,
        tool_use=[],
        stop_reason="end_turn",
        input_tokens=4,
        output_tokens=8,
        latency_ms=3,
        provider="fake",
        model_id="fake",
        region="local",
    )


class _Gateway:
    def __init__(self, text: str = "Um tinto de tanino baixo, assumindo assado simples.") -> None:
        self.calls = 0
        self.system = ""
        self.text = text

    def complete(self, request) -> ChatResponse:
        self.calls += 1
        self.system = request.system_prompt
        return _reply(self.text)


def test_free_question_answers_once_without_a_credit(db: Session, monkeypatch) -> None:
    _enable(monkeypatch)
    gateway = _Gateway()
    result = chat(
        db,
        get_settings(),
        messages=[{"role": "user", "content": "Que vinho combina com carneiro assado?"}],
        page={"path": "/"},
        order_token=None,
        is_admin=False,
        gateway=gateway,
        spend_credit=True,
    )
    assert gateway.calls == 1
    assert "Consulta livre" in gateway.system
    assert "Não pergunte orçamento" in gateway.system
    assert result["unavailable"] is False
    assert result.get("access") is None or result.get("access", {}).get("charged") is not True
    assert "?" not in result["reply"]


def test_refinement_offers_deepen_without_debit_or_model(db: Session, monkeypatch) -> None:
    _enable(monkeypatch)
    gateway = _Gateway()
    result = chat(
        db,
        get_settings(),
        messages=[
            {"role": "user", "content": "Que vinho combina com carneiro assado?"},
            {"role": "assistant", "content": "Um tinto, assumindo assado simples."},
            {"role": "user", "content": "E se o molho for de hortelã?"},
        ],
        page={"path": "/"},
        order_token=None,
        is_admin=False,
        gateway=gateway,
        spend_credit=True,
    )
    assert gateway.calls == 0
    assert result["cta"] is None
    assert result["access"]["deepen_offer"] is True
    assert result["access"]["charged"] is False
    assert "1 crédito" in result["reply"]


def test_new_question_stays_free(db: Session, monkeypatch) -> None:
    _enable(monkeypatch)
    gateway = _Gateway("Para peixe grelhado, a Wine Folly indica brancos cítricos se o peixe for magro.")
    result = chat(
        db,
        get_settings(),
        messages=[
            {"role": "user", "content": "Que vinho combina com carneiro assado?"},
            {"role": "assistant", "content": "Um tinto."},
            {"role": "user", "content": "Qual vinho com peixe grelhado?"},
        ],
        page={"path": "/"},
        order_token=None,
        is_admin=False,
        gateway=gateway,
    )
    assert gateway.calls == 1
    assert result.get("access") is None or result["access"].get("deepen_offer") is not True


def test_label_followup_stays_free(db: Session, monkeypatch) -> None:
    _enable(monkeypatch)
    gateway = _Gateway("Posso olhar a ficha deste rótulo.")
    result = chat(
        db,
        get_settings(),
        messages=[
            {"role": "user", "content": "Vi o Sacramentos Sabina Entre Serras 2025."},
            {"role": "assistant", "content": "É um sauvignon blanc."},
            {"role": "user", "content": "tem avaliação?"},
        ],
        page={"path": "/"},
        order_token=None,
        is_admin=False,
        gateway=gateway,
    )
    assert gateway.calls == 1
    assert result.get("access") is None or result["access"].get("deepen_offer") is not True


def test_order_help_stays_free_even_if_deepen_is_requested(db: Session, monkeypatch) -> None:
    _enable(monkeypatch)
    gateway = _Gateway("Abra o link do pedido para ver o Pix.")
    result = chat(
        db,
        get_settings(),
        messages=[
            {"role": "user", "content": "Que vinho combina com o pão?"},
            {"role": "assistant", "content": "Um tinto."},
            {"role": "user", "content": "Qual o Pix do meu pedido?"},
        ],
        page={"path": "/", "consult": "deepen"},
        order_token=None,
        is_admin=False,
        gateway=gateway,
        spend_credit=True,
    )
    assert gateway.calls == 1
    assert result.get("access") is None or result["access"].get("charged") is not True


def test_anonymous_deepen_does_not_call_the_model(db: Session, monkeypatch) -> None:
    _enable(monkeypatch)
    gateway = _Gateway()
    result = chat(
        db,
        get_settings(),
        messages=[{"role": "user", "content": "Quero aprofundar o vinho do carneiro."}],
        page={"path": "/", "consult": "deepen"},
        order_token=None,
        is_admin=False,
        gateway=gateway,
        spend_credit=True,
        account=None,
    )
    assert gateway.calls == 0
    assert result["unavailable"] is False
    assert "Identifique-se" in result["reply"]


def test_pack_credit_confirms_cost_before_debit(db: Session, monkeypatch) -> None:
    _enable(monkeypatch)
    account = type("A", (), {"id": 9, "email": "pacote@example.com"})()
    monkeypatch.setattr(
        "app.domain.gigio.service.access_for_account",
        lambda *_a, **_k: {
            "authorized": False,
            "identified": True,
            "can_use_ai": True,
            "credits": 10,
            "ai_credits": 10,
            "pack_credits": 10,
            "exhausted": False,
            "balance_source": "hub",
            "plan": {},
        },
    )

    def _debit(*_a, **_k):
        raise AssertionError("não debita antes da confirmação")

    monkeypatch.setattr("app.domain.gigio.service.reserve_credit", _debit)
    gateway = _Gateway()
    result = chat(
        db,
        get_settings(),
        messages=[{"role": "user", "content": "E se o molho mudar?"}],
        page={"path": "/", "consult": "deepen"},
        order_token=None,
        is_admin=False,
        gateway=gateway,
        spend_credit=False,
        account=account,
    )
    assert gateway.calls == 0
    assert result["access"]["needs_confirm"] is True
    assert result["access"].get("charged") is not True


def test_empty_balance_keeps_the_conversation(db: Session, monkeypatch) -> None:
    _enable(monkeypatch)
    account = type("A", (), {"id": 10, "email": "sem@example.com"})()
    monkeypatch.setattr(
        "app.domain.gigio.service.access_for_account",
        lambda *_a, **_k: {
            "authorized": False,
            "identified": True,
            "can_use_ai": False,
            "credits": 0,
            "exhausted": True,
            "message": "Os créditos de IA acabaram.",
            "plan": {"plans_href": "/planos"},
        },
    )
    gateway = _Gateway()
    result = chat(
        db,
        get_settings(),
        messages=[{"role": "user", "content": "Aprofunda esse vinho."}],
        page={"path": "/", "consult": "deepen"},
        order_token=None,
        is_admin=False,
        gateway=gateway,
        spend_credit=True,
        account=account,
    )
    assert gateway.calls == 0
    assert result["unavailable"] is False
    assert result["reply"]


def test_pack_only_deepen_debits_once_and_failure_releases(db: Session, monkeypatch) -> None:
    _enable(monkeypatch)
    calls = {"model": 0, "reserve": 0, "confirm": 0, "release": 0}

    class Empty:
        def complete(self, request) -> ChatResponse:
            calls["model"] += 1
            return _reply("")

    class Ok:
        def complete(self, request) -> ChatResponse:
            calls["model"] += 1
            return _reply("Com hortelã, o tinto muda: prefira um de tanino mais baixo.")

    monkeypatch.setattr(
        "app.domain.gigio.service.access_for_account",
        lambda *_a, **_k: {
            "authorized": False,
            "identified": True,
            "can_use_ai": True,
            "credits": 10,
            "ai_credits": 10,
            "monthly_credits": 0,
            "pack_credits": 10,
            "subscription_status": "none",
            "exhausted": False,
            "balance_source": "hub",
            "plan": {},
        },
    )
    monkeypatch.setattr(
        "app.domain.gigio.service.reserve_credit",
        lambda *_a, **_k: calls.__setitem__("reserve", calls["reserve"] + 1) or {"ok": True, "credits": 9},
    )
    monkeypatch.setattr(
        "app.domain.gigio.service.confirm_credit",
        lambda *_a, **_k: calls.__setitem__("confirm", calls["confirm"] + 1) or {"ok": True, "credits": 9},
    )
    monkeypatch.setattr(
        "app.domain.gigio.service.release_credit",
        lambda *_a, **_k: calls.__setitem__("release", calls["release"] + 1) or {"ok": True, "credits": 10},
    )
    account = type("A", (), {"id": 11, "email": "avulso@example.com"})()
    settings = get_settings()
    failed = chat(
        db,
        settings,
        messages=[{"role": "user", "content": "E se o molho for de hortelã?"}],
        page={"path": "/", "consult": "deepen"},
        order_token=None,
        is_admin=False,
        gateway=Empty(),
        account=account,
        spend_credit=True,
        operation_id="op-104d-fail",
    )
    assert failed["unavailable"] is True
    assert failed["access"]["charged"] is False
    assert calls["reserve"] == 1 and calls["release"] == 1 and calls["confirm"] == 0
    paid = chat(
        db,
        settings,
        messages=[{"role": "user", "content": "E se o molho for de hortelã?"}],
        page={"path": "/", "consult": "deepen"},
        order_token=None,
        is_admin=False,
        gateway=Ok(),
        account=account,
        spend_credit=True,
        operation_id="op-104d-ok",
    )
    assert paid["access"]["charged"] is True
    assert paid["access"]["credit_cost"] == 1
    replay = chat(
        db,
        settings,
        messages=[{"role": "user", "content": "E se o molho for de hortelã?"}],
        page={"path": "/", "consult": "deepen"},
        order_token=None,
        is_admin=False,
        gateway=Ok(),
        account=account,
        spend_credit=True,
        operation_id="op-104d-ok",
    )
    assert replay["reply"] == paid["reply"]
    assert calls == {"model": 3, "reserve": 2, "confirm": 1, "release": 1}


def test_free_reply_drops_a_refinement_question(db: Session, monkeypatch) -> None:
    _enable(monkeypatch)
    class _Two:
        def __init__(self) -> None:
            self.n = 0

        def complete(self, request) -> ChatResponse:
            self.n += 1
            if self.n == 1:
                return _reply("Um tinto combina. Qual o seu orçamento?")
            return _reply("Assumo uma faixa moderada e indico um tinto de tanino baixo.")

    gateway = _Two()
    result = chat(
        db,
        get_settings(),
        messages=[{"role": "user", "content": "Que vinho combina com carneiro assado?"}],
        page={"path": "/"},
        order_token=None,
        is_admin=False,
        gateway=gateway,
    )
    assert gateway.n == 2
    assert "orçamento" not in result["reply"].casefold()
    assert "tinto" in result["reply"].casefold()


def test_free_reply_drops_an_offer_to_keep_helping(db: Session, monkeypatch) -> None:
    _enable(monkeypatch)

    class _Two:
        def __init__(self) -> None:
            self.n = 0

        def complete(self, request) -> ChatResponse:
            self.n += 1
            if self.n == 1:
                return _reply("Um branco seco combina. Quer que eu ajude a montar essa mesa completa?")
            return _reply("Assumo peixe branco grelhado e indico um branco seco.")

    gateway = _Two()
    result = chat(
        db,
        get_settings(),
        messages=[{"role": "user", "content": "Que vinho combina com peixe grelhado?"}],
        page={"path": "/"},
        order_token=None,
        is_admin=False,
        gateway=gateway,
    )
    assert gateway.n == 2
    assert "?" not in result["reply"]
    assert "branco seco" in result["reply"].casefold()


def test_free_reply_drops_a_soft_invite(db: Session, monkeypatch) -> None:
    _enable(monkeypatch)

    class _Two:
        def __init__(self) -> None:
            self.n = 0

        def complete(self, request) -> ChatResponse:
            self.n += 1
            if self.n == 1:
                return _reply(
                    "Assumo peixe branco grelhado. Um Vinho Verde combina. "
                    "Se quiser me contar qual é o peixe, posso afinar a sugestão."
                )
            return _reply("Assumo peixe branco grelhado, sem molho pesado. Um Vinho Verde combina.")

    gateway = _Two()
    result = chat(
        db,
        get_settings(),
        messages=[{"role": "user", "content": "Que vinho combina com peixe grelhado?"}],
        page={"path": "/"},
        order_token=None,
        is_admin=False,
        gateway=gateway,
    )
    assert gateway.n == 2
    assert "me contar" not in result["reply"].casefold()
    assert "afinar" not in result["reply"].casefold()
    assert "Vinho Verde" in result["reply"]


def test_free_reply_drops_an_optional_followup(db: Session, monkeypatch) -> None:
    _enable(monkeypatch)

    class _Two:
        def __init__(self) -> None:
            self.n = 0

        def complete(self, request) -> ChatResponse:
            self.n += 1
            if self.n == 1:
                return _reply("Um Vinho Verde combina com peixe branco grelhado. Posso sugerir algo da vitrine se quiser!")
            return _reply("Assumo peixe branco grelhado. Um Vinho Verde combina.")

    gateway = _Two()
    result = chat(
        db,
        get_settings(),
        messages=[{"role": "user", "content": "Que vinho combina com peixe grelhado?"}],
        page={"path": "/"},
        order_token=None,
        is_admin=False,
        gateway=gateway,
    )
    assert gateway.n == 2
    assert "se quiser" not in result["reply"].casefold()
    assert "Vinho Verde" in result["reply"]
