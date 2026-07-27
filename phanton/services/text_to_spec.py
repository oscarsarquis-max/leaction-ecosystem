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
  sintese_produto, entrega_final).
- Se o usuário pedir DUAS pesquisas separadas, crie DUAS fases type=research
  (com descricao distinta) e uma fase type=synthesize que as agrupe com a
  metodologia via depends_on.
- A ENTREGA FINAL deve ser uma fase type=prompt que PRODUZ O ARTEFATO pedido
  pelo usuário (apresentação, documento, playbook, protótipo HTML, etc.) —
  NÃO um prompt para outra ferramenta. Tipicamente é a última fase.

O JSON deve ter:
- "runId": slug curto (kebab-case)
- "description": deve repetir/preservar o pedido do usuário (incluindo o tipo
  de entrega: apresentação, documento, etc.)
- "version": "1.0"
- "phases": dicionário de fases. Cada fase:
  - "name": título curto amigável
  - "type": methodology | research | synthesize | prompt
    (aliases aceitos: generate, grounding, evaluate, prompt_cursor, delivery)
  - "order": número sequencial (1, 2, 3...)
  - "descricao": escopo detalhado DESTA fase (o que o modelo deve fazer)
  - "depends_on": lista de ids de fases cujos artefatos alimentam esta fase
    (obrigatório em synthesize e prompt; omitir ou [] nas fases iniciais)

Capabilities:
- methodology: alinhamento metodológico / princípios
- research: pesquisa/grounding com busca (pode haver N)
- synthesize: cruza/agrupa artefatos anteriores
- prompt: GERA A ENTREGA FINAL solicitada (o artefato em si)

A fase final type=prompt deve ter:
- name amigável tipo "Entrega final" / "Apresentação" / "Documento final"
  (conforme o pedido)
- descricao explícita do ARTEFATO a produzir, ex.:
  "Produzir a apresentação completa solicitada pelo usuário, em HTML
   autocontido com slides navegáveis, usando metodologia + pesquisas + síntese
   como fonte da verdade. Não gerar prompt intermediário."

NÃO mencione Cursor, VS Code, Copilot ou outras IDEs na Spec.

Retorne APENAS o JSON válido, sem markdown e sem comentários.
""".strip()

_PROMPT_DESCRICAO = (
    "Produzir a ENTREGA FINAL pedida pelo usuário (o artefato concreto: "
    "apresentação, documento, playbook ou protótipo), usando 100% do esforço "
    "das fases anteriores. Não gerar prompt intermediário nem citar IDEs."
)


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", (value or "").strip().lower()).strip("-")
    return slug[:48] or "pipeline-gerado"


def _slug_phase_id(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", (value or "").strip().lower()).strip("_")
    return slug[:64] or "fase"


def _final_phase_name(user_prompt: str) -> str:
    text = (user_prompt or "").lower()
    if re.search(r"apresenta|slides?|pitch|deck", text):
        return "Apresentação final"
    if re.search(r"documento|relat[oó]rio|playbook|roteiro", text):
        return "Documento final"
    if re.search(r"prot[oó]tipo|html|p[aá]gina|landing", text):
        return "Protótipo final"
    return "Entrega final"


def _ensure_final_prompt_phase(phases: dict[str, Any], user_prompt: str = "") -> None:
    """Garante ao menos uma fase type=prompt no fim (id livre)."""
    prompt_ids = [
        pid
        for pid, cfg in phases.items()
        if isinstance(cfg, dict)
        and normalize_phase_type(cfg.get("type"), pid) == "prompt"
    ]
    final_name = _final_phase_name(user_prompt)
    if prompt_ids:
        for pid in prompt_ids:
            cfg = phases[pid]
            cfg["type"] = "prompt"
            # Remove nomes/descrições legadas que apontam para IDE
            name = str(cfg.get("name") or "")
            if re.search(r"(?i)cursor", name) or name.strip().lower().startswith("prompt"):
                cfg["name"] = final_name
            descricao = str(cfg.get("descricao") or cfg.get("description") or "")
            if not descricao or re.search(r"(?i)cursor|colar no|prompt para", descricao):
                cfg["descricao"] = (
                    f"{_PROMPT_DESCRICAO} Pedido do usuário: "
                    f"{(user_prompt or '').strip()[:400]}"
                )
        return

    other_orders = []
    for pid, cfg in phases.items():
        if isinstance(cfg, dict):
            try:
                other_orders.append(int(cfg.get("order") or 0))
            except (TypeError, ValueError):
                pass
    prior = [pid for pid in phases.keys()]
    phases["entrega_final"] = {
        "name": final_name,
        "type": "prompt",
        "order": (max(other_orders) + 1) if other_orders else len(phases) + 1,
        "descricao": (
            f"{_PROMPT_DESCRICAO} Pedido do usuário: "
            f"{(user_prompt or '').strip()[:400]}"
        ),
        "depends_on": prior,
    }


def _normalize_generated_spec(raw: dict[str, Any], user_prompt: str) -> dict[str, Any]:
    spec = dict(raw)

    run_id = spec.pop("runId", None) or spec.pop("run_id", None)
    if run_id and not spec.get("name"):
        spec["name"] = str(run_id)
    if not spec.get("name"):
        spec["name"] = _slugify(user_prompt[:60])
    # Preserva o pedido completo na description (a entrega final depende disso)
    user_clean = user_prompt.strip()
    if user_clean:
        spec["description"] = user_clean[:800]
        spec["user_prompt"] = user_clean
    elif not spec.get("description"):
        spec["description"] = "Pipeline gerado via Text-to-Spec"
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
            deps = cfg.get("depends_on") or []
            if isinstance(deps, str):
                deps = [deps]
            if isinstance(deps, list):
                cfg["depends_on"] = [_slug_phase_id(str(d)) for d in deps if d]
            phases[phase_id] = cfg
    spec["phases"] = phases

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

    ordered_ids = [
        pid
        for pid, _ in sorted(
            phases.items(),
            key=lambda item: int(item[1].get("order") or 999),
        )
    ]
    for phase_id in ordered_ids:
        cfg = phases[phase_id]
        capability = normalize_phase_type(cfg.get("type"), phase_id)
        if capability in {"synthesize", "prompt"} and not cfg.get("depends_on"):
            idx = ordered_ids.index(phase_id)
            cfg["depends_on"] = ordered_ids[:idx]

    _ensure_final_prompt_phase(phases, user_prompt=user_clean)
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
