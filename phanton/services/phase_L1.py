"""Capability: methodology — alinhamento metodológico (Spec-driven)."""

from __future__ import annotations

import asyncio
import json
from typing import Any, Optional

from sqlalchemy.orm import Session

from services.gemini_client import extract_json_payload, generate_content
from services.phase_context import phase_cfg, phase_description, pipeline_label


def _build_prompt(spec: dict[str, Any], phase_id: str, cfg: dict[str, Any]) -> str:
    descricao = phase_description(
        cfg,
        fallback=spec.get("description") or "Definir metodologia e princípios do projeto",
    )
    name = cfg.get("name") or phase_id

    return f"""
Você é um arquiteto de metodologia / Staff Engineer.
Gere o alinhamento metodológico para a fase "{name}" do pipeline "{pipeline_label(spec)}".

Instruções da fase:
{descricao}

Responda APENAS com JSON válido (sem markdown), neste formato:
{{
  "metodologia": "nome ou abordagem principal",
  "principios": ["principio 1", "principio 2"],
  "objetivo": "objetivo desta etapa",
  "notas": "observações relevantes para as próximas fases"
}}
""".strip()


async def execute_phase_L1(
    run_id: str,
    spec: dict[str, Any],
    db_session: Optional[Session] = None,
    phase_id: str = "metodologia",
) -> dict[str, Any]:
    del db_session
    spec = spec if isinstance(spec, dict) else {}
    cfg = phase_cfg(spec, phase_id)
    prompt = _build_prompt(spec, phase_id, cfg)

    try:
        raw_text, meta = await asyncio.to_thread(
            lambda: generate_content(
                prompt,
                enable_google_search=False,
                response_json=True,
                temperature=0.3,
            )
        )
        parsed = extract_json_payload(raw_text)
        if not isinstance(parsed, dict):
            raise ValueError("Metodologia não retornou JSON objeto")
        artifact = parsed
    except Exception as exc:
        # Fallback determinístico para não travar o pipeline
        artifact = {
            "metodologia": cfg.get("name") or phase_id,
            "principios": ["iteração com aprovação humana", "artefatos explícitos entre fases"],
            "objetivo": phase_description(cfg, fallback=spec.get("description") or ""),
            "notas": f"Fallback local (Gemini indisponível): {exc}",
        }
        meta = {"fallback": True}

    return {
        "status": "success",
        "phase": phase_id,
        "capability": "methodology",
        "run_id": run_id,
        "pipeline_name": pipeline_label(spec),
        "artifact_data": artifact,
        "meta": meta,
    }
