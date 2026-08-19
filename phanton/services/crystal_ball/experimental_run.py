"""Experimento Mativas — linha completa só em shadow (Crystal Ball)."""

from __future__ import annotations

import copy
import logging
import uuid
from datetime import UTC, datetime
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from services.crystal_ball.bridge import shadow_artifact_bridge
from services.crystal_ball.experimental_providers.mativas_lookup import (
    build_context7_shadow_artifact,
    lookup_metodologia_exata,
)
from services.crystal_ball.models import CrystalShadowPhase, CrystalShadowRun
from services.crystal_ball.passos_compare import (
    compare_passos,
    extract_passos_from_artifact,
)
from services.quality_score import attach_quality_score, compute_quality_score
from services.state_engine import CAPABILITY_HANDLERS

logger = logging.getLogger(__name__)

PHASE_CONTEXT7 = "context7_mativas"
PHASE_METHODOLOGY = "methodology"
PHASE_SYNTHESIZE = "synthesize"
PHASE_ENTREGA = "entrega_final"

_VOCAB_GUARDRAILS = """
GUARDRAILS DE VOCABULÁRIO (obrigatório):
- Substitua "metodologias ativas" / "metodologia ativa" por "metodologias inov-ativas".
- Substitua "dor"/"dores" por "desafio"/"desafios".
- O desafio do professor NÃO vira o tema literal dos passos: use-o como contexto
  situacional; os títulos/imperativos dos passos vêm da Biblioteca de Passos
  da metodologia (fonte context7_mativas), sem parafrasear o canônico.
""".strip()


class ExperimentalRunError(Exception):
    pass


def _as_uuid(value: str | UUID) -> UUID:
    return value if isinstance(value, UUID) else UUID(str(value))


def build_experimental_spec(
    *,
    user_prompt: str,
    metodologia: str,
) -> dict[str, Any]:
    return {
        "name": f"crystal-ball-mativas::{metodologia}",
        "description": user_prompt,
        "user_prompt": user_prompt,
        "experimental": True,
        "crystal_ball_experiment": "mativas_line",
        "phases": {
            PHASE_CONTEXT7: {
                "type": "context7_search",
                "order": 1,
                "name": "Context7 Mativas (experimental lookup)",
                "depends_on": [],
                "description": (
                    f"Lookup exato da metodologia '{metodologia}' no corpus Mativas."
                ),
            },
            PHASE_METHODOLOGY: {
                "type": "methodology",
                "order": 2,
                "name": "Methodology (guardrails)",
                "depends_on": [PHASE_CONTEXT7],
                "description": (
                    f"Alinhar a metodologia '{metodologia}' ao pedido do professor.\n"
                    f"{_VOCAB_GUARDRAILS}\n"
                    "Use o artefato context7_mativas como fonte canônica."
                ),
            },
            PHASE_SYNTHESIZE: {
                "type": "synthesize",
                "order": 3,
                "name": "Synthesize",
                "depends_on": [PHASE_CONTEXT7, PHASE_METHODOLOGY],
                "description": (
                    "Combine o hit Mativas (Biblioteca de Passos) + guardrails + "
                    "desafio do professor.\n"
                    "Em dinamica_passo_a_passo: titulo_do_card = imperativo LITERAL "
                    "da biblioteca; como_executar_detalhado = descricao_base LITERAL "
                    "(adapte só o mínimo necessário ao desafio, sem reescrever o canônico).\n"
                    f"{_VOCAB_GUARDRAILS}"
                ),
            },
            PHASE_ENTREGA: {
                "type": "prompt",
                "order": 4,
                "name": "Entrega final (roteiro)",
                "depends_on": [PHASE_CONTEXT7, PHASE_METHODOLOGY, PHASE_SYNTHESIZE],
                "description": (
                    "Gere o ROTEIRO DE AULA final em Markdown OU JSON.\n"
                    "Se JSON, use exatamente:\n"
                    '{"passos":[{"titulo":"...","descricao":"..."}, ...]}\n'
                    "onde titulo = imperativo da Biblioteca e descricao = descricao_base "
                    "(cópia literal preferencial).\n"
                    "Se Markdown, numere os passos 1..N com o imperativo como título "
                    "e a descricao_base no corpo.\n"
                    f"{_VOCAB_GUARDRAILS}"
                ),
            },
        },
    }


