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

from google.genai import types
from sqlalchemy.orm import Session

_ROOT = Path(__file__).resolve().parent.parent
_BACKEND = _ROOT / "backend"
for _path in (str(_ROOT), str(_BACKEND)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from database import SessionLocal  # noqa: E402
from services.build_order import normalize_build_order  # noqa: E402
from services.gemini_client import extract_json_payload, generate_content  # noqa: E402
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

logger = logging.getLogger(__name__)

_PRD_INPUT_CHARS = 12_000
_SDD_MARKDOWN_MAX = 24_000

_BUILD_ORDER_ITEM_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "modulo": types.Schema(type=types.Type.STRING),
        "depende_de": types.Schema(
            type=types.Type.ARRAY,
            items=types.Schema(type=types.Type.STRING),
        ),
        "escopo": types.Schema(type=types.Type.STRING),
    },
    required=["modulo", "depende_de", "escopo"],
)

SDD_RESPONSE_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "sdd_markdown": types.Schema(type=types.Type.STRING),
        "build_order": types.Schema(
            type=types.Type.ARRAY,
            items=_BUILD_ORDER_ITEM_SCHEMA,
        ),
    },
    required=["sdd_markdown", "build_order"],
)

BUILD_ORDER_ONLY_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "build_order": types.Schema(
            type=types.Type.ARRAY,
            items=_BUILD_ORDER_ITEM_SCHEMA,
        ),
    },
    required=["build_order"],
)

SDD_NARRATIVE_ONLY_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "sdd_markdown": types.Schema(type=types.Type.STRING),
    },
    required=["sdd_markdown"],
)


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
    if text.startswith("```"):
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
    return {"sdd_markdown": text, "build_order": build_order}


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
2. NÃO incluir diagramas ASCII, mermaid, sequenceDiagram ou blocos de código
   enormes — descreva a arquitetura em prosa e listas.
3. NÃO colar o PRD de volta. Se precisar citar a origem, use apenas:
   "Ver artefato da fase `{ref}`".
4. Seja conciso (MVP). Evite repetir o pedido do usuário.
5. Se os requisitos estruturados fixarem single_tenant, NÃO desenhe multi-tenant
   (sem isolamento por schema/tenant, sem X-Tenant-ID, sem Keycloak multi-realm
   por cliente).

Regras OBRIGATÓRIAS para build_order:
- Array de módulos/serviços na ordem de implementação (tipicamente 3 a 8).
- Cada item: modulo (kebab-case), depende_de (lista de nomes), escopo (1 linha).
- Se monolítico sem módulos claros, retorne build_order: [].
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
- 3 a 8 módulos kebab-case quando o sistema for multi-serviço.
- depende_de referencia nomes exatos de outros módulos da lista.
- escopo em uma linha.
- Monólito simples → build_order: [].
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

            return normalized, {
                **meta,
                "attempts": errors,
                "used_max_output_tokens": max_tokens,
                "prd_ref": prd_phase_id,
                "structured_output": True,
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
            return normalized, {
                **meta,
                **order_meta,
                "attempts": errors,
                "two_pass": True,
                "prd_ref": prd_phase_id,
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
