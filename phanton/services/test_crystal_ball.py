"""Testes Crystal Ball — isolamento e linhagem (sem LLM real no fork)."""

from __future__ import annotations

import asyncio
import uuid
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql+psycopg2://postgres:password@127.0.0.1:5435/orquestrador"


def _db_available() -> bool:
    try:
        eng = create_engine(DATABASE_URL, pool_pre_ping=True)
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        eng.dispose()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _db_available(), reason="Postgres Phanton :5435 indisponível"
)


@pytest.fixture()
def db():
    from database import Base
    import services.crystal_ball.models  # noqa: F401

    eng = create_engine(DATABASE_URL, pool_pre_ping=True)
    Base.metadata.create_all(bind=eng)
    Session = sessionmaker(bind=eng)
    session = Session()
    yield session
    session.rollback()
    session.close()
    eng.dispose()


def _seed_run(db):
    from models import PhaseExecution, PipelineRun

    run_id = uuid.uuid4()
    spec = {
        "name": "Crystal Test",
        "phases": {
            "generate_prd": {"type": "generate_prd", "order": 1, "name": "PRD"},
            "generate_sdd": {
                "type": "generate_sdd",
                "order": 2,
                "name": "SDD",
                "depends_on": ["generate_prd"],
            },
            "prompt_cursor": {
                "type": "prompt_cursor",
                "order": 3,
                "name": "Prompt",
                "depends_on": ["generate_sdd"],
            },
        },
    }
    db.add(PipelineRun(id=run_id, spec=spec, status="COMPLETED"))
    db.flush()

    arts = {
        "generate_prd": {
            "status": "success",
            "phase": "generate_prd",
            "artifact_data": {"prd_markdown": "PRD original"},
            "inputs_used": [],
            "quality_score": 90,
            "meta": {"quality_score": 90},
        },
        "generate_sdd": {
            "status": "success",
            "phase": "generate_sdd",
            "artifact_data": {"sdd_markdown": "SDD original", "contexto_de_uso": "web"},
            "inputs_used": ["generate_prd"],
            "quality_score": 88,
            "meta": {"quality_score": 88},
        },
        "prompt_cursor": {
            "status": "success",
            "phase": "prompt_cursor",
            "cursor_prompt": "PROMPT ORIGINAL PARA IDE",
            "artifact_data": {"cursor_prompt": "PROMPT ORIGINAL PARA IDE"},
            "inputs_used": ["generate_sdd"],
            "quality_score": 92,
            "meta": {"quality_score": 92},
        },
    }
    for phase_id, art in arts.items():
        db.add(
            PhaseExecution(
                id=uuid.uuid4(),
                run_id=run_id,
                phase_id=phase_id,
                status="APPROVED",
                artifact_data=art,
            )
        )
    db.commit()
    return run_id


def test_lineage_matches_inputs_used(db):
    from services.crystal_ball.service import get_lineage

    run_id = _seed_run(db)
    lineage = get_lineage(db, run_id)
    by_id = {n["phase_id"]: n for n in lineage["nodes"]}
    assert by_id["generate_sdd"]["inputs_used"] == ["generate_prd"]
    assert by_id["prompt_cursor"]["inputs_used"] == ["generate_sdd"]
    edge_pairs = {(e["from"], e["to"]) for e in lineage["edges"]}
    assert ("generate_prd", "generate_sdd") in edge_pairs


