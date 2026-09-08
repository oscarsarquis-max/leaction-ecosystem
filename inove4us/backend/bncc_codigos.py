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


_TEMA_PREFIX_RE = re.compile(r"^(Dia a Dia|Desafio)\s*·\s*", re.IGNORECASE)
_TEMA_TURMA_TAIL_RE = re.compile(
    r"\d+\s*[ºo°ª]|\bano\b|\bturma\b|\bsérie\b|\bserie\b",
    re.IGNORECASE,
)


def _descritivo_sem_codigo(*candidates: Any) -> str:
    for raw in candidates:
        text = str(raw or "").strip()
        if not text:
            continue
        text = _TEMA_PREFIX_RE.sub("", text)
        parts = [p.strip() for p in text.split("·") if p.strip()]
        if len(parts) >= 2 and _TEMA_TURMA_TAIL_RE.search(parts[-1]):
            parts = parts[:-1]
        text = " · ".join(parts)
        cleaned = BNCC_CODE_RE.sub("", text)
        cleaned = re.sub(r"[\s]*[—\-–]+\s*", " ", cleaned)
        cleaned = " ".join(cleaned.split()).strip(" ·,;/-")
        if cleaned and not BNCC_CODE_RE.fullmatch(cleaned):
            return cleaned
    return ""


def montar_tema_rotulo(
    *candidates: Any,
    catalog_tema: str | None = None,
    habilidade_codigo: str | None = None,
) -> dict[str, str | None]:
    """Código + descritivo: `EF06MA30 — Problemas…`. Código nunca some se existir."""
    explicit = str(habilidade_codigo or "").strip().upper()
    codes = extract_bncc_codigos(explicit, *candidates)
    if explicit and BNCC_CODE_RE.fullmatch(explicit) and explicit not in codes:
        codes.insert(0, explicit)
    codigo = codes[0] if codes else None
    desc = (str(catalog_tema or "").strip() or _descritivo_sem_codigo(*candidates)) or None
    if codigo and desc:
        rotulo = f"{codigo} — {desc}"
    else:
        rotulo = codigo or desc
    return {
        "habilidade_codigo": codigo,
        "tema_legivel": desc,
        "tema_rotulo": rotulo,
    }
