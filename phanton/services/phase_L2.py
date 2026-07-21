"""Capability: research — grounding/pesquisa (pode haver N fases deste tipo)."""

from __future__ import annotations

import asyncio
from typing import Any, Optional

from sqlalchemy.orm import Session

from services.gemini_client import extract_json_payload, generate_content
from services.phase_context import phase_cfg, phase_description, pipeline_label


def _build_prompt(spec: dict[str, Any], phase_id: str, cfg: dict[str, Any]) -> str:
    # Preferências da própria fase; L2_busca legado só como fallback.
    legacy = spec.get("L2_busca") if isinstance(spec.get("L2_busca"), dict) else {}
    descricao = phase_description(
        cfg,
        fallback=legacy.get("descricao")
        or spec.get("description")
        or "Busque referências reais e atuais",
    )
    foco = cfg.get("foco") or legacy.get("foco") or ""
    name = cfg.get("name") or phase_id

    return f"""
Você é um pesquisador. Use a busca do Google (grounding) para encontrar
casos reais e atuais relacionados ao pedido abaixo.

Fase: {name}
Pipeline: {pipeline_label(spec)}
Pedido de busca: {descricao}
Foco adicional: {foco or "nenhum"}

Responda APENAS com um JSON válido (sem markdown, sem comentários), neste formato:
{{
  "achados": [
    {{
      "titulo": "string",
      "fonte": "URL da fonte",
      "url": "URL da fonte",
      "resumo": "resumo objetivo do caso",
      "relacao_com_pedido": "como isso responde ao pedido desta fase"
    }}
  ]
}}

Inclua de 3 a 6 achados, priorizando fontes confiáveis e recentes.
""".strip()


async def execute_phase_L2(
    run_id: str,
    spec: dict[str, Any],
    db_session: Optional[Session] = None,
    phase_id: str = "pesquisa",
) -> dict[str, Any]:
    del db_session
    spec = spec if isinstance(spec, dict) else {}
    cfg = phase_cfg(spec, phase_id)
    prompt = _build_prompt(spec, phase_id, cfg)

    try:
        raw_text, meta = await asyncio.to_thread(
            lambda: generate_content(
                prompt,
                enable_google_search=True,
                response_json=False,
                temperature=0.3,
            )
        )
    except Exception as exc:
        return {
            "status": "error",
            "phase": phase_id,
            "capability": "research",
            "run_id": run_id,
            "pipeline_name": pipeline_label(spec),
            "error": str(exc),
            "artifact_data": {"achados": [], "erro": str(exc)},
        }

    try:
        parsed = extract_json_payload(raw_text)
        if isinstance(parsed, dict) and "achados" in parsed:
            achados = parsed.get("achados") or []
        elif isinstance(parsed, list):
            achados = parsed
        else:
            achados = [{"titulo": "Resultado bruto", "resumo": raw_text[:2000]}]
    except Exception:
        achados = [{"titulo": "Resultado bruto", "resumo": (raw_text or "")[:2000]}]

    return {
        "status": "success",
        "phase": phase_id,
        "capability": "research",
        "run_id": run_id,
        "pipeline_name": pipeline_label(spec),
        "artifact_data": {"achados": achados, "fase": phase_id, "nome": cfg.get("name")},
        "meta": meta,
    }
