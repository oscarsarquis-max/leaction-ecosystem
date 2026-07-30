"""Validação determinística de consistência de contexto (single vs multi-tenant)."""

from __future__ import annotations

import re
from typing import Any, Optional

from services.llm.json_utils import extract_json_payload
from services.llm.runtime import generate_content
from services.structured_requirements import normalize_structured_requirements

# Termos proibidos quando contexto_de_uso.tipo == single_tenant.
# (lista configurável — expandir conforme regressões reais)
SINGLE_TENANT_FORBIDDEN_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("tenant", re.compile(r"\btenants?\b", re.I)),
    ("multi-tenant", re.compile(r"\bmulti[\s-]?tenants?\b", re.I)),
    ("multitenant", re.compile(r"\bmultitenants?\b", re.I)),
    ("por organização", re.compile(r"\bpor\s+organiza[cç][aã]o\b", re.I)),
    (
        "sua própria organização",
        re.compile(r"\bsua\s+pr[oó]pria\s+organiza[cç][aã]o\b", re.I),
    ),
    ("várias empresas", re.compile(r"\bv[aá]rias?\s+empresas?\b", re.I)),
    ("vários clientes", re.compile(r"\bv[aá]rios?\s+clientes?\b", re.I)),
    ("múltiplos clientes", re.compile(r"\bm[uú]ltiplos?\s+clientes?\b", re.I)),
    ("isolamento por tenant", re.compile(r"\bisolamento\s+por\s+tenant\b", re.I)),
    ("schema por tenant", re.compile(r"\bschema\s+por\s+tenant\b", re.I)),
    ("X-Tenant-ID", re.compile(r"\bx[\s-]?tenant[\s-]?id\b", re.I)),
    ("cross-tenant", re.compile(r"\bcross[\s-]?tenant\b", re.I)),
]


def contexto_tipo_from_spec(spec: Any) -> str:
    if not isinstance(spec, dict):
        return "indefinido"
    raw = spec.get("structured_requirements")
    if not isinstance(raw, dict):
        return "indefinido"
    data = normalize_structured_requirements(raw)
    ctx = data.get("contexto_de_uso") or {}
    return str(ctx.get("tipo") or "indefinido").strip().lower()


