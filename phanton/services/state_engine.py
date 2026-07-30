"""Simulador local de AWS Step Functions (waitForTaskToken + gates humanos)."""

from __future__ import annotations

import asyncio
import copy
import logging
import re
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Awaitable, Callable, Optional
from uuid import UUID

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Garante imports de backend/ e services/ a partir da raiz do projeto.
_ROOT = Path(__file__).resolve().parent.parent
_BACKEND = _ROOT / "backend"
for _path in (str(_ROOT), str(_BACKEND)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from models import PhaseExecution, PipelineRun  # noqa: E402
from services.phase_context import normalize_phase_type, phase_cfg  # noqa: E402
from services.project_versioning import (  # noqa: E402
    ProjectVersioningError,
    assert_run_mutable,
    sync_run_identity,
)
from services.phase_L1 import execute_phase_L1  # noqa: E402
from services.phase_L2 import execute_phase_L2  # noqa: E402
from services.phase_L3 import execute_phase_L3  # noqa: E402
from services.phase_L4 import execute_phase_L4  # noqa: E402
from services.phase_internal_knowledge import execute_phase_context7_search  # noqa: E402
from services.phase_prd import execute_phase_prd  # noqa: E402
from services.phase_prompt_cursor import execute_phase_prompt_cursor  # noqa: E402
from services.phase_sdd import execute_phase_sdd  # noqa: E402
from services.phase_security_guidelines import (  # noqa: E402
    execute_phase_security_guidelines,
)
from services.phase_task_breakdown import execute_phase_task_breakdown  # noqa: E402
from services.quality_score import (  # noqa: E402
    AUTO_APPROVE_THRESHOLD,
    MAX_QUALITY_REDOS,
    QUALITY_REDO_THRESHOLD,
    attach_quality_score,
    build_quality_learning,
    compute_quality_score,
    should_auto_approve,
    should_redo_for_quality,
    unwrap_artifact_payload,
)

PhaseHandler = Callable[..., Awaitable[dict[str, Any]]]

# Fallback legado quando a spec não declara `phases`.
DEFAULT_PHASE_ORDER: list[str] = [
    "metodologia",
    "pesquisa",
    "sintese",
    "entrega_final",
]

# Compat: export antigo usado pelo main.py
PHASE_ORDER = DEFAULT_PHASE_ORDER

# Capabilities canônicas (a Spec escolhe quantas fases de cada tipo).
CAPABILITY_HANDLERS: dict[str, PhaseHandler] = {
    "methodology": execute_phase_L1,
    "research": execute_phase_L2,
    "context7_search": execute_phase_context7_search,
    "synthesize": execute_phase_L3,
    "generate_prd": execute_phase_prd,
    "generate_sdd": execute_phase_sdd,
    "security_guidelines": execute_phase_security_guidelines,
    "prompt_cursor": execute_phase_prompt_cursor,
    "task_breakdown": execute_phase_task_breakdown,
    # Entrega do artefato pedido (HTML/doc) — NÃO é prompt de IDE
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
    "entrega_final": execute_phase_L4,
    # IDs explícitos das novas capabilities
    "context7_search": execute_phase_context7_search,
    "generate_prd": execute_phase_prd,
    "generate_sdd": execute_phase_sdd,
    "security_guidelines": execute_phase_security_guidelines,
    "prompt_cursor": execute_phase_prompt_cursor,
    "task_breakdown": execute_phase_task_breakdown,
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
    """Resolve handler pela capability (`type`) da Spec; IDs L1..L4 são só compat.

    Preferência: `type` explícito na Spec > PHASE_HANDLERS[phase_id] > inferência.
    Assim `prompt_cursor` (IDE) e `prompt`/`delivery` (HTML) não se confundem.
    """
    cfg = phase_cfg(spec, phase_id)
    raw_type = cfg.get("type") if isinstance(cfg, dict) else None
    if raw_type:
        capability = normalize_phase_type(raw_type, phase_id)
        handler = CAPABILITY_HANDLERS.get(capability)
        if handler:
            return handler

    if phase_id in PHASE_HANDLERS:
        return PHASE_HANDLERS[phase_id]

    capability = normalize_phase_type(None, phase_id)
    handler = CAPABILITY_HANDLERS.get(capability)
    if handler:
        return handler

    raise StateEngineError(
        f"Nenhum handler registrado para a fase: {phase_id} "
        f"(type/capability='{capability}'). "
        f"Use type methodology|research|context7_search|synthesize|generate_prd|"
        f"generate_sdd|security_guidelines|prompt_cursor|task_breakdown|prompt "
        f"(ou IDs L1/L2/L3/L4 / nomes metodologia, pesquisa, context7_search, "
        f"sintese, generate_prd, generate_sdd, security_guidelines, "
        f"prompt_cursor, task_breakdown, entrega_final)."
    )


def _touch_run(run: PipelineRun) -> None:
    run.updated_at = datetime.utcnow()


def _spec_auto_approve(spec: dict[str, Any]) -> bool:
    return bool((spec or {}).get("auto_approve"))


def _expected_modules_from_run(db_session: Session, run_id: UUID) -> list[str]:
    """Módulos do build_order do SDD mais recente (p/ coverage em security)."""
    executions = (
        db_session.query(PhaseExecution)
        .filter(PhaseExecution.run_id == run_id)
        .order_by(PhaseExecution.id.desc())
        .all()
    )
    for execution in executions:
        art = execution.artifact_data if isinstance(execution.artifact_data, dict) else {}
        capability = normalize_phase_type(
            art.get("capability") or art.get("phase"),
            execution.phase_id,
        )
        if capability != "generate_sdd":
            continue
        _meta, content = unwrap_artifact_payload(art)
        order = content.get("build_order") or art.get("build_order") or []
        if not isinstance(order, list):
            continue
        modules: list[str] = []
        for item in order:
            if isinstance(item, dict) and item.get("modulo"):
                modules.append(str(item["modulo"]))
            elif isinstance(item, str) and item.strip():
                modules.append(item.strip())
        if modules:
            return modules
    return []


def _score_phase_artifact(
    db_session: Session,
    run_id: UUID,
    phase_id: str,
    spec: dict[str, Any],
    artifact: dict[str, Any],
) -> tuple[dict[str, Any], int]:
    capability = normalize_phase_type(
        (phase_cfg(spec, phase_id) or {}).get("type")
        if isinstance(phase_cfg(spec, phase_id), dict)
        else None,
        phase_id,
    )
    meta, _content = unwrap_artifact_payload(artifact)
    expected = None
    if capability == "security_guidelines":
        expected = _expected_modules_from_run(db_session, run_id) or None
    score = compute_quality_score(
        capability, meta, artifact, expected_modules=expected
    )
    return attach_quality_score(artifact, score), score


def _schedule_background(coro: Awaitable[Any]) -> None:
    """Agenda coroutine sem bloquear a resposta HTTP (UI pode fazer poll)."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        logger.exception("state_engine: sem event loop para background task")
        return
    task = loop.create_task(coro)

    def _done(t: asyncio.Task) -> None:
        try:
            exc = t.exception()
        except asyncio.CancelledError:
            return
        if exc is not None:
            logger.exception("state_engine background task falhou: %s", exc)

    task.add_done_callback(_done)


async def _bg_auto_approve(task_token: str, score: int) -> None:
    from database import SessionLocal

    db = SessionLocal()
    try:
        await approve_phase(
            db,
            task_token,
            approver="auto",
            comments=f"auto-approve quality_score={score}",
        )
    except Exception:
        logger.exception("auto-approve em background falhou token=%s", task_token)
    finally:
        db.close()


async def _bg_trigger_phase(run_id: UUID, phase_id: str) -> None:
    from database import SessionLocal

    db = SessionLocal()
    try:
        run = db.get(PipelineRun, run_id)
        if run is None:
            return
        spec = normalize_spec_phases(
            run.spec if isinstance(run.spec, dict) else dict(run.spec or {})
        )
        await trigger_phase(db, run_id, phase_id, spec)
    except Exception:
        logger.exception(
            "trigger_phase em background falhou run=%s phase=%s", run_id, phase_id
        )
        try:
            run = db.get(PipelineRun, run_id)
            if run is not None and (run.status or "").upper() == STATUS_RUNNING:
                _touch_run(run)
                db.commit()
        except Exception:
            db.rollback()
    finally:
        db.close()


async def start_pipeline(db_session: Session, run_id: str | UUID, spec: dict[str, Any]) -> dict[str, Any]:
    """Marca o run como RUNNING e dispara a primeira fase da spec."""
    run_uuid = _as_uuid(run_id)
    run = db_session.get(PipelineRun, run_uuid)
    if run is None:
        raise StateEngineError(f"Pipeline run não encontrado: {run_uuid}")

    try:
        assert_run_mutable(run)
    except ProjectVersioningError as exc:
        raise StateEngineError(str(exc)) from exc

    spec = normalize_spec_phases(dict(spec) if isinstance(spec, dict) else {})
    if "auto_approve" not in spec:
        spec["auto_approve"] = False
    else:
        spec["auto_approve"] = bool(spec.get("auto_approve"))
    order = phase_order_from_spec(spec)
    if not order:
        raise StateEngineError("spec.phases vazio — nenhuma fase para executar")

    # Persiste a ordem canônica + identidade projeto/versão.
    sync_run_identity(run, spec)
    run.status = STATUS_RUNNING
    _touch_run(run)

    first = order[0]
    # Marca a 1ª fase RUNNING no banco ANTES do background — a barra de estado
    # precisa refletir isso no primeiro poll.
    starter = PhaseExecution(
        id=uuid.uuid4(),
        run_id=run_uuid,
        phase_id=first,
        status=STATUS_RUNNING,
    )
    db_session.add(starter)
    db_session.commit()

    # Executa a 1ª fase em background para o HTTP liberar o run_id à UI.
    _schedule_background(_bg_trigger_phase(run_uuid, first))
    return {
        "run_id": str(run_uuid),
        "phase_id": first,
        "status": STATUS_RUNNING,
        "task_token": None,
        "artifact_data": None,
        "async_start": True,
    }


async def trigger_phase(
    db_session: Session,
    run_id: str | UUID,
    phase_id: str,
    spec: dict[str, Any],
) -> dict[str, Any]:
    """Executa uma fase, anexa quality_score e aguarda (ou auto-aprova)."""
    run_uuid = _as_uuid(run_id)
    handler = _resolve_handler(phase_id, spec)

    run = db_session.get(PipelineRun, run_uuid)
    if run is None:
        raise StateEngineError(f"Pipeline run não encontrado: {run_uuid}")

    # Reusa stub RUNNING criado no start/approve (evita duplicar e permite poll).
    phase = (
        db_session.query(PhaseExecution)
        .filter(
            PhaseExecution.run_id == run_uuid,
            PhaseExecution.phase_id == phase_id,
            PhaseExecution.status == STATUS_RUNNING,
        )
        .order_by(PhaseExecution.id.desc())
        .first()
    )
    if phase is None:
        phase = PhaseExecution(
            id=uuid.uuid4(),
            run_id=run_uuid,
            phase_id=phase_id,
            status=STATUS_RUNNING,
        )
        db_session.add(phase)
        db_session.commit()
        db_session.refresh(phase)

    capability = normalize_phase_type(
        (phase_cfg(spec, phase_id) or {}).get("type")
        if isinstance(phase_cfg(spec, phase_id), dict)
        else None,
        phase_id,
    )
    expected_modules = None
    if capability == "security_guidelines":
        expected_modules = _expected_modules_from_run(db_session, run_uuid) or None

    learning: dict[str, Any] | None = None
    quality_attempts: list[dict[str, Any]] = []
    best_artifact: dict[str, Any] | None = None
    best_score = -1
    score = 0
    artifact: dict[str, Any] = {}

    # Loop de qualidade: nota < 95 → refaz com regras de aprendizado.
    for attempt_idx in range(MAX_QUALITY_REDOS + 1):
        run_spec = copy.deepcopy(spec) if isinstance(spec, dict) else {}
        if learning is not None:
            phases_map = run_spec.setdefault("phases", {})
            if not isinstance(phases_map, dict):
                phases_map = {}
                run_spec["phases"] = phases_map
            cfg = dict(phases_map.get(phase_id) or {})
            cfg["quality_learning"] = learning
            phases_map[phase_id] = cfg

        artifact = await handler(str(run_uuid), run_spec, db_session, phase_id)
        if not isinstance(artifact, dict):
            artifact = {"artifact_data": artifact}

        artifact, score = _score_phase_artifact(
            db_session, run_uuid, phase_id, run_spec, artifact
        )
        quality_attempts.append(
            {
                "attempt": attempt_idx + 1,
                "score": score,
                "learning_applied": bool(learning),
            }
        )
        if score > best_score:
            best_score = score
            best_artifact = artifact

        meta = dict(artifact.get("meta") or {})
        meta["quality_attempts"] = list(quality_attempts)
        meta["quality_redo_threshold"] = QUALITY_REDO_THRESHOLD
        artifact["meta"] = meta
        artifact = attach_quality_score(artifact, score)

        # Mantém RUNNING visível na barra enquanto refaz.
        phase.artifact_data = artifact
        phase.status = STATUS_RUNNING
        _touch_run(run)
        db_session.commit()

        if not should_redo_for_quality(
            score, redos_done=attempt_idx, artifact=artifact
        ):
            break

        learning = build_quality_learning(
            capability,
            score,
            artifact,
            attempt=attempt_idx + 1,
            expected_modules=expected_modules,
        )
        logger.info(
            "quality redo phase=%s score=%s<%s attempt=%s lessons=%s",
            phase_id,
            score,
            QUALITY_REDO_THRESHOLD,
            attempt_idx + 1,
            len(learning.get("lessons") or []),
        )

    artifact = best_artifact or artifact
    score = best_score if best_score >= 0 else score
    meta = dict(artifact.get("meta") or {})
    meta["quality_attempts"] = list(quality_attempts)
    meta["quality_redo_threshold"] = QUALITY_REDO_THRESHOLD
    if learning is not None and score < QUALITY_REDO_THRESHOLD:
        meta["quality_learning_exhausted"] = True
    artifact["meta"] = meta
    artifact = attach_quality_score(artifact, score)

    phase.artifact_data = artifact
    phase.task_token = str(uuid.uuid4())
    phase.status = STATUS_AWAITING_APPROVAL
    if score < QUALITY_REDO_THRESHOLD:
        phase.comments = (
            f"qualidade {score}<{QUALITY_REDO_THRESHOLD} após "
            f"{len(quality_attempts)} tentativa(s) — revisão humana"
        )
    _touch_run(run)
    db_session.commit()
    db_session.refresh(phase)

    if should_auto_approve(
        auto_approve=_spec_auto_approve(spec),
        phase_type=capability,
        quality_score=score,
        threshold=AUTO_APPROVE_THRESHOLD,
    ):
        # Não encadear approve→próxima fase no mesmo request — a UI precisa
        # observar RUNNING/APPROVED fase a fase via poll.
        _schedule_background(_bg_auto_approve(phase.task_token, score))
        return {
            "run_id": str(run_uuid),
            "phase_id": phase_id,
            "phase_execution_id": str(phase.id),
            "status": phase.status,
            "task_token": phase.task_token,
            "artifact_data": phase.artifact_data,
            "quality_score": score,
            "auto_approve_scheduled": True,
            "quality_attempts": quality_attempts,
        }

    return {
        "run_id": str(run_uuid),
        "phase_id": phase_id,
        "phase_execution_id": str(phase.id),
        "status": phase.status,
        "task_token": phase.task_token,
        "artifact_data": phase.artifact_data,
        "quality_score": score,
        "quality_attempts": quality_attempts,
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

    try:
        assert_run_mutable(run)
    except ProjectVersioningError as exc:
        raise StateEngineError(str(exc)) from exc

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

    run.status = STATUS_RUNNING
    _touch_run(run)
    # Stub RUNNING da próxima fase — aparece na barra antes do LLM terminar.
    next_stub = PhaseExecution(
        id=uuid.uuid4(),
        run_id=phase.run_id,
        phase_id=next_phase_id,
        status=STATUS_RUNNING,
    )
    db_session.add(next_stub)
    db_session.commit()

    # Próxima fase em background — barra de estado atualiza por poll.
    _schedule_background(_bg_trigger_phase(phase.run_id, next_phase_id))
    return {
        "run_id": str(phase.run_id),
        "approved_phase_id": phase.phase_id,
        "status": STATUS_RUNNING,
        "next_phase": {
            "phase_id": next_phase_id,
            "status": STATUS_RUNNING,
            "task_token": None,
            "async_trigger": True,
        },
        "artifact_data": phase.artifact_data,
        "task_token": None,
    }


async def reopen_auto_approved_phase(
    db_session: Session,
    run_id: str | UUID,
    phase_id: str,
) -> dict[str, Any]:
    """Reabre fase aprovada por `auto` para revisão humana; remove fases posteriores."""
    run_uuid = _as_uuid(run_id)
    run = db_session.get(PipelineRun, run_uuid)
    if run is None:
        raise StateEngineError(f"Pipeline run não encontrado: {run_uuid}")

    try:
        assert_run_mutable(run)
    except ProjectVersioningError as exc:
        raise StateEngineError(str(exc)) from exc

    phase = (
        db_session.query(PhaseExecution)
        .filter(
            PhaseExecution.run_id == run_uuid,
            PhaseExecution.phase_id == phase_id,
        )
        .order_by(PhaseExecution.id.desc())
        .first()
    )
    if phase is None:
        raise StateEngineError(f"Fase '{phase_id}' não encontrada neste run")

    if phase.status != STATUS_APPROVED:
        raise StateEngineError(
            f"Só é possível reabrir fases APPROVED (status={phase.status})"
        )
    if (phase.approver or "").strip().lower() != "auto":
        raise StateEngineError(
            "Só é possível reabrir fases aprovadas automaticamente (approver=auto)"
        )

    # Remove execuções posteriores (encadeadas após esta aprovação).
    later = (
        db_session.query(PhaseExecution)
        .filter(
            PhaseExecution.run_id == run_uuid,
            PhaseExecution.id > phase.id,
        )
        .all()
    )
    for row in later:
        db_session.delete(row)

    if not phase.task_token:
        phase.task_token = str(uuid.uuid4())
    phase.status = STATUS_AWAITING_APPROVAL
    phase.approver = None
    phase.comments = "reaberto para revisão humana"
    run.status = STATUS_RUNNING
    _touch_run(run)
    db_session.commit()
    db_session.refresh(phase)

    return {
        "run_id": str(run_uuid),
        "phase_id": phase.phase_id,
        "status": phase.status,
        "task_token": phase.task_token,
        "artifact_data": phase.artifact_data,
    }
