"""Contexto de fase a partir da Spec (ids livres, depends_on, type)."""

from __future__ import annotations

import re
from typing import Any

from sqlalchemy.orm import Session

from services.phase_artifacts import latest_phase_artifact, unwrap_artifact


def phase_cfg(spec: dict[str, Any] | None, phase_id: str) -> dict[str, Any]:
    if not isinstance(spec, dict):
        return {}
    phases = spec.get("phases")
    if not isinstance(phases, dict):
        return {}
    cfg = phases.get(phase_id)
    return dict(cfg) if isinstance(cfg, dict) else {}


def phase_description(cfg: dict[str, Any], *, fallback: str = "") -> str:
    base = str(
        cfg.get("descricao")
        or cfg.get("description")
        or cfg.get("prompt")
        or fallback
        or ""
    ).strip()
    learning = cfg.get("quality_learning") if isinstance(cfg, dict) else None
    if learning:
        from services.quality_score import format_quality_learning_block

        block = format_quality_learning_block(learning)
        if block:
            base = f"{base}\n\n{block}".strip() if base else block
    return base


# phase_id (exato) → capability. Sempre vence o type enviado pelo LLM.
_PHASE_ID_EXACT: dict[str, str] = {
    "context7_search": "context7_search",
    "context7": "context7_search",
    "generate_prd": "generate_prd",
    "prd": "generate_prd",
    "generate_sdd": "generate_sdd",
    "sdd": "generate_sdd",
    "security_guidelines": "security_guidelines",
    "security_review": "security_guidelines",
    "diretrizes_seguranca": "security_guidelines",
    "diretrizes_de_seguranca": "security_guidelines",
    "security": "security_guidelines",
    "sec_guidelines": "security_guidelines",
    "appsec": "security_guidelines",
    "prompt_cursor": "prompt_cursor",
    "ide_prompt": "prompt_cursor",
    "cursor_prompt": "prompt_cursor",
    "task_breakdown": "task_breakdown",
    "tasks_breakdown": "task_breakdown",
    "linear_export": "task_breakdown",
    "jira_export": "task_breakdown",
}

# Substrings no phase_id (ordem importa: mais específico primeiro).
_PHASE_ID_SUBSTRINGS: tuple[tuple[str, str], ...] = (
    ("security_guidelines", "security_guidelines"),
    ("diretrizes_seguranca", "security_guidelines"),
    ("security_review", "security_guidelines"),
    ("prompt_cursor", "prompt_cursor"),
    ("cursor_prompt", "prompt_cursor"),
    ("ide_prompt", "prompt_cursor"),
    ("context7", "context7_search"),
    ("generate_prd", "generate_prd"),
    ("generate_sdd", "generate_sdd"),
    ("task_breakdown", "task_breakdown"),
    ("linear_export", "task_breakdown"),
    ("jira_export", "task_breakdown"),
)


def resolve_capability_from_phase_id(phase_id: str) -> str | None:
    """Capability âncora pelo phase_id, ou None se não for âncora conhecida."""
    pid = str(phase_id or "").strip().lower()
    if not pid:
        return None
    if pid in _PHASE_ID_EXACT:
        return _PHASE_ID_EXACT[pid]
    for token, capability in _PHASE_ID_SUBSTRINGS:
        if token in pid:
            return capability
    # Prefixo/sufixo security_* / *_security (exceto nomes ambíguos)
    if pid.startswith("security_") or pid.endswith("_security"):
        return "security_guidelines"
    if pid.startswith("prd_") or pid.endswith("_prd"):
        return "generate_prd"
    if pid.startswith("sdd_") or pid.endswith("_sdd"):
        return "generate_sdd"
    if pid.startswith("task_breakdown") or pid.endswith("_task_breakdown"):
        return "task_breakdown"
    return None


