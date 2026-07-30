"""Provedor Ollama (HTTP local / soberano)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

import httpx
from dotenv import load_dotenv

from services.llm.base_provider import LLMProvider, LLMResult

_BACKEND_ENV = Path(__file__).resolve().parent.parent.parent / "backend" / ".env"
DEFAULT_OLLAMA_BASE_URL = "http://127.0.0.1:11434"
DEFAULT_OLLAMA_MODEL = "llama3"


def _load_env() -> None:
    load_dotenv(_BACKEND_ENV, override=True)


def resolve_ollama_base_url() -> str:
    _load_env()
    return (
        (os.getenv("LLM_BASE_URL") or "").strip().rstrip("/")
        or DEFAULT_OLLAMA_BASE_URL
    )


def resolve_ollama_model() -> str:
    _load_env()
    # Preferência: OLLAMA_MODEL (alias operacional) → LLM_MODEL → default
    return (
        (os.getenv("OLLAMA_MODEL") or "").strip()
        or (os.getenv("LLM_MODEL") or "").strip()
        or DEFAULT_OLLAMA_MODEL
    )


class OllamaProvider(LLMProvider):
    """Chamadas à API ``/api/generate`` do Ollama via httpx."""

    def __init__(
        self,
        *,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 300.0,
    ):
        self._base_url = (base_url or resolve_ollama_base_url()).rstrip("/")
        self._model = model or resolve_ollama_model()
        self._timeout = timeout

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
        system_parts: list[str] = []
        if system_instruction and system_instruction.strip():
            system_parts.append(system_instruction.strip())
        if response_json or response_schema is not None:
            system_parts.append(
                "Responda APENAS com JSON válido. "
                "Não use markdown, cercas ```json nem texto fora do objeto/array JSON."
            )
        system = "\n\n".join(system_parts) if system_parts else None

        options: dict[str, Any] = {"temperature": temperature}
        if max_output_tokens is not None:
            options["num_predict"] = int(max_output_tokens)

        payload: dict[str, Any] = {
            "model": self._model,
            "prompt": prompt,
            "stream": False,
            "options": options,
        }
        if system:
            payload["system"] = system
        if response_json or response_schema is not None:
            # format=json quando suportado pelo modelo/Ollama
            payload["format"] = "json"

        url = f"{self._base_url}/api/generate"
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(url, json=payload)
            if response.status_code >= 400:
                detail = (response.text or "").strip()
                try:
                    err_json = response.json()
                    if isinstance(err_json, dict):
                        detail = str(
                            err_json.get("error")
                            or err_json.get("message")
                            or detail
                        )
                except Exception:
                    pass
                hint = ""
                blob = detail.lower()
                if response.status_code == 500 or "memory" in blob or "vram" in blob:
                    hint = (
                        " Dica: Ollama 500 costuma ser falta de RAM/VRAM ao carregar "
                        f"o modelo `{self._model}`. Feche apps, use um tag menor "
                        "(ex.: qwen2.5-coder:3b / :1.5b) ou volte LLM_PROVIDER=google."
                    )
                raise RuntimeError(
                    f"Ollama HTTP {response.status_code} em {url}: {detail}.{hint}"
                )
            data = response.json()

        text = ""
        if isinstance(data, dict):
            raw = data.get("response")
            if isinstance(raw, str):
                text = raw.strip()
            elif isinstance(data.get("message"), dict):
                msg = data["message"].get("content")
                if isinstance(msg, str):
                    text = msg.strip()

        meta: dict[str, Any] = {
            "model": self._model,
            "provider": "ollama",
            "base_url": self._base_url,
        }
        if response_schema is not None:
            meta["structured_output_requested"] = True
            meta["response_schema_ignored"] = True
        if enable_web_search:
            meta["web_search_unsupported"] = True

        if not text:
            raise RuntimeError(
                "Ollama retornou texto vazio. "
                "Verifique se o modelo está disponível (`ollama pull …`) "
                f"e se {url} está acessível."
            )

        return LLMResult(text=text, meta=meta)
