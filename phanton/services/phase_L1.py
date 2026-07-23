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

Responda APENAS com JSON válido (sem markdown), neste formato EXATO
(a ordem dos campos importa — preencha TODOS):
{{
  "metodologia": "nome ou abordagem principal",
  "notas": "2 a 5 frases com observações úteis para as próximas fases (riscos, restrições, dependências, o que NÃO fazer). Campo OBRIGATÓRIO e NÃO vazio.",
  "objetivo": "objetivo desta etapa",
  "principios": ["principio 1", "principio 2", "principio 3"]
}}

Regras:
- "notas" é obrigatório: nunca omita nem deixe string vazia.
- Seja concreto; evite frases genéricas do tipo "seguir boas práticas".
""".strip()


def _normalize_methodology_artifact(parsed: dict[str, Any], *, fallback_notas: str = "") -> dict[str, Any]:
    """Garante campos canônicos; `notas` nunca fica ausente/vazio na UI."""
    notas = (
        parsed.get("notas")
        or parsed.get("notes")
        or parsed.get("observacoes")
        or parsed.get("observações")
        or parsed.get("recomendacoes")
        or parsed.get("recomendações")
        or ""
    )
    if isinstance(notas, list):
        notas = "\n".join(str(item) for item in notas if item is not None)
    notas = str(notas).strip()
    if not notas:
        notas = fallback_notas or (
            "Sem notas explícitas do modelo — revisar metodologia/objetivo antes "
            "das fases de pesquisa e síntese."
        )

    principios = parsed.get("principios") or parsed.get("principles") or []
    if isinstance(principios, str):
        principios = [principios]

    return {
        "metodologia": parsed.get("metodologia") or parsed.get("methodology") or "",
        "notas": notas,
        "objetivo": parsed.get("objetivo")
        or parsed.get("objective")
        or parsed.get("objetivo_geral")
        or "",
        "principios": list(principios),
    }


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
                max_output_tokens=4096,
            )
        )
        parsed = extract_json_payload(raw_text)
        if not isinstance(parsed, dict):
            raise ValueError("Metodologia não retornou JSON objeto")
        artifact = _normalize_methodology_artifact(parsed)
    except Exception as exc:
        # Fallback determinístico para não travar o pipeline
        artifact = _normalize_methodology_artifact(
            {
                "metodologia": cfg.get("name") or phase_id,
                "principios": [
                    "iteração com aprovação humana",
                    "artefatos explícitos entre fases",
                ],
                "objetivo": phase_description(
                    cfg, fallback=spec.get("description") or ""
                ),
                "notas": f"Fallback local (Gemini indisponível): {exc}",
            }
        )
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
