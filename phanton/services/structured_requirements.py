"""Rascunho estruturado de requisitos (ISO/IEC/IEEE 29148, simplificado)."""

from __future__ import annotations

import json
from typing import Any, Optional

from services.llm.json_utils import extract_json_payload
from services.llm.runtime import generate_content

PERFIL_SOFTWARE = "software_saas"
PERFIL_ARTEFATO = "artefato"
CONTEXTO_TIPOS = frozenset({"single_tenant", "multi_tenant", "indefinido"})

_STAKEHOLDER_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "papel": {"type": "STRING"},
        "descricao": {"type": "STRING"},
    },
    "required": ["papel", "descricao"],
}

_CONTEXTO_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "tipo": {"type": "STRING"},
        "justificativa": {"type": "STRING"},
    },
    "required": ["tipo", "justificativa"],
}

STRUCTURED_REQUIREMENTS_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "perfil_sugerido": {"type": "STRING"},
        "proposito_escopo": {"type": "STRING"},
        "contexto_de_uso": _CONTEXTO_SCHEMA,
        "partes_interessadas": {
            "type": "ARRAY",
            "items": _STAKEHOLDER_SCHEMA,
        },
        "requisitos_funcionais": {
            "type": "ARRAY",
            "items": {"type": "STRING"},
        },
        "requisitos_nao_funcionais": {
            "type": "ARRAY",
            "items": {"type": "STRING"},
        },
        "restricoes_premissas": {
            "type": "ARRAY",
            "items": {"type": "STRING"},
        },
        "interfaces_integracoes": {
            "type": "ARRAY",
            "items": {"type": "STRING"},
        },
    },
    "required": [
        "perfil_sugerido",
        "proposito_escopo",
        "contexto_de_uso",
        "partes_interessadas",
        "requisitos_funcionais",
        "requisitos_nao_funcionais",
        "restricoes_premissas",
        "interfaces_integracoes",
    ],
}


_DRAFT_PROMPT = """
Atue como analista de requisitos (ISO/IEC/IEEE 29148, forma simplificada).
A partir do pedido em linguagem natural, produza um rascunho estruturado.

Regras:
1. perfil_sugerido:
   - "software_saas" se o pedido for construir software/sistema/plataforma/SaaS/API
   - "artefato" se for entrega única (HTML, slides, documento, playbook, protótipo visual)
     SEM implementação de software
2. contexto_de_uso.tipo:
   - "single_tenant" só se o texto deixar claro uso interno / uma organização
   - "multi_tenant" só se deixar claro produto para várias empresas/clientes
   - "indefinido" se houver ambiguidade (ex.: "da empresa" sem dizer se é SaaS multi-cliente)
3. Não invente decisões que o texto não suporte. Prefira listas curtas e "indefinido"/[].
4. proposito_escopo: 1–3 frases objetivas.
5. partes_interessadas / requisitos_* / restricoes / interfaces: arrays (podem ser vazios).

Pedido do usuário:
""".strip()


def _as_str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        text = str(item or "").strip()
        if text:
            out.append(text)
    return out


def _normalize_contexto(raw: Any) -> dict[str, str]:
    data = raw if isinstance(raw, dict) else {}
    tipo = str(data.get("tipo") or "indefinido").strip().lower().replace("-", "_")
    if tipo in ("singletenant", "single"):
        tipo = "single_tenant"
    elif tipo in ("multitenant", "multi"):
        tipo = "multi_tenant"
    elif tipo not in CONTEXTO_TIPOS:
        tipo = "indefinido"
    just = str(data.get("justificativa") or "").strip()
    if not just:
        just = (
            "Não foi possível inferir single vs multi-tenant a partir do pedido."
            if tipo == "indefinido"
            else f"Inferido como {tipo} a partir do pedido."
        )
    return {"tipo": tipo, "justificativa": just}


