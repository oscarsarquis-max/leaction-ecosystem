"""Classificação de domínio sensível + perfis de standards de mercado."""

from __future__ import annotations

import re
from typing import Any, Optional

# Domínios iniciais (extensível). Valor = id estável usado nos perfis.
_DOMAIN_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "financeiro",
        re.compile(
            r"\b("
            r"financeiro|fintech|pagamento|pagamentos|pix|open[\s-]?finance|"
            r"open[\s-]?banking|ledger|cont[aá]bil|banco|banking|cobran[cç]a|"
            r"cart[aã]o|credit|d[eé]bito|reconcili?a[cç][aã]o|tesouraria|"
            r"wallet|carteira digital|psp|adquir[eê]ncia"
            r")\b",
            re.I,
        ),
    ),
    (
        "saude",
        re.compile(
            r"\b("
            r"sa[uú]de|health|hipaa|prontu[aá]rio|hospital|cl[ií]nica|"
            r"telemedicina|paciente|farmac[eê]utic|hl7|fhir|"
            r"dados de sa[uú]de|e[\s-]?sa[uú]de"
            r")\b",
            re.I,
        ),
    ),
]

# Standards reais por domínio (pesquisa de mercado — não inventar nomes).
DOMAIN_STANDARDS: dict[str, list[str]] = {
    "financeiro": [
        "OWASP ASVS 5.0 (Level 3)",
        "FAPI 2.0",
        "OWASP API Security Top 10",
        "LGPD",
    ],
    "saude": [
        "OWASP ASVS 5.0 (Level 3)",
        "OWASP API Security Top 10",
        "LGPD",
        "Controles de privacidade para dados de saúde (mínimo necessário)",
    ],
}

# Diretrizes gerais curadas (citando capítulos/controles reais).
DOMAIN_GENERAL_GUIDELINES: dict[str, list[str]] = {
    "financeiro": [
        "Criptografia em repouso e em trânsito para todo dado financeiro (ASVS V6/V9)",
        "Nenhum segredo em código/config versionada; secrets management dedicado (ASVS V3)",
        "Log estruturado de toda operação sensível, sem PII em texto claro (ASVS V7, LGPD)",
        "Rate limiting e autenticação forte em toda API exposta (OWASP API Security Top 10)",
        "Open Finance/Open Banking: aderir a FAPI 2.0 (PAR, PKCE, token sender-constrained)",
    ],
    "saude": [
        "Criptografia em repouso e em trânsito para dados de saúde (ASVS V6/V9)",
        "Controle de acesso por papel e consentimento antes de qualquer leitura clínica (ASVS V4, LGPD)",
        "Log de acesso a prontuário/dados sensíveis sem expor PII em claro (ASVS V7)",
        "Rate limiting e autenticação forte em APIs clínicas (OWASP API Security Top 10)",
        "Princípio do mínimo necessário e retenção limitada (LGPD)",
    ],
}


def classify_sensitive_domain(text: str) -> Optional[str]:
    """Retorna id do domínio sensível ou None se genérico."""
    blob = (text or "").strip()
    if not blob:
        return None
    for domain_id, pattern in _DOMAIN_PATTERNS:
        if pattern.search(blob):
            return domain_id
    return None


def is_sensitive_domain(text: str) -> bool:
    return classify_sensitive_domain(text) is not None


def standards_for_domain(domain_id: Optional[str]) -> list[str]:
    if not domain_id:
        return []
    return list(DOMAIN_STANDARDS.get(domain_id) or [])


def general_guidelines_for_domain(domain_id: Optional[str]) -> list[str]:
    if not domain_id:
        return []
    return list(DOMAIN_GENERAL_GUIDELINES.get(domain_id) or [])


