"""Testes do experimento Mativas (Crystal Ball only)."""

from __future__ import annotations

import asyncio
import inspect
import uuid
from unittest.mock import AsyncMock, patch

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


def test_mativas_lookup_exact_pbl():
    from services.crystal_ball.experimental_providers.mativas_lookup import (
        lookup_metodologia_exata,
    )

    hit = lookup_metodologia_exata("Aprendizagem Baseada em Problemas")
    assert hit is not None
    assert hit["metodologia"] == "Aprendizagem Baseada em Problemas"
    assert isinstance(hit.get("passos"), list)
    assert len(hit["passos"]) == 8
    assert hit["passos"][0].get("imperativo")


def test_mativas_lookup_not_in_context7_package():
    """Provider experimental NÃO vive em services.context7."""
    import services.context7 as c7

    src = inspect.getsource(c7)
    assert "mativas_lookup" not in src
    # Módulo experimental existe só sob crystal_ball
    from services.crystal_ball.experimental_providers import mativas_lookup as ml

    assert "crystal_ball" in ml.__name__


def test_experimental_not_in_state_engine_handlers():
    from services import state_engine

    # Nenhuma rota/handler de produção aponta para mativas_lookup
    import services.state_engine as se

    src = inspect.getsource(se)
    assert "mativas_lookup" not in src
    assert "experimental-run" not in src
    assert "experimental_providers" not in src


def test_passos_compare_literal():
    from services.crystal_ball.passos_compare import compare_passos

    ref = [
        {"ordem": 1, "imperativo": "Apresente a situação-problema", "descricao_base": "desc A"},
        {"ordem": 2, "imperativo": "Organize os grupos", "descricao_base": "desc B"},
    ]
    gen = [
        {"titulo": "Apresente a situação-problema", "descricao": "desc A"},
        {"titulo": "Organize os grupos", "descricao": "PARA FRASE"},
    ]
    report = compare_passos(gen, ref)
    assert report["n_referencia"] == 2
    assert report["identical_count"] == 1
    assert report["titulo_identical_count"] == 2
    assert report["descricao_identical_count"] == 1
    assert report["details"][1]["identical"] is False


def test_experimental_run_shadow_only_mocked_handlers(db):
    """Roda as 4 fases em shadow sem LLM; não cria pipeline_runs."""
    from models import PipelineRun
    from services.crystal_ball.experimental_run import run_mativas_experimental
    from services.crystal_ball.experimental_providers.mativas_lookup import (
        lookup_metodologia_exata,
    )

    before = db.query(PipelineRun).count()
    registro = lookup_metodologia_exata("Aprendizagem Baseada em Problemas")
    assert registro is not None
    ref_passos = registro["passos"]

    async def fake_methodology(run_id, spec, db_session, phase_id):
        return {
            "status": "success",
            "capability": "methodology",
            "artifact_data": {
                "metodologia": "Aprendizagem Baseada em Problemas",
                "notas": "usar biblioteca literal",
                "objetivo": "roteiro",
                "principios": ["autonomia"],
            },
            "inputs_used": ["context7_mativas"],
            "meta": {},
        }

    async def fake_synthesize(run_id, spec, db_session, phase_id):
        cards = [
            {
                "titulo_do_card": p["imperativo"],
                "como_executar_detalhado": p["descricao_base"],
            }
            for p in ref_passos
        ]
        return {
            "status": "success",
            "capability": "synthesize",
            "artifact_data": {
                "resumo_sintese": "ok",
                "pontos_chave": ["pbl"],
                "dinamica_passo_a_passo": cards,
                "requisitos_para_implementacao": [],
            },
            "inputs_used": ["context7_mativas", "methodology"],
            "meta": {},
        }

    async def fake_entrega(run_id, spec, db_session, phase_id):
        import json

        passos = [
            {"titulo": p["imperativo"], "descricao": p["descricao_base"]}
            for p in ref_passos
        ]
        body = json.dumps({"passos": passos}, ensure_ascii=False)
        return {
            "status": "success",
            "capability": "prompt",
            "artifact_data": {
                "delivery": body,
                "format": "markdown",
                "cursor_prompt": body,
            },
            "delivery": body,
            "inputs_used": ["context7_mativas", "methodology", "synthesize"],
            "meta": {},
        }

    with patch.dict(
        "services.crystal_ball.experimental_run.CAPABILITY_HANDLERS",
        {
            "methodology": fake_methodology,
            "synthesize": fake_synthesize,
            "prompt": fake_entrega,
        },
        clear=False,
    ):
        result = asyncio.run(
            run_mativas_experimental(
                db,
                user_prompt=(
                    "Sou professora do ensino médio. Desafio: alunos não conseguem "
                    "aplicar o que aprenderam em situações reais. Gere um roteiro "
                    "de aula com Aprendizagem Baseada em Problemas."
                ),
                metodologia="Aprendizagem Baseada em Problemas",
            )
        )

    assert result["is_simulation"] is True
    assert result["experimental"] is True
    assert result["status"] == "experimental_done"
    assert result["comparison"]["identical_count"] == len(ref_passos)
    assert result["comparison"]["identical_ratio"] == 1.0
    assert len(result["lineage"]["nodes"]) == 4
    assert result["lineage"]["edges"]
    # Isolamento: nenhum pipeline_run novo
    assert db.query(PipelineRun).count() == before
    # Shadow sem source oficial
    from services.crystal_ball.models import CrystalShadowRun

    shadow = db.get(CrystalShadowRun, uuid.UUID(result["shadow_run_id"]))
    assert shadow is not None
    assert shadow.source_run_id is None


