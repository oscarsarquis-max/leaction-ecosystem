"""Utilitários JSON neutros de vendor (parse resiliente a markdown)."""

from __future__ import annotations

import json
import re
from typing import Any


def repair_truncated_json(fragment: str) -> Any:
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
    """Extrai JSON mesmo com preâmbulo ou fences ```json (comum em IAs locais)."""
    cleaned = (text or "").strip()
    if not cleaned:
        raise ValueError("Resposta vazia do LLM")

    fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned, re.IGNORECASE)
    if fence:
        fenced = fence.group(1).strip()
        if fenced:
            cleaned = fenced
        else:
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.I)
            cleaned = re.sub(r"\s*```$", "", cleaned).strip()

    if not cleaned:
        raise ValueError("Resposta vazia do LLM (cerca markdown sem conteúdo)")

    def _try_parse(candidate: str) -> Any:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass
        try:
            obj, _ = json.JSONDecoder().raw_decode(candidate)
            return obj
        except Exception:
            pass
        return repair_truncated_json(candidate)

    # Caminho feliz: começa com JSON
    if cleaned.lstrip()[:1] in "{[":
        try:
            return _try_parse(cleaned.lstrip())
        except Exception as first_err:
            start_candidates = [
                i for i in (cleaned.find("{"), cleaned.find("[")) if i >= 0
            ]
            if not start_candidates:
                raise ValueError(
                    f"Resposta do LLM não é JSON utilizável: {first_err}. "
                    f"Prévia: {cleaned[:240]!r}"
                ) from first_err
            fragment = cleaned[min(start_candidates) :].strip()
            try:
                return _try_parse(fragment)
            except Exception:
                raise ValueError(
                    f"JSON inválido/truncado do LLM: {first_err}. "
                    f"Prévia: {fragment[:240]!r}"
                ) from first_err

    # Rede de segurança: texto livre antes do JSON (ASCII/mermaid, etc.)
    start_candidates = [i for i in (cleaned.find("{"), cleaned.find("[")) if i >= 0]
    if not start_candidates:
        raise ValueError(
            f"Resposta do LLM não é JSON (começa com texto e sem objeto). "
            f"Prévia: {cleaned[:240]!r}"
        )
    fragment = cleaned[min(start_candidates) :].strip()
    try:
        return _try_parse(fragment)
    except Exception as err:
        raise ValueError(
            f"JSON inválido/truncado do LLM (após preâmbulo): {err}. "
            f"Prévia: {fragment[:240]!r}"
        ) from err
