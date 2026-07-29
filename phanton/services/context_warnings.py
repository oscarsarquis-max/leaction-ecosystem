"""Lacunas de contexto crítico no pedido → warnings[] no Spec (não bloqueia)."""

from __future__ import annotations

import re
from typing import Any, Optional

# Campos canônicos do checklist (genérico).
CAMPO_CONTEXTO_USO = "contexto_de_uso"
CAMPO_ESCALA = "escala_esperada"
CAMPO_DEPLOY = "ambiente_de_deploy"
CAMPO_INTEGRACOES = "integracoes_nomeadas"
CAMPO_REGULATORIO = "escopo_regulatorio"

CRITICAL_CAMPOS: frozenset[str] = frozenset(
    {
        CAMPO_CONTEXTO_USO,
        CAMPO_ESCALA,
        CAMPO_DEPLOY,
        CAMPO_INTEGRACOES,
        CAMPO_REGULATORIO,
    }
)

_WARNING_CATALOG: dict[str, dict[str, str]] = {
    CAMPO_CONTEXTO_USO: {
        "descricao": (
            "Não ficou claro se é uso interno (single-tenant) ou produto "
            "multi-tenant (SaaS) para várias empresas."
        ),
        "impacto": (
            "PRD/SDD podem assumir arquitetura multi-tenant desnecessária "
            "(ou sub-dimensionar isolamento se for multi-tenant de verdade)."
        ),
    },
    CAMPO_ESCALA: {
        "descricao": (
            "Não há indicação de escala esperada (dezenas vs milhares vs milhões "
            "de usuários/transações/dados)."
        ),
        "impacto": (
            "Arquitetura e stack podem ser sub ou superdimensionadas sem uma "
            "direção de volume."
        ),
    },
    CAMPO_DEPLOY: {
        "descricao": (
            "Não ficou claro o ambiente de deploy (cloud própria, on-prem, "
            "SaaS de terceiro)."
        ),
        "impacto": (
            "Decisões de infraestrutura, rede e compliance de hospedagem podem "
            "divergir do que o cliente realmente pode operar."
        ),
    },
    CAMPO_INTEGRACOES: {
        "descricao": (
            "O pedido cita banco/API bancária de forma genérica, sem nomear "
            "instituição, PSP ou padrão de integração específico."
        ),
        "impacto": (
            "SDD/prompt podem inventar um conector genérico incompatível com o "
            "parceiro ou Open Finance real a integrar."
        ),
    },
    CAMPO_REGULATORIO: {
        "descricao": (
            "Além do que foi citado, pode haver jurisdição/norma adicional "
            "relevante ao domínio que não foi mencionada."
        ),
        "impacto": (
            "security_guidelines e o desenho podem omitir controles obrigatórios "
            "para o mercado-alvo (ex.: Bacen, HIPAA, SOX)."
        ),
    },
}

# --- Detecção: contexto JÁ claro (não emitir warning) ---

_RE_MULTI_TENANT = re.compile(
    r"\b("
    r"multi[\s-]?tenant|multitenant|v[aá]rios?\s+clientes|v[aá]rias?\s+empresas|"
    r"m[uú]ltiplos?\s+clientes|m[uú]ltiplas?\s+empresas|saas\s+para\s+vender|"
    r"produto\s+para\s+vender|white[\s-]?label|por\s+tenant"
    r")\b",
    re.I,
)

_RE_SINGLE_TENANT = re.compile(
    r"\b("
    r"single[\s-]?tenant|singletenant|uso\s+interno|"
    r"[uú]nica\s+empresa|[uú]nica\s+organiza[cç][aã]o|"
    r"uma\s+(s[oó]\s+)?empresa|n[aã]o\s+[eé]\s+produto\s+para\s+vender|"
    r"interno\s+da\s+empresa|s[oó]\s+(para\s+)?(a\s+)?(nossa|minha)\s+empresa|"
    r"monolocadora[rã]io|um\s+s[oó]\s+cliente\s+interno"
    r")\b",
    re.I,
)

