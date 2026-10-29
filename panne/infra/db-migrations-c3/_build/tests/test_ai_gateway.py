from pathlib import Path

import pytest
from app.modules.ai_orchestration.bedrock_adapter import BedrockClaudeGateway
from app.modules.ai_orchestration.fake_gateway import FakeModelGateway
from app.modules.ai_orchestration.gateway import GatewayError, ModelRequest
from app.modules.ai_orchestration.schema import proposal_json_schema
from app.modules.ai_orchestration.settings import BedrockSettingsError, load_bedrock_settings


def _request() -> ModelRequest:
    return ModelRequest(
        interaction_type="create_formulation_proposal",
        system_prompt="sistema",
        user_payload={"objective": "pão sintético"},
        output_schema=proposal_json_schema(),
        schema_name="ProposalOutput",
    )


def test_fake_gateway_normalizes_response() -> None:
    gateway = FakeModelGateway()
    response = gateway.complete(_request())
    assert response.provider == "fake"
    assert response.model_id == "fake-model"
    assert response.stop_reason == "end_turn"
    assert "items" in response.content
    assert gateway.last_request is not None


def _env_example_path() -> Path:
    here = Path(__file__).resolve()
    for candidate in (
        here.parents[2] / ".env.example",
        here.parents[1] / ".env.example",
    ):
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(".env.example da Panne não encontrado")


def test_settings_are_external_and_example_has_no_static_keys() -> None:
    example = _env_example_path().read_text(encoding="utf-8")
    assert "AWS_ACCESS_KEY_ID" not in example
    assert "AWS_SECRET_ACCESS_KEY" not in example
    assert "AWS_SESSION_TOKEN" not in example
    with pytest.raises(BedrockSettingsError):
        load_bedrock_settings({})
    loaded = load_bedrock_settings(
        {
            "AWS_REGION": "us-east-2",
            "BEDROCK_REGION": "us-east-1",
            "BEDROCK_MODEL_ID": "configured-model",
            "BEDROCK_MAX_TOKENS": "512",
            "BEDROCK_TEMPERATURE": "0",
        }
    )
    assert loaded.model_id == "configured-model"
    assert loaded.region == "us-east-1"


def test_bedrock_adapter_uses_converse_and_rejects_mantle() -> None:
    class _Meta:
        endpoint_url = "https://bedrock-mantle.example"

    class _Client:
        meta = _Meta()

        def converse(self, **kwargs):
            raise AssertionError("não deve chamar mantle")

    gateway = BedrockClaudeGateway(
        client=_Client(),
        settings=load_bedrock_settings(
            {
                "AWS_REGION": "us-east-1",
                "BEDROCK_MODEL_ID": "configured-model",
            }
        ),
    )
    with pytest.raises(GatewayError, match="mantle"):
        gateway._runtime_client(gateway._settings_or_load())


def test_bedrock_adapter_maps_access_timeout_throttle_and_schema() -> None:
    class _Client:
        meta = type("M", (), {"endpoint_url": "https://bedrock-runtime.us-east-1.amazonaws.com"})()

        def __init__(self, error: Exception):
            self.error = error

        def converse(self, **kwargs):
            assert "outputConfig" in kwargs
            assert "bedrock-mantle" not in str(kwargs)
            raise self.error

    settings = load_bedrock_settings(
        {"AWS_REGION": "us-east-1", "BEDROCK_MODEL_ID": "configured-model"}
    )
    sleeps: list[float] = []
    for exc, code in (
        (type("AccessDeniedException", (Exception,), {})("denied"), "AccessDeniedException"),
        (type("ModelTimeoutException", (Exception,), {})("timeout"), "ModelTimeoutException"),
        (type("ThrottlingException", (Exception,), {})("slow"), "ThrottlingException"),
        (type("ValidationException", (Exception,), {})("schema"), "ValidationException"),
    ):
        gateway = BedrockClaudeGateway(
            client=_Client(exc),
            settings=settings,
            sleep=sleeps.append,
        )
        with pytest.raises(GatewayError, match=code):
            gateway.complete(_request())


def test_bedrock_adapter_reads_structured_json() -> None:
    class _Client:
        meta = type("M", (), {"endpoint_url": "https://bedrock-runtime.us-east-1.amazonaws.com"})()

        def converse(self, **kwargs):
            return {
                "output": {"message": {"content": [{"text": '{"title":"ok"}'}]}},
                "usage": {"inputTokens": 3, "outputTokens": 5},
                "stopReason": "end_turn",
            }

    gateway = BedrockClaudeGateway(
        client=_Client(),
        settings=load_bedrock_settings(
            {"AWS_REGION": "us-east-1", "BEDROCK_MODEL_ID": "configured-model"}
        ),
    )
    response = gateway.complete(_request())
    assert response.content == {"title": "ok"}
    assert response.input_token_count == 3
    assert response.structured_output_mode == "json_schema"


def test_unsupported_structured_output_fails() -> None:
    gateway = BedrockClaudeGateway(
        settings=load_bedrock_settings(
            {
                "AWS_REGION": "us-east-1",
                "BEDROCK_MODEL_ID": "configured-model",
                "BEDROCK_STRUCTURED_OUTPUT_MODE": "unsupported",
            }
        )
    )
    with pytest.raises(GatewayError, match="structured_output_unsupported"):
        gateway.complete(_request())
