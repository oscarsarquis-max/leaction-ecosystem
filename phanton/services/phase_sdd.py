"""Capability: generate_sdd — Software Design Document a partir do PRD.

Usa saída estruturada do Gemini (response_schema) e, se necessário, uma
segunda chamada só para `build_order`. Não duplica o PRD no artefato.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import sys
from pathlib import Path
from typing import Any, Optional

from sqlalchemy.orm import Session

_ROOT = Path(__file__).resolve().parent.parent
_BACKEND = _ROOT / "backend"
for _path in (str(_ROOT), str(_BACKEND)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from database import SessionLocal  # noqa: E402
from services.build_order import normalize_build_order  # noqa: E402
from services.llm.json_utils import extract_json_payload  # noqa: E402
from services.llm.runtime import generate_content  # noqa: E402
from services.phase_context import (  # noqa: E402
    load_dependency_artifacts,
    phase_cfg,
    phase_description,
    pipeline_label,
    resolve_depends_on,
)
from services.structured_requirements import (  # noqa: E402
    format_structured_requirements_block,
)
from services.sdd_quality import apply_sdd_quality_gates  # noqa: E402

logger = logging.getLogger(__name__)

_PRD_INPUT_CHARS = 12_000
_SDD_MARKDOWN_MAX = 24_000

_BUILD_ORDER_ITEM_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "modulo": {"type": "STRING"},
        "depende_de": {
            "type": "ARRAY",
            "items": {"type": "STRING"},
        },
        "escopo": {"type": "STRING"},
        "camada": {
            "type": "STRING",
            "enum": ["backend", "frontend", "shared"],
        },
    },
    "required": ["modulo", "depende_de", "escopo", "camada"],
}

SDD_RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "sdd_markdown": {"type": "STRING"},
        "architecture_mermaid": {"type": "STRING"},
        "build_order": {
            "type": "ARRAY",
            "items": _BUILD_ORDER_ITEM_SCHEMA,
        },
    },
    "required": ["sdd_markdown", "architecture_mermaid", "build_order"],
}

BUILD_ORDER_ONLY_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "build_order": {
            "type": "ARRAY",
            "items": _BUILD_ORDER_ITEM_SCHEMA,
        },
    },
    "required": ["build_order"],
}

SDD_NARRATIVE_ONLY_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "sdd_markdown": {"type": "STRING"},
    },
    "required": ["sdd_markdown"],
}


def _extract_prd_markdown(inputs: dict[str, Any]) -> tuple[str, Optional[str]]:
    """Retorna (prd_text_truncado, phase_id_fonte)."""
    for phase_id, payload in (inputs or {}).items():
        if not isinstance(payload, dict):
            continue
        md = payload.get("prd_markdown")
        if isinstance(md, str) and md.strip():
            return md.strip()[:_PRD_INPUT_CHARS], str(phase_id)
        nested = payload.get("artifact_data")
        if isinstance(nested, dict):
            md = nested.get("prd_markdown")
            if isinstance(md, str) and md.strip():
                return md.strip()[:_PRD_INPUT_CHARS], str(phase_id)
    # fallback: serialização compacta sem re-expandir tudo
    blob = json.dumps(inputs, ensure_ascii=False, default=str)
    return blob[:_PRD_INPUT_CHARS], None


def _strip_prd_appendix(markdown: str) -> str:
    """Remove seções que colam o PRD inteiro de volta no SDD."""
    text = (markdown or "").strip()
    if not text:
        return text
    # Corta a partir de headings conhecidos de "referência ao PRD"
    pattern = re.compile(
        r"\n##\s+Refer[eê]ncia\s+ao\s+PRD\b.*$",
        re.IGNORECASE | re.DOTALL,
    )
    text = pattern.sub("", text).rstrip()
    return text


_MERMAID_FENCE_RE = re.compile(
    r"```(?:mermaid)?\s*\n(.*?)```",
    re.IGNORECASE | re.DOTALL,
)


def _clean_mermaid(raw: str) -> str:
    text = str(raw or "").strip()
    if not text:
        return ""
    fence = _MERMAID_FENCE_RE.search(text)
    if fence:
        text = fence.group(1).strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines:
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    # Aceita flowchart / graph / C4-ish / sequence
    low = text.lower()
    if not (
        low.startswith("flowchart")
        or low.startswith("graph ")
        or low.startswith("sequencediagram")
        or low.startswith("c4context")
        or low.startswith("c4container")
    ):
        # Se veio sem keyword, assume flowchart TB
        if "-->" in text or "==>" in text:
            text = f"flowchart TB\n{text}"
        else:
            return ""
    return text[:8000]


def _architecture_from_build_order(build_order: list[dict[str, Any]]) -> str:
    """Diagrama Mermaid mínimo a partir do build_order (fallback)."""
    if not build_order:
        return (
            "flowchart TB\n"
            "  UI[Apresentação / UI]\n"
            "  APP[Aplicação / API]\n"
            "  DATA[(Dados)]\n"
            "  UI --> APP --> DATA"
        )
    lines = ["flowchart TB"]
    ids: dict[str, str] = {}
    for i, item in enumerate(build_order):
        if not isinstance(item, dict):
            continue
        name = str(item.get("modulo") or f"mod-{i+1}").strip()
        safe = re.sub(r"[^a-zA-Z0-9_]", "_", name) or f"m{i+1}"
        ids[name] = safe
        camada = str(item.get("camada") or "").strip()
        label = f"{name}" + (f" ({camada})" if camada else "")
        lines.append(f'  {safe}["{label}"]')
    for item in build_order:
        if not isinstance(item, dict):
            continue
        name = str(item.get("modulo") or "").strip()
        src = ids.get(name)
        if not src:
            continue
        deps = item.get("depende_de") or []
        if not isinstance(deps, list):
            continue
        for dep in deps:
            dst = ids.get(str(dep).strip())
            if dst:
                lines.append(f"  {dst} --> {src}")
    if len(lines) == 1:
        return _architecture_from_build_order([])
    return "\n".join(lines)


def _extract_mermaid_from_markdown(markdown: str) -> tuple[str, str]:
    """Se o SDD trouxe mermaid embutido, separa do texto."""
    text = markdown or ""
    match = _MERMAID_FENCE_RE.search(text)
    if not match:
        return text, ""
    diagram = _clean_mermaid(match.group(0))
    cleaned = (text[: match.start()] + text[match.end() :]).strip()
    return cleaned, diagram


def _normalize_sdd(parsed: dict[str, Any]) -> dict[str, Any]:
    md = (
        parsed.get("sdd_markdown")
        or parsed.get("sdd")
        or parsed.get("markdown")
        or parsed.get("documento")
        or ""
    )
    if isinstance(md, dict):
        md = md.get("content") or md.get("texto") or json.dumps(md, ensure_ascii=False)
    text = str(md or "").strip()
    if text.startswith("```") and not text.lower().startswith("```mermaid"):
        lines = text.splitlines()
        if lines:
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    text = _strip_prd_appendix(text)
    if len(text) > _SDD_MARKDOWN_MAX:
        text = text[:_SDD_MARKDOWN_MAX].rstrip() + "\n\n…[sdd truncado]"

    build_order = normalize_build_order(
        parsed.get("build_order") or parsed.get("modules") or parsed.get("modulos")
    )

    diagram = _clean_mermaid(
        parsed.get("architecture_mermaid")
        or parsed.get("architecture_diagram")
        or parsed.get("diagrama_arquitetura")
        or ""
    )
    if not diagram:
        text, embedded = _extract_mermaid_from_markdown(text)
        diagram = embedded
    if not diagram:
        diagram = _architecture_from_build_order(build_order)

    return {
        "sdd_markdown": text,
        "architecture_mermaid": diagram,
        "build_order": build_order,
    }


def _fallback_sdd(
    inputs: dict[str, Any],
    spec: dict[str, Any],
    *,
    reason: str,
    prd_phase_id: Optional[str] = None,
) -> dict[str, Any]:
    """Fallback sem colar o PRD — apenas referência por fase."""
    label = pipeline_label(spec)
    ref = prd_phase_id or "generate_prd"
    return {
        "sdd_markdown": f"""# SDD — {label}