def _store_phase(
    db: Session,
    shadow_id: UUID,
    phase_id: str,
    artifact: dict[str, Any],
    *,
    origin: str,
) -> None:
    meta = dict(artifact.get("meta") or {})
    meta["is_simulation"] = True
    meta["experimental"] = True
    artifact["meta"] = meta
    artifact["is_simulation"] = True
    score = None
    try:
        cap = str(artifact.get("capability") or "")
        if cap:
            score = compute_quality_score(
                cap, meta, artifact.get("artifact_data") or artifact
            )
            artifact = attach_quality_score(artifact, score)
    except Exception:
        score = None

    db.add(
        CrystalShadowPhase(
            id=uuid.uuid4(),
            shadow_run_id=shadow_id,
            phase_id=phase_id,
            status="recalculated",
            origin=origin,
            artifact_data=artifact,
            quality_score=score,
        )
    )
    db.commit()


async def _run_handler(
    db: Session,
    shadow_id: UUID,
    phase_id: str,
    capability: str,
    spec: dict[str, Any],
) -> dict[str, Any]:
    handler = CAPABILITY_HANDLERS.get(capability)
    if handler is None:
        raise ExperimentalRunError(f"handler real ausente: {capability}")
    with shadow_artifact_bridge():
        artifact = await handler(str(shadow_id), copy.deepcopy(spec), db, phase_id)
    if not isinstance(artifact, dict):
        artifact = {"artifact_data": artifact}
    # Proveniência explícita
    deps = (
        (spec.get("phases") or {}).get(phase_id, {}).get("depends_on")
        if isinstance(spec.get("phases"), dict)
        else []
    )
    if not artifact.get("inputs_used"):
        artifact["inputs_used"] = list(deps or [])
    _store_phase(db, shadow_id, phase_id, artifact, origin="experimental")
    return artifact


def build_shadow_lineage(db: Session, shadow_run_id: str | UUID) -> dict[str, Any]:
    shadow = db.get(CrystalShadowRun, _as_uuid(shadow_run_id))
    if shadow is None:
        raise LookupError(f"shadow run não encontrado: {shadow_run_id}")
    spec = shadow.spec if isinstance(shadow.spec, dict) else {}
    phases_cfg = spec.get("phases") if isinstance(spec.get("phases"), dict) else {}
    order = sorted(
        phases_cfg.keys(),
        key=lambda pid: int((phases_cfg.get(pid) or {}).get("order") or 999),
    )
    rows = (
        db.query(CrystalShadowPhase)
        .filter(CrystalShadowPhase.shadow_run_id == shadow.id)
        .order_by(CrystalShadowPhase.created_at.asc())
        .all()
    )
    latest: dict[str, CrystalShadowPhase] = {}
    for row in rows:
        latest[row.phase_id] = row

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for phase_id in order:
        row = latest.get(phase_id)
        art = row.artifact_data if row else None
        inputs: list[str] = []
        if isinstance(art, dict) and isinstance(art.get("inputs_used"), list):
            inputs = [str(x) for x in art["inputs_used"] if x]
        if not inputs:
            cfg = phases_cfg.get(phase_id) or {}
            raw = cfg.get("depends_on") or []
            inputs = [str(x) for x in raw] if isinstance(raw, list) else []
        nodes.append(
            {
                "phase_id": phase_id,
                "name": (phases_cfg.get(phase_id) or {}).get("name") or phase_id,
                "type": (phases_cfg.get(phase_id) or {}).get("type"),
                "status": row.status if row else "MISSING",
                "has_artifact": bool(row and row.artifact_data),
                "inputs_used": inputs,
                "quality_score": row.quality_score if row else None,
                "origin": row.origin if row else None,
            }
        )
        for src in inputs:
            key = (src, phase_id)
            if key not in seen:
                seen.add(key)
                edges.append({"from": src, "to": phase_id})

    return {
        "shadow_run_id": str(shadow.id),
        "is_simulation": True,
        "experimental": True,
        "status": shadow.status,
        "phase_order": order,
        "nodes": nodes,
        "edges": edges,
    }