_RE_SCALE = re.compile(
    r"\b("
    r"dezenas?|centenas?|milhares?|milh[oõ]es?|bilh[oõ]es?|"
    r"\d+\s*(usu[aá]rios?|users?|transações|transacoes|req(uisições)?/s|"
    r"tps|qps|tenants?)"
    r"|escala\s+(pequena|m[eé]dia|grande|enterprise)"
    r"|alto\s+volume|baixo\s+volume|piloto|poc\b"
    r")\b",
    re.I,
)

_RE_DEPLOY = re.compile(
    r"\b("
    r"aws|azure|gcp|google\s+cloud|on[\s-]?prem(ise)?|onprem|"
    r"kubernetes|k8s|ecs|eks|cloud\s+pr[oó]pria|nuvem\s+pr[oó]pria|"
    r"datacenter|data\s+center|heroku|vercel|cloud\s+p[uú]blica|"
    r"self[\s-]?hosted|hospedagem\s+pr[oó]pria|saas\s+de\s+terceiro"
    r")\b",
    re.I,
)

_RE_GENERIC_BANK = re.compile(
    r"\b("
    r"banco|banc[aá]ri[oa]|open[\s-]?finance|open[\s-]?banking|"
    r"api\s+banc[aá]ria|conta\s+corrente|extrato|psp|adquirente|"
    r"pagamento|pix\b|integra[cç][aã]o\s+banc"
    r")\b",
    re.I,
)

_RE_NAMED_INTEGRATION = re.compile(
    r"\b("
    r"pluggy|belvo|stripe|adyen|pagseguro|pagarme|mercadopago|"
    r"stone|cielo|rede|getnet|asaas|iugu|juno|efi\b|gerencianet|"
    r"banco\s+do\s+brasil|bradesco|ita[uú]|santander|nubank|inter\b|"
    r"c6\s+bank|btg|xp\s+investimentos|sicoob|sicredi|"
    r"fapi\s*2(\.0)?|open\s+finance\s+brasil"
    r")\b",
    re.I,
)

_RE_REGULATORY_MENTIONED = re.compile(
    r"\b("
    r"lgpd|gdpr|hipaa|pci[\s-]?dss|sox|bacen|banco\s+central|"
    r"open\s+finance|fapi|asvs|owasp|sox|soc\s*2|iso\s*27001|"
    r"cf\s*m|anvisa|cvm\b"
    r")\b",
    re.I,
)

_RE_SENSITIVE_DOMAIN = re.compile(
    r"\b("
    r"financeiro|fintech|sa[uú]de|hospital|cl[ií]nica|pagamento|banc|"
    r"open\s+finance|prontu[aá]rio"
    r")\b",
    re.I,
)


def _entry(campo: str) -> dict[str, str]:
    cat = _WARNING_CATALOG[campo]
    return {
        "campo": campo,
        "descricao": cat["descricao"],
        "impacto": cat["impacto"],
    }


def _has_uso_contexto_claro(text: str) -> bool:
    return bool(_RE_MULTI_TENANT.search(text) or _RE_SINGLE_TENANT.search(text))


def _has_escala_clara(text: str) -> bool:
    return bool(_RE_SCALE.search(text))


def _has_deploy_claro(text: str) -> bool:
    return bool(_RE_DEPLOY.search(text))


def _needs_integracao_warning(text: str) -> bool:
    if not _RE_GENERIC_BANK.search(text):
        return False
    return not bool(_RE_NAMED_INTEGRATION.search(text))


def _needs_regulatorio_warning(text: str) -> bool:
    """Só sinaliza se domínio parece regulado e a norma/jurisdição ficou vaga."""
    if not _RE_SENSITIVE_DOMAIN.search(text):
        return False
    # Mencionar só LGPD de passagem ainda deixa jurisdição/setor incompletos
    # se for financeiro sem Bacen/Open Finance/FAPI — mas LGPD sozinho conta
    # como "algo citado". Warning quando NÃO há nenhuma menção regulatória.
    return not bool(_RE_REGULATORY_MENTIONED.search(text))


def _blob_from_structured(structured: dict[str, Any]) -> str:
    """Texto agregado dos campos estruturados para checagens de escala/deploy/etc."""
    parts: list[str] = []
    for key in (
        "proposito_escopo",
        "requisitos_funcionais",
        "requisitos_nao_funcionais",
        "restricoes_premissas",
        "interfaces_integracoes",
    ):
        val = structured.get(key)
        if isinstance(val, list):
            parts.extend(str(x) for x in val)
        elif val:
            parts.append(str(val))
    ctx = structured.get("contexto_de_uso")
    if isinstance(ctx, dict):
        parts.append(str(ctx.get("justificativa") or ""))
        parts.append(str(ctx.get("tipo") or ""))
    return "\n".join(parts)


