"""Capability: generate_sdd — Software Design Document a partir do PRD."""

from __future__ import annotations

import asyncio
import json
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
from services.gemini_client import extract_json_payload, generate_content  # noqa: E402
from services.phase_context import (  # noqa: E402
    load_dependency_artifacts,
    phase_cfg,
    phase_description,
    pipeline_label,
    resolve_depends_on,
)

_MAX_INPUT_CHARS = 48_000


def _compact_inputs(inputs: dict[str, Any], limit: int = _MAX_INPUT_CHARS) -> dict[str, Any]:
    serialized = json.dumps(inputs, ensure_ascii=False, default=str)
    if len(serialized) <= limit:
        return inputs
    compact: dict[str, Any] = {}
    budget = max(2500, limit // max(len(inputs), 1))
    for key, value in inputs.items():
        chunk = json.dumps(value, ensure_ascii=False, default=str)
        compact[key] = chunk[:budget] + ("…[truncado]" if len(chunk) > budget else "")
    return compact


def _build_sdd_prompt(
    inputs: dict[str, Any],
    spec: dict[str, Any],
    phase_id: str,
    cfg: dict[str, Any],
) -> str:
    inputs_json = json.dumps(inputs, ensure_ascii=False, indent=2, default=str)
    descricao = phase_description(
        cfg,
        fallback="Gerar SDD completo a partir do PRD.",
    )
    deps = resolve_depends_on(spec, phase_id)
    pedido = str(
        spec.get("user_prompt") or spec.get("description") or pipeline_label(spec)
    ).strip()

    return f"""
Atue como um Arquiteto de Software Sênior.

Com base no PRD recebido, crie um SDD (Software Design Document) em formato Markdown.

Pipeline: {pipeline_label(spec)}
Fase: {cfg.get("name") or phase_id}
depends_on: {", ".join(deps) or "nenhuma"}

Pedido original do usuário:
{pedido}

Instruções desta fase:
{descricao}

=== Artefatos de entrada (PRD e correlatos) ===
{inputs_json}

O documento Markdown DEVE conter as seções:
1. Stack Tecnológica escolhida (com justificativa breve)
2. Arquitetura do Sistema (camadas / componentes)
3. Modelo de Dados (tabelas/coleções principais e relacionamentos)
4. Contratos de API / Componentes (endpoints ou interfaces principais)

Responda APENAS com um único objeto JSON válido (UTF-8), SEM markdown externo
e SEM comentários, no formato:
{{
  "sdd_markdown": "# SDD\\n\\n...conteúdo markdown completo..."
}}
""".strip()


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
    return {"sdd_markdown": text}


def _fallback_sdd(inputs: dict[str, Any], spec: dict[str, Any], *, reason: str) -> dict[str, Any]:
    label = pipeline_label(spec)
    prd_hint = ""
    for payload in inputs.values():
        if isinstance(payload, dict) and payload.get("prd_markdown"):
            prd_hint = str(payload["prd_markdown"])[:4000]
            break
    return {
        "sdd_markdown": f"""# SDD — {label}

## Stack Tecnológica
Definir stack alinhada ao PRD (modo fallback: {reason}).

## Arquitetura do Sistema
- Camada de apresentação
- Camada de aplicação / API
- Camada de dados

## Modelo de Dados
Entidades principais a derivar do PRD.

## Contratos de API / Componentes
Listar endpoints/interfaces mínimos do MVP.

## Referência ao PRD
{prd_hint or "_PRD não extraído — usar artefato depends_on._"}
""".strip()
    }


def _generate_sdd_safe(
    inputs: dict[str, Any],
    spec: dict[str, Any],
    phase_id: str,
    cfg: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    errors: list[str] = []
    meta: dict[str, Any] = {}
    attempts = [
        (_compact_inputs(inputs, 48_000), True, 0.3, 8192),
        (_compact_inputs(inputs, 24_000), True, 0.2, 6144),
        (_compact_inputs(inputs, 12_000), False, 0.15, 4096),
    ]
    for compact, as_json, temperature, max_tokens in attempts:
        prompt = _build_sdd_prompt(compact, spec, phase_id, cfg)
        try:
            raw_text, meta = generate_content(
                prompt,
                enable_google_search=False,
                response_json=as_json,
                temperature=temperature,
                max_output_tokens=max_tokens,
            )
            parsed = extract_json_payload(raw_text)
            if isinstance(parsed, dict):
                normalized = _normalize_sdd(parsed)
                if normalized.get("sdd_markdown"):
                    return normalized, {
                        **meta,
                        "attempts": errors,
                        "used_max_output_tokens": max_tokens,
                    }
            stripped = (raw_text or "").strip()
            if stripped.startswith("#"):
                return {"sdd_markdown": stripped}, {
                    **meta,
                    "attempts": errors,
                    "raw_markdown": True,
                }
            errors.append(f"sem_sdd(tokens={max_tokens})")
        except Exception as exc:
            errors.append(f"{type(exc).__name__}: {exc}")

    return _fallback_sdd(inputs, spec, reason="; ".join(errors) or "modelo indisponível"), {
        **meta,
        "fallback": True,
        "attempts": errors,
    }


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
                "inputs_used": list(inputs.keys()),
                "meta": meta,
            }
        except Exception as exc:
            try:
                inputs = load_dependency_artifacts(session, run_id, spec, phase_id) or {}
            except Exception:
                inputs = {}
            if inputs:
                parsed = _fallback_sdd(inputs, spec, reason=str(exc))
                return {
                    "status": "success",
                    "phase": phase_id,
                    "capability": "generate_sdd",
                    "run_id": run_id,
                    "pipeline_name": pipeline_label(spec),
                    "artifact_data": parsed,
                    "sdd_markdown": parsed.get("sdd_markdown"),
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
