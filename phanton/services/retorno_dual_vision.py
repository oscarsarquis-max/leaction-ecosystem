"""Dupla visão do retorno: pipeline (projeto) + melhorias no Phanton (ferramenta)."""

from __future__ import annotations

import json
import re
from typing import Any, Optional

# Cabeçalhos que separam a metade "melhoria no Phanton"
_PHANTON_HEADER = re.compile(
    r"(?im)^#{1,3}\s*(?:"
    r"retorno\s*[-—–:]?\s*phanton|"
    r"melhorias?\s*(?:sobre|no|do|da)?\s*phanton|"
    r"sobre\s+o\s+phanton|"
    r"phanton|"
    r"ferramenta|"
    r"orquestrador"
    r")\s*$"
)

# Cabeçalhos da metade pipeline / projeto
_PIPELINE_HEADER = re.compile(
    r"(?im)^#{1,3}\s*(?:"
    r"retorno\s*[-—–:]?\s*pipeline|"
    r"pipeline|"
    r"projeto|"
    r"desvios|"
    r"implementa(?:ção|cao)|"
    r"altera(?:ções|coes)\s+do\s+pipeline"
    r")\s*$"
)


def split_retorno_dual_vision(text: str) -> dict[str, str]:
    """Divide o retorno em seções pipeline e phanton (heurística por headings)."""
    raw = (text or "").strip()
    if not raw:
        return {"pipeline": "", "phanton": "", "split_mode": "empty"}

    lines = raw.splitlines()
    sections: list[tuple[str, list[str]]] = []
    current_kind = "body"
    current_lines: list[str] = []

    def flush() -> None:
        nonlocal current_lines, current_kind
        if current_lines or current_kind != "body":
            sections.append((current_kind, current_lines))
        current_lines = []

    for line in lines:
        if _PHANTON_HEADER.match(line.strip()):
            flush()
            current_kind = "phanton"
            continue
        if _PIPELINE_HEADER.match(line.strip()):
            flush()
            current_kind = "pipeline"
            continue
        current_lines.append(line)
    flush()

    pipeline_parts: list[str] = []
    phanton_parts: list[str] = []
    body_parts: list[str] = []
    for kind, chunk_lines in sections:
        chunk = "\n".join(chunk_lines).strip()
        if not chunk:
            continue
        if kind == "pipeline":
            pipeline_parts.append(chunk)
        elif kind == "phanton":
            phanton_parts.append(chunk)
        else:
            body_parts.append(chunk)

    if pipeline_parts or phanton_parts:
        pipeline = "\n\n".join(pipeline_parts).strip()
        phanton = "\n\n".join(phanton_parts).strip()
        # Corpo sem heading cai no pipeline (desvios de construção)
        if body_parts and not pipeline:
            pipeline = "\n\n".join(body_parts).strip()
        elif body_parts and pipeline:
            pipeline = ("\n\n".join(body_parts) + "\n\n" + pipeline).strip()
        return {
            "pipeline": pipeline or raw,
            "phanton": phanton,
            "split_mode": "headed",
        }

    return {"pipeline": raw, "phanton": "", "split_mode": "unheaded"}


def _bullet_lines(text: str, *, limit: int = 8) -> list[str]:
    bullets: list[str] = []
    for line in (text or "").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if re.match(r"^[-*•]\s+", stripped) or re.match(r"^\d+[.)]\s+", stripped):
            item = re.sub(r"^([-*•]|\d+[.)])\s+", "", stripped).strip()
            if item:
                bullets.append(item)
        if len(bullets) >= limit:
            break
    return bullets


def summarize_phanton_improvement_local(phanton_text: str) -> dict[str, Any]:
    """Resumo determinístico (sem LLM) da melhoria proposta no Phanton."""
    text = (phanton_text or "").strip()
    if not text:
        return {
            "has_proposal": False,
            "title": None,
            "summary": None,
            "items": [],
        }

    bullets = _bullet_lines(text)
    first_para = ""
    for block in re.split(r"\n\s*\n", text):
        candidate = " ".join(block.split()).strip()
        if candidate and not _PHANTON_HEADER.match(candidate):
            first_para = candidate
            break

    title = bullets[0] if bullets else (first_para[:96] + ("…" if len(first_para) > 96 else ""))
    if not title:
        title = "Melhoria proposta no Phanton"

    summary_parts = []
    if first_para:
        summary_parts.append(first_para[:500])
    if bullets:
        summary_parts.append(
            "Itens: " + "; ".join(bullets[:6])
        )
    summary = "\n\n".join(summary_parts).strip() or text[:600]

    return {
        "has_proposal": True,
        "title": title,
        "summary": summary,
        "items": bullets,
    }


def extract_phanton_improvement_with_llm(full_retorno: str) -> Optional[dict[str, Any]]:
    """Usa Gemini para extrair melhoria Phanton quando não há seção explícita."""
    text = (full_retorno or "").strip()
    if len(text) < 40:
        return None

    try:
        from services.gemini_client import generate_content
    except Exception:
        return None

    prompt = (
        "Analise o retorno do implementador abaixo.\n"
        "Extraia APENAS melhorias propostas para a ferramenta Phanton "
        "(orquestrador de pipelines), não mudanças do projeto/produto entregue.\n"
        "Se não houver melhoria explícita ou implícita no Phanton, "
        'retorne {"has_proposal": false}.\n'
        "Caso haja, retorne JSON:\n"
        '{"has_proposal": true, "title": "...", "summary": "...", "items": ["..."]}\n\n'
        f"Retorno:\n{text[:8000]}"
    )
    try:
        raw_text, _meta = generate_content(
            prompt,
            enable_google_search=False,
            response_json=True,
            temperature=0.1,
        )
    except Exception:
        return None

    try:
        data = json.loads(raw_text) if isinstance(raw_text, str) else raw_text
    except (TypeError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict) or not data.get("has_proposal"):
        return None

    title = str(data.get("title") or "Melhoria proposta no Phanton").strip()
    summary = str(data.get("summary") or "").strip()
    items = data.get("items") if isinstance(data.get("items"), list) else []
    items = [str(i).strip() for i in items if str(i).strip()][:10]
    if not summary and items:
        summary = "Itens: " + "; ".join(items)
    if not summary:
        return None
    return {
        "has_proposal": True,
        "title": title[:160],
        "summary": summary[:2000],
        "items": items,
    }


def resolve_phanton_improvement_proposal(
    full_retorno: str,
    *,
    use_llm_fallback: bool = True,
) -> dict[str, Any]:
    """Resolve proposta Phanton a partir do retorno (seção explícita ou LLM)."""
    split = split_retorno_dual_vision(full_retorno)
    local = summarize_phanton_improvement_local(split.get("phanton") or "")
    if local.get("has_proposal"):
        return {
            **local,
            "raw_section": split.get("phanton") or "",
            "pipeline_section": split.get("pipeline") or full_retorno,
            "split_mode": split.get("split_mode"),
            "source": "section",
        }

    if use_llm_fallback:
        llm = extract_phanton_improvement_with_llm(full_retorno)
        if llm and llm.get("has_proposal"):
            return {
                **llm,
                "raw_section": full_retorno,
                "pipeline_section": split.get("pipeline") or full_retorno,
                "split_mode": split.get("split_mode"),
                "source": "llm",
            }

    return {
        "has_proposal": False,
        "title": None,
        "summary": None,
        "items": [],
        "raw_section": "",
        "pipeline_section": split.get("pipeline") or full_retorno,
        "split_mode": split.get("split_mode"),
        "source": "none",
    }