def test_fork_does_not_touch_official_run(db):
    from models import PhaseExecution
    from services.crystal_ball.service import create_fork, edit_shadow_phase

    run_id = _seed_run(db)
    before = [
        (r.phase_id, r.artifact_data)
        for r in db.query(PhaseExecution)
        .filter(PhaseExecution.run_id == run_id)
        .order_by(PhaseExecution.id)
        .all()
    ]

    fork = create_fork(db, run_id, "generate_sdd")
    assert fork["is_simulation"] is True
    edit_shadow_phase(
        db,
        fork["shadow_run_id"],
        "generate_sdd",
        {
            "status": "success",
            "phase": "generate_sdd",
            "artifact_data": {
                "sdd_markdown": "SDD EDITADO NO SHADOW",
                "contexto_de_uso": "mobile",
            },
            "inputs_used": ["generate_prd"],
        },
    )

    after = [
        (r.phase_id, r.artifact_data)
        for r in db.query(PhaseExecution)
        .filter(PhaseExecution.run_id == run_id)
        .order_by(PhaseExecution.id)
        .all()
    ]
    assert before == after


def test_recalculate_downstream_only_and_changes_prompt(db):
    from models import PhaseExecution
    from services.crystal_ball import service as svc
    from services.crystal_ball.service import create_fork, edit_shadow_phase, recalculate

    run_id = _seed_run(db)
    fork = create_fork(db, run_id, "generate_sdd")
    edit_shadow_phase(
        db,
        fork["shadow_run_id"],
        "generate_sdd",
        {
            "status": "success",
            "phase": "generate_sdd",
            "artifact_data": {"sdd_markdown": "SDD FORK", "contexto_de_uso": "iot"},
            "inputs_used": ["generate_prd"],
        },
    )

    async def fake_prompt_cursor(run_id, spec, db_session, phase_id="prompt_cursor"):
        return {
            "status": "success",
            "phase": phase_id,
            "capability": "prompt_cursor",
            "cursor_prompt": "PROMPT FORKADO DIFERENTE",
            "artifact_data": {"cursor_prompt": "PROMPT FORKADO DIFERENTE"},
            "inputs_used": ["generate_sdd"],
            "meta": {},
        }

    original = dict(svc.CAPABILITY_HANDLERS)
    try:
        svc.CAPABILITY_HANDLERS["prompt_cursor"] = fake_prompt_cursor
        result = asyncio.run(recalculate(db, fork["shadow_run_id"]))
    finally:
        svc.CAPABILITY_HANDLERS.clear()
        svc.CAPABILITY_HANDLERS.update(original)

    assert result["is_simulation"] is True
    assert result["prompt_changed"] is True
    assert "FORKADO" in (result.get("predicted_prompt") or "")
    assert all(p["phase_id"] != "generate_prd" for p in result["recalculated_phases"])

    official = (
        db.query(PhaseExecution)
        .filter(
            PhaseExecution.run_id == run_id,
            PhaseExecution.phase_id == "prompt_cursor",
        )
        .one()
    )
    assert "ORIGINAL" in (official.artifact_data.get("cursor_prompt") or "")


def test_quick_preview_ephemeral_not_official_run(db):
    from models import PipelineRun
    from services.crystal_ball.service import run_quick_preview

    count_before = db.query(PipelineRun).count()

    with patch(
        "services.crystal_ball.preview.generate_content",
        return_value=(
            "[PRÉVIA — NÃO É PROMPT DE PRODUÇÃO]\n\n## Objetivo\nTeste",
            {"fallback": False},
        ),
    ):
        result = asyncio.run(run_quick_preview(db, text="Quero um app de notas"))

    assert result["is_preview"] is True
    assert "PRÉVIA" in result["preview_prompt"]
    assert db.query(PipelineRun).count() == count_before


def test_l1_includes_inputs_used_key():
    from services.phase_L1 import execute_phase_L1

    with patch(
        "services.phase_L1.generate_content",
        return_value=(
            '{"metodologia":"x","notas":"y","objetivo":"z","principios":["a"]}',
            {},
        ),
    ):
        art = asyncio.run(
            execute_phase_L1(
                str(uuid.uuid4()),
                {
                    "description": "t",
                    "phases": {"metodologia": {"type": "methodology"}},
                },
                db_session=None,
                phase_id="metodologia",
            )
        )
    assert "inputs_used" in art
    assert isinstance(art["inputs_used"], list)
