"""Comparação literal passos gerados × Biblioteca de Passos Mativas."""

from __future__ import annotations

import json
import re
from typing import Any, Optional

from services.llm.json_utils import extract_json_payload


def _norm_text(s: Any) -> str:
    text = str(s or "").strip()
    text = re.sub(r"^\*\*Descri[cç][aã]o\s+Base:\*\*\s*", "", text, flags=re.I)
    text = re.sub(r"^Descri[cç][aã]o\s+Base:\s*", "", text, flags=re.I)
    text = re.sub(r"\*\*", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _best_alignment(
    gen: list[dict[str, str]], ref: list[dict[str, str]]
) -> list[dict[str, str]]:
    """Se o 1º bloco gerado for título do documento, desloca para alinhar aos imperativos."""
    if not gen or not ref:
        return gen
    if _norm_text(gen[0].get("titulo")) == _norm_text(ref[0].get("titulo")):
        return gen
    # tenta shift +1
    if len(gen) > 1 and _norm_text(gen[1].get("titulo")) == _norm_text(
        ref[0].get("titulo")
    ):
        return gen[1:]
    return gen


def _canon_passos(raw: Any) -> list[dict[str, str]]:
    """Normaliza lista heterogênea → [{titulo, descricao}]."""
    if not isinstance(raw, list):
        return []
    out: list[dict[str, str]] = []
    for item in raw:
        if isinstance(item, str) and item.strip():
            out.append({"titulo": item.strip(), "descricao": ""})
            continue
        if not isinstance(item, dict):
            continue
        titulo = (
            item.get("titulo")
            or item.get("imperativo")
            or item.get("titulo_do_card")
            or item.get("title")
            or ""
        )
        descricao = (
            item.get("descricao")
            or item.get("descricao_base")
            or item.get("como_executar_detalhado")
            or item.get("description")
            or ""
        )
        if str(titulo).strip() or str(descricao).strip():
            out.append(
                {
                    "titulo": str(titulo).strip(),
                    "descricao": str(descricao).strip(),
                }
            )
    return out


def extract_passos_from_artifact(artifact: Any) -> list[dict[str, str]]:
    """Extrai passos do artefato final (entrega / síntese / nested)."""
    if not isinstance(artifact, dict):
        return []

    candidates: list[Any] = [
        artifact.get("passos"),
        artifact.get("dinamica_passo_a_passo"),
    ]
    inner = artifact.get("artifact_data")
    if isinstance(inner, dict):
        candidates.extend(
            [
                inner.get("passos"),
                inner.get("dinamica_passo_a_passo"),
            ]
        )
        # entrega markdown/json
        for key in ("delivery", "cursor_prompt", "html_code"):
            blob = inner.get(key) or artifact.get(key)
            if isinstance(blob, str) and blob.strip():
                parsed = _try_parse_passos_blob(blob)
                if parsed:
                    return parsed

    for key in ("delivery", "cursor_prompt"):
        blob = artifact.get(key)
        if isinstance(blob, str) and blob.strip():
            parsed = _try_parse_passos_blob(blob)
            if parsed:
                return parsed

    for cand in candidates:
        normalized = _canon_passos(cand)
        if normalized:
            return normalized
    return []


def _try_parse_passos_blob(blob: str) -> list[dict[str, str]]:
    text = blob.strip()
    # JSON embutido
    if "{" in text:
        try:
            parsed = extract_json_payload(text)
            if isinstance(parsed, dict):
                for key in ("passos", "dinamica_passo_a_passo", "steps"):
                    found = _canon_passos(parsed.get(key))
                    if found:
                        return found
            if isinstance(parsed, list):
                found = _canon_passos(parsed)
                if found:
                    return found
        except Exception:
            pass

    # Markdown: ## 1. Título / ### Passo N
    steps: list[dict[str, str]] = []
    blocks = re.split(r"\n(?=#{1,3}\s*\d+[\.\):]?\s+)", text)
    if len(blocks) <= 1:
        blocks = re.split(r"\n(?=\d+[\.\)]\s+\S)", text)
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        m = re.match(
            r"^(?:#{1,3}\s*)?(?:\d+[\.\):]?\s+)?(.+?)(?:\n+|$)(.*)$",
            block,
            re.S,
        )
        if not m:
            continue
        titulo = m.group(1).strip().lstrip("#").strip()
        desc = m.group(2).strip()
        if len(titulo) >= 3:
            steps.append({"titulo": titulo, "descricao": desc})
    return steps if len(steps) >= 2 else []


def compare_passos(
    generated: list[dict[str, str]],
    reference: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compara campo a campo: titulo↔imperativo, descricao↔descricao_base."""
    ref = _canon_passos(
        [
            {
                "titulo": p.get("imperativo") or p.get("titulo"),
                "descricao": p.get("descricao_base") or p.get("descricao"),
            }
            for p in reference
            if isinstance(p, dict)
        ]
    )
    gen = _best_alignment(_canon_passos(generated), ref)
    n_ref = len(ref)
    n_gen = len(gen)
    n = max(n_ref, n_gen)
    details: list[dict[str, Any]] = []
    identical = 0
    titulo_ok = 0
    desc_ok = 0

    for i in range(n):
        g = gen[i] if i < n_gen else {"titulo": "", "descricao": ""}
        r = ref[i] if i < n_ref else {"titulo": "", "descricao": ""}
        t_match = _norm_text(g["titulo"]) == _norm_text(r["titulo"]) and bool(
            _norm_text(r["titulo"])
        )
        d_match = _norm_text(g["descricao"]) == _norm_text(r["descricao"]) and bool(
            _norm_text(r["descricao"])
        )
        both = t_match and d_match
        if both:
            identical += 1
        if t_match:
            titulo_ok += 1
        if d_match:
            desc_ok += 1
        details.append(
            {
                "ordem": i + 1,
                "identical": both,
                "titulo_identical": t_match,
                "descricao_identical": d_match,
                "gerado": g,
                "referencia": {
                    "imperativo": r["titulo"],
                    "descricao_base": r["descricao"],
                },
            }
        )

    return {
        "n_referencia": n_ref,
        "n_gerado": n_gen,
        "identical_count": identical,
        "titulo_identical_count": titulo_ok,
        "descricao_identical_count": desc_ok,
        "identical_ratio": (identical / n_ref) if n_ref else None,
        "details": details,
    }