async def run_mativas_experimental(
    db: Session,
    *,
    user_prompt: str,
    metodologia: str,
    owned_by_user_id: UUID | None = None,
) -> dict[str, Any]:
    """Orquestra context7(Mativas) → methodology → synthesize → entrega_final."""
    prompt = (user_prompt or "").strip()
    metodo = (metodologia or "").strip()
    if len(prompt) < 8:
        raise ExperimentalRunError("user_prompt muito curto")
    if not metodo:
        raise ExperimentalRunError("metodologia obrigatória")

    # Valida lookup antes de criar shadow
    registro = lookup_metodologia_exata(metodo)
    if registro is None:
        raise ExperimentalRunError(
            f"Metodologia não encontrada no corpus (lookup exato): {metodo!r}"
        )

    spec = build_experimental_spec(user_prompt=prompt, metodologia=metodo)
    shadow = CrystalShadowRun(
        id=uuid.uuid4(),
        source_run_id=None,  # experimental puro — sem run oficial
        fork_phase_id=PHASE_CONTEXT7,
        status="experimental_running",
        spec=spec,
        owned_by_user_id=owned_by_user_id,
        notes=(
            "EXPERIMENTAL Mativas — shadow-only; não é run oficial; "
            "provider crystal_ball.mativas_lookup"
        ),
    )
    db.add(shadow)
    db.commit()

    errors: list[dict[str, str]] = []
    artifacts: dict[str, dict[str, Any]] = {}

    try:
        # Fase 1 — lookup experimental (não usa handler context7 de produção)
        c7 = build_context7_shadow_artifact(
            metodologia=metodo, user_prompt=prompt
        )
        _store_phase(db, shadow.id, PHASE_CONTEXT7, c7, origin="experimental_lookup")
        artifacts[PHASE_CONTEXT7] = c7

        # Fases 2–4 — handlers reais em modo shadow
        for phase_id, capability in (
            (PHASE_METHODOLOGY, "methodology"),
            (PHASE_SYNTHESIZE, "synthesize"),
            (PHASE_ENTREGA, "prompt"),
        ):
            try:
                art = await _run_handler(db, shadow.id, phase_id, capability, spec)
                artifacts[phase_id] = art
                # Handlers oficiais devolvem status=error sem exception — não marcar done.
                if str(art.get("status") or "").lower() == "error":
                    inner = art.get("artifact_data") if isinstance(art.get("artifact_data"), dict) else {}
                    msg = (
                        (inner or {}).get("erro")
                        or art.get("error")
                        or f"fase {phase_id} retornou status=error"
                    )
                    errors.append({"phase_id": phase_id, "error": str(msg)})
                    shadow.status = "error"
                    shadow.notes = f"erro em {phase_id}: {msg}"
                    shadow.updated_at = datetime.now(UTC)
                    db.commit()
                    break
            except Exception as exc:
                logger.exception("experimental phase failed: %s", phase_id)
                errors.append({"phase_id": phase_id, "error": str(exc)})
                shadow.status = "error"
                shadow.notes = f"erro em {phase_id}: {exc}"
                shadow.updated_at = datetime.now(UTC)
                db.commit()
                break
    except Exception as exc:
        logger.exception("experimental-run failed")
        shadow.status = "error"
        shadow.notes = str(exc)
        shadow.updated_at = datetime.now(UTC)
        db.commit()
        raise ExperimentalRunError(str(exc)) from exc

    # Comparação: preferir entrega; fallback síntese
    ref_passos = registro.get("passos") if isinstance(registro.get("passos"), list) else []
    gen_passos = extract_passos_from_artifact(artifacts.get(PHASE_ENTREGA) or {})
    source_of_passos = "entrega_final"
    if not gen_passos:
        gen_passos = extract_passos_from_artifact(artifacts.get(PHASE_SYNTHESIZE) or {})
        source_of_passos = "synthesize"
    comparison = compare_passos(gen_passos, ref_passos)
    comparison["extracted_from"] = source_of_passos

    if not errors:
        shadow.status = "experimental_done"
    shadow.updated_at = datetime.now(UTC)
    # excerpt
    entrega = artifacts.get(PHASE_ENTREGA) or {}
    inner = entrega.get("artifact_data") if isinstance(entrega.get("artifact_data"), dict) else {}
    excerpt = (
        (inner.get("delivery") if isinstance(inner, dict) else None)
        or entrega.get("delivery")
        or ""
    )
    if isinstance(excerpt, str):
        shadow.final_prompt_excerpt = excerpt[:4000]
    db.commit()

    lineage = build_shadow_lineage(db, shadow.id)
    shadow_view = _shadow_phases_payload(db, shadow.id)

    return {
        "is_simulation": True,
        "experimental": True,
        "shadow_run_id": str(shadow.id),
        "status": shadow.status,
        "metodologia": registro.get("metodologia"),
        "phase_order": [
            PHASE_CONTEXT7,
            PHASE_METHODOLOGY,
            PHASE_SYNTHESIZE,
            PHASE_ENTREGA,
        ],
        "phases": shadow_view["phases"],
        "artifacts_summary": {
            pid: {
                "has_artifact": True,
                "capability": (art or {}).get("capability"),
                "inputs_used": (art or {}).get("inputs_used"),
                "meta": (art or {}).get("meta"),
            }
            for pid, art in artifacts.items()
        },
        "lineage": lineage,
        "comparison": comparison,
        "errors": errors,
        "referencia_n_passos": len(ref_passos),
    }


