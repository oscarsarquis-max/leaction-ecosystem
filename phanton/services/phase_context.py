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
    return str(
        cfg.get("descricao")
        or cfg.get("description")
        or cfg.get("prompt")
        or fallback
        or ""
    ).strip()


def normalize_phase_type(raw: Any, phase_id: str = "") -> str:
    """Mapeia type da Spec (e aliases legados) para capability canônica."""
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
        "prompt": "prompt",
        "prompt_cursor": "prompt",
        "delivery": "prompt",
        "html": "prompt",
        "render": "prompt",
        "frontend": "prompt",
    }
    if value in aliases:
        return aliases[value]

    # Spec sem `type`: infere pelo próprio phase_id (ex.: metodologia, pesquisa_x).
    pid = str(phase_id or "").strip().lower()
    if pid in aliases:
        return aliases[pid]
    for token, capability in (
        ("metodologia", "methodology"),
        ("methodology", "methodology"),
        ("pesquisa", "research"),
        ("research", "research"),
        ("grounding", "research"),
        ("sintese", "synthesize"),
        ("síntese", "synthesize"),
        ("synthesize", "synthesize"),
        ("prompt", "prompt"),
    ):
        if token in pid:
            return capability

    match = re.match(r"^L(\d+)", str(phase_id).strip(), re.I)
    if match:
        level = int(match.group(1))
        return {1: "methodology", 2: "research", 3: "synthesize", 4: "prompt"}.get(
            level, "research"
        )
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
