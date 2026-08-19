"""Testes corpus genérico + sugestao_prompt_geral + resultado real."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql+psycopg2://postgres:password@127.0.0.1:5435/orquestrador"

_FIXTURE_CORPUS = Path(__file__).resolve().parent / "_fixture_mini_corpus.json"


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


@pytest.fixture(scope="module", autouse=True)
def _write_fixture_corpus():
    data = {
        "itens": [
            {
                "codigo": "ALPHA",
                "titulo": "Item Alpha",
                "texto_literal": "COPIAR ISTO LITERALMENTE",
                "nota_livre": "pode parafrasear",
            },
            {
                "codigo": "BETA",
                "titulo": "Item Beta",
                "texto_literal": "OUTRO LITERAL",
                "nota_livre": "livre",
            },
        ]
    }
    _FIXTURE_CORPUS.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    yield
    # keep file for debugging; tests use absolute path in schema


def test_mativas_still_lookup_via_generic_wrapper():
    from services.crystal_ball.experimental_providers.mativas_lookup import (
        lookup_metodologia_exata,
    )

    hit = lookup_metodologia_exata("Aprendizagem Baseada em Problemas")
    assert hit is not None
    assert hit["metodologia"] == "Aprendizagem Baseada em Problemas"
    assert len(hit["passos"]) == 8


def test_generic_corpus_lookup_fixture():
    from services.crystal_ball.experimental_providers.generic_corpus_lookup import (
        lookup_by_chave,
    )

    schema = {
        "campo_chave": "codigo",
        "lista_raiz": "itens",
        "fonte_path": str(_FIXTURE_CORPUS),
        "campos_copia_literal": [
            {"campo": "texto_literal", "tipo": "texto"},
        ],
        "campos_sinteticos": ["nota_livre", "titulo"],
    }
    hit = lookup_by_chave(schema, "alpha")
    assert hit is not None
    assert hit["codigo"] == "ALPHA"
    assert hit["texto_literal"] == "COPIAR ISTO LITERALMENTE"


def test_campo_compare_texto_and_passos():
    from services.crystal_ball.campo_compare import compare_literal_fields
    from services.crystal_ball.experimental_providers.generic_corpus_lookup import (
        MATIVAS_SCHEMA_CONFIG,
        lookup_by_chave,
    )

    registro = lookup_by_chave(MATIVAS_SCHEMA_CONFIG, "Aprendizagem Baseada em Problemas")
    assert registro
    # gerado idêntico aos passos
    gen = {
        "passos": [
            {
                "titulo": p["imperativo"],
                "descricao": p["descricao_base"],
            }
            for p in registro["passos"]
        ]
    }
    cmp_ = compare_literal_fields(
        generated_artifact=gen,
        reference_record=registro,
        schema_config=MATIVAS_SCHEMA_CONFIG,
    )
    assert cmp_["identical_ratio"] == 1.0
    assert cmp_["nota_por_campo"]["passos"]["identical_count"] == 8


def test_register_second_corpus_and_sugestao(db):
    from services.crystal_ball.corpora import ensure_mativas_corpus, register_corpus
    from services.crystal_ball.models import CrystalShadowRun
    from services.crystal_ball.sugestao_prompt import gerar_sugestao_prompt_geral

    ensure_mativas_corpus(db)
    slug = f"mini-{uuid.uuid4().hex[:8]}"
    corpus = register_corpus(
        db,
        slug=slug,
        nome="Mini Corpus Teste",
        tipo_fonte="upload_json",
        schema_config={
            "campo_chave": "codigo",
            "lista_raiz": "itens",
            "fonte_path": str(_FIXTURE_CORPUS).replace("\\", "/"),
            "campos_copia_literal": [
                {"campo": "texto_literal", "tipo": "texto"},
            ],
            "campos_sinteticos": ["nota_livre"],
        },
    )

    # 2 shadows com comparison propositalmente falha no campo literal
    ids = []
    for i in range(2):
        sh = CrystalShadowRun(
            id=uuid.uuid4(),
            source_run_id=None,
            fork_phase_id="context7_corpus",
            status="experimental_done",
            spec={
                "metodologia": "ALPHA",
                "comparison": {
                    "nota_agregada": 0.0,
                    "identical_ratio": 0.0,
                    "chave_valor": "ALPHA",
                    "nota_por_campo": {
                        "texto_literal": {
                            "campo": "texto_literal",
                            "tipo": "texto",
                            "identical": False,
                            "identical_ratio": 0.0,
                        }
                    },
                },
            },
            notes=f"fixture {i}",
        )
        db.add(sh)
        ids.append(sh.id)
    db.commit()

    result = gerar_sugestao_prompt_geral(
        db, corpus_id=corpus.id, shadow_run_ids=ids, prompt_mestre="PROMPT X"
    )
    assert result["fase"] == "sugestao_prompt_geral"
    assert result["ciclo"]["numero_ciclo"] >= 1
    assert result["ciclo"]["nota_agregada"] == 0.0
    md = result["sugestao"]["markdown"]
    assert "substituição determinística" in md.lower() or "determinística" in md
    assert "texto_literal" in md
    assert "PROMPT X" in md
    assert "nunca escreve" in result["disclaimer"].lower() or "cópia manual" in result[
        "disclaimer"
    ].lower()

    # segundo ciclo
    result2 = gerar_sugestao_prompt_geral(
        db, corpus_id=corpus.id, shadow_run_ids=ids
    )
    assert result2["ciclo"]["numero_ciclo"] == result["ciclo"]["numero_ciclo"] + 1


def test_resultado_real_comparable(db):
    from services.crystal_ball.corpora import ensure_mativas_corpus
    from services.crystal_ball.resultado_real import registrar_resultado_real

    corpus = ensure_mativas_corpus(db)
    # passos idênticos → nota 1.0
    from services.crystal_ball.experimental_providers.mativas_lookup import (
        lookup_metodologia_exata,
    )

    reg = lookup_metodologia_exata("Aprendizagem Baseada em Problemas")
    payload = {
        "passos": [
            {"titulo": p["imperativo"], "descricao": p["descricao_base"]}
            for p in reg["passos"]
        ]
    }
    out = registrar_resultado_real(
        db,
        corpus_id=corpus.id,
        chave_valor="Aprendizagem Baseada em Problemas",
        payload=payload,
        desafio_texto="desafio teste",
        numero_ciclo=1,
    )
    assert out["comparison"]["nota_agregada"] == 1.0
    assert "manual" in out["disclaimer"].lower()
