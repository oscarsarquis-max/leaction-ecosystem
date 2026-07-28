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
  sintese_produto, generate_prd, generate_sdd, prompt_cursor, entrega_final).
- Se o usuário pedir DUAS pesquisas separadas, crie DUAS fases type=research
  (com descricao distinta) e uma fase type=synthesize que as agrupe com a
  metodologia via depends_on.

TOPOLOGIA PADRÃO — construção de SOFTWARE / aplicação / sistema / plataforma:
1. Fases methodology e research (paralelas se necessário; research pode ser N)
2. Uma fase synthesize unindo as anteriores (depends_on)
3. Uma fase generate_prd dependendo da síntese
4. Uma fase generate_sdd dependendo do PRD
5. Uma fase final prompt_cursor dependendo do SDD
Mapeie IDs e depends_on corretamente para formar o grafo lógico.

TOPOLOGIA — entrega de ARTEFATO (HTML interativo, apresentação, playbook,
documento educativo, protótipo visual) SEM pedir implementação de software:
- methodology + research (+ synthesize) e fase final type=prompt que PRODUZ
  O ARTEFATO pedido (não um prompt de IDE).

O JSON deve ter:
- "runId": slug curto (kebab-case)
- "description": deve repetir/preservar o pedido do usuário (incluindo o tipo
  de entrega: software, apresentação, documento, etc.)
- "version": "1.0"
- "phases": dicionário de fases. Cada fase:
  - "name": título curto amigável
  - "type": methodology | research | synthesize | generate_prd | generate_sdd
    | prompt_cursor | prompt
    (aliases: generate, grounding, evaluate, prd, sdd, delivery, html,
    ide_prompt)
  - "order": número sequencial (1, 2, 3...)
  - "descricao": escopo detalhado DESTA fase (o que o modelo deve fazer)
  - "depends_on": lista de ids de fases cujos artefatos alimentam esta fase
    (obrigatório em synthesize, generate_prd, generate_sdd, prompt_cursor e
    prompt; omitir ou [] nas fases iniciais)

Capabilities:
- methodology: alinhamento metodológico / princípios
- research: pesquisa/grounding com busca (pode haver N)
- synthesize: cruza/agrupa artefatos anteriores
- generate_prd: gera PRD (Product Requirements Document) em Markdown
- generate_sdd: gera SDD (Software Design Document) em Markdown a partir do PRD
- prompt_cursor: gera prompt executável curto para o Cursor IDE (lê PRD.md/SDD.md)
- prompt: GERA A ENTREGA FINAL solicitada (HTML/doc/artefato) — NÃO é prompt de IDE

