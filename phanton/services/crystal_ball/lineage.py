"""Leitura de linhagem a partir de phase_executions (somente leitura)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from models import PhaseExecution, PipelineRun
from services.phase_context import phase_cfg, resolve_depends_on
from services.state_engine import phase_order_from_spec


def _as_uuid(run_id: str | UUID) -> UUID:
    return run_id if isinstance(run_id, UUID) else UUID(str(run_id))


def _latest_rows_by_phase(db: Session, run_uuid: UUID) -> dict[str, PhaseExecution]:
    rows = (
        db.query(PhaseExecution)
        .filter(PhaseExecution.run_id == run_uuid)
        .order_by(PhaseExecution.id.asc())
        .all()
    )
    latest: dict[str, PhaseExecution] = {}
    for row in rows:
        latest[row.phase_id] = row
    return latest


def _inputs_used_from_artifact(artifact: Any) -> list[str]:
    if not isinstance(artifact, dict):
        return []
    raw = artifact.get("inputs_used")
    if isinstance(raw, list):
        return [str(x) for x in raw if x]
    return []


def build_lineage(db: Session, run_id: str | UUID) -> dict[str, Any]:
    """Grafo nós/arestas a partir dos artefatos do run oficial."""
    run_uuid = _as_uuid(run_id)
    run = db.get(PipelineRun, run_uuid)
    if run is None:
        raise LookupError(f"run não encontrado: {run_uuid}")

    spec = run.spec if isinstance(run.spec, dict) else {}
    order = phase_order_from_spec(spec)
    latest = _latest_rows_by_phase(db, run_uuid)

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, str]] = []
    seen_edges: set[tuple[str, str]] = set()

    for phase_id in order:
        row = latest.get(phase_id)
        artifact = row.artifact_data if row is not None else None
        inputs = _inputs_used_from_artifact(artifact)
        if not inputs:
            # Fallback de leitura: depends_on da Spec (não altera o que foi gravado)
            try:
                inputs = list(resolve_depends_on(spec, phase_id) or [])
            except Exception:
                inputs = []

        score = None
        if isinstance(artifact, dict):
            score = artifact.get("quality_score")
            if score is None and isinstance(artifact.get("meta"), dict):
                score = artifact["meta"].get("quality_score")

        cfg = phase_cfg(spec, phase_id)
        nodes.append(
            {
                "phase_id": phase_id,
                "name": (cfg.get("name") if isinstance(cfg, dict) else None) or phase_id,
                "type": (cfg.get("type") if isinstance(cfg, dict) else None),
                "status": row.status if row is not None else "MISSING",
                "has_artifact": row is not None and row.artifact_data is not None,
                "inputs_used": inputs,
                "quality_score": score,
            }
        )
        for src in inputs:
            key = (str(src), phase_id)
            if key not in seen_edges:
                seen_edges.add(key)
                edges.append({"from": str(src), "to": phase_id})

    return {
        "run_id": str(run_uuid),
        "status": run.status,
        "project_name": run.project_name,
        "phase_order": order,
        "nodes": nodes,
        "edges": edges,
    }


def extract_final_prompt(artifact: Any) -> str:
    if not isinstance(artifact, dict):
        return ""
    inner = artifact.get("artifact_data") if isinstance(artifact.get("artifact_data"), dict) else {}
    for key in ("cursor_prompt", "module_prompts"):
        val = artifact.get(key)
        if val is None and inner:
            val = inner.get(key)
        if isinstance(val, str) and val.strip():
            return val
        if isinstance(val, list) and val:
            parts = []
            for item in val:
                if isinstance(item, dict):
                    parts.append(str(item.get("prompt") or item.get("cursor_prompt") or item))
                else:
                    parts.append(str(item))
            return "\n\n---\n\n".join(parts)
    return ""


def quality_from_artifact(artifact: Any) -> int | None:
    if not isinstance(artifact, dict):
        return None
    score = artifact.get("quality_score")
    if score is None and isinstance(artifact.get("meta"), dict):
        score = artifact["meta"].get("quality_score")
    try:
        return int(score) if score is not None else None
    except (TypeError, ValueError):
        return None
