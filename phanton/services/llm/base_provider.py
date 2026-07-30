"""Contrato abstrato dos provedores LLM."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class LLMResult:
    """Resultado neutro de uma geração de texto."""

    text: str
    meta: dict[str, Any] = field(default_factory=dict)


class LLMProvider(ABC):
    """Interface assíncrona de inferência — independente do vendor."""

    @abstractmethod
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
        """Gera texto a partir do prompt.

        Capacidades opcionais (web search, schema) podem ser ignoradas ou
        degradadas pelo provedor — ver ``meta`` no retorno.
        """

    async def generate_text(
        self,
        prompt: str,
        *,
        system_instruction: str | None = None,
        response_json: bool = False,
        temperature: float = 0.3,
        max_output_tokens: int | None = None,
        enable_web_search: bool = False,
        response_schema: Any = None,
    ) -> str:
        """Atalho: retorna apenas o texto."""
        result = await self.generate(
            prompt,
            system_instruction=system_instruction,
            response_json=response_json,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            enable_web_search=enable_web_search,
            response_schema=response_schema,
        )
        return result.text