def _normalize_stakeholders(raw: Any) -> list[dict[str, str]]:
    if not isinstance(raw, list):
        return []
    out: list[dict[str, str]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        papel = str(item.get("papel") or "").strip()
        desc = str(item.get("descricao") or "").strip()
        if papel or desc:
            out.append({"papel": papel or "stakeholder", "descricao": desc})
    return out


def normalize_structured_requirements(raw: Any) -> dict[str, Any]:
    data = raw if isinstance(raw, dict) else {}
    perfil = str(data.get("perfil_sugerido") or "").strip().lower().replace("-", "_")
    if perfil in ("software", "saas", "software_saas", "sistema"):
        perfil = PERFIL_SOFTWARE
    elif perfil in ("artefato", "artifact", "html", "documento", "apresentacao"):
        perfil = PERFIL_ARTEFATO
    else:
        # fallback leve: se veio sem perfil, assume software se houver RF
        perfil = (
            PERFIL_SOFTWARE
            if _as_str_list(data.get("requisitos_funcionais"))
            else PERFIL_ARTEFATO
        )

    return {
        "perfil_sugerido": perfil,
        "proposito_escopo": str(data.get("proposito_escopo") or "").strip(),
        "contexto_de_uso": _normalize_contexto(data.get("contexto_de_uso")),
        "partes_interessadas": _normalize_stakeholders(data.get("partes_interessadas")),
        "requisitos_funcionais": _as_str_list(data.get("requisitos_funcionais")),
        "requisitos_nao_funcionais": _as_str_list(data.get("requisitos_nao_funcionais")),
        "restricoes_premissas": _as_str_list(data.get("restricoes_premissas")),
        "interfaces_integracoes": _as_str_list(data.get("interfaces_integracoes")),
    }


def empty_structured_requirements(*, perfil: str = PERFIL_ARTEFATO) -> dict[str, Any]:
    return normalize_structured_requirements(
        {
            "perfil_sugerido": perfil,
            "proposito_escopo": "",
            "contexto_de_uso": {"tipo": "indefinido", "justificativa": ""},
            "partes_interessadas": [],
            "requisitos_funcionais": [],
            "requisitos_nao_funcionais": [],
            "restricoes_premissas": [],
            "interfaces_integracoes": [],
        }
    )


def draft_structured_requirements(user_prompt: str) -> tuple[dict[str, Any], str]:
    """Gera rascunho estruturado via Gemini (response_schema)."""
    prompt = f"{_DRAFT_PROMPT}\n{(user_prompt or '').strip()}"
    raw_text, meta = generate_content(
        prompt,
        enable_google_search=False,
        response_json=True,
        response_schema=STRUCTURED_REQUIREMENTS_SCHEMA,
        temperature=0.2,
        max_output_tokens=4096,
    )
    parsed = extract_json_payload(raw_text)
    if not isinstance(parsed, dict):
        raise ValueError("O modelo não retornou requisitos estruturados válidos")
    return normalize_structured_requirements(parsed), str(meta.get("model") or "")


def format_structured_requirements_block(
    structured: Optional[dict[str, Any]],
) -> str:
    """Bloco de texto para injetar em prompts de Spec/PRD/SDD."""
    if not isinstance(structured, dict) or not structured:
        return ""
    data = normalize_structured_requirements(structured)
    if data.get("perfil_sugerido") != PERFIL_SOFTWARE:
        return ""

    ctx = data.get("contexto_de_uso") or {}
    tipo = ctx.get("tipo") or "indefinido"
    lines = [
        "=== Requisitos estruturados (confirmados / revisados pelo humano) ===",
        f"Perfil: {data.get('perfil_sugerido')}",
        f"Propósito/escopo: {data.get('proposito_escopo') or '(vazio)'}",
        f"Contexto de uso: {tipo}",
        f"Justificativa: {ctx.get('justificativa') or '(vazia)'}",
    ]
    if tipo == "single_tenant":
        lines.append(
            "OBRIGATÓRIO: arquitetura SINGLE-TENANT (uma organização). "
            "NÃO proponha multi-tenant, isolamento por tenant/schema, header "
            "X-Tenant-ID, nem Keycloak multi-realm por cliente, a menos que "
            "outro requisito explícito peça isso."
        )
    elif tipo == "multi_tenant":
        lines.append(
            "OBRIGATÓRIO: arquitetura MULTI-TENANT (vários clientes/empresas) "
            "com isolamento adequado entre tenants."
        )
    else:
        lines.append(
            "Contexto de uso INDEFINIDO — não assuma multi-tenant nem "
            "single-tenant sem deixar a ambiguidade explícita."
        )

    def _bullets(title: str, items: list[str]) -> None:
        lines.append(f"{title}:")
        if not items:
            lines.append("- (nenhum)")
        else:
            for item in items:
                lines.append(f"- {item}")

    stakeholders = data.get("partes_interessadas") or []
    lines.append("Partes interessadas:")
    if not stakeholders:
        lines.append("- (nenhuma)")
    else:
        for st in stakeholders:
            lines.append(f"- {st.get('papel')}: {st.get('descricao')}")

    _bullets("Requisitos funcionais", data.get("requisitos_funcionais") or [])
    _bullets("Requisitos não-funcionais", data.get("requisitos_nao_funcionais") or [])
    _bullets("Restrições/premissas", data.get("restricoes_premissas") or [])
    _bullets("Interfaces/integrações", data.get("interfaces_integracoes") or [])
    return "\n".join(lines)


def structured_requirements_json(structured: Optional[dict[str, Any]]) -> str:
    if not isinstance(structured, dict):
        return ""
    return json.dumps(
        normalize_structured_requirements(structured),
        ensure_ascii=False,
        indent=2,
    )
