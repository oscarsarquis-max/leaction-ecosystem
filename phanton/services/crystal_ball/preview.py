"""Prévia rápida — uma chamada barata, efêmera, is_preview=true."""

from __future__ import annotations

import asyncio
from typing import Any

from services.llm.runtime import generate_content


_PREVIEW_PROMPT = """
Você é um assistente que aproxima GROSSEIRAMENTE o formato de um prompt de
implementação (estilo IDE) a partir de um pedido em linguagem natural.

NÃO gere diagramas mermaid.
NÃO invente fases de pipeline.
Seja curto (máx. ~40 linhas).

Pedido do usuário:
{user_text}

Responda em Markdown com seções:
## Objetivo
## Escopo
## Restrições / segurança (hipóteses)
## Próximos passos sugeridos

Inclua no topo a linha: [PRÉVIA — NÃO É PROMPT DE PRODUÇÃO]
""".strip()


async def quick_preview(
    *,
    text: str | None = None,
    structured_requirements: dict[str, Any] | None = None,
) -> dict[str, Any]:
    user_bits: list[str] = []
    if text and str(text).strip():
        user_bits.append(str(text).strip())
    if isinstance(structured_requirements, dict) and structured_requirements:
        user_bits.append(f"structured_requirements (rascunho): {structured_requirements}")
    user_text = "\n\n".join(user_bits) if user_bits else "(pedido vazio)"

    prompt = _PREVIEW_PROMPT.format(user_text=user_text[:6000])
    confidence = "low"
    if len(user_text) > 200:
        confidence = "medium"

    try:
        raw_text, meta = await asyncio.to_thread(
            lambda: generate_content(
                prompt,
                enable_google_search=False,
                response_json=False,
                temperature=0.4,
                max_output_tokens=2048,
            )
        )
        body = (raw_text or "").strip()
        if not body.startswith("[PRÉVIA"):
            body = f"[PRÉVIA — NÃO É PROMPT DE PRODUÇÃO]\n\n{body}"
        return {
            "is_preview": True,
            "confidence": confidence,
            "preview_prompt": body,
            "meta": meta if isinstance(meta, dict) else {"provider_meta": meta},
            "disclaimer": (
                "Prévia aproximada — não substitui o pipeline nem o prompt_cursor de produção."
            ),
        }
    except Exception as exc:
        return {
            "is_preview": True,
            "confidence": "low",
            "preview_prompt": (
                "[PRÉVIA — NÃO É PROMPT DE PRODUÇÃO]\n\n"
                f"(fallback local) Não foi possível chamar o LLM: {exc}\n\n"
                f"Pedido recebido:\n{user_text[:1500]}"
            ),
            "meta": {"fallback": True, "error": str(exc)},
            "disclaimer": (
                "Prévia aproximada — não substitui o pipeline nem o prompt_cursor de produção."
            ),
        }
