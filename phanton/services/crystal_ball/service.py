"""Serviço Crystal Ball — fork / recalculate / calibrate (isolado)."""

from __future__ import annotations

import copy
import logging
import uuid
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from models import PhaseExecution, PipelineRun
from services.crystal_ball.bridge import shadow_artifact_bridge
from services.crystal_ball.lineage import (
    build_lineage,
    extract_final_prompt,
    quality_from_artifact,
)
from services.crystal_ball.models import (
    CrystalPrediction,
    CrystalShadowPhase,
    CrystalShadowRun,
)
from services.crystal_ball.preview import quick_preview
from services.phase_context import normalize_phase_type, phase_cfg
from services.quality_score import attach_quality_score, compute_quality_score
from services.state_engine import (
    CAPABILITY_HANDLERS,
    PHASE_HANDLERS,
    phase_order_from_spec,
)

logger = logging.getLogger(__name__)


class CrystalBallError(Exception):
    pass


def _as_uuid(value: str | UUID) -> UUID:
    return value if isinstance(value, UUID) else UUID(str(value))


def _resolve_handler(phase_id: str, spec: dict[str, Any]):
    cfg = phase_cfg(spec, phase_id)
    cap = normalize_phase_type(
        cfg.get("type") if isinstance(cfg, dict) else None,
        phase_id,
    )
    if cap in CAPABILITY_HANDLERS:
        return CAPABILITY_HANDLERS[cap], cap
    if phase_id in PHASE_HANDLERS:
        return PHASE_HANDLERS[phase_id], cap
    raise CrystalBallError(f"handler não encontrado para fase {phase_id}")


def _latest_official_artifacts(db: Session, run_uuid: UUID) -> dict[str, dict[str, Any]]:
    rows = (
        db.query(PhaseExecution)
        .filter(PhaseExecution.run_id == run_uuid)
        .order_by(PhaseExecution.id.asc())
        .all()
    )
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        if isinstance(row.artifact_data, dict):
            out[row.phase_id] = copy.deepcopy(row.artifact_data)
    return out


def get_lineage(db: Session, run_id: str | UUID) -> dict[str, Any]:
    return build_lineage(db, run_id)


def create_fork(
    db: Session,
    run_id: str | UUID,
    fork_phase_id: str,
) -> dict[str, Any]:
    """Copia artefatos oficiais até fork_phase_id (inclusive) para um shadow run."""
    run_uuid = _as_uuid(run_id)
    run = db.get(PipelineRun, run_uuid)
    if run is None:
        raise CrystalBallError(f"run oficial não encontrado: {run_uuid}")

    spec = copy.deepcopy(run.spec) if isinstance(run.spec, dict) else {}
    order = phase_order_from_spec(spec)
    if fork_phase_id not in order:
        raise CrystalBallError(f"fase {fork_phase_id} não está na Spec do run")

    fork_idx = order.index(fork_phase_id)
    artifacts = _latest_official_artifacts(db, run_uuid)

    shadow = CrystalShadowRun(
        id=uuid.uuid4(),
        source_run_id=run_uuid,
        fork_phase_id=fork_phase_id,
        status="forked",
        spec=spec,
        notes="shadow simulation — não é run oficial",
    )
    db.add(shadow)
    db.flush()

    copied: list[str] = []
    for phase_id in order[: fork_idx + 1]:
        art = artifacts.get(phase_id)
        if art is None:
            continue
        db.add(
            CrystalShadowPhase(
                id=uuid.uuid4(),
                shadow_run_id=shadow.id,
                phase_id=phase_id,
                status="copied",
                origin="copied",
                artifact_data=art,
                quality_score=quality_from_artifact(art),
            )
        )
        copied.append(phase_id)

    db.commit()
    db.refresh(shadow)
    return {
        "shadow_run_id": str(shadow.id),
        "source_run_id": str(run_uuid),
        "fork_phase_id": fork_phase_id,
        "status": shadow.status,
        "copied_phases": copied,
        "downstream_phases": order[fork_idx + 1 :],
        "is_simulation": True,
    }


def edit_shadow_phase(
    db: Session,
    shadow_run_id: str | UUID,
    phase_id: str,
    artifact_data: dict[str, Any],
) -> dict[str, Any]:
    shadow_uuid = _as_uuid(shadow_run_id)
    shadow = db.get(CrystalShadowRun, shadow_uuid)
    if shadow is None:
        raise CrystalBallError(f"shadow run não encontrado: {shadow_uuid}")

    row = (
        db.query(CrystalShadowPhase)
        .filter(
            CrystalShadowPhase.shadow_run_id == shadow_uuid,
            CrystalShadowPhase.phase_id == phase_id,
        )
        .order_by(CrystalShadowPhase.created_at.desc())
        .first()
    )
    payload = copy.deepcopy(artifact_data)
    if not isinstance(payload, dict):
        raise CrystalBallError("artifact_data deve ser objeto JSON")

    # Garante envelope mínimo
    if "artifact_data" not in payload and phase_id:
        payload = {
            "status": "success",
            "phase": phase_id,
            "artifact_data": payload,
            "meta": {"shadow_edit": True},
        }
    meta = dict(payload.get("meta") or {})
    meta["shadow_edit"] = True
    meta["is_simulation"] = True
    payload["meta"] = meta

    if row is None:
        row = CrystalShadowPhase(
            id=uuid.uuid4(),
            shadow_run_id=shadow_uuid,
            phase_id=phase_id,
            status="edited",
            origin="edited",
            artifact_data=payload,
            quality_score=quality_from_artifact(payload),
        )
        db.add(row)
    else:
        row.artifact_data = payload
        row.status = "edited"
        row.origin = "edited"
        row.quality_score = quality_from_artifact(payload)

    shadow.edited_phase_id = phase_id
    shadow.status = "edited"
    shadow.updated_at = datetime.now(UTC)
    db.commit()
    return {
        "shadow_run_id": str(shadow_uuid),
        "phase_id": phase_id,
        "status": "edited",
        "is_simulation": True,
    }


