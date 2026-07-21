"""Capability: synthesize — agrupa artefatos anteriores (depends_on)."""

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

_MAX_INPUT_CHARS = 40_000


def _compact_inputs(inputs: dict[str, Any], limit: int = _MAX_INPUT_CHARS) -> dict[str, Any]:
    serialized = json.dumps(inputs, ensure_ascii=False, default=str)
    if len(serialized) <= limit:
        return inputs
    compact: dict[str, Any] = {}
    budget = max(2000, limit // max(len(inputs), 1))
    for key, value in inputs.items():
        chunk = json.dumps(value, ensure_ascii=False, default=str)
        compact[key] = chunk[:budget] + ("…[truncado]" if len(chunk) > budget else "")
    return compact


def _build_synthesis_prompt(
    inputs: dict[str, Any],
    spec: dict[str, Any],
    phase_id: str,
    cfg: dict[str, Any],
) -> str:
    inputs_json = json.dumps(inputs, ensure_ascii=False, indent=2, default=str)
    descricao = phase_description(
        cfg,
        fallback=(
            "Sintetize os artefatos de entrada em um resultado coerente "
            "para a próxima fase de entrega."
        ),
    )
    deps = resolve_depends_on(spec, phase_id)

    return f"""
Você é um arquiteto de soluções. Sintetize os artefatos das fases anteriores.

Pipeline: {pipeline_label(spec)}
Fase atual: {cfg.get("name") or phase_id}
Fases de entrada (depends_on): {", ".join(deps) or "nenhuma"}

Instruções da síntese:
{descricao}

=== Artefatos de entrada ===
{inputs_json}

Responda APENAS com um único objeto JSON válido (UTF-8), SEM markdown e SEM comentários.
Regras anti-quebra:
- Strings em uma linha quando possível; se precisar de quebra, use \\n escapado.
- NÃO use aspas simples. NÃO deixe vírgula sobrando.
- Máximo 6 cards. Textos curtos e objetivos.

Formato exato:
{{
  "resumo_sintese": "texto breve da síntese",
  "pontos_chave": ["ponto 1", "ponto 2"],
  "dinamica_passo_a_passo": [
    {{
      "titulo_do_card": "string",
      "como_executar_detalhado": "string"
    }}
  ],
  "requisitos_para_implementacao": ["requisito 1", "requisito 2"]
}}
""".strip()


def _normalize_synthesis(parsed: dict[str, Any]) -> dict[str, Any]:
    cards = parsed.get("dinamica_passo_a_passo") or parsed.get("passos") or []
    if not isinstance(cards, list):
        cards = []
    pontos = parsed.get("pontos_chave") or parsed.get("key_points") or []
    if not isinstance(pontos, list):
        pontos = [str(pontos)] if pontos else []
    requisitos = (
        parsed.get("requisitos_para_implementacao")
        or parsed.get("requisitos")
        or []
    )
    if not isinstance(requisitos, list):
        requisitos = [str(requisitos)] if requisitos else []

    return {
        "resumo_sintese": str(
            parsed.get("resumo_sintese")
            or parsed.get("resumo")
            or parsed.get("summary")
            or ""
        ).strip(),
        "pontos_chave": [str(p) for p in pontos if p is not None],
        "dinamica_passo_a_passo": cards,
        "requisitos_para_implementacao": [str(r) for r in requisitos if r is not None],
    }


def _fallback_synthesis(
    inputs: dict[str, Any],
    spec: dict[str, Any],
    *,
    reason: str,
) -> dict[str, Any]:
    pontos: list[str] = []
    cards: list[dict[str, str]] = []
    for phase_id, payload in inputs.items():
        pontos.append(f"Incorporar aprendizados da fase `{phase_id}`")
        if isinstance(payload, dict):
            if payload.get("metodologia"):
                cards.append(
                    {
                        "titulo_do_card": f"Aplicar metodologia ({phase_id})",
                        "como_executar_detalhado": str(payload.get("metodologia")),
                    }
                )
            achados = payload.get("achados")
            if isinstance(achados, list) and achados:
                first = achados[0] if isinstance(achados[0], dict) else {"titulo": str(achados[0])}
                cards.append(
                    {
                        "titulo_do_card": f"Referência de pesquisa ({phase_id})",
                        "como_executar_detalhado": str(
                            first.get("resumo") or first.get("titulo") or first
                        ),
                    }
                )
            if payload.get("resumo_sintese"):
                cards.append(
                    {
                        "titulo_do_card": f"Consolidar síntese parcial ({phase_id})",
                        "como_executar_detalhado": str(payload.get("resumo_sintese")),
                    }
                )
        if len(cards) >= 6:
            break

    if not cards:
        cards.append(
            {
                "titulo_do_card": "Consolidar requisitos",
                "como_executar_detalhado": (
                    "Usar os artefatos das fases anteriores para definir MVP, "
                    "stack e plano de implementação."
                ),
            }
        )

    return {
        "resumo_sintese": (
            f"Síntese consolidada para '{pipeline_label(spec)}' a partir de "
            f"{', '.join(inputs.keys()) or 'fases anteriores'}. "
            f"(Modo fallback: {reason})"
        ),
        "pontos_chave": pontos[:8] or ["Usar artefatos anteriores como fonte da verdade"],
        "dinamica_passo_a_passo": cards[:6],
        "requisitos_para_implementacao": [
            "Respeitar metodologia e restrições das fases anteriores",
            "Priorizar MVP implementável no Cursor",
            "Preservar referências/casos relevantes das pesquisas",
        ],
    }


def _synthesize_safe(
    inputs: dict[str, Any],
    spec: dict[str, Any],
    phase_id: str,
    cfg: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    errors: list[str] = []
    meta: dict[str, Any] = {}

    attempts = [
        (_compact_inputs(inputs, 40_000), True, 0.3, 4096),
        (_compact_inputs(inputs, 20_000), False, 0.2, 3072),
        (_compact_inputs(inputs, 10_000), False, 0.1, 2048),
    ]

    for compact, as_json, temperature, max_tokens in attempts:
        prompt = _build_synthesis_prompt(compact, spec, phase_id, cfg)
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
                normalized = _normalize_synthesis(parsed)
                if normalized.get("resumo_sintese") or normalized.get("dinamica_passo_a_passo"):
                    meta = {
                        **meta,
                        "attempts": errors,
                        "used_response_json": as_json,
                        "used_max_output_tokens": max_tokens,
                    }
                    return normalized, meta
            errors.append(f"formato_invalido(json={as_json})")
        except Exception as exc:
            errors.append(f"{type(exc).__name__}: {exc}")

    fallback = _fallback_synthesis(
        inputs,
        spec,
        reason="; ".join(errors) or "falha na síntese",
    )
    return fallback, {**meta, "fallback": True, "attempts": errors}


async def execute_phase_L3(
    run_id: str,
    spec: dict[str, Any],
    db_session: Optional[Session] = None,
    phase_id: str = "sintese",
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
                    f"Nenhum artefato de entrada encontrado para '{phase_id}'. "
                    "Aprove as fases anteriores (depends_on) antes da síntese."
                )

            parsed, meta = await asyncio.to_thread(
                _synthesize_safe,
                inputs,
                spec,
                phase_id,
                cfg,
            )

            return {
                "status": "success",
                "phase": phase_id,
                "capability": "synthesize",
                "run_id": run_id,
                "pipeline_name": pipeline_label(spec),
                "artifact_data": parsed,
                "inputs_used": list(inputs.keys()),
                "meta": meta,
            }
        except Exception as exc:
            try:
                inputs = load_dependency_artifacts(session, run_id, spec, phase_id) or {}
            except Exception:
                inputs = {}
            if inputs:
                parsed = _fallback_synthesis(inputs, spec, reason=str(exc))
                return {
                    "status": "success",
                    "phase": phase_id,
                    "capability": "synthesize",
                    "run_id": run_id,
                    "pipeline_name": pipeline_label(spec),
                    "artifact_data": parsed,
                    "inputs_used": list(inputs.keys()),
                    "meta": {"fallback": True, "error": str(exc)},
                }
            return {
                "status": "error",
                "phase": phase_id,
                "capability": "synthesize",
                "run_id": run_id,
                "pipeline_name": pipeline_label(spec),
                "artifact_data": {"erro": str(exc)},
            }
    finally:
        if owns_session:
            session.close()
