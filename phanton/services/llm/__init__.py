"""Camada de provedores LLM plugáveis (Google / Ollama)."""

from services.llm.base_provider import LLMProvider, LLMResult
from services.llm.factory import LLMFactory
from services.llm.json_utils import extract_json_payload
from services.llm.runtime import generate, generate_content, generate_sync

__all__ = [
    "LLMFactory",
    "LLMProvider",
    "LLMResult",
    "extract_json_payload",
    "generate",
    "generate_content",
    "generate_sync",
]
