"""Seleção do gateway existente. Sem segundo adaptador."""

from __future__ import annotations

import os

from app.config import get_settings
from app.modules.ai_orchestration.bedrock_adapter import BedrockClaudeGateway
from app.modules.ai_orchestration.fake_gateway import FakeModelGateway
from app.modules.ai_orchestration.gateway import ModelGateway
from app.modules.ai_orchestration.guardrails import require_production_guardrail
from app.modules.ai_orchestration.settings import load_bedrock_settings


def resolve_gateway(environ: dict[str, str] | None = None) -> ModelGateway:
    env = environ if environ is not None else os.environ
    mode = (env.get("PANNE_AI_GATEWAY") or "").strip().lower()
    settings_env = env.get("PANNE_ENV") or get_settings().env
    if mode == "fake" or (mode == "" and settings_env in {"test", "local", "demo"}):
        return FakeModelGateway()
    settings = load_bedrock_settings(env)
    require_production_guardrail(settings, env)
    return BedrockClaudeGateway(settings=settings)