## Stack Tecnológica
Definir stack alinhada ao PRD aprovado (modo fallback: {reason}).

## Arquitetura do Sistema
- Camada de apresentação
- Camada de aplicação / API
- Camada de dados

## Modelo de Dados
Entidades principais a derivar do PRD.

## Contratos de API / Componentes
Listar endpoints/interfaces mínimos do MVP.

## Referência ao PRD
Ver artefato da fase `{ref}` (não reimprimir o PRD neste documento).
""".strip(),
        "architecture_mermaid": (
            "flowchart TB\n"
            "  UI[Apresentação / UI]\n"
            "  APP[Aplicação / API]\n"
            "  DATA[(Dados)]\n"
            "  UI --> APP --> DATA"
        ),
        "build_order": [],
    }


def _build_sdd_structured_prompt(
    prd_text: str,
    spec: dict[str, Any],
    phase_id: str,
    cfg: dict[str, Any],
    *,
    prd_phase_id: Optional[str],
) -> str:
    descricao = phase_description(cfg, fallback="Gerar SDD completo a partir do PRD.")
    deps = resolve_depends_on(spec, phase_id)
    pedido = str(
        spec.get("user_prompt") or spec.get("description") or pipeline_label(spec)
    ).strip()
    ref = prd_phase_id or "generate_prd"
    req_block = format_structured_requirements_block(
        spec.get("structured_requirements")
        if isinstance(spec, dict)
        else None
    )

    return f"""
