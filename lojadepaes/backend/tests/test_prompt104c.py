"""104C: a consultoria usa a ficha publicada, não só a URL do guia."""

from app.core.config import get_settings
from app.domain.gigio.gateway import ChatResponse
from app.domain.gigio.intent import TurnDecision
from app.domain.gigio.pairing import (
    needs_stored_evidence,
    publish_authorized_pilot,
    sources_for_conversation,
    stored_evidence_brief,
)
from app.domain.gigio.service import _execute_allowed_tool, chat
from sqlalchemy.orm import Session
from tests.test_prompt81 import _enable_pairing


class _CaptureGateway:
    def __init__(self) -> None:
        self.system = ""

    def complete(self, request) -> ChatResponse:
        self.system = request.system_prompt
        return ChatResponse(
            text="O Descorchados atribui 95 pontos a este rótulo e safra. Isso não prova harmonização.",
            tool_use=[],
            stop_reason="end_turn",
            input_tokens=10,
            output_tokens=20,
            latency_ms=5,
            provider="fake",
            model_id="fake",
            region="local",
        )


def test_label_question_receives_the_stored_sheet_without_a_purchase_button(db: Session, monkeypatch) -> None:
    _enable_pairing(monkeypatch)
    publish_authorized_pilot(db)
    gateway = _CaptureGateway()
    result = chat(
        db,
        get_settings(),
        messages=[{"role": "user", "content": "O Sacramentos Sabina Entre Serras 2025 tem avaliação?"}],
        page={"path": "/"},
        order_token=None,
        is_admin=False,
        gateway=gateway,
    )
    assert "95" in gateway.system
    assert "Sabina Entre Serras" in gateway.system
    assert "não o guia inteiro" in gateway.system.casefold()
    assert "pesquisa nova" in gateway.system.casefold()
    assert result["cta"] is None
    assert result["sources"][0]["retrieval_role"] == "evaluation"
    assert "95" in result["sources"][0]["score_line"]


def test_followup_recovers_the_same_sheet(db: Session) -> None:
    publish_authorized_pilot(db)
    history = [{"role": "user", "content": "Vi o Sacramentos Sabina Entre Serras 2025."}]
    brief, keys = stored_evidence_brief(db, user_text="tem avaliação?", history=history)
    assert "evaluation" in keys
    assert "95" in brief
    assert "2025" in brief
    sources = sources_for_conversation(db, enabled=True, user_text="tem avaliação?", reply="", history=history)
    assert sources[0]["retrieval_role"] == "evaluation"
    assert "Paralelas" not in sources[0]["title"]


def test_brazilian_followup_states_the_verified_reach(db: Session) -> None:
    publish_authorized_pilot(db)
    history = [{"role": "user", "content": "O Sacramentos Sabina Entre Serras 2025 tem avaliação?"}]
    brief, _keys = stored_evidence_brief(db, user_text="e um brasileiro?", history=history)
    assert "Sabina Entre Serras" in brief
    assert "Paralelas" in brief
    assert "não o guia inteiro" in brief.casefold()
    assert needs_stored_evidence("quero um pão brasileiro", history, accompaniments=False) is False


def test_adega_locator_is_not_a_score(db: Session) -> None:
    publish_authorized_pilot(db)
    brief, keys = stored_evidence_brief(db, user_text="O Guia ADEGA 2026 tem nota de algum rótulo?", history=None)
    assert "informational" in keys
    assert "evaluation" not in keys
    assert "95" not in brief
    assert "94" not in brief
    assert "não há nota" in brief.casefold() or "sem nota" in brief.casefold()


def test_lamb_has_no_specialized_sheet(db: Session) -> None:
    publish_authorized_pilot(db)
    brief, keys = stored_evidence_brief(db, user_text="Que vinho combina com carneiro assado?", history=None)
    assert "gap-carneiro" in keys
    assert "não há ficha" in brief.casefold()
    assert "95" not in brief
    assert "Wine Folly" not in brief


def test_fish_pairing_uses_the_style_sheet_not_the_score(db: Session) -> None:
    publish_authorized_pilot(db)
    brief, keys = stored_evidence_brief(db, user_text="Qual vinho com peixe grelhado?", history=None)
    assert "evaluation" not in keys
    assert "95" not in brief
    assert "Wine Folly" in brief or "peixe" in brief.casefold()


def test_price_followup_does_not_turn_the_score_into_a_price(db: Session) -> None:
    publish_authorized_pilot(db)
    history = [{"role": "user", "content": "O Sacramentos Sabina Entre Serras 2025 tem avaliação?"}]
    brief, keys = stored_evidence_brief(db, user_text="nessa faixa de preço?", history=history)
    assert "gap-preco" in keys
    assert "95" in brief
    assert "não" in brief.casefold() and "preço" in brief.casefold()


def test_guide_question_can_read_the_sheet_tool(db: Session, monkeypatch) -> None:
    _enable_pairing(monkeypatch)
    publish_authorized_pilot(db)
    result = _execute_allowed_tool(
        "lookup_pairing_references",
        {"q": "tem avaliação?"},
        session=db,
        settings=get_settings(),
        order_reference=None,
        order_token=None,
        is_admin=False,
        decision=TurnDecision("support", False, False),
        user_text="tem avaliação?",
        history=[{"role": "user", "content": "O Sacramentos Sabina Entre Serras 2025"}],
    )
    assert result["evaluations"]
    assert "95" in result["evaluations"][0]["synthesis"]
    skipped = _execute_allowed_tool(
        "lookup_pairing_references",
        {"q": "onde está meu pedido?"},
        session=db,
        settings=get_settings(),
        order_reference=None,
        order_token=None,
        is_admin=False,
        decision=TurnDecision("support", False, False),
        user_text="onde está meu pedido?",
    )
    assert skipped["evaluations"] == []