def test_experimental_edit_context7_recalculates_only_downstream(db):
    """Editar context7_mativas recalcula methodology/synthesize/entrega — sem re-lookup."""
    from services.crystal_ball.experimental_run import (
        experimental_edit_and_recalculate,
        run_mativas_experimental,
    )
    from services.crystal_ball.experimental_providers.mativas_lookup import (
        lookup_metodologia_exata,
    )
    from services.crystal_ball.models import CrystalShadowPhase

    registro = lookup_metodologia_exata("Aprendizagem Baseada em Problemas")
    ref_passos = registro["passos"]
    calls = {"methodology": 0, "synthesize": 0, "prompt": 0}

    async def fake_methodology(run_id, spec, db_session, phase_id):
        calls["methodology"] += 1
        return {
            "status": "success",
            "capability": "methodology",
            "artifact_data": {
                "metodologia": "Aprendizagem Baseada em Problemas",
                "notas": f"call#{calls['methodology']}",
                "objetivo": "roteiro",
                "principios": ["autonomia"],
            },
            "inputs_used": ["context7_mativas"],
            "meta": {},
        }

    async def fake_synthesize(run_id, spec, db_session, phase_id):
        calls["synthesize"] += 1
        cards = [
            {
                "titulo_do_card": p["imperativo"],
                "como_executar_detalhado": p["descricao_base"],
            }
            for p in ref_passos
        ]
        return {
            "status": "success",
            "capability": "synthesize",
            "artifact_data": {
                "resumo_sintese": f"synth#{calls['synthesize']}",
                "pontos_chave": ["pbl"],
                "dinamica_passo_a_passo": cards,
                "requisitos_para_implementacao": [],
            },
            "inputs_used": ["context7_mativas", "methodology"],
            "meta": {},
        }

    async def fake_entrega(run_id, spec, db_session, phase_id):
        import json

        calls["prompt"] += 1
        passos = [
            {"titulo": p["imperativo"], "descricao": p["descricao_base"]}
            for p in ref_passos
        ]
        body = json.dumps({"passos": passos}, ensure_ascii=False)
        return {
            "status": "success",
            "capability": "prompt",
            "artifact_data": {
                "delivery": body,
                "format": "markdown",
                "cursor_prompt": body,
            },
            "delivery": body,
            "inputs_used": ["context7_mativas", "methodology", "synthesize"],
            "meta": {},
        }

    with patch.dict(
        "services.crystal_ball.experimental_run.CAPABILITY_HANDLERS",
        {
            "methodology": fake_methodology,
            "synthesize": fake_synthesize,
            "prompt": fake_entrega,
        },
        clear=False,
    ):
        # Também patch no service.recalculate path
        with patch.dict(
            "services.crystal_ball.service.CAPABILITY_HANDLERS",
            {
                "methodology": fake_methodology,
                "synthesize": fake_synthesize,
                "prompt": fake_entrega,
                "context7_search": AsyncMock(
                    side_effect=AssertionError("lookup não deve reexecutar")
                ),
            },
            clear=False,
        ):
            first = asyncio.run(
                run_mativas_experimental(
                    db,
                    user_prompt=(
                        "Sou professora do ensino médio. Desafio: alunos não "
                        "aplicam o conteúdo. Gere roteiro PBL."
                    ),
                    metodologia="Aprendizagem Baseada em Problemas",
                )
            )
            assert calls == {"methodology": 1, "synthesize": 1, "prompt": 1}

            shadow_id = first["shadow_run_id"]
            c7_row = (
                db.query(CrystalShadowPhase)
                .filter(
                    CrystalShadowPhase.shadow_run_id == uuid.UUID(shadow_id),
                    CrystalShadowPhase.phase_id == "context7_mativas",
                )
                .order_by(CrystalShadowPhase.created_at.desc())
                .first()
            )
            assert c7_row is not None
            assert c7_row.origin == "experimental_lookup"
            edited = dict(c7_row.artifact_data)
            # marca edição no hit
            inner = dict(edited.get("artifact_data") or {})
            inner["nota_manual"] = "variacao-teste-crystal"
            edited["artifact_data"] = inner

            second = asyncio.run(
                experimental_edit_and_recalculate(
                    db,
                    shadow_id,
                    from_phase_id="context7_mativas",
                    artifact_data=edited,
                )
            )

    assert second["lookup_reexecuted"] is False
    assert second["context7_origin_after"] == "edited"
    # só downstream
    assert set(second["recalculated_phase_ids"]) == {
        "methodology",
        "synthesize",
        "entrega_final",
    }
    assert "context7_mativas" not in second["recalculated_phase_ids"]
    assert calls["methodology"] == 2
    assert calls["synthesize"] == 2
    assert calls["prompt"] == 2
    # Proveniência de runs oficiais não é usada (source null)
    from services.crystal_ball.models import CrystalShadowRun

    shadow = db.get(CrystalShadowRun, uuid.UUID(shadow_id))
    assert shadow.source_run_id is None
