"""Provedor Google GenAI (Gemini) — grounding e structured output."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv
from google import genai
from google.genai import types

from services.llm.base_provider import LLMProvider, LLMResult
from services.llm.schema_compat import to_provider_schema

_BACKEND_ENV = Path(__file__).resolve().parent.parent.parent / "backend" / ".env"

DEFAULT_GOOGLE_MODEL = "gemini-3.5-flash"
_DEPRECATED_MODELS = {
    "gemini-2.5-flash": DEFAULT_GOOGLE_MODEL,
    "models/gemini-2.5-flash": DEFAULT_GOOGLE_MODEL,
    "gemini-2.5-flash-lite": DEFAULT_GOOGLE_MODEL,
    "gemini-1.5-flash": DEFAULT_GOOGLE_MODEL,
}


def _load_env() -> None:
    load_dotenv(_BACKEND_ENV, override=True)


def _looks_like_google_model(name: str) -> bool:
    """Evita enviar tag Ollama (ex.: qwen2.5-coder:3b) à API Gemini."""
    n = name.removeprefix("models/").strip().lower()
    if not n:
        return False
    if ":" in n:  # tags Ollama estilo nome:tamanho
        return False
    return n.startswith("gemini") or n in _DEPRECATED_MODELS


def resolve_google_model() -> str:
    """Resolve modelo Google: LLM_MODEL (se Gemini) → GEMINI_MODEL → default."""
    _load_env()
    candidates = [
        (os.getenv("LLM_MODEL") or "").strip(),
        (os.getenv("GEMINI_MODEL") or "").strip(),
        DEFAULT_GOOGLE_MODEL,
    ]
    for model in candidates:
        if not model or not _looks_like_google_model(model):
            continue
        normalized = model.removeprefix("models/")
        mapped = _DEPRECATED_MODELS.get(model) or _DEPRECATED_MODELS.get(normalized)
        return mapped or normalized
    return DEFAULT_GOOGLE_MODEL


def get_google_api_key() -> str:
    _load_env()
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key or api_key == "sua_chave_aqui":
        raise RuntimeError(
            "GEMINI_API_KEY não configurada. Defina a chave em backend/.env"
        )
    return api_key


def _response_text(response: Any) -> str:
    """Extrai texto mesmo quando response.text vem vazio (parts / finish_reason)."""
    try:
        direct = getattr(response, "text", None)
        if isinstance(direct, str) and direct.strip():
            return direct.strip()
    except Exception:
        # google-genai às vezes levanta ao acessar .text sem parts.
        pass

    chunks: list[str] = []
    for candidate in getattr(response, "candidates", None) or []:
        content = getattr(candidate, "content", None)
        for part in getattr(content, "parts", None) or []:
            part_text = getattr(part, "text", None)
            if isinstance(part_text, str) and part_text:
                chunks.append(part_text)
    return "\n".join(chunks).strip()


class GoogleProvider(LLMProvider):
    """Implementação Gemini via google-genai SDK."""

    def __init__(self, *, api_key: Optional[str] = None, model: Optional[str] = None):
        self._api_key = api_key
        self._model = model

    def _sync_generate(
        self,
        prompt: str,
        *,
        system_instruction: str | None,
        response_json: bool,
        temperature: float,
        max_output_tokens: int | None,
        enable_web_search: bool,
        response_schema: Any,
    ) -> LLMResult:
        api_key = self._api_key or get_google_api_key()
        model = self._model or resolve_google_model()
        client = genai.Client(api_key=api_key)

        tools: Optional[list[types.Tool]] = None
        if enable_web_search:
            tools = [types.Tool(google_search=types.GoogleSearch())]

        config_kwargs: dict[str, Any] = {"temperature": temperature}
        if system_instruction:
            config_kwargs["system_instruction"] = system_instruction
        if tools:
            config_kwargs["tools"] = tools
        # response_mime_type / schema costumam conflitar com google_search.
        if (response_json or response_schema is not None) and not enable_web_search:
            config_kwargs["response_mime_type"] = "application/json"
            if response_schema is not None:
                config_kwargs["response_schema"] = to_provider_schema(response_schema)
        if max_output_tokens:
            config_kwargs["max_output_tokens"] = max_output_tokens

        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(**config_kwargs),
        )

        text = _response_text(response)
        meta: dict[str, Any] = {"model": model, "provider": "google"}
        if response_schema is not None:
            meta["structured_output"] = True

        try:
            candidate = response.candidates[0] if response.candidates else None
            if candidate is not None:
                finish = getattr(candidate, "finish_reason", None)
                if finish is not None:
                    meta["finish_reason"] = str(finish)
                gm = getattr(candidate, "grounding_metadata", None)
                if gm is not None:
                    meta["grounding"] = {
                        "web_search_queries": list(
                            getattr(gm, "web_search_queries", None) or []
                        ),
                        "grounding_chunks": [
                            {
                                "uri": getattr(
                                    getattr(chunk, "web", None), "uri", None
                                ),
                                "title": getattr(
                                    getattr(chunk, "web", None), "title", None
                                ),
                            }
                            for chunk in (getattr(gm, "grounding_chunks", None) or [])
                        ],
                    }
            prompt_feedback = getattr(response, "prompt_feedback", None)
            block = (
                getattr(prompt_feedback, "block_reason", None)
                if prompt_feedback
                else None
            )
            if block is not None:
                meta["block_reason"] = str(block)
        except Exception:
            pass

        if not text:
            reason = (
                meta.get("block_reason") or meta.get("finish_reason") or "desconhecido"
            )
            raise RuntimeError(
                f"Gemini retornou texto vazio (motivo={reason}). "
                "Tente reduzir o tamanho das entradas ou repetir a fase."
            )

        return LLMResult(text=text, meta=meta)

    async def generate(
        self,
        prompt: str,
        *,
        system_instruction: str | None = None,
        response_json: bool = False,
        temperature: float = 0.3,
        max_output_tokens: int | None = None,
        enable_web_search: bool = False,
        response_schema: Any = None,
    ) -> LLMResult:
        return await asyncio.to_thread(
            self._sync_generate,
            prompt,
            system_instruction=system_instruction,
            response_json=response_json,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            enable_web_search=enable_web_search,
            response_schema=response_schema,
        )
