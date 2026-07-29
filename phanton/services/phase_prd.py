"""Capability: generate_prd — Product Requirements Document a partir da síntese."""

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


def _build_prd_prompt(
    inputs: dict[str, Any],
    spec: dict[str, Any],
    phase_id: str,
    cfg: dict[str, Any],
) -> str:
    inputs_json = json.dumps(inputs, ensure_ascii=False, indent=2, default=str)
    descricao = phase_description(
        cfg,
        fallback=(
            "Gerar PRD completo a partir da síntese metodológica e de pesquisa."
        ),
    )
    deps = resolve_depends_on(spec, phase_id)
    from services.structured_requirements import format_structured_requirements_block

    pedido = str(
        spec.get("user_prompt") or spec.get("description") or pipeline_label(spec)
    ).strip()
    req_block = format_structured_requirements_block(
        spec.get("structured_requirements") if isinstance(spec, dict) else None
    )

    return f"""
Atue como um Product Manager Sênior.

Com base na síntese metodológica e de pesquisa recebida, crie um PRD
(Product Requirements Document) em formato Markdown.

Pipeline: {pipeline_label(spec)}
Fase: {cfg.get("name") or phase_id}
depends_on: {", ".join(deps) or "nenhuma"}

Pedido original do usuário:
{pedido}

{req_block}

Instruções desta fase:
{descricao}

=== Artefatos de entrada (fonte da verdade) ===
{inputs_json}

O documento Markdown DEVE conter as seções:
1. Visão Geral
2. Público-alvo
3. Regras de Negócio Core
4. Casos de Uso / Jornadas
5. Critérios de Aceite

Responda APENAS com um único objeto JSON válido (UTF-8), SEM markdown externo
e SEM comentários, no formato:
{{
  "prd_markdown": "# PRD\\n\\n...conteúdo markdown completo..."
}}
""".strip()


def _normalize_prd(parsed: dict[str, Any]) -> dict[str, Any]:
    md = (
        parsed.get("prd_markdown")
        or parsed.get("prd")
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
    return {"prd_markdown": text}


def _fallback_prd(inputs: dict[str, Any], spec: dict[str, Any], *, reason: str) -> dict[str, Any]:
    label = pipeline_label(spec)
    body = json.dumps(inputs, ensure_ascii=False, indent=2, default=str)
    if len(body) > 12_000:
        body = body[:12_000] + "\n…[truncado]"
    return {
        "prd_markdown": f"""# PRD — {label}

## Visão Geral
Documento gerado em modo fallback ({reason}). Consolidar requisitos a partir
das fases anteriores para orientar o design e a implementação.

## Público-alvo
Definir a partir do pedido do usuário e da síntese metodológica.

## Regras de Negócio Core
- Respeitar metodologia e restrições das fases anteriores
- Priorizar MVP entregável

## Casos de Uso / Jornadas
Descrever jornadas principais com base nos artefatos de entrada.

## Critérios de Aceite
- [ ] Requisitos da síntese atendidos
- [ ] Escopo MVP claro e testável

## Anexo — Artefatos de entrada
```json
{body}
```
""".strip()
    }


def _generate_prd_safe(
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
        prompt = _build_prd_prompt(compact, spec, phase_id, cfg)
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
                normalized = _normalize_prd(parsed)
                if normalized.get("prd_markdown"):
                    return normalized, {
                        **meta,
                        "attempts": errors,
                        "used_max_output_tokens": max_tokens,
                    }
            # Resposta pode ter vindo como markdown puro
            stripped = (raw_text or "").strip()
            if stripped.startswith("#"):
                return {"prd_markdown": stripped}, {
                    **meta,
                    "attempts": errors,
                    "raw_markdown": True,
                }
            errors.append(f"sem_prd(tokens={max_tokens})")
        except Exception as exc:
            errors.append(f"{type(exc).__name__}: {exc}")

    return _fallback_prd(inputs, spec, reason="; ".join(errors) or "modelo indisponível"), {
        **meta,
        "fallback": True,
        "attempts": errors,
    }


async def execute_phase_prd(
    run_id: str,
    spec: dict[str, Any],
    db_session: Optional[Session] = None,
    phase_id: str = "generate_prd",
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
                    "Aprove a síntese (depends_on) antes do PRD."
                )
            parsed, meta = await asyncio.to_thread(
                _generate_prd_safe, inputs, spec, phase_id, cfg
            )
            return {
                "status": "success",
                "phase": phase_id,
                "capability": "generate_prd",
                "run_id": run_id,
                "pipeline_name": pipeline_label(spec),
                "artifact_data": parsed,
                "prd_markdown": parsed.get("prd_markdown"),
                "inputs_used": list(inputs.keys()),
                "meta": meta,
            }
        except Exception as exc:
            try:
                inputs = load_dependency_artifacts(session, run_id, spec, phase_id) or {}
            except Exception:
                inputs = {}
            if inputs:
                parsed = _fallback_prd(inputs, spec, reason=str(exc))
                return {
                    "status": "success",
                    "phase": phase_id,
                    "capability": "generate_prd",
                    "run_id": run_id,
                    "pipeline_name": pipeline_label(spec),
                    "artifact_data": parsed,
                    "prd_markdown": parsed.get("prd_markdown"),
                    "inputs_used": list(inputs.keys()),
                    "meta": {"fallback": True, "error": str(exc)},
                }
            return {
                "status": "error",
                "phase": phase_id,
                "capability": "generate_prd",
                "run_id": run_id,
                "pipeline_name": pipeline_label(spec),
                "artifact_data": {"erro": str(exc)},
            }
    finally:
        if owns_session:
            session.close()
