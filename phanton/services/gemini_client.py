"""Cliente Gemini compartilhado (L2 Grounding, L3 Síntese)."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv
from google import genai
from google.genai import types

_BACKEND_ENV = Path(__file__).resolve().parent.parent / "backend" / ".env"
load_dotenv(_BACKEND_ENV, override=True)

DEFAULT_MODEL = "gemini-3.5-flash"
_DEPRECATED_MODELS = {
    "gemini-2.5-flash": DEFAULT_MODEL,
    "models/gemini-2.5-flash": DEFAULT_MODEL,
    "gemini-2.5-flash-lite": DEFAULT_MODEL,
    "gemini-1.5-flash": DEFAULT_MODEL,
}


def load_env() -> None:
    load_dotenv(_BACKEND_ENV, override=True)


def resolve_model() -> str:
    load_env()
    model = (os.getenv("GEMINI_MODEL") or DEFAULT_MODEL).strip() or DEFAULT_MODEL
    normalized = model.removeprefix("models/")
    mapped = _DEPRECATED_MODELS.get(model) or _DEPRECATED_MODELS.get(normalized)
    return mapped or normalized


def get_api_key() -> str:
    load_env()
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key or api_key == "sua_chave_aqui":
        raise RuntimeError(
            "GEMINI_API_KEY não configurada. Defina a chave em backend/.env"
        )
    return api_key


def _repair_truncated_json(fragment: str) -> Any:
    """Tenta recuperar JSON truncado/malformado comum em respostas longas."""
    text = (fragment or "").strip()
    if not text:
        raise ValueError("Fragmento JSON vazio")

    # Remove vírgulas finais antes de } ou ]
    text = re.sub(r",\s*([}\]])", r"\1", text)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Fecha strings/aberturas pendentes de forma heurística.
    in_string = False
    escape = False
    stack: list[str] = []
    for ch in text:
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch in "{[":
            stack.append("}" if ch == "{" else "]")
        elif ch in "}]":
            if stack and stack[-1] == ch:
                stack.pop()

    candidate = text
    if in_string:
        candidate += '"'
    # Remove vírgula pendente no fim
    candidate = re.sub(r",\s*$", "", candidate)
    candidate += "".join(reversed(stack))
    candidate = re.sub(r",\s*([}\]])", r"\1", candidate)

    suffixes = (
        "",
        "}",
        "]}",
        '"]}',
        '"}]}',
        "}}",
        "]}}",
        '"}]}',
    )
    for suffix in suffixes:
        try:
            return json.loads(candidate + suffix)
        except json.JSONDecodeError:
            continue

    raise ValueError(f"Não foi possível reparar JSON truncado. Prévia: {text[:240]!r}")


def extract_json_payload(text: str) -> Any:
    cleaned = (text or "").strip()
    if not cleaned:
        raise ValueError("Resposta vazia do Gemini")

    fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned, re.IGNORECASE)
    if fence:
        fenced = fence.group(1).strip()
        if fenced:
            cleaned = fenced
        else:
            # Cerca vazia — remove delimitadores e segue.
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.I)
            cleaned = re.sub(r"\s*```$", "", cleaned).strip()

    if not cleaned:
        raise ValueError("Resposta vazia do Gemini (cerca markdown sem conteúdo)")

    # Evita o JSONDecodeError cru "Expecting value: line 1 column 1".
    if not cleaned.lstrip()[:1] in "{[":
        # Pode ser Markdown puro — quem chama decide se aceita texto.
        raise ValueError(
            f"Resposta do Gemini não é JSON (começa com texto). "
            f"Prévia: {cleaned[:240]!r}"
        )

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as first_err:
        start_candidates = [i for i in (cleaned.find("{"), cleaned.find("[")) if i >= 0]
        if not start_candidates:
            raise ValueError(
                f"Resposta do Gemini não é JSON utilizável: {first_err}. "
                f"Prévia: {cleaned[:240]!r}"
            ) from first_err
        start = min(start_candidates)
        fragment = cleaned[start:].strip()
        if not fragment:
            raise ValueError(
                "Resposta do Gemini parece JSON mas o fragmento está vazio."
            ) from first_err
        try:
            return json.loads(fragment)
        except json.JSONDecodeError:
            pass
        try:
            obj, _ = json.JSONDecoder().raw_decode(fragment)
            return obj
        except Exception:
            pass
        try:
            return _repair_truncated_json(fragment)
        except Exception:
            raise ValueError(
                f"JSON inválido/truncado do Gemini: {first_err}. "
                f"Prévia: {fragment[:240]!r}"
            ) from first_err


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


def generate_content(
    prompt: str,
    *,
    enable_google_search: bool = False,
    response_json: bool = False,
    temperature: float = 0.3,
    max_output_tokens: Optional[int] = None,
) -> tuple[str, dict[str, Any]]:
    """Chamada síncrona ao Gemini. Use via asyncio.to_thread no handler async."""
    api_key = get_api_key()
    model = resolve_model()
    client = genai.Client(api_key=api_key)

    tools: Optional[list[types.Tool]] = None
    if enable_google_search:
        tools = [types.Tool(google_search=types.GoogleSearch())]

    config_kwargs: dict[str, Any] = {"temperature": temperature}
    if tools:
        config_kwargs["tools"] = tools
    # response_mime_type costuma conflitar com google_search; só usar sem grounding.
    if response_json and not enable_google_search:
        config_kwargs["response_mime_type"] = "application/json"
    if max_output_tokens:
        config_kwargs["max_output_tokens"] = max_output_tokens

    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(**config_kwargs),
    )

    text = _response_text(response)
    meta: dict[str, Any] = {"model": model}

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
                            "uri": getattr(getattr(chunk, "web", None), "uri", None),
                            "title": getattr(getattr(chunk, "web", None), "title", None),
                        }
                        for chunk in (getattr(gm, "grounding_chunks", None) or [])
                    ],
                }
        prompt_feedback = getattr(response, "prompt_feedback", None)
        block = getattr(prompt_feedback, "block_reason", None) if prompt_feedback else None
        if block is not None:
            meta["block_reason"] = str(block)
    except Exception:
        pass

    if not text:
        reason = meta.get("block_reason") or meta.get("finish_reason") or "desconhecido"
        raise RuntimeError(
            f"Gemini retornou texto vazio (motivo={reason}). "
            "Tente reduzir o tamanho das entradas ou repetir a fase."
        )

    return text, meta