async def recalculate(
    db: Session,
    shadow_run_id: str | UUID,
) -> dict[str, Any]:
    """Reexecuta só fases downstream do fork_phase_id em modo shadow."""
    shadow_uuid = _as_uuid(shadow_run_id)
    shadow = db.get(CrystalShadowRun, shadow_uuid)
    if shadow is None:
        raise CrystalBallError(f"shadow run não encontrado: {shadow_uuid}")

    spec = shadow.spec if isinstance(shadow.spec, dict) else {}
    order = phase_order_from_spec(spec)
    fork_phase_id = shadow.fork_phase_id
    if fork_phase_id not in order:
        raise CrystalBallError("fork_phase_id inválido no shadow")

    fork_idx = order.index(fork_phase_id)
    downstream = order[fork_idx + 1 :]
    shadow.status = "recalculating"
    db.commit()

    recalculated: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []

    for phase_id in downstream:
        try:
            handler, capability = _resolve_handler(phase_id, spec)
            with shadow_artifact_bridge():
                artifact = await handler(str(shadow_uuid), copy.deepcopy(spec), db, phase_id)
            if not isinstance(artifact, dict):
                artifact = {"artifact_data": artifact}

            meta = dict(artifact.get("meta") or {})
            score = compute_quality_score(
                capability,
                meta,
                artifact.get("artifact_data") or artifact,
            )
            artifact = attach_quality_score(artifact, score)
            meta = dict(artifact.get("meta") or {})
            meta["is_simulation"] = True
            meta["shadow_recalculated"] = True
            artifact["meta"] = meta
            artifact["is_simulation"] = True

            # Remove rows anteriores recalculated desta fase
            old = (
                db.query(CrystalShadowPhase)
                .filter(
                    CrystalShadowPhase.shadow_run_id == shadow_uuid,
                    CrystalShadowPhase.phase_id == phase_id,
                    CrystalShadowPhase.origin == "recalculated",
                )
                .all()
            )
            for row in old:
                db.delete(row)

            db.add(
                CrystalShadowPhase(
                    id=uuid.uuid4(),
                    shadow_run_id=shadow_uuid,
                    phase_id=phase_id,
                    status="recalculated",
                    origin="recalculated",
                    artifact_data=artifact,
                    quality_score=score,
                )
            )
            db.commit()
            recalculated.append(
                {"phase_id": phase_id, "quality_score": score, "capability": capability}
            )
        except Exception as exc:
            logger.exception("crystal recalculate failed phase=%s", phase_id)
            errors.append({"phase_id": phase_id, "error": str(exc)})
            db.rollback()
            shadow = db.get(CrystalShadowRun, shadow_uuid)
            if shadow is not None:
                shadow.status = "error"
                shadow.notes = f"erro em {phase_id}: {exc}"
                db.commit()
            break

    shadow = db.get(CrystalShadowRun, shadow_uuid)
    assert shadow is not None

    # Prompt final previsto = última prompt_cursor recalculada, se houver
    final_art = None
    final_score = None
    for phase_id in reversed(order):
        row = (
            db.query(CrystalShadowPhase)
            .filter(
                CrystalShadowPhase.shadow_run_id == shadow_uuid,
                CrystalShadowPhase.phase_id == phase_id,
            )
            .order_by(CrystalShadowPhase.created_at.desc())
            .first()
        )
        if row is None:
            continue
        cfg = phase_cfg(spec, phase_id)
        cap = normalize_phase_type(cfg.get("type") if isinstance(cfg, dict) else None, phase_id)
        if cap == "prompt_cursor" or phase_id in ("prompt_cursor", "ide_prompt"):
            final_art = row.artifact_data
            final_score = row.quality_score
            break

    if final_score is None and recalculated:
        final_score = recalculated[-1].get("quality_score")

    prompt_text = extract_final_prompt(final_art) if final_art else ""
    shadow.predicted_quality_score = final_score
    shadow.final_prompt_excerpt = (prompt_text or "")[:4000] or None
    shadow.status = "ready" if not errors else "error"
    shadow.updated_at = datetime.now(UTC)
    db.commit()

    # Registro de previsão para calibração futura
    pred = CrystalPrediction(
        id=uuid.uuid4(),
        source_run_id=shadow.source_run_id,
        shadow_run_id=shadow.id,
        kind="fork",
        predicted_quality_score=final_score,
        confidence="medium",
        preview_text=(prompt_text or "")[:2000] or None,
    )
    db.add(pred)
    db.commit()

    # Diff vs original
    original = _latest_official_artifacts(db, shadow.source_run_id)
    orig_prompt = ""
    orig_score = None
    for phase_id in reversed(order):
        art = original.get(phase_id)
        if not art:
            continue
        cfg = phase_cfg(spec, phase_id)
        cap = normalize_phase_type(cfg.get("type") if isinstance(cfg, dict) else None, phase_id)
        if cap == "prompt_cursor" or phase_id in ("prompt_cursor", "ide_prompt"):
            orig_prompt = extract_final_prompt(art)
            orig_score = quality_from_artifact(art)
            break

    return {
        "shadow_run_id": str(shadow_uuid),
        "source_run_id": str(shadow.source_run_id),
        "status": shadow.status,
        "is_simulation": True,
        "recalculated_phases": recalculated,
        "errors": errors,
        "predicted_quality_score": final_score,
        "original_quality_score": orig_score,
        "predicted_prompt": prompt_text,
        "original_prompt": orig_prompt,
        "prompt_changed": (prompt_text or "") != (orig_prompt or ""),
        "prediction_id": str(pred.id),
    }


