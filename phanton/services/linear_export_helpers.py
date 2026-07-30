"""Helpers para localizar o artefato task_breakdown de um run."""

from __future__ import annotations

from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from models import PhaseExecution, PipelineRun
from services.phase_artifacts import as_uuid, latest_phase_artifact, unwrap_artifact
from services.phase_context import normalize_phase_type, ordered_phase_ids, phase_cfg


def resolve_spec_title(run: PipelineRun) -> str:
    spec = run.spec if isinstance(run.spec, dict) else {}
    if getattr(run, "project_name", None):
        name = str(run.project_name).strip()
        if name:
            return name[:120]
    for key in ("name", "description", "user_prompt"):
        value = spec.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()[:120]
    if getattr(run, "project_key", None):
        return str(run.project_key)[:120]
    return f"phanton-run-{str(run.id)[:8]}"


def find_task_breakdown_artifact(
    db_session: Session,
    run_id: str | UUID,
    spec: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], str]:
    """
    Retorna (artifact_dict, phase_id) da fase task_breakdown.
    Levanta ValueError se não encontrar artefato utilizável.
    """
    run_uuid = as_uuid(run_id)
    spec_dict = spec if isinstance(spec, dict) else {}

    candidate_ids: list[str] = []
    for pid in ordered_phase_ids(spec_dict):
        cfg = phase_cfg(spec_dict, pid)
        cap = normalize_phase_type(cfg.get("type"), pid)
        if cap == "task_breakdown":
            candidate_ids.append(pid)

    # IDs comuns mesmo sem type explícito
    for pid in ("task_breakdown", "tasks_breakdown", "linear_export"):
        if pid not in candidate_ids:
            candidate_ids.append(pid)

    for pid in candidate_ids:
        raw = latest_phase_artifact(db_session, run_uuid, pid)
        if isinstance(raw, dict) and isinstance(raw.get("epics"), list) and raw["epics"]:
            return raw, pid
        # Envelope completo às vezes
        if isinstance(raw, dict) and isinstance(raw.get("artifact_data"), dict):
            inner = raw["artifact_data"]
            if isinstance(inner.get("epics"), list) and inner["epics"]:
                return inner, pid

    # Varredura nas execuções do run (última por phase_id)
    rows = (
        db_session.query(PhaseExecution)
        .filter(PhaseExecution.run_id == run_uuid)
        .order_by(PhaseExecution.id.desc())
        .all()
    )
    seen: set[str] = set()
    for row in rows:
        pid = str(row.phase_id or "")
        if pid in seen:
            continue
        seen.add(pid)
        cap = normalize_phase_type(None, pid)
        if cap != "task_breakdown" and "task_breakdown" not in pid.lower():
            continue
        data = unwrap_artifact(row.artifact_data)
        if isinstance(data, dict) and isinstance(data.get("epics"), list) and data["epics"]:
            return data, pid

    raise ValueError(
        "Nenhum artefato task_breakdown com epics encontrado neste run. "
        "Execute e aprove a fase task_breakdown antes de exportar."
    )
