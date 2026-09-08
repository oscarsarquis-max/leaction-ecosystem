"""Códigos BNCC de uma aula — lista ordenada, sem depender de VARCHAR(255)."""
from __future__ import annotations

import json
import re
from typing import Any

BNCC_CODE_RE = re.compile(r"\b((?:EF|EM)\d{2}[A-Z]{2,4}\d{2,3})\b", re.IGNORECASE)


def extract_bncc_codigos(*parts: Any) -> list[str]:
    """Todos os códigos no texto, ordem estável, sem duplicata."""
    blob = " ".join(str(p or "") for p in parts)
    seen: set[str] = set()
    ordered: list[str] = []
    for match in BNCC_CODE_RE.finditer(blob):
        code = match.group(1).upper()
        if code not in seen:
            seen.add(code)
            ordered.append(code)
    return ordered


def normalize_habilidades_bncc(raw: Any) -> list[str]:
    """Aceita JSON/list/string e devolve códigos canônicos na ordem de seleção."""
    if raw is None or raw == "":
        return []
    if isinstance(raw, (bytes, memoryview)):
        raw = bytes(raw).decode("utf-8", errors="replace")
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return []
        if text.startswith("[") or text.startswith("{"):
            try:
                raw = json.loads(text)
            except json.JSONDecodeError:
                return extract_bncc_codigos(text)
        else:
            return extract_bncc_codigos(text)
    if isinstance(raw, dict):
        raw = raw.get("habilidades_bncc") or raw.get("habilidade_codigos") or raw.get("codigos") or []
    if not isinstance(raw, (list, tuple)):
        return extract_bncc_codigos(raw)
    ordered: list[str] = []
    seen: set[str] = set()
    for item in raw:
        if isinstance(item, dict):
            piece = item.get("habilidade_codigo") or item.get("codigo") or ""
        else:
            piece = item
        for code in extract_bncc_codigos(piece):
            if code not in seen:
                seen.add(code)
                ordered.append(code)
    return ordered


def habilidades_bncc_da_aula(row: dict[str, Any] | None) -> list[str]:
    """Fonte da verdade: coluna JSON; fallback regex em tema/ementa (aulas antigas)."""
    row = row or {}
    codes = normalize_habilidades_bncc(row.get("habilidades_bncc"))
    if codes:
        return codes
    return extract_bncc_codigos(row.get("tema_aula"), row.get("ementa_topico"))