Retorne APENAS o JSON válido, sem markdown e sem comentários.
""".strip()

_PROMPT_DESCRICAO = (
    "Produzir a ENTREGA FINAL pedida pelo usuário (o artefato concreto: "
    "apresentação, documento, playbook ou protótipo), usando 100% do esforço "
    "das fases anteriores. Não gerar prompt intermediário nem citar IDEs."
)

_PRD_DESCRICAO = (
    "Gerar PRD (Product Requirements Document) em Markdown a partir da síntese: "
    "Visão Geral, Público-alvo, Regras de Negócio Core, Casos de Uso/Jornadas e "
    "Critérios de Aceite."
)

_SDD_DESCRICAO = (
    "Gerar SDD (Software Design Document) em Markdown a partir do PRD: "
    "Stack Tecnológica, Arquitetura do Sistema, Modelo de Dados e Contratos "
    "de API/Componentes."
)

_CURSOR_DESCRICAO = (
    "Gerar prompt de ação curto e executável para o Cursor IDE, instruindo a "
    "IA a ler PRD.md e SDD.md na raiz e implementar passo a passo respeitando "
    "a arquitetura."
)

_SOFTWARE_RE = re.compile(
    r"\b("
    r"software|aplicativo|aplica[cç][aã]o|sistema|plataforma|saas|"
    r"backend|frontend|full[\s-]?stack|mvp|implementar|codificar|"
    r"desenvolver (um |o |uma |a )?(app|software|sistema|plataforma|api)"
    r")\b",
    re.I,
)

_ARTIFACT_DELIVERY_RE = re.compile(
    r"\b("
    r"html|apresenta[cç][aã]o|slides?|pitch|deck|playbook|roteiro|"
    r"p[aá]gina interativa|prot[oó]tipo visual|experi[eê]ncia digital educativa"
    r")\b",
    re.I,
)


def _wants_software_build(user_prompt: str) -> bool:
    """True quando o pedido é construir software (PRD→SDD→Cursor)."""
    text = user_prompt or ""
    if not _SOFTWARE_RE.search(text):
        return False
    # Artefato educativo/HTML explícito sem ênfase em implementar sistema
    if _ARTIFACT_DELIVERY_RE.search(text) and not re.search(
        r"\b(implementar|codificar|reposit[oó]rio|cursor ide|stack)\b",
        text,
        re.I,
    ):
        return False
    return True


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


def _max_order(phases: dict[str, Any]) -> int:
    orders: list[int] = []
    for cfg in phases.values():
        if isinstance(cfg, dict):
            try:
                orders.append(int(cfg.get("order") or 0))
            except (TypeError, ValueError):
                pass
    return max(orders) if orders else 0


def _find_phase_ids_by_capability(
    phases: dict[str, Any], capability: str
) -> list[str]:
    return [
        pid
        for pid, cfg in phases.items()
        if isinstance(cfg, dict)
        and normalize_phase_type(cfg.get("type"), pid) == capability
    ]


def _ensure_final_prompt_phase(phases: dict[str, Any], user_prompt: str = "") -> None:
    """Garante ao menos uma fase type=prompt no fim (entrega de artefato)."""
    prompt_ids = _find_phase_ids_by_capability(phases, "prompt")
    final_name = _final_phase_name(user_prompt)
    if prompt_ids:
        for pid in prompt_ids:
            cfg = phases[pid]
            cfg["type"] = "prompt"
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

    prior = [pid for pid in phases.keys()]
    phases["entrega_final"] = {
        "name": final_name,
        "type": "prompt",
        "order": _max_order(phases) + 1,
        "descricao": (
            f"{_PROMPT_DESCRICAO} Pedido do usuário: "
            f"{(user_prompt or '').strip()[:400]}"
        ),
        "depends_on": prior,
    }


def _ensure_software_topology(phases: dict[str, Any], user_prompt: str = "") -> None:
    """Garante synthesize → generate_prd → generate_sdd → prompt_cursor."""
    synth_ids = _find_phase_ids_by_capability(phases, "synthesize")
    if not synth_ids:
        # Cria síntese mínima dependendo de tudo que já existe
        prior = list(phases.keys())
        phases["sintese_produto"] = {
            "name": "Síntese do produto",
            "type": "synthesize",
            "order": _max_order(phases) + 1,
            "descricao": (
                "Sintetizar metodologia e pesquisas em requisitos e direção "
                f"de produto. Pedido: {(user_prompt or '').strip()[:300]}"
            ),
            "depends_on": prior,
        }
        synth_ids = ["sintese_produto"]

    prd_ids = _find_phase_ids_by_capability(phases, "generate_prd")
    if not prd_ids:
        phases["generate_prd"] = {
            "name": "PRD — Requisitos do Produto",
            "type": "generate_prd",
            "order": _max_order(phases) + 1,
            "descricao": _PRD_DESCRICAO,
            "depends_on": [synth_ids[-1]],
        }
        prd_ids = ["generate_prd"]
    else:
        for pid in prd_ids:
            cfg = phases[pid]
            cfg["type"] = "generate_prd"
            if not cfg.get("depends_on"):
                cfg["depends_on"] = [synth_ids[-1]]
            if not cfg.get("descricao"):
                cfg["descricao"] = _PRD_DESCRICAO

    sdd_ids = _find_phase_ids_by_capability(phases, "generate_sdd")
    if not sdd_ids:
        phases["generate_sdd"] = {
            "name": "SDD — Design de Software",
            "type": "generate_sdd",
            "order": _max_order(phases) + 1,
            "descricao": _SDD_DESCRICAO,
            "depends_on": [prd_ids[-1]],
        }
        sdd_ids = ["generate_sdd"]
    else:
        for pid in sdd_ids:
            cfg = phases[pid]
            cfg["type"] = "generate_sdd"
            if not cfg.get("depends_on"):
                cfg["depends_on"] = [prd_ids[-1]]
            if not cfg.get("descricao"):
                cfg["descricao"] = _SDD_DESCRICAO

    cursor_ids = _find_phase_ids_by_capability(phases, "prompt_cursor")
    if not cursor_ids:
        phases["prompt_cursor"] = {
            "name": "Prompt para Cursor IDE",
            "type": "prompt_cursor",
            "order": _max_order(phases) + 1,
            "descricao": (
                f"{_CURSOR_DESCRICAO} Pedido: {(user_prompt or '').strip()[:300]}"
            ),
            "depends_on": [sdd_ids[-1]],
        }
    else:
        for pid in cursor_ids:
            cfg = phases[pid]
            cfg["type"] = "prompt_cursor"
            if not cfg.get("depends_on"):
                cfg["depends_on"] = [sdd_ids[-1]]
            if not cfg.get("descricao"):
                cfg["descricao"] = _CURSOR_DESCRICAO

    # Em fluxo de software, não forçar fase type=prompt (entrega HTML)
    # a menos que o modelo já a tenha criado de propósito.


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
    needs_deps = {
        "synthesize",
        "generate_prd",
        "generate_sdd",
        "prompt_cursor",
        "prompt",
    }
    for phase_id in ordered_ids:
        cfg = phases[phase_id]
        capability = normalize_phase_type(cfg.get("type"), phase_id)
        if capability in needs_deps and not cfg.get("depends_on"):
            idx = ordered_ids.index(phase_id)
            cfg["depends_on"] = ordered_ids[:idx]

    if _wants_software_build(user_clean):
        _ensure_software_topology(phases, user_prompt=user_clean)
    else:
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
