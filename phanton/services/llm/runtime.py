"""Helpers de execução sync sobre o LLMProvider assíncrono."""

from __future__ import annotations

import asyncio
import concurrent.futures
from typing import Any, Optional

from services.llm.base_provider import LLMResult
from services.llm.factory import LLMFactory


def run_coro_sync(coro: Any) -> Any:
    """Executa coroutine a partir de contexto síncrono."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result()


async def generate(
    prompt: str,
    *,
    system_instruction: str | None = None,
    response_json: bool = False,
    temperature: float = 0.3,
    max_output_tokens: int | None = None,
    enable_web_search: bool = False,
    enable_google_search: bool | None = None,
    response_schema: Any = None,
) -> LLMResult:
    """Atalho async: LLMFactory.get_provider().generate(...)."""
    web = enable_web_search
    if enable_google_search is not None:
        web = bool(enable_google_search)
    llm = LLMFactory.get_provider()
    return await llm.generate(
        prompt,
        system_instruction=system_instruction,
        response_json=response_json,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        enable_web_search=web,
        response_schema=response_schema,
    )


def generate_sync(
    prompt: str,
    *,
    system_instruction: str | None = None,
    response_json: bool = False,
    temperature: float = 0.3,
    max_output_tokens: int | None = None,
    enable_web_search: bool = False,
    enable_google_search: bool | None = None,
    response_schema: Any = None,
) -> LLMResult:
    """Versão síncrona (helpers / to_thread)."""
    return run_coro_sync(
        generate(
            prompt,
            system_instruction=system_instruction,
            response_json=response_json,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            enable_web_search=enable_web_search,
            enable_google_search=enable_google_search,
            response_schema=response_schema,
        )
    )


def generate_content(
    prompt: str,
    *,
    enable_google_search: bool = False,
    response_json: bool = False,
    response_schema: Any = None,
    temperature: float = 0.3,
    max_output_tokens: Optional[int] = None,
    system_instruction: str | None = None,
) -> tuple[str, dict[str, Any]]:
    """API sync em tupla (text, meta) — drop-in dos call sites antigos."""
    result = generate_sync(
        prompt,
        system_instruction=system_instruction,
        response_json=response_json,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        enable_google_search=enable_google_search,
        response_schema=response_schema,
    )
    return result.text, dict(result.meta or {})
