"""Limites técnicos do assistente. Sem segredos e sem cobrança."""

from __future__ import annotations

import os

PROMPT_TEMPLATE_NAME = "panne_recipe_assistant"
PROMPT_TEMPLATE_VERSION = "2"
MAX_EVIDENCE_FRAGMENTS = 8
MAX_EVIDENCE_CHARS = 800
MAX_OBJECTIVE_CHARS = 2_000
MAX_NOTES_CHARS = 1_000
MAX_LIST_ITEMS = 20
MAX_ITEM_CHARS = 200
MAX_OUTPUT_TOKENS = 4_096
DEFAULT_TEMPERATURE = 0.0
GATEWAY_TIMEOUT_SECONDS = 45
MAX_SAFE_RETRIES = 2
MAX_CONCURRENT_PROPOSALS = 2
ALLOWED_MODELS = ("fake-model",)
ALLOWED_MASS_UNITS = frozenset({"g", "kg", "mg"})


def runtime_limits(environ: dict[str, str] | None = None) -> dict:
    env = environ if environ is not None else os.environ
    models = tuple(
        item.strip()
        for item in (env.get("PANNE_AI_ALLOWED_MODELS") or "fake-model").split(",")
        if item.strip()
    ) or ALLOWED_MODELS
    return {
        "max_evidence_fragments": int(env.get("PANNE_AI_MAX_FRAGMENTS") or MAX_EVIDENCE_FRAGMENTS),
        "max_evidence_chars": int(env.get("PANNE_AI_MAX_EVIDENCE_CHARS") or MAX_EVIDENCE_CHARS),
        "max_objective_chars": int(env.get("PANNE_AI_MAX_OBJECTIVE_CHARS") or MAX_OBJECTIVE_CHARS),
        "max_output_tokens": int(env.get("PANNE_AI_MAX_OUTPUT_TOKENS") or MAX_OUTPUT_TOKENS),
        "timeout_seconds": int(env.get("PANNE_AI_TIMEOUT_SECONDS") or GATEWAY_TIMEOUT_SECONDS),
        "max_retries": int(env.get("PANNE_AI_MAX_RETRIES") or MAX_SAFE_RETRIES),
        "max_concurrent": int(env.get("PANNE_AI_MAX_CONCURRENT") or MAX_CONCURRENT_PROPOSALS),
        "temperature": float(env.get("PANNE_AI_TEMPERATURE") or DEFAULT_TEMPERATURE),
        "allowed_models": models,
        "prompt_template_name": PROMPT_TEMPLATE_NAME,
        "prompt_template_version": PROMPT_TEMPLATE_VERSION,
    }
