"""Testes dos gates de qualidade do SDD (Assessment + frontend)."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from services.build_order import normalize_build_order  # noqa: E402
from services.sdd_quality import (  # noqa: E402
    apply_sdd_quality_gates,
    build_order_has_frontend,
    prd_requires_assessments,
    prd_requires_ui,
)


def test_prd_requires_assessments_and_ui():
    prd = (
        "LMS com avaliações, nota mínima 70% e player YouTube. "
        "Certificado PDF e portal do aluno."
    )
    assert prd_requires_assessments(prd)
    assert prd_requires_ui(prd)


def test_injects_assessment_appendix_and_frontend_module():
    prd = "Curso com avaliação, quiz e certificado. Interface SPA Next.js."
    sdd = """# SDD

## Stack Tecnológica
Fastify + Postgres

## Modelo de Dados
User, Course, Enrollment

## Contratos de API / Componentes
GET /courses
"""
    order = normalize_build_order(
        [
            {
                "modulo": "database-core",
                "depende_de": [],
                "escopo": "schema",
                "camada": "backend",
            },
            {
                "modulo": "lms-engine",
                "depende_de": ["database-core"],
                "escopo": "CRUD cursos",
                "camada": "backend",
            },
        ]
    )
    assert not build_order_has_frontend(order)

    md, new_order, warnings = apply_sdd_quality_gates(
        sdd_markdown=sdd,
        build_order=order,
        prd_text=prd,
        user_prompt="LMS educacional com player",
    )
    assert "sdd_missing_assessment_entities" in warnings
    assert "Assessment" in md
    assert "build_order_missing_frontend_module" in warnings
    assert build_order_has_frontend(new_order)
    fe = next(e for e in new_order if e["camada"] == "frontend")
    assert fe["modulo"] == "app-frontend"
    assert "lms-engine" in fe["depende_de"]


def test_does_not_duplicate_frontend_when_present():
    prd = "Portal do aluno com React"
    order = normalize_build_order(
        [
            {
                "modulo": "api-core",
                "depende_de": [],
                "escopo": "API",
                "camada": "backend",
            },
            {
                "modulo": "student-portal",
                "depende_de": ["api-core"],
                "escopo": "SPA React",
                "camada": "frontend",
            },
        ]
    )
    md, new_order, warnings = apply_sdd_quality_gates(
        sdd_markdown="## Modelo de Dados\nUser",
        build_order=order,
        prd_text=prd,
    )
    assert "build_order_missing_frontend_module" not in warnings
    assert len([e for e in new_order if e.get("camada") == "frontend"]) == 1
    assert md  # unchanged meaningfully


def test_normalize_build_order_infers_frontend_camada():
    order = normalize_build_order(
        [
            {
                "modulo": "media-player-ui",
                "depende_de": ["api"],
                "escopo": "player overlays",
            }
        ]
    )
    assert order[0]["camada"] == "frontend"
