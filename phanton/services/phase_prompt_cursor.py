"""Capability: prompt_cursor — prompt executável para IDE a partir de PRD + SDD.

Separado da capability `prompt` (phase_L4), que continua gerando a ENTREGA
final pedida pelo usuário (HTML/Markdown), sem prompt de IDE.
"""

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

_MAX_INPUT_CHARS = 56_000


def _compact_inputs(inputs: dict[str, Any], limit: int = _MAX_INPUT_CHARS) -> dict[str, Any]:
    serialized = json.dumps(inputs, ensure_ascii=False, default=str)
    if len(serialized) <= limit:
        return inputs
    compact: dict[str, Any] = {}
    budget = max(3000, limit // max(len(inputs), 1))
    for key, value in inputs.items():
        chunk = json.dumps(value, ensure_ascii=False, default=str)
        compact[key] = chunk[:budget] + ("…[truncado]" if len(chunk) > budget else "")
    return compact


def _extract_docs(inputs: dict[str, Any]) -> tuple[str, str]:
    prd = ""
    sdd = ""
    for payload in inputs.values():
        if not isinstance(payload, dict):
            continue
        if not prd and payload.get("prd_markdown"):
            prd = str(payload["prd_markdown"])
        if not sdd and payload.get("sdd_markdown"):
            sdd = str(payload["sdd_markdown"])
        nested = payload.get("artifact_data")
        if isinstance(nested, dict):
            if not prd and nested.get("prd_markdown"):
                prd = str(nested["prd_markdown"])
            if not sdd and nested.get("sdd_markdown"):
                sdd = str(nested["sdd_markdown"])
    return prd.strip(), sdd.strip()


def _build_cursor_prompt_request(
    inputs: dict[str, Any],
    spec: dict[str, Any],
    phase_id: str,
    cfg: dict[str, Any],
) -> str:
    inputs_json = json.dumps(inputs, ensure_ascii=False, indent=2, default=str)
    descricao = phase_description(
        cfg,
        fallback=(
            "Criar prompt de ação curto e executável para implementação no Cursor IDE."
        ),
    )
    deps = resolve_depends_on(spec, phase_id)
    pedido = str(
        spec.get("user_prompt") or spec.get("description") or pipeline_label(spec)
    ).strip()
    prd, sdd = _extract_docs(inputs)

    return f"""
Atue como Staff Engineer.

Você receberá o PRD e o SDD do projeto. Sua tarefa é criar um prompt de ação
executável, curto e direto, para o desenvolvedor colar no Cursor IDE.
O prompt deve instruir a IA codificadora (Claude 3.5 Sonnet / agente do Cursor)
a ler os arquivos PRD.md e SDD.md (que serão salvos na raiz do projeto) e
iniciar a implementação passo a passo respeitando a arquitetura definida.

Pipeline: {pipeline_label(spec)}
Fase: {cfg.get("name") or phase_id}
depends_on: {", ".join(deps) or "nenhuma"}

Pedido original do usuário:
{pedido}

Instruções desta fase:
{descricao}

=== PRD (resumo/fonte) ===
{prd[:20_000] if prd else "(não encontrado como prd_markdown — use artefatos abaixo)"}

=== SDD (resumo/fonte) ===
{sdd[:20_000] if sdd else "(não encontrado como sdd_markdown — use artefatos abaixo)"}

=== Artefatos brutos ===
{inputs_json}

Regras do cursor_prompt:
- Curto, direto, acionável (idealmente < 600 palavras).
- Assumir que PRD.md e SDD.md existem na raiz.
- Pedir implementação incremental, testes e respeito à arquitetura do SDD.
- Não reescrever o PRD/SDD inteiros dentro do prompt.

Responda APENAS com um único objeto JSON válido (UTF-8):
{{
  "cursor_prompt": "texto do prompt executável..."
}}
""".strip()


def _normalize_cursor(parsed: dict[str, Any]) -> dict[str, Any]:
    text = (
        parsed.get("cursor_prompt")
        or parsed.get("prompt")
        or parsed.get("prompt_markdown")
        or ""
    )
    if isinstance(text, dict):
        text = text.get("content") or text.get("texto") or json.dumps(text, ensure_ascii=False)
    return {"cursor_prompt": str(text or "").strip()}


def _fallback_cursor(
    inputs: dict[str, Any],
    spec: dict[str, Any],
    *,
    reason: str,
) -> dict[str, Any]:
    label = pipeline_label(spec)
    prd, sdd = _extract_docs(inputs)
    return {
        "cursor_prompt": f"""# Implementação — {label}

Você é um engenheiro sênior no Cursor IDE.

## Contexto
Os arquivos `PRD.md` e `SDD.md` estão na raiz do projeto. Leia-os por completo
antes de escrever código. (Geração em fallback: {reason})

## Objetivo
Implementar o MVP descrito no PRD respeitando a arquitetura e os contratos do SDD.

## Passo a passo
1. Confirme stack, pastas e modelo de dados do SDD.
2. Crie a estrutura mínima do projeto (sem over-engineering).
3. Implemente as entidades/APIs/componentes prioritários do MVP.
4. Adicione testes básicos e um README de execução local.
5. Pare e reporte o que falta após o primeiro incremento útil.

## Fontes
- PRD.md{" (presente no artefato)" if prd else ""}
- SDD.md{" (presente no artefato)" if sdd else ""}

Comece pelo passo 1.
""".strip()
    }


def _generate_cursor_safe(
    inputs: dict[str, Any],
    spec: dict[str, Any],
    phase_id: str,
    cfg: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    errors: list[str] = []
    meta: dict[str, Any] = {}
    attempts = [
        (_compact_inputs(inputs, 56_000), True, 0.25, 4096),
        (_compact_inputs(inputs, 28_000), True, 0.2, 3072),
        (_compact_inputs(inputs, 14_000), False, 0.15, 2048),
    ]
    for compact, as_json, temperature, max_tokens in attempts:
        prompt = _build_cursor_prompt_request(compact, spec, phase_id, cfg)
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
                normalized = _normalize_cursor(parsed)
                if normalized.get("cursor_prompt"):
                    return normalized, {
                        **meta,
                        "attempts": errors,
                        "used_max_output_tokens": max_tokens,
                    }
            stripped = (raw_text or "").strip()
            if len(stripped) > 80 and not stripped.lstrip().startswith("{"):
                return {"cursor_prompt": stripped}, {
                    **meta,
                    "attempts": errors,
                    "raw_text": True,
                }
            errors.append(f"sem_cursor_prompt(tokens={max_tokens})")
        except Exception as exc:
            errors.append(f"{type(exc).__name__}: {exc}")

    return (
        _fallback_cursor(inputs, spec, reason="; ".join(errors) or "modelo indisponível"),
        {**meta, "fallback": True, "attempts": errors},
    )


async def execute_phase_prompt_cursor(
    run_id: str,
    spec: dict[str, Any],
    db_session: Optional[Session] = None,
    phase_id: str = "prompt_cursor",
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
                    "Aprove PRD e SDD (depends_on) antes do prompt Cursor."
                )
            parsed, meta = await asyncio.to_thread(
                _generate_cursor_safe, inputs, spec, phase_id, cfg
            )
            return {
                "status": "success",
                "phase": phase_id,
                "capability": "prompt_cursor",
                "run_id": run_id,
                "pipeline_name": pipeline_label(spec),
                "artifact_data": parsed,
                "cursor_prompt": parsed.get("cursor_prompt"),
                "format": "markdown",
                "inputs_used": list(inputs.keys()),
                "meta": meta,
            }
        except Exception as exc:
            try:
                inputs = load_dependency_artifacts(session, run_id, spec, phase_id) or {}
            except Exception:
                inputs = {}
            if inputs:
                parsed = _fallback_cursor(inputs, spec, reason=str(exc))
                return {
                    "status": "success",
                    "phase": phase_id,
                    "capability": "prompt_cursor",
                    "run_id": run_id,
                    "pipeline_name": pipeline_label(spec),
                    "artifact_data": parsed,
                    "cursor_prompt": parsed.get("cursor_prompt"),
                    "format": "markdown",
                    "inputs_used": list(inputs.keys()),
                    "meta": {"fallback": True, "error": str(exc)},
                }
            return {
                "status": "error",
                "phase": phase_id,
                "capability": "prompt_cursor",
                "run_id": run_id,
                "pipeline_name": pipeline_label(spec),
                "artifact_data": {"erro": str(exc)},
            }
    finally:
        if owns_session:
            session.close()
