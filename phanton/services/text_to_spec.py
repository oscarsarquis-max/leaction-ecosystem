"""Text-to-Spec: linguagem natural → Pipeline Spec JSON (fases dinâmicas)."""

from __future__ import annotations

import re
from typing import Any

from services.gemini_client import extract_json_payload, generate_content
from services.phase_context import normalize_phase_type
from services.state_engine import normalize_spec_phases

_SYSTEM_INSTRUCTION = """
Atue como Arquiteto de Software. Transforme o pedido do usuário em um JSON de
configuração de pipeline para o orquestrador Phanton.

IMPORTANTE — o pipeline é DINÂMICO:
- NÃO fixe sempre L1/L2/L3/L4.
- Crie quantas fases forem necessárias, com IDs descritivos em snake_case
  (ex.: metodologia_eduscrum, pesquisa_casos_escolas, pesquisa_stack_tecnica,
  sintese_produto, prompt_cursor).
- Se o usuário pedir DUAS pesquisas separadas, crie DUAS fases type=research
  (com descricao distinta) e uma fase type=synthesize que as agrupe com a
  metodologia via depends_on.
- A entrega final deve ser uma fase type=prompt (prompt técnico para o Cursor IDE),
  tipicamente a última.

O JSON deve ter:
- "runId": slug curto (kebab-case)
- "description": resumo em uma frase
- "version": "1.0"
- "phases": dicionário de fases. Cada fase:
  - "name": título curto amigável
  - "type": methodology | research | synthesize | prompt
    (aliases aceitos: generate, grounding, evaluate, prompt_cursor)
  - "order": número sequencial (1, 2, 3...)
  - "descricao": escopo detalhado DESTA fase (o que o modelo deve fazer)
  - "depends_on": lista de ids de fases cujos artefatos alimentam esta fase
    (obrigatório em synthesize e prompt; omitir ou [] nas fases iniciais)

Capabilities:
- methodology: alinhamento metodológico / princípios
- research: pesquisa/grounding com busca (pode haver N)
- synthesize: cruza/agrupa artefatos anteriores
- prompt: gera o prompt Markdown para o Cursor implementar o sistema

A fase final type=prompt deve ter descricao equivalente a:
"Gerar o prompt técnico detalhado e no estado da arte para ser utilizado no
Cursor IDE para a implementação do sistema."

Retorne APENAS o JSON válido, sem markdown e sem comentários.
""".strip()

_PROMPT_DESCRICAO = (
    "Destilar 100% do esforço das fases anteriores (metodologia, pesquisas e "
    "síntese) no melhor prompt Markdown possível para o Cursor IDE: completo, "
    "auto-contido, anti-alucinação, com stack, arquitetura, estrutura de "
    "arquivos, contratos, plano step-by-step e critérios de aceite verificáveis."
)


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", (value or "").strip().lower()).strip("-")
    return slug[:48] or "pipeline-gerado"


def _slug_phase_id(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", (value or "").strip().lower()).strip("_")
    return slug[:64] or "fase"


def _ensure_final_prompt_phase(phases: dict[str, Any]) -> None:
    """Garante ao menos uma fase type=prompt no fim (id livre)."""
    prompt_ids = [
        pid
        for pid, cfg in phases.items()
        if isinstance(cfg, dict)
        and normalize_phase_type(cfg.get("type"), pid) == "prompt"
    ]
    if prompt_ids:
        for pid in prompt_ids:
            cfg = phases[pid]
            cfg["type"] = "prompt"
            if not cfg.get("descricao") and not cfg.get("description"):
                cfg["descricao"] = _PROMPT_DESCRICAO
        return

    # Cria prompt_cursor se o modelo omitiu a entrega
    other_orders = []
    for pid, cfg in phases.items():
        if isinstance(cfg, dict):
            try:
                other_orders.append(int(cfg.get("order") or 0))
            except (TypeError, ValueError):
                pass
    prior = [pid for pid in phases.keys()]
    phases["prompt_cursor"] = {
        "name": "Prompt para o Cursor",
        "type": "prompt",
        "order": (max(other_orders) + 1) if other_orders else len(phases) + 1,
        "descricao": _PROMPT_DESCRICAO,
        "depends_on": prior,
    }


def _normalize_generated_spec(raw: dict[str, Any], user_prompt: str) -> dict[str, Any]:
    spec = dict(raw)

    run_id = spec.pop("runId", None) or spec.pop("run_id", None)
    if run_id and not spec.get("name"):
        spec["name"] = str(run_id)
    if not spec.get("name"):
        spec["name"] = _slugify(user_prompt[:60])
    if not spec.get("description"):
        spec["description"] = user_prompt.strip()[:280] or "Pipeline gerado via Text-to-Spec"
    if not spec.get("version"):
        spec["version"] = "1.0"

    phases_in = spec.get("phases")
    phases: dict[str, Any] = {}
    if isinstance(phases_in, dict):
        for raw_id, cfg in phases_in.items():
            phase_id = _slug_phase_id(str(raw_id))
            if not isinstance(cfg, dict):
                cfg = {"descricao": str(cfg)}
            cfg = dict(cfg)
            cfg["type"] = normalize_phase_type(cfg.get("type"), phase_id)
            if not cfg.get("name"):
                cfg["name"] = phase_id.replace("_", " ").title()
            if not cfg.get("descricao") and cfg.get("description"):
                cfg["descricao"] = cfg["description"]
            # depends_on: normaliza ids
            deps = cfg.get("depends_on") or []
            if isinstance(deps, str):
                deps = [deps]
            if isinstance(deps, list):
                cfg["depends_on"] = [_slug_phase_id(str(d)) for d in deps if d]
            phases[phase_id] = cfg
    spec["phases"] = phases

    # order sequencial se ausente
    ordered = sorted(
        phases.items(),
        key=lambda item: (
            int(item[1].get("order")) if str(item[1].get("order", "")).isdigit() else 999,
            item[0],
        ),
    )
    for index, (phase_id, cfg) in enumerate(ordered, start=1):
        if cfg.get("order") is None:
            cfg["order"] = index

    # depends_on default para synthesize/prompt = fases anteriores
    ordered_ids = [pid for pid, _ in sorted(
        phases.items(),
        key=lambda item: int(item[1].get("order") or 999),
    )]
    for phase_id in ordered_ids:
        cfg = phases[phase_id]
        capability = normalize_phase_type(cfg.get("type"), phase_id)
        if capability in {"synthesize", "prompt"} and not cfg.get("depends_on"):
            idx = ordered_ids.index(phase_id)
            cfg["depends_on"] = ordered_ids[:idx]

    _ensure_final_prompt_phase(phases)
    return normalize_spec_phases(spec)


def generate_pipeline_spec(user_prompt: str) -> tuple[dict[str, Any], str]:
    prompt = f"{_SYSTEM_INSTRUCTION}\n\nPedido do usuário:\n{user_prompt.strip()}"
    raw_text, meta = generate_content(
        prompt,
        enable_google_search=False,
        response_json=True,
        temperature=0.2,
    )
    parsed = extract_json_payload(raw_text)
    if not isinstance(parsed, dict):
        raise ValueError("O modelo não retornou um objeto JSON de Pipeline Spec")

    spec = _normalize_generated_spec(parsed, user_prompt)
    if not spec.get("phases"):
        raise ValueError("Pipeline Spec gerada sem fases — refine o pedido e tente novamente")

    return spec, str(meta.get("model") or "")
