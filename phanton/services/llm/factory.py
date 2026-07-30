"""Factory / singleton dos provedores LLM."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from services.llm.base_provider import LLMProvider

_BACKEND_ENV = Path(__file__).resolve().parent.parent.parent / "backend" / ".env"


def _load_env() -> None:
    load_dotenv(_BACKEND_ENV, override=True)


def resolve_provider_name() -> str:
    _load_env()
    raw = (os.getenv("LLM_PROVIDER") or "google").strip().lower()
    aliases = {
        "google": "google",
        "gemini": "google",
        "genai": "google",
        "ollama": "ollama",
        "local": "ollama",
    }
    return aliases.get(raw, raw)


class LLMFactory:
    """Resolve o provedor a partir de ``LLM_PROVIDER`` (singleton lazy)."""

    _instance: Optional[LLMProvider] = None
    _instance_name: Optional[str] = None

    @classmethod
    def reset(cls) -> None:
        """Limpa o singleton (útil em testes)."""
        cls._instance = None
        cls._instance_name = None

    @classmethod
    def get_provider(cls, *, force_reload: bool = False) -> LLMProvider:
        name = resolve_provider_name()
        if (
            not force_reload
            and cls._instance is not None
            and cls._instance_name == name
        ):
            return cls._instance

        if name == "google":
            from services.llm.google_provider import GoogleProvider

            provider: LLMProvider = GoogleProvider()
        elif name == "ollama":
            from services.llm.ollama_provider import OllamaProvider

            provider = OllamaProvider()
        else:
            raise ValueError(
                f"LLM_PROVIDER desconhecido: {name!r}. Use 'google' ou 'ollama'."
            )

        cls._instance = provider
        cls._instance_name = name
        return provider
