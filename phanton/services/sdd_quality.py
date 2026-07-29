"""Checagens de qualidade do SDD pós-geração (sem LLM).

Fecha gaps recorrentes: entidades de avaliação ausentes e build_order
só-backend quando o PRD descreve UI/player.
"""

from __future__ import annotations

import re
from typing import Any

_ASSESSMENT_PRD = re.compile(
    r"\b("
    r"avalia[cç][aã]o|avalia[cç][oõ]es|quiz|prova|question[aá]rio|"
    r"nota\s*m[ií]nima|exame|assessment|attempt"
    r")\b",
    re.I,
)

_ASSESSMENT_ENTITIES = re.compile(
    r"\b("
    r"Assessment|Attempt|Question|ItemResponse|"
    r"avalia[cç][aã]o|tentativa\s+de\s+avalia|"
    r"banco\s+de\s+quest"
    r")\b",
    re.I,
)

_UI_PRD = re.compile(
    r"\b("
    r"frontend|front[\s-]?end|SPA|Next\.?js|React|Vue|UI|UX|"
    r"player|portal|dashboard|tela|interface|cat[aá]logo|"
    r"p[aá]gina|mobile\s+web|PWA"
    r")\b",
    re.I,
)

_FRONTEND_MOD = re.compile(
    r"(frontend|front-end|-ui\b|-ui-|player|spa|webapp|portal)",
    re.I,
)

_ASSESSMENT_APPENDIX = """

## Modelo de Dados — Avaliações (obrigatório pelo PRD)

O PRD menciona avaliações/notas. O SDD **deve** incluir (mínimo):

- `Assessment` — id, courseId, title, minScore, maxAttempts
- `Attempt` — id, assessmentId, userId, score, submittedAt
- `Question` / itens da prova (quando aplicável)
- `Enrollment.averageGrade` derivado dos Attempts (não preenchido à mão)

Sem essas entidades, gamificação, xAPI `passed`/`failed` e certificados com nota mínima ficam sem origem canônica.
""".rstrip()


def prd_requires_assessments(prd_text: str) -> bool:
    return bool(_ASSESSMENT_PRD.search(prd_text or ""))


def sdd_has_assessment_entities(sdd_markdown: str) -> bool:
    return bool(_ASSESSMENT_ENTITIES.search(sdd_markdown or ""))


def prd_requires_ui(prd_text: str, user_prompt: str = "") -> bool:
    blob = f"{prd_text or ''}\n{user_prompt or ''}"
    return bool(_UI_PRD.search(blob))


def build_order_has_frontend(build_order: list[dict[str, Any]]) -> bool:
    for entry in build_order or []:
        if not isinstance(entry, dict):
            continue
        camada = str(entry.get("camada") or "").lower()
        if camada == "frontend":
            return True
        name = str(entry.get("modulo") or "")
        escopo = str(entry.get("escopo") or "")
        if _FRONTEND_MOD.search(f"{name} {escopo}"):
            return True
    return False


def ensure_assessment_section(sdd_markdown: str, prd_text: str) -> tuple[str, list[str]]:
    """Anexa checklist de Assessment se o PRD exige e o SDD omite."""
    warnings: list[str] = []
    text = sdd_markdown or ""
    if not prd_requires_assessments(prd_text):
        return text, warnings
    if sdd_has_assessment_entities(text):
        return text, warnings
    warnings.append("sdd_missing_assessment_entities")
    if "## Modelo de Dados — Avaliações" not in text:
        text = text.rstrip() + "\n" + _ASSESSMENT_APPENDIX + "\n"
    return text, warnings


def ensure_frontend_in_build_order(
    build_order: list[dict[str, Any]],
    *,
    prd_text: str,
    user_prompt: str = "",
) -> tuple[list[dict[str, Any]], list[str]]:
    """Injeta módulo frontend descritivo se o PRD/pedido pedem UI e a fila é só API."""
    warnings: list[str] = []
    order = [dict(x) for x in (build_order or []) if isinstance(x, dict)]
    if not order:
        return order, warnings
    if not prd_requires_ui(prd_text, user_prompt):
        return order, warnings
    if build_order_has_frontend(order):
        # Garante camada marcada
        for entry in order:
            name = str(entry.get("modulo") or "")
            escopo = str(entry.get("escopo") or "")
            if _FRONTEND_MOD.search(f"{name} {escopo}") and not entry.get("camada"):
                entry["camada"] = "frontend"
        return order, warnings

    warnings.append("build_order_missing_frontend_module")
    # Depende do último módulo backend da fila (ou vazio)
    backend_names = [
        str(e.get("modulo"))
        for e in order
        if str(e.get("camada") or "backend").lower() != "frontend" and e.get("modulo")
    ]
    deps = [backend_names[-1]] if backend_names else []
    order.append(
        {
            "modulo": "app-frontend",
            "depende_de": deps,
            "escopo": (
                "SPA/UI: rotas (catálogo, player/lição, ranking, certificado, admin), "
                "consumo das APIs já entregues, auth no cliente, CSP do SPA, "
                "estados loading/erro/offline; sem redesign de API"
            ),
            "camada": "frontend",
        }
    )
    return order, warnings


def apply_sdd_quality_gates(
    *,
    sdd_markdown: str,
    build_order: list[dict[str, Any]],
    prd_text: str,
    user_prompt: str = "",
) -> tuple[str, list[dict[str, Any]], list[str]]:
    warnings: list[str] = []
    md, w1 = ensure_assessment_section(sdd_markdown, prd_text)
    warnings.extend(w1)
    order, w2 = ensure_frontend_in_build_order(
        build_order, prd_text=prd_text, user_prompt=user_prompt
    )
    warnings.extend(w2)
    return md, order, warnings
