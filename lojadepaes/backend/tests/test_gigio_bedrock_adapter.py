from app.core.config import Settings
from app.domain.gigio.bedrock import (
    BedrockGigioGateway,
    anthropic_messages,
    anthropic_tools,
    extract_invoke,
    invoke_body,
)
from app.domain.gigio.gateway import ChatRequest, ChatTurn
from app.domain.gigio.settings import (
    CHAMELLEON_BEDROCK_MODEL_ID,
    CHAMELLEON_BEDROCK_REGION,
    load_gigio_model_settings,
)
from app.domain.gigio.tools import TOOL_SPECS


def test_settings_use_chamelleon_contract() -> None:
    model = load_gigio_model_settings(Settings(bedrock_region="", bedrock_model_id=""), environ={})
    assert model.region == CHAMELLEON_BEDROCK_REGION
    assert model.model_id == "us.anthropic.claude-sonnet-4-6"
    assert model.model_id == CHAMELLEON_BEDROCK_MODEL_ID
    assert "20250514" not in model.model_id
    assert model.ssl_verify is True


def test_invoke_body_matches_chamelleon_messages_api() -> None:
    settings = load_gigio_model_settings(Settings(), environ={})
    body = invoke_body(
        ChatRequest(
            system_prompt="regras",
            messages=[
                ChatTurn(role="user", text="Qual a diferença entre fermentação e sova?"),
                ChatTurn(
                    role="assistant",
                    tool_use=[{"id": "tool-1", "name": "lookup_editorial", "input": {"topic_key": "concept:fermentacao"}}],
                ),
                ChatTurn(role="user", tool_results=[{"id": "tool-1", "content": {"notes": []}}]),
            ],
            tools=TOOL_SPECS,
            max_tokens=200,
        ),
        settings,
    )
    assert body["anthropic_version"] == "bedrock-2023-05-31"
    assert body["system"] == "regras"
    assert body["messages"][0]["content"] == "Qual a diferença entre fermentação e sova?"
    assert body["messages"][1]["content"][0]["type"] == "tool_use"
    assert body["messages"][2]["content"][0]["type"] == "tool_result"
    names = {item["name"] for item in anthropic_tools(TOOL_SPECS)}
    assert "lookup_products" in names
    assert "input_schema" in body["tools"][0]
    assert "inputSchema" not in body["tools"][0]


def test_extract_tool_use_and_text() -> None:
    text, tools, stop = extract_invoke(
        {
            "stop_reason": "tool_use",
            "content": [
                {"type": "text", "text": "vou consultar"},
                {"type": "tool_use", "id": "abc", "name": "lookup_products", "input": {"q": "pão"}},
            ],
        }
    )
    assert text == "vou consultar"
    assert tools == [{"id": "abc", "name": "lookup_products", "input": {"q": "pão"}}]
    assert stop == "tool_use"
    assert anthropic_messages([]) == []


class _FakeBody:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def read(self) -> bytes:
        import json

        return json.dumps(self._payload).encode("utf-8")


class _FakeClient:
    def __init__(self) -> None:
        self.calls: list[dict] = []
        self.meta = type("Meta", (), {"endpoint_url": "https://bedrock-runtime.us-east-1.amazonaws.com"})()

    def invoke_model(self, **kwargs):
        self.calls.append(kwargs)
        return {
            "body": _FakeBody(
                {
                    "content": [{"type": "text", "text": "Sugestão: toste o pão publicado e sirva com manteiga."}],
                    "stop_reason": "end_turn",
                    "usage": {"input_tokens": 11, "output_tokens": 22},
                }
            )
        }


def test_gateway_calls_invoke_model_not_converse() -> None:
    client = _FakeClient()
    settings = load_gigio_model_settings(Settings(), environ={})
    gateway = BedrockGigioGateway(client=client, settings=settings)
    response = gateway.complete(
        ChatRequest(
            system_prompt="sistema",
            messages=[ChatTurn(role="user", text="Uma ideia com os pães da vitrine")],
            tools=[],
            max_tokens=80,
        )
    )
    assert not hasattr(client, "converse") or not getattr(client, "converse_called", False)
    assert client.calls[0]["modelId"] == CHAMELLEON_BEDROCK_MODEL_ID
    assert response.provider == "bedrock"
    assert "toste" in response.text.casefold()
    assert response.input_tokens == 11