def get_shadow(db: Session, shadow_run_id: str | UUID) -> dict[str, Any]:
    shadow_uuid = _as_uuid(shadow_run_id)
    shadow = db.get(CrystalShadowRun, shadow_uuid)
    if shadow is None:
        raise CrystalBallError(f"shadow run não encontrado: {shadow_uuid}")
    phases = (
        db.query(CrystalShadowPhase)
        .filter(CrystalShadowPhase.shadow_run_id == shadow_uuid)
        .order_by(CrystalShadowPhase.created_at.asc())
        .all()
    )
    # latest per phase
    latest: dict[str, CrystalShadowPhase] = {}
    for row in phases:
        latest[row.phase_id] = row
    return {
        "shadow_run_id": str(shadow.id),
        "source_run_id": str(shadow.source_run_id),
        "fork_phase_id": shadow.fork_phase_id,
        "status": shadow.status,
        "is_simulation": True,
        "predicted_quality_score": shadow.predicted_quality_score,
        "final_prompt_excerpt": shadow.final_prompt_excerpt,
        "phases": [
            {
                "phase_id": p.phase_id,
                "status": p.status,
                "origin": p.origin,
                "quality_score": p.quality_score,
                "artifact_data": p.artifact_data,
            }
            for p in latest.values()
        ],
    }


def calibrate_against_run(db: Session, run_id: str | UUID) -> dict[str, Any]:
    """Compara quality_score real do prompt_cursor com previsões pendentes."""
    run_uuid = _as_uuid(run_id)
    arts = _latest_official_artifacts(db, run_uuid)
    actual = None
    for phase_id, art in arts.items():
        cfg = phase_cfg({}, phase_id)
        # use normalize on phase_id alone
        cap = normalize_phase_type(None, phase_id)
        if cap == "prompt_cursor" or "prompt_cursor" in phase_id:
            actual = quality_from_artifact(art)
            break

    preds = (
        db.query(CrystalPrediction)
        .filter(
            CrystalPrediction.source_run_id == run_uuid,
            CrystalPrediction.calibrated_at.is_(None),
        )
        .order_by(CrystalPrediction.created_at.desc())
        .all()
    )
    updated = []
    for pred in preds:
        pred.actual_quality_score = actual
        if actual is not None and pred.predicted_quality_score is not None:
            pred.prediction_error = int(actual) - int(pred.predicted_quality_score)
        pred.calibrated_at = datetime.now(UTC)
        updated.append(
            {
                "prediction_id": str(pred.id),
                "kind": pred.kind,
                "predicted": pred.predicted_quality_score,
                "actual": pred.actual_quality_score,
                "prediction_error": pred.prediction_error,
            }
        )
    db.commit()
    return {
        "run_id": str(run_uuid),
        "actual_quality_score": actual,
        "calibrations": updated,
    }


async def run_quick_preview(
    db: Session | None,
    *,
    text: str | None = None,
    structured_requirements: dict[str, Any] | None = None,
    link_source_run_id: str | None = None,
) -> dict[str, Any]:
    result = await quick_preview(
        text=text,
        structured_requirements=structured_requirements,
    )
    if db is not None:
        pred = CrystalPrediction(
            id=uuid.uuid4(),
            source_run_id=_as_uuid(link_source_run_id) if link_source_run_id else None,
            kind="preview",
            predicted_quality_score=None,
            preview_text=(result.get("preview_prompt") or "")[:2000],
            confidence=result.get("confidence"),
        )
        db.add(pred)
        db.commit()
        result["prediction_id"] = str(pred.id)
    result["is_preview"] = True
    return result