def _shadow_phases_payload(db: Session, shadow_id: UUID) -> dict[str, Any]:
    rows = (
        db.query(CrystalShadowPhase)
        .filter(CrystalShadowPhase.shadow_run_id == shadow_id)
        .order_by(CrystalShadowPhase.created_at.asc())
        .all()
    )
    latest: dict[str, CrystalShadowPhase] = {}
    for row in rows:
        latest[row.phase_id] = row
    return {
        "phases": [
            {
                "phase_id": p.phase_id,
                "status": p.status,
                "origin": p.origin,
                "quality_score": p.quality_score,
                "artifact_data": p.artifact_data,
            }
            for p in latest.values()
        ]
    }


def _comparison_for_shadow(db: Session, shadow_id: UUID) -> dict[str, Any]:
    shadow = db.get(CrystalShadowRun, shadow_id)
    if shadow is None:
        return {}
    spec = shadow.spec if isinstance(shadow.spec, dict) else {}
    metodo = ""
    # tenta extrair metodologia do artefato context7
    row_c7 = (
        db.query(CrystalShadowPhase)
        .filter(
            CrystalShadowPhase.shadow_run_id == shadow_id,
            CrystalShadowPhase.phase_id == PHASE_CONTEXT7,
        )
        .order_by(CrystalShadowPhase.created_at.desc())
        .first()
    )
    registro = None
    if row_c7 and isinstance(row_c7.artifact_data, dict):
        inner = row_c7.artifact_data.get("artifact_data") or {}
        if isinstance(inner, dict):
            registro = inner.get("mativas_registro")
            metodo = str(inner.get("metodologia_fixada") or "")
    if registro is None and metodo:
        registro = lookup_metodologia_exata(metodo)
    if registro is None:
        # fallback: nome no spec
        name = str(spec.get("name") or "")
        if "::" in name:
            registro = lookup_metodologia_exata(name.split("::", 1)[-1])
    ref_passos = (
        registro.get("passos")
        if isinstance(registro, dict) and isinstance(registro.get("passos"), list)
        else []
    )

    entrega = (
        db.query(CrystalShadowPhase)
        .filter(
            CrystalShadowPhase.shadow_run_id == shadow_id,
            CrystalShadowPhase.phase_id == PHASE_ENTREGA,
        )
        .order_by(CrystalShadowPhase.created_at.desc())
        .first()
    )
    gen = extract_passos_from_artifact(
        entrega.artifact_data if entrega else {}
    )
    source = "entrega_final"
    if not gen:
        synth = (
            db.query(CrystalShadowPhase)
            .filter(
                CrystalShadowPhase.shadow_run_id == shadow_id,
                CrystalShadowPhase.phase_id == PHASE_SYNTHESIZE,
            )
            .order_by(CrystalShadowPhase.created_at.desc())
            .first()
        )
        gen = extract_passos_from_artifact(synth.artifact_data if synth else {})
        source = "synthesize"
    comparison = compare_passos(gen, ref_passos)
    comparison["extracted_from"] = source
    return comparison


