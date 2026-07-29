"""Text-to-Spec: linguagem natural → Pipeline Spec JSON (fases dinâmicas)."""

from __future__ import annotations

import re
from typing import Any, Optional

from google.genai import types

from services.context_warnings import normalize_warnings
from services.gemini_client import extract_json_payload, generate_content
from services.phase_context import normalize_phase_type
from services.security_domain import is_sensitive_domain
from services.state_engine import normalize_spec_phases
from services.structured_requirements import (
    PERFIL_SOFTWARE,
    format_structured_requirements_block,
    normalize_structured_requirements,
)

_SYSTEM_INSTRUCTION = """
Atue como Arquiteto de Software. Transforme o pedido do usuário em um JSON de
configuração de pipeline para o orquestrador Phanton.

IMPORTANTE — o pipeline é DINÂMICO:
- NÃO fixe sempre L1/L2/L3/L4.
- Crie quantas fases forem necessárias, com IDs descritivos em snake_case
  (ex.: methodology_eduscrum, context7_search, pesquisa_casos, sintese_produto,
  generate_prd, generate_sdd, prompt_cursor, entrega_final).
- Se o usuário pedir DUAS pesquisas separadas, crie DUAS fases type=research
  (com descricao distinta) e uma fase type=synthesize que as agrupe com a
  metodologia via depends_on.

TOPOLOGIA PADRÃO — construção de SOFTWARE / aplicação / sistema / plataforma / SaaS:
1. No INÍCIO do DAG (junto com methodology e research): fase obrigatória
   type=context7_search — busca PRDs/SDDs similares na base interna context7.
2. Fases methodology e research (paralelas se necessário; research pode ser N)
3. Uma fase synthesize que DEPENDE de context7_search + methodology + research
4. Uma fase generate_prd dependendo da síntese
5. Uma fase generate_sdd dependendo do PRD
6. Se o domínio for SENSÍVEL/REGULADO (financeiro, saúde, etc.): fase SEPARADA
   type=security_guidelines dependendo do SDD (gate humano próprio — NÃO embutir
   segurança dentro do prompt_cursor)
7. Uma fase final prompt_cursor dependendo do SDD (e de security_guidelines quando
   houver)
Mapeie IDs e depends_on corretamente para formar o grafo lógico.

TOPOLOGIA — entrega de ARTEFATO (HTML interativo, apresentação, playbook,
documento educativo, protótipo visual) SEM pedir implementação de software:
- methodology + research (+ synthesize) e fase final type=prompt que PRODUZ
  O ARTEFATO pedido (não um prompt de IDE). context7_search NÃO é obrigatório
  neste fluxo.

O JSON deve ter:
- "runId": slug curto (kebab-case)
- "description": deve repetir/preservar o pedido do usuário (incluindo o tipo
  de entrega: software, apresentação, documento, etc.)
- "version": "1.0"
- "warnings": array OBRIGATÓRIO (pode ser []) de lacunas de contexto no pedido.
  Cada item: {"campo", "descricao", "impacto"}. Checklist mínimo a avaliar:
  1) contexto_de_uso — single-tenant (uso interno) vs multi-tenant (SaaS)?
  2) escala_esperada — dezenas / milhares / milhões (só direção)?
  3) ambiente_de_deploy — cloud própria / on-prem / SaaS terceiro?
  4) integracoes_nomeadas — citou banco/API genérica sem nomear PSP/instituição?
  5) escopo_regulatorio — domínio sensível sem norma/jurisdição mencionada?
  Se o pedido JÁ deixa o item claro, NÃO inclua esse campo em warnings.
  NÃO bloqueie a geração — só sinalize.
- "phases": dicionário de fases. Cada fase:
  - "name": título curto amigável
  - "type": methodology | research | context7_search | synthesize | generate_prd
    | generate_sdd | security_guidelines | prompt_cursor | prompt
    (aliases: generate, grounding, evaluate, context7, prd, sdd, security,
    ide_prompt, delivery, html)
  - "order": número sequencial (1, 2, 3...)
  - "descricao": escopo detalhado DESTA fase (o que o modelo deve fazer)
  - "depends_on": lista de ids de fases cujos artefatos alimentam esta fase
    (obrigatório em synthesize, generate_prd, generate_sdd, security_guidelines,
    prompt_cursor e prompt; omitir ou [] nas fases iniciais incluindo context7_search)

Capabilities:
- methodology: alinhamento metodológico / princípios
- research: pesquisa/grounding com busca (pode haver N)
- context7_search: consulta memória organizacional (PRDs/SDDs históricos)
- synthesize: cruza/agrupa artefatos anteriores (inclui context7 quando houver)
- generate_prd: gera PRD (Product Requirements Document) em Markdown
- generate_sdd: gera SDD (Software Design Document) em Markdown a partir do PRD
- security_guidelines: fase SEPARADA de diretrizes de segurança (padrões de mercado
  como ASVS/FAPI/OWASP API Top 10/LGPD) — exige aprovação humana própria antes
  do prompt_cursor; só para domínio sensível/regulado
- prompt_cursor: gera prompt executável curto para o Cursor IDE (lê PRD.md/SDD.md)
- prompt: GERA A ENTREGA FINAL solicitada (HTML/doc/artefato) — NÃO é prompt de IDE

Retorne APENAS o JSON válido, sem markdown e sem comentários.
""".strip()

