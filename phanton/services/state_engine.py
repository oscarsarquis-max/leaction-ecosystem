"""Simulador local de AWS Step Functions (waitForTaskToken + gates humanos)."""

from __future__ import annotations

import re
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Awaitable, Callable, Optional
from uuid import UUID

from sqlalchemy.orm import Session

# Garante imports de backend/ e services/ a partir da raiz do projeto.
_ROOT = Path(__file__).resolve().parent.parent
_BACKEND = _ROOT / "backend"
for _path in (str(_ROOT), str(_BACKEND)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from models import PhaseExecution, PipelineRun  # noqa: E402
from services.phase_context import normalize_phase_type, phase_cfg  # noqa: E402
from services.phase_L1 import execute_phase_L1  # noqa: E402
from services.phase_L2 import execute_phase_L2  # noqa: E402
from services.phase_L3 import execute_phase_L3  # noqa: E402
from services.phase_L4 import execute_phase_L4  # noqa: E402

PhaseHandler = Callable[..., Awaitable[dict[str, Any]]]

# Fallback legado quando a spec não declara `phases`.
DEFAULT_PHASE_ORDER: list[str] = [
    "metodologia",
    "pesquisa",
    "sintese",
    "prompt_cursor",
]

# Compat: export antigo usado pelo main.py
PHASE_ORDER = DEFAULT_PHASE_ORDER

# Capabilities canônicas (a Spec escolhe quantas fases de cada tipo).
CAPABILITY_HANDLERS: dict[str, PhaseHandler] = {
    "methodology": execute_phase_L1,
    "research": execute_phase_L2,
    "synthesize": execute_phase_L3,
    "prompt": execute_phase_L4,
}

# Compat legado: IDs L1..L4 e nomes da DEFAULT_PHASE_ORDER ainda resolvem.
PHASE_HANDLERS: dict[str, PhaseHandler] = {
    "L1": execute_phase_L1,
    "L2": execute_phase_L2,
    "L3": execute_phase_L3,
    "L4": execute_phase_L4,
    "metodologia": execute_phase_L1,
    "pesquisa": execute_phase_L2,
    "sintese": execute_phase_L3,
    "prompt_cursor": execute_phase_L4,
}

STATUS_RUNNING = "RUNNING"
STATUS_AWAITING_APPROVAL = "AWAITING_APPROVAL"
STATUS_APPROVED = "APPROVED"
STATUS_COMPLETED = "COMPLETED"


class StateEngineError(Exception):
    """Erro de domínio do state engine."""


def _as_uuid(run_id: str | UUID) -> UUID:
    return run_id if isinstance(run_id, UUID) else UUID(str(run_id))


def _phase_sort_key(phase_id: str, cfg: Any) -> tuple:
    """Ordena por order explícito na config, senão por prefixo L1/L2/L3…"""
    if isinstance(cfg, dict) and cfg.get("order") is not None:
        try:
            return (0, int(cfg["order"]), str(phase_id))
        except (TypeError, ValueError):
            pass
    match = re.match(r"^L(\d+)", str(phase_id).strip(), re.IGNORECASE)
    if match:
        return (1, int(match.group(1)), str(phase_id))
    return (2, 9999, str(phase_id))


def phase_order_from_spec(spec: dict[str, Any] | None) -> list[str]:
    """Ordem dinâmica das fases pela Spec (`order`), independente das chaves JSON."""
    if not isinstance(spec, dict):
        return list(DEFAULT_PHASE_ORDER)

    phases = spec.get("phases")
    if isinstance(phases, dict) and phases:
        items = [(str(key), value) for key, value in phases.items()]
        items.sort(key=lambda item: _phase_sort_key(item[0], item[1]))
        return [key for key, _ in items]

    if isinstance(phases, list) and phases:
        ordered: list[str] = []
        for item in phases:
            if isinstance(item, str):
                ordered.append(item)
            elif isinstance(item, dict) and item.get("id"):
                ordered.append(str(item["id"]))
        if ordered:
            ordered.sort(key=lambda pid: _phase_sort_key(pid, None))
            return ordered

    return list(DEFAULT_PHASE_ORDER)


def normalize_spec_phases(spec: dict[str, Any]) -> dict[str, Any]:
    """Regrava spec['phases'] na ordem da Spec (mutável, retorna o mesmo dict)."""
    if not isinstance(spec, dict):
        return spec
    phases = spec.get("phases")
    if not isinstance(phases, dict) or not phases:
        return spec
    order = phase_order_from_spec(spec)
    # Normaliza type canônico em cada fase (sem forçar IDs L1..L4).
    for phase_id in order:
        cfg = phases.get(phase_id)
        if not isinstance(cfg, dict):
            continue
        cfg["type"] = normalize_phase_type(cfg.get("type"), phase_id)
        if not cfg.get("name"):
            cfg["name"] = str(phase_id).replace("_", " ").title()
    spec["phases"] = {key: phases[key] for key in order if key in phases}
    return spec


def _next_phase_from_spec(spec: dict[str, Any] | None, current_phase_id: str) -> Optional[str]:
    order = phase_order_from_spec(spec)
    try:
        idx = order.index(current_phase_id)
    except ValueError as exc:
        raise StateEngineError(
            f"Fase '{current_phase_id}' não está declarada em spec.phases: {order}"
        ) from exc
    nxt = idx + 1
    if nxt >= len(order):
        return None
    return order[nxt]


def _resolve_handler(phase_id: str, spec: dict[str, Any] | None) -> PhaseHandler:
    """Resolve handler pela capability (`type`) da Spec; IDs L1..L4 são só compat."""
    if phase_id in PHASE_HANDLERS:
        return PHASE_HANDLERS[phase_id]

    cfg = phase_cfg(spec, phase_id)
    capability = normalize_phase_type(cfg.get("type"), phase_id)
    handler = CAPABILITY_HANDLERS.get(capability)
    if handler:
        return handler

    raise StateEngineError(
        f"Nenhum handler registrado para a fase: {phase_id} "
        f"(type/capability='{capability}'). "
        f"Use type methodology|research|synthesize|prompt "
        f"(ou IDs L1/L2/L3/L4 / nomes metodologia, pesquisa, sintese, prompt_cursor)."
    )


def _touch_run(run: PipelineRun) -> None:
    run.updated_at = datetime.utcnow()


async def start_pipeline(db_session: Session, run_id: str | UUID, spec: dict[str, Any]) -> dict[str, Any]:
    """Marca o run como RUNNING e dispara a primeira fase da spec."""
    run_uuid = _as_uuid(run_id)
    run = db_session.get(PipelineRun, run_uuid)
    if run is None:
        raise StateEngineError(f"Pipeline run não encontrado: {run_uuid}")

    spec = normalize_spec_phases(dict(spec) if isinstance(spec, dict) else {})
    order = phase_order_from_spec(spec)
    if not order:
        raise StateEngineError("spec.phases vazio — nenhuma fase para executar")

    # Persiste a ordem canônica no run (evita JSON embaralhado no banco).
    run.spec = spec
    run.status = STATUS_RUNNING
    _touch_run(run)
    db_session.commit()

    return await trigger_phase(db_session, run_uuid, order[0], spec)


async def trigger_phase(
    db_session: Session,
    run_id: str | UUID,
    phase_id: str,
    spec: dict[str, Any],
) -> dict[str, Any]:
    """Executa uma fase, persiste artefato e entra em AWAITING_APPROVAL (task token)."""
    run_uuid = _as_uuid(run_id)
    handler = _resolve_handler(phase_id, spec)

    run = db_session.get(PipelineRun, run_uuid)
    if run is None:
        raise StateEngineError(f"Pipeline run não encontrado: {run_uuid}")

    phase = PhaseExecution(
        id=uuid.uuid4(),
        run_id=run_uuid,
        phase_id=phase_id,
        status=STATUS_RUNNING,
    )
    db_session.add(phase)
    db_session.commit()
    db_session.refresh(phase)

    artifact = await handler(str(run_uuid), spec, db_session, phase_id)

    phase.artifact_data = artifact
    phase.task_token = str(uuid.uuid4())
    phase.status = STATUS_AWAITING_APPROVAL
    _touch_run(run)
    db_session.commit()
    db_session.refresh(phase)

    return {
        "run_id": str(run_uuid),
        "phase_id": phase_id,
        "phase_execution_id": str(phase.id),
        "status": phase.status,
        "task_token": phase.task_token,
        "artifact_data": phase.artifact_data,
    }


async def approve_phase(
    db_session: Session,
    task_token: str,
    modified_artifact: Optional[dict[str, Any]] = None,
    *,
    approver: Optional[str] = None,
    comments: Optional[str] = None,
) -> dict[str, Any]:
    """Aprova a fase pelo task_token e engatilha a próxima fase da spec."""
    phase = (
        db_session.query(PhaseExecution)
        .filter(PhaseExecution.task_token == task_token)
        .one_or_none()
    )
    if phase is None:
        raise StateEngineError(f"task_token não encontrado: {task_token}")

    if phase.status != STATUS_AWAITING_APPROVAL:
        raise StateEngineError(
            f"Fase {phase.phase_id} não está aguardando aprovação (status={phase.status})"
        )

    run = db_session.get(PipelineRun, phase.run_id)
    if run is None:
        raise StateEngineError(f"Pipeline run não encontrado: {phase.run_id}")

    phase.status = STATUS_APPROVED
    if modified_artifact is not None:
        phase.artifact_data = modified_artifact
    if approver is not None:
        phase.approver = approver
    if comments is not None:
        phase.comments = comments
    _touch_run(run)
    db_session.commit()

    spec = normalize_spec_phases(
        run.spec if isinstance(run.spec, dict) else dict(run.spec or {})
    )
    # Persiste normalização caso o run antigo tenha chaves fora de ordem.
    if run.spec != spec:
        run.spec = spec
        db_session.commit()

    next_phase_id = _next_phase_from_spec(spec, phase.phase_id)

    if next_phase_id is None:
        run.status = STATUS_COMPLETED
        _touch_run(run)
        db_session.commit()
        return {
            "run_id": str(phase.run_id),
            "approved_phase_id": phase.phase_id,
            "status": STATUS_COMPLETED,
            "next_phase": None,
            "task_token": None,
            "artifact_data": phase.artifact_data,
        }

    next_result = await trigger_phase(
        db_session,
        phase.run_id,
        next_phase_id,
        spec,
    )
    return {
        "run_id": str(phase.run_id),
        "approved_phase_id": phase.phase_id,
        "status": STATUS_RUNNING,
        "next_phase": next_result,
        "artifact_data": phase.artifact_data,
    }
