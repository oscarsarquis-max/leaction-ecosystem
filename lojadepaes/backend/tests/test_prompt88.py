from app.core.config import get_settings
from app.domain.gigio.bedrock import extract_invoke
from app.domain.gigio.fake import FakeGigioGateway
from app.domain.gigio.gateway import ChatRequest, ChatResponse
from app.domain.gigio.hygiene import is_leaked_tool_instruction, usable_customer_reply
from app.domain.gigio.policy import INCOMPLETE_REPLY
from app.domain.gigio.rules import PROCESS_RULES, PROCESS_RULES_VERSION
from app.domain.gigio.service import chat
from app.domain.gigio.tools import execute_tool
from sqlalchemy.orm import Session
from tests.test_gigio import _ok, _published

ARABIA = (
    "Vou dar um jantar com o tema noite das arábias. "
    "Que pão e acompanhamentos vc me recomenda? E bebidas?"
)
LEAK = '<invoke name="lookup_products"> <parameter name="q"> </parameter> </invoke>'


def _enable(monkeypatch) -> None:
    monkeypatch.setenv("LOJADEPAES_GIGIO_ENABLED", "true")
    monkeypatch.setenv("LOJADEPAES_GIGIO_GATEWAY", "fake")
    get_settings.cache_clear()


def _resp(text: str, tools: list | None = None) -> ChatResponse:
    return ChatResponse(
        text=text,
        tool_use=list(tools or []),
        stop_reason="tool_use" if tools else "end_turn",
        input_tokens=8,
        output_tokens=20,
        latency_ms=4,
        provider="fake",
        model_id="fake",
        region="local",
    )


class Scripted:
    def __init__(self, script: list[ChatResponse]) -> None:
        self.script = list(script)
        self.calls: list[ChatRequest] = []

    def complete(self, request: ChatRequest) -> ChatResponse:
        self.calls.append(request)
        if self.script:
            return self.script.pop(0)
        return _ok("Para o jantar, um pão da vitrine com humus e salada, sem presumir álcool.")


def test_rules_version_is_88() -> None:
    assert int(PROCESS_RULES_VERSION) >= 88
    assert "Nunca escreva invocação de ferramenta" in PROCESS_RULES
    assert "propose_builder" in PROCESS_RULES


def test_leak_detection_keeps_mixed_and_user_citation() -> None:
    assert is_leaked_tool_instruction(LEAK)
    assert usable_customer_reply(LEAK) == ""
    mixed = f"Para o jantar sirva pão achatado com humus. {LEAK}"
    cleaned = usable_customer_reply(mixed)
    assert "pão achatado" in cleaned
    assert "invoke" not in cleaned
    assert not is_leaked_tool_instruction("o que significa <invoke name=\"lookup_products\"> na documentação?")


def test_xml_text_is_not_executed_as_tool(db: Session, monkeypatch) -> None:
    _enable(monkeypatch)
    _published(db, "Pão de Café")
    db.commit()
    text, tools, _stop = extract_invoke(
        {"stop_reason": "end_turn", "content": [{"type": "text", "text": LEAK}]}
    )
    assert tools == []
    assert "invoke" in text
    gateway = Scripted([_resp(LEAK), _ok("Para um jantar com tema de noite das arábias, um pão achatado da vitrine com humus.")])
    result = chat(
        db,
        get_settings(),
        messages=[{"role": "user", "content": ARABIA}],
        page={"path": "/"},
        order_token=None,
        is_admin=False,
        gateway=gateway,
    )
    assert result["unavailable"] is False
    assert "invoke" not in result["reply"]
    assert "parameter" not in result["reply"]
    assert "jantar" in result["reply"].casefold() or "pão" in result["reply"].casefold()
    assert all(not call.tools for call in gateway.calls[1:])


def test_structured_tool_still_runs(db: Session, monkeypatch) -> None:
    _enable(monkeypatch)
    loaf = _published(db, "Pão Fermentação Natural")
    db.commit()
    gateway = Scripted(
        [
            _resp("", [{"id": "t1", "name": "lookup_products", "input": {"q": "fermentação"}}]),
            _ok(f"O {loaf.name} está publicado e serve bem a um jantar."),
        ]
    )
    result = chat(
        db,
        get_settings(),
        messages=[{"role": "user", "content": ARABIA}],
        page={"path": "/"},
        order_token=None,
        is_admin=False,
        gateway=gateway,
    )
    assert result["unavailable"] is False
    assert loaf.name.split()[0] in result["reply"] or "jantar" in result["reply"].casefold()


def test_empty_and_unknown_tool_are_defined(db: Session) -> None:
    empty = execute_tool(
        "lookup_products",
        {"q": ""},
        session=db,
        settings=get_settings(),
        order_reference=None,
        order_token=None,
        is_admin=False,
    )
    assert empty["error"] == "empty_query"
    assert empty["items"] == []
    unknown = execute_tool(
        "drop_database",
        {},
        session=db,
        settings=get_settings(),
        order_reference=None,
        order_token=None,
        is_admin=False,
    )
    assert unknown["error"] == "unknown_tool"


def test_double_leak_is_explicit_failure(db: Session, monkeypatch) -> None:
    _enable(monkeypatch)
    gateway = Scripted([_resp(LEAK), _resp(LEAK)])
    result = chat(
        db,
        get_settings(),
        messages=[{"role": "user", "content": ARABIA}],
        page={"path": "/"},
        order_token=None,
        is_admin=False,
        gateway=gateway,
    )
    assert result["unavailable"] is True
    assert result["reply"] == INCOMPLETE_REPLY
    assert "invoke" not in result["reply"]
    assert "estoque" not in result["reply"].casefold()
    assert "longa demais" not in result["reply"]


def test_user_citing_tool_syntax_is_not_a_command(db: Session, monkeypatch) -> None:
    _enable(monkeypatch)
    result = chat(
        db,
        get_settings(),
        messages=[
            {
                "role": "user",
                "content": "O que significa esta sintaxe: <invoke name=\"lookup_products\"> ?",
            }
        ],
        page={"path": "/"},
        order_token=None,
        is_admin=False,
        gateway=FakeGigioGateway(),
    )
    assert result["unavailable"] is False
    assert "invoke" not in result["reply"]
    assert result["reply"]


def test_arabia_paraphrase_and_no_alcohol(db: Session, monkeypatch) -> None:
    _enable(monkeypatch)
    result = chat(
        db,
        get_settings(),
        messages=[
            {
                "role": "user",
                "content": "Jantar com tema persa, que pão combina? Bebidas sem álcool, por favor.",
            }
        ],
        page={"path": "/"},
        order_token=None,
        is_admin=False,
        gateway=FakeGigioGateway(),
    )
    assert result["unavailable"] is False
    assert "invoke" not in result["reply"]
    assert result["reply"].strip()
