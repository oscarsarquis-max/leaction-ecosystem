"""Pytest fixtures — QMind DB isolation tests (domain-docs-v0)."""

from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine, text

ADMIN_URL = os.getenv(
    "QMIND_DB_ADMIN_URL",
    "postgresql+psycopg://admin:password123@localhost:5433/qmind",
)
APP_URL = os.getenv(
    "DATABASE_URL_APP",
    "postgresql+psycopg://qmind_app:qmind_app_dev@localhost:5433/qmind",
)


@pytest.fixture(scope="session")
def admin_engine():
    eng = create_engine(ADMIN_URL, pool_pre_ping=True)
    yield eng
    eng.dispose()


@pytest.fixture(scope="session")
def app_engine():
    eng = create_engine(APP_URL, pool_pre_ping=True)
    yield eng
    eng.dispose()


@pytest.fixture()
def two_orgs(admin_engine):
    """Create two organizations + one assessment each; yield ids; cleanup."""
    with admin_engine.begin() as conn:
        org_a = conn.execute(
            text(
                "INSERT INTO organizations (name, status) VALUES ('Org A Isolation', 'active') RETURNING id"
            )
        ).scalar_one()
        org_b = conn.execute(
            text(
                "INSERT INTO organizations (name, status) VALUES ('Org B Isolation', 'active') RETURNING id"
            )
        ).scalar_one()

        model_id = conn.execute(
            text("SELECT id FROM assessment_models WHERE code = 'qmind_iso9001_diag' LIMIT 1")
        ).scalar_one()
        sv_id = conn.execute(
            text("SELECT id FROM standard_versions WHERE version_label = '2015' LIMIT 1")
        ).scalar_one()

        a_assess = conn.execute(
            text(
                """
                INSERT INTO assessments (
                  organization_id, assessment_model_id, standard_version_id, type, status
                ) VALUES (:org, :model, :sv, 'diagnosis', 'draft')
                RETURNING id
                """
            ),
            {"org": org_a, "model": model_id, "sv": sv_id},
        ).scalar_one()
        b_assess = conn.execute(
            text(
                """
                INSERT INTO assessments (
                  organization_id, assessment_model_id, standard_version_id, type, status
                ) VALUES (:org, :model, :sv, 'diagnosis', 'draft')
                RETURNING id
                """
            ),
            {"org": org_b, "model": model_id, "sv": sv_id},
        ).scalar_one()

    yield {
        "org_a": org_a,
        "org_b": org_b,
        "assess_a": a_assess,
        "assess_b": b_assess,
    }

    with admin_engine.begin() as conn:
        conn.execute(text("DELETE FROM assessments WHERE organization_id IN (:a, :b)"), {"a": org_a, "b": org_b})
        conn.execute(text("DELETE FROM organizations WHERE id IN (:a, :b)"), {"a": org_a, "b": org_b})