_WARNING_ITEM_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "campo": types.Schema(type=types.Type.STRING),
        "descricao": types.Schema(type=types.Type.STRING),
        "impacto": types.Schema(type=types.Type.STRING),
    },
    required=["campo", "descricao", "impacto"],
)

# phases fica como OBJECT livre (IDs dinâmicos); warnings é array obrigatório.
SPEC_RESPONSE_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "runId": types.Schema(type=types.Type.STRING),
        "description": types.Schema(type=types.Type.STRING),
        "version": types.Schema(type=types.Type.STRING),
        "warnings": types.Schema(
            type=types.Type.ARRAY,
            items=_WARNING_ITEM_SCHEMA,
        ),
        "phases": types.Schema(type=types.Type.OBJECT),
    },
    required=["warnings", "phases"],
)

_PROMPT_DESCRICAO = (
    "Produzir a ENTREGA FINAL pedida pelo usuário (o artefato concreto: "
    "apresentação, documento, playbook ou protótipo), usando 100% do esforço "
    "das fases anteriores. Não gerar prompt intermediário nem citar IDEs."
)

_CONTEXT7_DESCRICAO = (
    "Buscar na base interna context7 PRDs e SDDs historicos similares ao desafio "
    "atual; retornar fragmentos relevantes (regras de negocio e arquitetura) "
    "como padrao ouro para a sintese."
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

_SECURITY_DESCRICAO = (
    "Gerar diretrizes de segurança gerais e por módulo com base em padrões de "
    "mercado aplicáveis ao domínio (ex.: OWASP ASVS 5.0 Level 3, FAPI 2.0, "
    "OWASP API Security Top 10, LGPD). Fase separada — exige aprovação humana "
    "antes do prompt_cursor."
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


def _find_security_candidate_ids(phases: dict[str, Any]) -> list[str]:
    """IDs de fases de segurança (por type canônico ou nome/id do LLM)."""
    found: list[str] = []
    for pid, cfg in phases.items():
        if not isinstance(cfg, dict):
            continue
        if normalize_phase_type(cfg.get("type"), pid) == "security_guidelines":
            found.append(pid)
            continue
        name = str(cfg.get("name") or "").lower()
        if re.search(
            r"seguran[cç]a|security\s*guideline|security\s*review|appsec|owasp|fapi",
            name,
        ):
            found.append(pid)
    found = list(dict.fromkeys(found))
    found.sort(key=lambda p: (0 if p == "security_guidelines" else 1, p))
    return found


def _place_security_after_sdd(
    phases: dict[str, Any],
    *,
    sdd_id: str,
    user_prompt: str,
) -> str:
    """
    Consolida a fase security_guidelines depois de generate_sdd.
    Retorna o phase_id canônico usado.
    """
    candidates = _find_security_candidate_ids(phases)
    canonical = "security_guidelines"

    # Merge: manter um único nó canônico; remover aliases extras
    source_cfg: dict[str, Any] = {}
    for pid in candidates:
        cfg = phases.get(pid)
        if isinstance(cfg, dict) and not source_cfg:
            source_cfg = dict(cfg)
        if pid != canonical:
            phases.pop(pid, None)

    try:
        sdd_order = int(phases[sdd_id].get("order") or 0)
    except (TypeError, ValueError, KeyError):
        sdd_order = _max_order(phases)

    sec_order = sdd_order + 1
    # Empurra fases que estavam no mesmo slot ou depois (exceto a própria)
    for pid, cfg in list(phases.items()):
        if pid == canonical or not isinstance(cfg, dict):
            continue
        try:
            order = int(cfg.get("order") or 0)
        except (TypeError, ValueError):
            order = 0
        if order >= sec_order:
            cfg["order"] = order + 1

    phases[canonical] = {
        **source_cfg,
        "name": source_cfg.get("name") or "Diretrizes de Segurança",
        "type": "security_guidelines",
        "order": sec_order,
        "descricao": source_cfg.get("descricao")
        or source_cfg.get("description")
        or (
            f"{_SECURITY_DESCRICAO} Pedido: {(user_prompt or '').strip()[:300]}"
        ),
        "depends_on": [sdd_id],
        "requires_approval": True,
    }
    return canonical


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
    """Garante context7 + synthesize → generate_prd → generate_sdd → prompt_cursor."""
    # 1) Memoria organizacional no inicio do DAG
    ctx_ids = _find_phase_ids_by_capability(phases, "context7_search")
    if not ctx_ids:
        # Empurra orders existentes para abrir espaco no inicio
        for cfg in phases.values():
            if not isinstance(cfg, dict):
                continue
            try:
                order = int(cfg.get("order") or 0)
            except (TypeError, ValueError):
                order = 0
            cfg["order"] = order + 1 if order >= 1 else order + 1
        phases["context7_search"] = {
            "name": "Memoria organizacional (context7)",
            "type": "context7_search",
            "order": 1,
            "descricao": (
                f"{_CONTEXT7_DESCRICAO} Pedido: {(user_prompt or '').strip()[:300]}"
            ),
            "depends_on": [],
        }
        ctx_ids = ["context7_search"]
    else:
        for pid in ctx_ids:
            cfg = phases[pid]
            cfg["type"] = "context7_search"
            if not cfg.get("descricao"):
                cfg["descricao"] = _CONTEXT7_DESCRICAO
            cfg.setdefault("depends_on", [])

    synth_ids = _find_phase_ids_by_capability(phases, "synthesize")
    if not synth_ids:
        # Sintese depende de tudo que ja existe (inclui context7)
        prior = [pid for pid in phases.keys() if pid not in ctx_ids]
        # Garante context7 nas deps mesmo se prior estiver vazio
        deps = list(dict.fromkeys(ctx_ids + prior))
        phases["sintese_produto"] = {
            "name": "Síntese do produto",
            "type": "synthesize",
            "order": _max_order(phases) + 1,
            "descricao": (
                "Sintetizar metodologia, pesquisas externas e padroes historicos "
                f"do context7. Pedido: {(user_prompt or '').strip()[:300]}"
            ),
            "depends_on": deps,
        }
        synth_ids = ["sintese_produto"]
    else:
        for pid in synth_ids:
            cfg = phases[pid]
            cfg["type"] = "synthesize"
            deps = list(cfg.get("depends_on") or [])
            for ctx in ctx_ids:
                if ctx not in deps:
                    deps.append(ctx)
            cfg["depends_on"] = deps
            if not cfg.get("descricao"):
                cfg["descricao"] = (
                    "Sintetizar metodologia, pesquisas e Base Historica context7."
                )

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

    # Fase SEPARADA de segurança (gate humano próprio) — só domínio sensível
    cursor_upstream = [sdd_ids[-1]]
    if is_sensitive_domain(user_prompt):
        sec_id = _place_security_after_sdd(
            phases,
            sdd_id=sdd_ids[-1],
            user_prompt=user_prompt or "",
        )
        cursor_upstream = [sdd_ids[-1], sec_id]
    else:
        # Remove qualquer fase de segurança inventada em domínio genérico
        for pid in list(_find_security_candidate_ids(phases)):
            phases.pop(pid, None)

    cursor_ids = _find_phase_ids_by_capability(phases, "prompt_cursor")
    if not cursor_ids:
        # order depois de security (se houver)
        after = cursor_upstream[-1]
        try:
            base_order = int(phases[after].get("order") or 0) + 1
        except (TypeError, ValueError, KeyError):
            base_order = _max_order(phases) + 1
        phases["prompt_cursor"] = {
            "name": "Prompt para Cursor IDE",
            "type": "prompt_cursor",
            "order": base_order,
            "descricao": (
                f"{_CURSOR_DESCRICAO} Pedido: {(user_prompt or '').strip()[:300]}"
            ),
            "depends_on": list(cursor_upstream),
        }
    else:
        for pid in cursor_ids:
            cfg = phases[pid]
            cfg["type"] = "prompt_cursor"
            # depends_on explícito: SDD (+ security quando existir) — não só append
            cfg["depends_on"] = list(cursor_upstream)
            # Garante order depois do último upstream
            try:
                upstream_orders = [
                    int(phases[u].get("order") or 0)
                    for u in cursor_upstream
                    if u in phases
                ]
                min_cursor = (max(upstream_orders) + 1) if upstream_orders else None
            except (TypeError, ValueError):
                min_cursor = None
            if min_cursor is not None:
                try:
                    cur_order = int(cfg.get("order") or 0)
                except (TypeError, ValueError):
                    cur_order = 0
                if cur_order < min_cursor:
                    cfg["order"] = min_cursor
            if not cfg.get("descricao"):
                cfg["descricao"] = _CURSOR_DESCRICAO

    # Em fluxo de software, não forçar fase type=prompt (entrega HTML)
    # a menos que o modelo já a tenha criado de propósito.


def _normalize_generated_spec(
    raw: dict[str, Any],
    user_prompt: str,
    structured_requirements: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
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

    structured = structured_requirements
    if structured is None and isinstance(spec.get("structured_requirements"), dict):
        structured = spec.get("structured_requirements")
    if isinstance(structured, dict) and structured:
        spec["structured_requirements"] = normalize_structured_requirements(structured)
    else:
        spec.pop("structured_requirements", None)

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
        "security_guidelines",
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

    # Default: aprovação humana em todas as fases (opt-in no start/UI).
    spec["auto_approve"] = bool(spec.get("auto_approve", False))

    structured_for_warn = spec.get("structured_requirements")
    # Sempre presente (nunca omitir) — checklist (texto e/ou structured) vence.
    spec["warnings"] = normalize_warnings(
        spec.get("warnings"),
        user_clean,
        structured_requirements=structured_for_warn,
    )

    return normalize_spec_phases(spec)


def generate_pipeline_spec(
    user_prompt: str,
    structured_requirements: Optional[dict[str, Any]] = None,
) -> tuple[dict[str, Any], str]:
    structured = None
    if isinstance(structured_requirements, dict) and structured_requirements:
        structured = normalize_structured_requirements(structured_requirements)

    req_block = format_structured_requirements_block(structured)
    prompt = (
        f"{_SYSTEM_INSTRUCTION}\n\nPedido do usuário:\n{user_prompt.strip()}"
    )
    if req_block:
        prompt = f"{prompt}\n\n{req_block}"
        if (
            isinstance(structured, dict)
            and structured.get("perfil_sugerido") == PERFIL_SOFTWARE
            and (structured.get("contexto_de_uso") or {}).get("tipo") == "single_tenant"
        ):
            prompt += (
                "\n\nAo descrever fases (especialmente generate_sdd / prompt_cursor), "
                "respeite single-tenant: não peça multi-tenant, X-Tenant-ID ou "
                "isolamento por schema de tenant."
            )

    raw_text, meta = generate_content(
        prompt,
        enable_google_search=False,
        response_json=True,
        response_schema=SPEC_RESPONSE_SCHEMA,
        temperature=0.2,
    )
    parsed = extract_json_payload(raw_text)
    if not isinstance(parsed, dict):
        raise ValueError("O modelo não retornou um objeto JSON de Pipeline Spec")

    spec = _normalize_generated_spec(
        parsed, user_prompt, structured_requirements=structured
    )
    if not spec.get("phases"):
        raise ValueError("Pipeline Spec gerada sem fases — refine o pedido e tente novamente")
    # Garantia final pós-normalização (normalize_spec_phases não remove warnings).
    if not isinstance(spec.get("warnings"), list):
        spec["warnings"] = normalize_warnings(
            None,
            user_prompt,
            structured_requirements=structured,
        )

    return spec, str(meta.get("model") or "")