def module_guidelines_hint(domain_id: Optional[str], modulo: str, escopo: str = "") -> list[str]:
    """Heurística curada por domínio + nome/escopo do módulo (fallback sem LLM)."""
    mod = (modulo or "").lower()
    esc = (escopo or "").lower()
    blob = f"{mod} {esc}"

    if domain_id == "financeiro":
        if "ledger" in blob or "razão" in blob or "razao" in blob:
            return [
                "Controle de acesso por role antes de qualquer escrita (ASVS V4)",
                "Nenhuma escrita fora de transação ACID",
                "Trilha de auditoria imutável separada do dado operacional (ASVS V7)",
            ]
        if "bank" in blob or "pix" in blob or "open finance" in blob or "open-finance" in blob:
            return [
                "FAPI 2.0 obrigatório: PAR + PKCE + token sender-constrained (mTLS ou DPoP)",
                "Validação e expiração curta de todo token de acesso a Open Finance/PIX",
                "Nenhum dado de consentimento armazenado além do necessário (LGPD)",
            ]
        if "schedul" in blob or "agenda" in blob or "pagamento" in blob:
            return [
                "Idempotency key obrigatória em toda execução de pagamento (evita replay)",
                "Autorização explícita antes de qualquer alteração de agenda recorrente (ASVS V4)",
            ]
        if "reconcil" in blob or "extrato" in blob:
            return [
                "Nenhuma divergência resolvida automaticamente sem trilha auditável (ASVS V7)",
                "Validação de origem do extrato importado antes de processar",
            ]
        if "notif" in blob or "alert" in blob:
            return [
                "Nenhum dado financeiro sensível no corpo de notificação push/e-mail "
                "(evitar exposição excessiva — OWASP API Security Top 10)",
            ]
        return [
            "Autorização explícita em toda operação que altere saldo ou obrigação (ASVS V4)",
            "Auditoria completa sem PII em claro (ASVS V7, LGPD)",
            "Proteção contra abuso de API (rate limit, authn/authz — OWASP API Top 10)",
        ]

    if domain_id == "saude":
        return [
            "Autorização por papel/consentimento antes de ler ou alterar dados clínicos (ASVS V4)",
            "Mascaramento/minimização de PII em logs e notificações (LGPD, ASVS V7)",
            "Proteção de APIs clínicas (authn forte + rate limit — OWASP API Top 10)",
        ]

    return [
        "Aplicar controles ASVS Level 3 relevantes ao módulo",
        "Autenticação/autorização e rate limiting em interfaces expostas (OWASP API Top 10)",
        "Privacidade e minimização de dados (LGPD)",
    ]


def extract_security_artifact(inputs: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Procura artefato security_guidelines nos depends_on."""
    for payload in (inputs or {}).values():
        if not isinstance(payload, dict):
            continue
        if payload.get("standards_aplicados") or payload.get("diretrizes_gerais"):
            return payload
        nested = payload.get("artifact_data")
        if isinstance(nested, dict) and (
            nested.get("standards_aplicados") or nested.get("diretrizes_gerais")
        ):
            return nested
    return None


def format_security_section(
    security: dict[str, Any],
    *,
    modulo: Optional[str] = None,
) -> str:
    """Monta bloco Markdown de segurança para anexar ao prompt."""
    if not isinstance(security, dict):
        return ""
    standards = security.get("standards_aplicados") or []
    if isinstance(standards, str):
        standards = [standards]
    gerais = security.get("diretrizes_gerais") or []
    por_mod = security.get("diretrizes_por_modulo") or {}
    if not isinstance(por_mod, dict):
        por_mod = {}

    lines: list[str] = []
    std_label = ", ".join(str(s) for s in standards if str(s).strip()) or "padrões do domínio"
    lines.append(f"## Segurança (padrão: {std_label})")
    for item in gerais:
        text = str(item).strip()
        if text:
            lines.append(f"- {text}")
    if modulo:
        # match case-insensitive
        mod_items = None
        for key, value in por_mod.items():
            if str(key).lower() == str(modulo).lower():
                mod_items = value
                break
        if isinstance(mod_items, list):
            for item in mod_items:
                text = str(item).strip()
                if text:
                    lines.append(f"- {text}")
    if len(lines) <= 1:
        return ""
    return "\n".join(lines)


def append_security_section(
    prompt: str,
    security: Optional[dict[str, Any]],
    *,
    modulo: Optional[str] = None,
) -> str:
    if not security:
        return prompt or ""
    section = format_security_section(security, modulo=modulo)
    if not section:
        return prompt or ""
    base = (prompt or "").rstrip()
    if "## Segurança (padrão:" in base:
        return base
    return f"{base}\n\n{section}\n"