def normalize_phase_type(raw: Any, phase_id: str = "") -> str:
    """Mapeia type da Spec para capability canônica.

    Regra âncora: se o phase_id for conhecido (security_guidelines, generate_prd,
    generate_sdd, prompt_cursor, context7_search, …), o type é FORÇADO por esse
    id — independente do valor que o LLM tenha mandado (methodology, prompt,
    research, ausente, etc.).
    """
    anchored = resolve_capability_from_phase_id(phase_id)
    if anchored:
        return anchored

    value = str(raw or "").strip().lower()
    aliases = {
        "generate": "methodology",
        "methodology": "methodology",
        "metodologia": "methodology",
        "transform": "research",
        "research": "research",
        "grounding": "research",
        "busca": "research",
        "pesquisa": "research",
        "evaluate": "synthesize",
        "synthesize": "synthesize",
        "synthesis": "synthesize",
        "sintese": "synthesize",
        "síntese": "synthesize",
        "context7_search": "context7_search",
        "context7": "context7_search",
        "internal_knowledge": "context7_search",
        "rag_internal": "context7_search",
        "generate_prd": "generate_prd",
        "prd": "generate_prd",
        "generate_sdd": "generate_sdd",
        "sdd": "generate_sdd",
        "security_guidelines": "security_guidelines",
        "security": "security_guidelines",
        "sec_guidelines": "security_guidelines",
        "appsec": "security_guidelines",
        "prompt_cursor": "prompt_cursor",
        "ide_prompt": "prompt_cursor",
        "cursor_prompt": "prompt_cursor",
        "task_breakdown": "task_breakdown",
        "tasks_breakdown": "task_breakdown",
        "linear_export": "task_breakdown",
        "jira_export": "task_breakdown",
        "prompt": "prompt",
        "delivery": "prompt",
        "html": "prompt",
        "render": "prompt",
        "frontend": "prompt",
        "entrega": "prompt",
    }
    if value in aliases:
        return aliases[value]

    pid = str(phase_id or "").strip().lower()
    if pid in aliases:
        return aliases[pid]
    for token, capability in (
        ("metodologia", "methodology"),
        ("methodology", "methodology"),
        ("context7", "context7_search"),
        ("internal_knowledge", "context7_search"),
        ("pesquisa", "research"),
        ("research", "research"),
        ("grounding", "research"),
        ("sintese", "synthesize"),
        ("síntese", "synthesize"),
        ("synthesize", "synthesize"),
        ("entrega", "prompt"),
        ("delivery", "prompt"),
    ):
        if token in pid:
            return capability

    match = re.match(r"^L(\d+)", str(phase_id).strip(), re.I)
    if match:
        level = int(match.group(1))
        return {
            1: "methodology",
            2: "research",
            3: "synthesize",
            4: "prompt",
            5: "generate_prd",
            6: "generate_sdd",
            7: "prompt_cursor",
            8: "context7_search",
            9: "task_breakdown",
        }.get(level, "research")
    return "research"


def _phase_sort_key(phase_id: str, cfg: Any) -> tuple:
    if isinstance(cfg, dict) and cfg.get("order") is not None:
        try:
            return (0, int(cfg["order"]), str(phase_id))
        except (TypeError, ValueError):
            pass
    match = re.match(r"^L(\d+)", str(phase_id).strip(), re.IGNORECASE)
    if match:
        return (1, int(match.group(1)), str(phase_id))
    return (2, 9999, str(phase_id))


def ordered_phase_ids(spec: dict[str, Any] | None) -> list[str]:
    if not isinstance(spec, dict):
        return []
    phases = spec.get("phases")
    if not isinstance(phases, dict) or not phases:
        return []
    items = [(str(key), value) for key, value in phases.items()]
    items.sort(key=lambda item: _phase_sort_key(item[0], item[1]))
    return [key for key, _ in items]


def resolve_depends_on(spec: dict[str, Any] | None, phase_id: str) -> list[str]:
    """depends_on explícito na Spec; senão, todas as fases anteriores na ordem."""
    cfg = phase_cfg(spec, phase_id)
    raw = cfg.get("depends_on") or cfg.get("inputs") or []
    if isinstance(raw, str):
        deps = [raw]
    elif isinstance(raw, list):
        deps = [str(item) for item in raw if item]
    else:
        deps = []

    if deps:
        return deps

    order = ordered_phase_ids(spec)
    try:
        idx = order.index(phase_id)
    except ValueError:
        return []
    return order[:idx]


def load_dependency_artifacts(
    db_session: Session,
    run_id: str,
    spec: dict[str, Any] | None,
    phase_id: str,
) -> dict[str, Any]:
    """Carrega artefatos das fases em depends_on (ou anteriores)."""
    deps = resolve_depends_on(spec, phase_id)
    artifacts: dict[str, Any] = {}
    for dep_id in deps:
        data = latest_phase_artifact(db_session, run_id, dep_id)
        if data is not None:
            artifacts[dep_id] = unwrap_artifact(data)
    return artifacts


def pipeline_label(spec: dict[str, Any] | None) -> str:
    if not isinstance(spec, dict):
        return "pipeline"
    return str(spec.get("name") or spec.get("description") or "pipeline")