def detect_context_warnings(
    user_prompt: str,
    structured_requirements: Any = None,
) -> list[dict[str, str]]:
    """Checklist fixo: prefer structured_requirements quando presente."""
    text = (user_prompt or "").strip()
    structured = (
        structured_requirements
        if isinstance(structured_requirements, dict)
        else None
    )

    if structured and structured.get("perfil_sugerido") == "software_saas":
        warnings: list[dict[str, str]] = []
        ctx = structured.get("contexto_de_uso")
        tipo = ""
        if isinstance(ctx, dict):
            tipo = str(ctx.get("tipo") or "").strip().lower()
        if tipo in ("", "indefinido"):
            warnings.append(_entry(CAMPO_CONTEXTO_USO))

        blob = f"{text}\n{_blob_from_structured(structured)}"
        if not _has_escala_clara(blob):
            warnings.append(_entry(CAMPO_ESCALA))
        if not _has_deploy_claro(blob):
            warnings.append(_entry(CAMPO_DEPLOY))
        if _needs_integracao_warning(blob):
            warnings.append(_entry(CAMPO_INTEGRACOES))
        if _needs_regulatorio_warning(blob):
            warnings.append(_entry(CAMPO_REGULATORIO))
        return warnings

    if not text:
        return [_entry(c) for c in (
            CAMPO_CONTEXTO_USO,
            CAMPO_ESCALA,
            CAMPO_DEPLOY,
        )]

    warnings = []
    if not _has_uso_contexto_claro(text):
        warnings.append(_entry(CAMPO_CONTEXTO_USO))
    if not _has_escala_clara(text):
        warnings.append(_entry(CAMPO_ESCALA))
    if not _has_deploy_claro(text):
        warnings.append(_entry(CAMPO_DEPLOY))
    if _needs_integracao_warning(text):
        warnings.append(_entry(CAMPO_INTEGRACOES))
    if _needs_regulatorio_warning(text):
        warnings.append(_entry(CAMPO_REGULATORIO))
    return warnings


def _coerce_warning_item(raw: Any) -> Optional[dict[str, str]]:
    if not isinstance(raw, dict):
        return None
    campo = str(raw.get("campo") or "").strip()
    if not campo:
        return None
    descricao = str(raw.get("descricao") or "").strip()
    impacto = str(raw.get("impacto") or "").strip()
    if campo in _WARNING_CATALOG:
        cat = _WARNING_CATALOG[campo]
        descricao = descricao or cat["descricao"]
        impacto = impacto or cat["impacto"]
    if not descricao:
        return None
    return {"campo": campo, "descricao": descricao, "impacto": impacto or ""}


def normalize_warnings(
    raw_warnings: Any,
    user_prompt: str,
    structured_requirements: Any = None,
) -> list[dict[str, str]]:
    """Garante warnings[] sempre lista; checklist crítico vence sobre o LLM."""
    heuristic = {
        w["campo"]: w
        for w in detect_context_warnings(
            user_prompt,
            structured_requirements=structured_requirements,
        )
    }
    llm_items: list[dict[str, str]] = []
    if isinstance(raw_warnings, list):
        for item in raw_warnings:
            coerced = _coerce_warning_item(item)
            if coerced:
                llm_items.append(coerced)

    # Extras do LLM fora do checklist crítico
    extras = {
        w["campo"]: w
        for w in llm_items
        if w["campo"] not in CRITICAL_CAMPOS
    }

    # Checklist: heurística é autoridade (evita falso positivo/negativo do LLM)
    ordered_campos = [
        CAMPO_CONTEXTO_USO,
        CAMPO_ESCALA,
        CAMPO_DEPLOY,
        CAMPO_INTEGRACOES,
        CAMPO_REGULATORIO,
    ]
    result: list[dict[str, str]] = []
    for campo in ordered_campos:
        if campo in heuristic:
            result.append(heuristic[campo])
    for campo, item in extras.items():
        result.append(item)
    return result