def _join_texts(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "\n".join(_join_texts(v) for v in value)
    if isinstance(value, dict):
        return "\n".join(f"{k}: {_join_texts(v)}" for k, v in value.items())
    return str(value)


def find_forbidden_terms(text: str, *, contexto_tipo: str) -> list[str]:
    """Retorna labels dos termos proibidos encontrados no texto."""
    if (contexto_tipo or "").strip().lower() != "single_tenant":
        return []
    blob = text or ""
    found: list[str] = []
    for label, pattern in SINGLE_TENANT_FORBIDDEN_PATTERNS:
        if pattern.search(blob):
            found.append(label)
    return found


def validar_consistencia_contexto(
    textos_por_modulo: dict[str, Any],
    contexto_de_uso: Any,
) -> list[dict[str, Any]]:
    """
    textos_por_modulo: { modulo: str | list[str] | dict }
    contexto_de_uso: dict com tipo, ou string tipo, ou None
    Retorna lista de {modulo, termos, trecho}.
    """
    if isinstance(contexto_de_uso, dict):
        tipo = str(contexto_de_uso.get("tipo") or "indefinido").strip().lower()
    else:
        tipo = str(contexto_de_uso or "indefinido").strip().lower()

    if tipo != "single_tenant":
        return []

    problemas: list[dict[str, Any]] = []
    for modulo, raw in (textos_por_modulo or {}).items():
        text = _join_texts(raw)
        termos = find_forbidden_terms(text, contexto_tipo=tipo)
        if termos:
            problemas.append(
                {
                    "modulo": str(modulo),
                    "termos": termos,
                    "trecho": text[:240].replace("\n", " "),
                }
            )
    return problemas


def regenerar_diretrizes_modulo_single_tenant(
    *,
    modulo: str,
    escopo: str,
    termos_problema: list[str],
    domain_id: str,
    standards: list[str],
) -> list[str]:
    """Chamada pontual: regenera diretrizes de UM módulo sem linguagem multi-tenant."""
    termos = ", ".join(termos_problema) or "tenant"
    prompt = f"""
Atue como arquiteto AppSec. O sistema é SINGLE-TENANT (uma única organização).

Regenere APENAS as diretrizes de segurança do módulo `{modulo}`.
Escopo do módulo: {escopo or "(não informado)"}
Domínio: {domain_id}
Standards: {standards}

PROIBIDO usar qualquer um destes termos/conceitos: {termos}, multi-tenant,
isolamento por organização, X-Tenant-ID, schema por tenant, cross-tenant.

Em single-tenant, fale em autorização por papel/usuário DENTRO da mesma
organização, não em isolamento entre empresas/tenants.

Responda APENAS JSON:
{{"diretrizes": ["...","...","..."]}}
""".strip()
    raw_text, _meta = generate_content(
        prompt,
        enable_google_search=False,
        response_json=True,
        temperature=0.15,
        max_output_tokens=2048,
    )
    parsed = extract_json_payload(raw_text)
    if not isinstance(parsed, dict):
        raise ValueError("regen módulo: JSON inválido")
    items = parsed.get("diretrizes") or parsed.get("diretrizes_por_modulo") or []
    if isinstance(items, dict):
        items = items.get(modulo) or next(iter(items.values()), [])
    if not isinstance(items, list) or not items:
        raise ValueError("regen módulo: diretrizes vazias")
    cleaned = [str(x).strip() for x in items if str(x).strip()]
    still = find_forbidden_terms("\n".join(cleaned), contexto_tipo="single_tenant")
    if still:
        raise ValueError(f"regen módulo ainda contém: {', '.join(still)}")
    return cleaned


def regenerar_prompt_modulo_single_tenant(
    *,
    modulo: str,
    escopo: str,
    prompt_atual: str,
    termos_problema: list[str],
    testes_requeridos: list[str],
) -> dict[str, Any]:
    """Regenera prompt + testes de um módulo sem vazamento multi-tenant."""
    termos = ", ".join(termos_problema) or "tenant"
    testes_hint = "\n".join(f"- {t}" for t in testes_requeridos) or "- (derive do escopo)"
    prompt = f"""
Reescreva o prompt de implementação do módulo `{modulo}` para qualquer IDE
com agente de código (texto neutro — sem citar Cursor, Copilot, Windsurf, etc.).
O sistema é SINGLE-TENANT (uma única organização).

Escopo: {escopo or "(não informado)"}
Termos PROIBIDOS no texto: {termos}, multi-tenant, X-Tenant-ID, schema por tenant,
"sua própria organização" (no sentido multi-empresa).

Prompt atual (corrigir):
---
{prompt_atual[:6000]}
---

Testes já desejados (mantenha ou refine, sem termos proibidos):
{testes_hint}

Responda APENAS JSON:
{{
  "prompt": "texto do prompt sem seção ## Testes (será anexada depois)",
  "testes_requeridos": ["teste específico 1", "teste específico 2"]
}}
testes_requeridos DEVE ter pelo menos 2 itens concretos (não genéricos).
""".strip()
    raw_text, _meta = generate_content(
        prompt,
        enable_google_search=False,
        response_json=True,
        temperature=0.15,
        max_output_tokens=3072,
    )
    parsed = extract_json_payload(raw_text)
    if not isinstance(parsed, dict):
        raise ValueError("regen prompt: JSON inválido")
    new_prompt = str(parsed.get("prompt") or "").strip()
    testes = parsed.get("testes_requeridos") or []
    if isinstance(testes, str):
        testes = [testes]
    testes = [str(t).strip() for t in testes if str(t).strip()]
    if not new_prompt:
        raise ValueError("regen prompt: prompt vazio")
    if len(testes) < 1:
        raise ValueError("regen prompt: testes_requeridos vazio")
    blob = new_prompt + "\n" + "\n".join(testes)
    still = find_forbidden_terms(blob, contexto_tipo="single_tenant")
    if still:
        raise ValueError(f"regen prompt ainda contém: {', '.join(still)}")
    return {"prompt": new_prompt, "testes_requeridos": testes}


def enforce_security_context_consistency(
    payload: dict[str, Any],
    spec: dict[str, Any],
    *,
    build_order: Optional[list[dict[str, Any]]] = None,
    domain_id: str = "financeiro",
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """
    Valida diretrizes_por_modulo (+ gerais). Regenera módulos problemáticos 1x.
    Retorna (payload_atualizado, avisos_persistentes).
    """
    tipo = contexto_tipo_from_spec(spec)
    if tipo != "single_tenant":
        return payload, []

    data = dict(payload)
    por_mod = dict(data.get("diretrizes_por_modulo") or {})
    gerais = data.get("diretrizes_gerais") or []
    standards = data.get("standards_aplicados") or []

    # Também checa gerais (como módulo sintético)
    textos = {**por_mod, "__gerais__": gerais}
    problemas = validar_consistencia_contexto(textos, {"tipo": tipo})
    avisos: list[dict[str, Any]] = []
    escopo_by_mod = {
        (e.get("modulo") or ""): (e.get("escopo") or "")
        for e in (build_order or [])
        if isinstance(e, dict)
    }

    for prob in problemas:
        modulo = prob["modulo"]
        termos = prob.get("termos") or []
        if modulo == "__gerais__":
            # limpa gerais com filtro simples (sem LLM) — remove linhas ofensoras
            cleaned = []
            for line in gerais:
                if not find_forbidden_terms(str(line), contexto_tipo=tipo):
                    cleaned.append(line)
            if cleaned:
                data["diretrizes_gerais"] = cleaned
                gerais = cleaned
            else:
                avisos.append(
                    {
                        "modulo": "diretrizes_gerais",
                        "termos": termos,
                        "mensagem": (
                            "possível inconsistência de contexto — revisar "
                            "manualmente (diretrizes gerais)"
                        ),
                    }
                )
            continue

        try:
            new_items = regenerar_diretrizes_modulo_single_tenant(
                modulo=modulo,
                escopo=escopo_by_mod.get(modulo, ""),
                termos_problema=termos,
                domain_id=domain_id,
                standards=[str(s) for s in standards],
            )
            por_mod[modulo] = new_items
        except Exception as exc:
            avisos.append(
                {
                    "modulo": modulo,
                    "termos": termos,
                    "mensagem": (
                        "possível inconsistência de contexto — revisar "
                        f"manualmente ({exc})"
                    ),
                }
            )

    data["diretrizes_por_modulo"] = por_mod
    # revalida
    restantes = validar_consistencia_contexto(
        {**por_mod, "__gerais__": data.get("diretrizes_gerais") or []},
        {"tipo": tipo},
    )
    for prob in restantes:
        mod = prob["modulo"]
        if mod == "__gerais__":
            mod = "diretrizes_gerais"
        if not any(a.get("modulo") == mod for a in avisos):
            avisos.append(
                {
                    "modulo": mod,
                    "termos": prob.get("termos") or [],
                    "mensagem": (
                        "possível inconsistência de contexto — revisar manualmente"
                    ),
                }
            )
    if avisos:
        data["context_consistency_warnings"] = avisos
    else:
        data.pop("context_consistency_warnings", None)
    return data, avisos
