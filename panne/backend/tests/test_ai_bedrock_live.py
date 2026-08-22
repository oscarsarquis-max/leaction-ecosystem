"""Teste vivo opcional. Desabilitado por padrão. Sem persistir credenciais."""

from __future__ import annotations

import os

import pytest
from app.modules.ai_orchestration.bedrock_adapter import BedrockClaudeGateway
from app.modules.ai_orchestration.gateway import ModelRequest
from app.modules.ai_orchestration.schema import ProposalOutput, proposal_json_schema
from app.modules.ai_orchestration.settings import load_bedrock_settings

pytestmark = pytest.mark.skipif(
    os.environ.get("BEDROCK_LIVE_TEST") != "1",
    reason="teste vivo Bedrock desabilitado",
)


def test_live_bedrock_synthetic_structured_output() -> None:
    settings = load_bedrock_settings()
    assert settings.max_tokens <= 1024
    gateway = BedrockClaudeGateway(settings=settings)
    response = gateway.complete(
        ModelRequest(
            interaction_type="create_formulation_proposal",
            system_prompt="Responda só no schema. Não use normas. Entrada sintética.",
            user_payload={
                "objective": "proposta sintética de pão de teste",
                "allowed_ingredient_versions": [],
                "evidence": [],
                "rules": ["não publicar", "não usar norma"],
            },
            output_schema=proposal_json_schema(),
            schema_name="ProposalOutput",
        )
    )
    parsed = ProposalOutput.model_validate(response.content)
    assert parsed.title
    assert response.provider == "bedrock"
    assert "AKIA" not in str(response.content)