Atue como Arquiteto de Software Sênior.

Gere um Software Design Document (SDD) a partir do PRD abaixo.
A resposta será forçada em JSON estruturado pelo sistema — preencha os campos.

Pipeline: {pipeline_label(spec)}
Fase: {cfg.get("name") or phase_id}
depends_on: {", ".join(deps) or "nenhuma"}
Pedido: {pedido}

Instruções:
{descricao}

{req_block}

=== PRD (fonte; truncado se longo) ===
{prd_text}

Regras OBRIGATÓRIAS para sdd_markdown:
1. Incluir seções: Stack Tecnológica; Arquitetura do Sistema; Modelo de Dados;
   Contratos de API / Componentes.
2. NÃO colocar mermaid/ASCII dentro do sdd_markdown — o diagrama vai no campo
   separado architecture_mermaid. No markdown, descreva a arquitetura em prosa
   e listas.
3. NÃO colar o PRD de volta. Se precisar citar a origem, use apenas:
   "Ver artefato da fase `{ref}`".
4. Seja conciso (MVP). Evite repetir o pedido do usuário.
5. Se os requisitos estruturados fixarem single_tenant, NÃO desenhe multi-tenant
   (sem isolamento por schema/tenant, sem X-Tenant-ID, sem Keycloak multi-realm
   por cliente).
6. Se o PRD mencionar avaliações/quiz/nota mínima/certificado com nota: o Modelo
   de Dados DEVE incluir Assessment, Attempt (e Question se couber) e explicar
   como Enrollment.averageGrade é derivado. Sem isso o SDD está incompleto.
7. Se o PRD mencionar SPA/player/portal/UI: descreva a camada de apresentação
   (rotas/telas mínimas) e inclua ≥1 módulo `camada=frontend` no build_order.

Regras OBRIGATÓRIAS para architecture_mermaid:
- String com diagrama Mermaid da arquitetura (preferir `flowchart TB`).
- Mostre camadas/módulos principais e setas de dependência (UI → API → dados,
  ou serviços do MVP).