async def experimental_edit_and_recalculate(
    db: Session,
    shadow_run_id: str | UUID,
    *,
    from_phase_id: str,
    artifact_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Edita (opcional) uma fase do experimento e recalcula só o downstream.

    Reusa ``services.crystal_ball.service.recalculate`` — não duplica handlers.
    """
    from services.crystal_ball import service as cb_service

    shadow_uuid = _as_uuid(shadow_run_id)
    shadow = db.get(CrystalShadowRun, shadow_uuid)
    if shadow is None:
        raise ExperimentalRunError(f"shadow run não encontrado: {shadow_uuid}")
    spec = shadow.spec if isinstance(shadow.spec, dict) else {}
    if not (spec.get("experimental") or spec.get("crystal_ball_experiment")):
        raise ExperimentalRunError(
            "shadow não é experimental Mativas — use /shadow/.../recalculate"
        )

    phase = (from_phase_id or "").strip()
    if phase not in (
        PHASE_CONTEXT7,
        PHASE_METHODOLOGY,
        PHASE_SYNTHESIZE,
        PHASE_ENTREGA,
    ):
        raise ExperimentalRunError(f"fase experimental inválida: {phase}")

    if artifact_data is not None:
        cb_service.edit_shadow_phase(db, shadow_uuid, phase, artifact_data)
    else:
        # Só âncora o recálculo na fase indicada
        shadow.fork_phase_id = phase
        shadow.edited_phase_id = phase
        db.commit()

    # Snapshot origins before recalc (para teste: context7 não some)
    before_c7 = (
        db.query(CrystalShadowPhase)
        .filter(
            CrystalShadowPhase.shadow_run_id == shadow_uuid,
            CrystalShadowPhase.phase_id == PHASE_CONTEXT7,
        )
        .order_by(CrystalShadowPhase.created_at.desc())
        .first()
    )
    c7_origin_before = before_c7.origin if before_c7 else None

    recalc = await cb_service.recalculate(
        db, shadow_uuid, from_phase_id=phase
    )
    comparison = _comparison_for_shadow(db, shadow_uuid)
    lineage = build_shadow_lineage(db, shadow_uuid)
    phases = _shadow_phases_payload(db, shadow_uuid)["phases"]

    after_c7 = (
        db.query(CrystalShadowPhase)
        .filter(
            CrystalShadowPhase.shadow_run_id == shadow_uuid,
            CrystalShadowPhase.phase_id == PHASE_CONTEXT7,
        )
        .order_by(CrystalShadowPhase.created_at.desc())
        .first()
    )

    return {
        "is_simulation": True,
        "experimental": True,
        "shadow_run_id": str(shadow_uuid),
        "from_phase_id": phase,
        "recalculate": recalc,
        "recalculated_phase_ids": [
            x.get("phase_id") for x in (recalc.get("recalculated_phases") or [])
        ],
        "lookup_reexecuted": False,
        "context7_origin_before": c7_origin_before,
        "context7_origin_after": after_c7.origin if after_c7 else None,
        "phases": phases,
        "lineage": lineage,
        "comparison": comparison,
        "status": recalc.get("status"),
    }