- Sem fences ``` — só o corpo Mermaid.
- Sem textos longos nos nós (rótulos curtos).
- Se single_tenant, NÃO desenhe multi-tenant.

Regras OBRIGATÓRIAS para build_order:
- Array de módulos na ordem de implementação: OBRIGATÓRIO 3 a 8 itens
  (mesmo em monólito — fatie em módulos lógicos: ex. domain-core,
  api-or-storage, app-frontend). Nunca retorne array vazio.
- Cada item: modulo (kebab-case), depende_de, escopo (1 linha),
  camada (`backend` | `frontend` | `shared`).
- Se houver UI/player/portal no PRD, incluir pelo menos um módulo frontend
  (ex.: app-frontend ou *-player) descrevendo telas, não só APIs.
- NÃO embutir JSON de exemplo, TypeScript, schemas de domínio nem
  payloads grandes dentro de sdd_markdown ou de qualquer campo —
  isso trunca a resposta. Modelo de dados em prosa/listas curtas.
""".strip()


def _build_order_only_prompt(
    prd_text: str,
    sdd_markdown: str,
    spec: dict[str, Any],
) -> str:
    pedido = str(
        spec.get("user_prompt") or spec.get("description") or pipeline_label(spec)
    ).strip()
    return f"""
Com base no PRD e no SDD abaixo, produza APENAS o campo build_order
(módulos de implementação ordenados com dependências).

Pedido: {pedido}

=== PRD (trecho) ===
{prd_text[:8000]}

=== SDD (trecho) ===
{(sdd_markdown or "")[:10000]}

Regras:
- OBRIGATÓRIO 3 a 8 módulos kebab-case (monólito: fatie em módulos lógicos).
  Nunca retorne array vazio.
- depende_de referencia nomes exatos de outros módulos da lista.
- escopo em uma linha; camada = backend|frontend|shared.
- Se PRD/SDD citam UI/player/portal → ≥1 módulo camada=frontend.
- Resposta mínima: só o array build_order, sem exemplos JSON/TS embutidos.
""".strip()


def _call_structured(
    prompt: str,
    *,
    schema: Any,
    temperature: float,
    max_output_tokens: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    raw_text, meta = generate_content(
        prompt,
        enable_google_search=False,
        response_json=True,
        response_schema=schema,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
    )
    parsed = extract_json_payload(raw_text)
    if not isinstance(parsed, dict):
        raise ValueError("Resposta estruturada não é objeto JSON")
    return parsed, meta


def _generate_build_order_pass(
    prd_text: str,
    sdd_markdown: str,
    spec: dict[str, Any],
    errors: list[str],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    prompt = _build_order_only_prompt(prd_text, sdd_markdown, spec)
    meta: dict[str, Any] = {}
    for temperature, max_tokens in ((0.2, 4096), (0.15, 3072)):
        try:
            parsed, meta = _call_structured(
                prompt,
                schema=BUILD_ORDER_ONLY_SCHEMA,
                temperature=temperature,
                max_output_tokens=max_tokens,
            )
            order = normalize_build_order(parsed.get("build_order"))
            if order:
                return order, {**meta, "build_order_pass": True}
            errors.append(f"build_order_vazio(tokens={max_tokens})")
        except Exception as exc:
            errors.append(f"build_order_pass:{type(exc).__name__}: {exc}")
    return [], meta


def _generate_sdd_safe(
    inputs: dict[str, Any],
    spec: dict[str, Any],
    phase_id: str,
    cfg: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    errors: list[str] = []
    meta: dict[str, Any] = {}
    prd_text, prd_phase_id = _extract_prd_markdown(inputs)
    prompt = _build_sdd_structured_prompt(
        prd_text, spec, phase_id, cfg, prd_phase_id=prd_phase_id
    )

    # Passo 1: narrativa + build_order via schema nativo
    attempts = (
        (0.25, 12_288),
        (0.2, 10_240),
        (0.15, 8_192),
    )
    for temperature, max_tokens in attempts:
        try:
            parsed, meta = _call_structured(
                prompt,
                schema=SDD_RESPONSE_SCHEMA,
                temperature=temperature,
                max_output_tokens=max_tokens,
            )
            normalized = _normalize_sdd(parsed)
            if not normalized.get("sdd_markdown"):
                errors.append(f"sdd_vazio(tokens={max_tokens})")
                continue

            # Se build_order veio vazio, tenta pass dedicado (não cai no fallback ainda)
            if not normalized.get("build_order"):
                logger.warning(
                    "generate_sdd: build_order vazio após schema — "
                    "tentando pass dedicado"
                )
                order, order_meta = _generate_build_order_pass(
                    prd_text, normalized["sdd_markdown"], spec, errors
                )
                normalized["build_order"] = order
                meta = {
                    **meta,
                    **order_meta,
                    "build_order_recovered": bool(order),
                }
                if not order:
                    logger.warning(
                        "generate_sdd: build_order continua vazio após pass dedicado"
                    )

            pedido = str(
                spec.get("user_prompt") or spec.get("description") or ""
            )
            md, order, quality_warnings = apply_sdd_quality_gates(
                sdd_markdown=normalized["sdd_markdown"],
                build_order=normalized.get("build_order") or [],
                prd_text=prd_text,
                user_prompt=pedido,
            )
            normalized["sdd_markdown"] = md
            normalized["build_order"] = order
            if not str(normalized.get("architecture_mermaid") or "").strip():
                normalized["architecture_mermaid"] = _architecture_from_build_order(
                    order or []
                )

            return normalized, {
                **meta,
                "attempts": errors,
                "used_max_output_tokens": max_tokens,
                "prd_ref": prd_phase_id,
                "structured_output": True,
                "sdd_quality_warnings": quality_warnings,
            }
        except Exception as exc:
            errors.append(f"{type(exc).__name__}: {exc}")

    # Passo 1b: só narrativa estruturada, depois build_order
    try:
        parsed, meta = _call_structured(
            prompt,
            schema=SDD_NARRATIVE_ONLY_SCHEMA,
            temperature=0.2,
            max_output_tokens=10_240,
        )
        normalized = _normalize_sdd({**parsed, "build_order": []})
        if normalized.get("sdd_markdown"):
            order, order_meta = _generate_build_order_pass(
                prd_text, normalized["sdd_markdown"], spec, errors
            )
            normalized["build_order"] = order
            pedido = str(
                spec.get("user_prompt") or spec.get("description") or ""
            )
            md, order, quality_warnings = apply_sdd_quality_gates(
                sdd_markdown=normalized["sdd_markdown"],
                build_order=normalized.get("build_order") or [],
                prd_text=prd_text,
                user_prompt=pedido,
            )
            normalized["sdd_markdown"] = md
            normalized["build_order"] = order
            if not str(normalized.get("architecture_mermaid") or "").strip():
                normalized["architecture_mermaid"] = _architecture_from_build_order(
                    order or []
                )
            return normalized, {
                **meta,
                **order_meta,
                "attempts": errors,
                "two_pass": True,
                "prd_ref": prd_phase_id,
                "sdd_quality_warnings": quality_warnings,
            }
        errors.append("narrative_only_vazia")
    except Exception as exc:
        errors.append(f"narrative_only:{type(exc).__name__}: {exc}")

    return (
        _fallback_sdd(
            inputs,
            spec,
            reason="; ".join(errors) or "modelo indisponível",
            prd_phase_id=prd_phase_id,
        ),
        {**meta, "fallback": True, "attempts": errors, "prd_ref": prd_phase_id},
    )


async def execute_phase_sdd(
    run_id: str,
    spec: dict[str, Any],
    db_session: Optional[Session] = None,
    phase_id: str = "generate_sdd",
) -> dict[str, Any]:
    owns_session = db_session is None
    session = db_session or SessionLocal()
    spec = spec if isinstance(spec, dict) else {}
    cfg = phase_cfg(spec, phase_id)

    try:
        try:
            inputs = load_dependency_artifacts(session, run_id, spec, phase_id)
            if not inputs:
                raise RuntimeError(
                    f"Nenhum artefato de entrada para '{phase_id}'. "
                    "Aprove o PRD (depends_on) antes do SDD."
                )
            parsed, meta = await asyncio.to_thread(
                _generate_sdd_safe, inputs, spec, phase_id, cfg
            )
            return {
                "status": "success",
                "phase": phase_id,
                "capability": "generate_sdd",
                "run_id": run_id,
                "pipeline_name": pipeline_label(spec),
                "artifact_data": parsed,
                "sdd_markdown": parsed.get("sdd_markdown"),
                "architecture_mermaid": parsed.get("architecture_mermaid"),
                "build_order": parsed.get("build_order") or [],
                "inputs_used": list(inputs.keys()),
                "meta": meta,
            }
        except Exception as exc:
            try:
                inputs = load_dependency_artifacts(session, run_id, spec, phase_id) or {}
            except Exception:
                inputs = {}
            if inputs:
                _, prd_phase_id = _extract_prd_markdown(inputs)
                parsed = _fallback_sdd(
                    inputs, spec, reason=str(exc), prd_phase_id=prd_phase_id
                )
                return {
                    "status": "success",
                    "phase": phase_id,
                    "capability": "generate_sdd",
                    "run_id": run_id,
                    "pipeline_name": pipeline_label(spec),
                    "artifact_data": parsed,
                    "sdd_markdown": parsed.get("sdd_markdown"),
                    "architecture_mermaid": parsed.get("architecture_mermaid"),
                    "build_order": parsed.get("build_order") or [],
                    "inputs_used": list(inputs.keys()),
                    "meta": {"fallback": True, "error": str(exc)},
                }
            return {
                "status": "error",
                "phase": phase_id,
                "capability": "generate_sdd",
                "run_id": run_id,
                "pipeline_name": pipeline_label(spec),
                "artifact_data": {"erro": str(exc)},
            }
    finally:
        if owns_session:
            session.close()
