"""ISOI-004 — Finding → Action tests."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.main import app
from app.modules.improvement_cases.problem_schemas import ProblemAnalysis
from tests.conftest import ADMIN_URL

CASES = "/api/v1/organizations/current/improvement-cases"
PLANS = "/api/v1/action-plans"


def _headers(sub: str, org_id: str | None = None) -> dict[str, str]:
    h = {
        "X-Dev-User-Sub": sub,
        "X-Dev-User-Email": f"{sub}@example.com",
    }
    if org_id:
        h["X-Organization-Id"] = org_id
    return h


def _create_org(client: TestClient, sub: str, name: str | None = None) -> str:
    r = client.post(
        "/api/v1/organizations",
        json={"name": name or f"FA Org {sub[:8]}", "timezone": "America/Sao_Paulo"},
        headers=_headers(sub),
    )
    assert r.status_code == 201, r.text
    return r.json()["organization"]["id"]


def _membership_id(org_id: str, sub: str) -> str:
    eng = create_engine(ADMIN_URL)
    with eng.connect() as conn:
        mid = conn.execute(
            text(
                """
                SELECT m.id FROM memberships m
                JOIN users u ON u.id = m.user_id
                WHERE m.organization_id = :org AND u.idp_sub = :sub
                """
            ),
            {"org": org_id, "sub": sub},
        ).scalar_one()
    eng.dispose()
    return str(mid)


def _fill_profile(client: TestClient, headers: dict[str, str]) -> None:
    r = client.patch(
        "/api/v1/organizations/current/profile",
        headers=headers,
        json={
            "trade_name": "Acme",
            "summary": "Resumo",
            "industry": "Saúde",
            "business_model": "b2b",
            "employee_range": "11-50",
            "unit_count": 1,
            "certification_status": "none",
            "quality_structure": "formal",
        },
    )
    assert r.status_code == 200, r.text


def _create_case(client: TestClient, headers: dict[str, str]) -> dict:
    r = client.post(
        CASES,
        headers=headers,
        json={
            "problem_statement": "Atrasos",
            "impact_statement": "SLA",
            "related_process": "Pedidos",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def _envelope(*, org_id: str, case_id: str) -> dict:
    return {
        "schema_version": "1.0",
        "core_organization_id": org_id,
        "improvement_case_id": case_id,
        "analysis_id": str(uuid.uuid4()),
        "request_id": "req-fa",
        "correlation_id": "corr-fa",
        "generated_at": "2026-08-19T15:00:00Z",
        "context_status": "ready_for_initial_analysis",
        "interpretation_summary": "Síntese",
        "hypotheses": [],
        "findings": [
            {
                "code": "F-1",
                "title": "Atenção ao processo",
                "description": "Desc",
                "relationship_to_problem": "Relação",
                "business_impact": "Impacto",
                "supporting_facts": [],
                "missing_information": [],
                "iso_basis": ["4.4"],
                "recommended_next_step": "Mapear o fluxo do processo",
                "requires_human_validation": True,
            }
        ],
        "limitations": ["Sem evidências."],
    }


def _create_run(client: TestClient, headers: dict[str, str], case_id: str, org_id: str) -> dict:
    mock = MagicMock()
    mock.analyze_problem.return_value = ProblemAnalysis.model_validate(
        _envelope(org_id=org_id, case_id=case_id)
    )
    with patch(
        "app.modules.improvement_cases.analysis_service.OrganizationalIntelligenceClient",
        return_value=mock,
    ):
        r = client.post(f"{CASES}/{case_id}/analysis-runs", headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture()
def client():
    return TestClient(app)


def test_xor_assessment_plans_still_work(client: TestClient):
    """CHECK XOR rejects both-null; constraint exists; assessment create API still works shape."""
    eng = create_engine(ADMIN_URL)
    with eng.connect() as conn:
        name = conn.execute(
            text(
                """
                SELECT conname FROM pg_constraint
                WHERE conname = 'ck_action_plans_origin_xor'
                """
            )
        ).scalar()
        assert name == "ck_action_plans_origin_xor"

        org = conn.execute(
            text("SELECT id FROM organizations LIMIT 1")
        ).scalar()
        assert org is not None
        try:
            with conn.begin_nested():
                conn.execute(
                    text(
                        """
                        INSERT INTO action_plans (
                          organization_id, assessment_id, improvement_case_id, status
                        ) VALUES (:org, NULL, NULL, 'draft')
                        """
                    ),
                    {"org": org},
                )
            raise AssertionError("expected XOR check failure")
        except Exception as exc:
            assert "ck_action_plans_origin_xor" in str(exc) or "CheckViolation" in type(
                exc
            ).__name__
        conn.rollback()
    eng.dispose()


def test_create_action_from_finding_atomic_and_unique(client: TestClient):
    sub = f"fa-{uuid.uuid4()}"
    org = _create_org(client, sub)
    h = _headers(sub, org)
    _fill_profile(client, h)
    case = _create_case(client, h)
    run = _create_run(client, h, case["id"], org)
    owner = _membership_id(org, sub)
    due = (datetime.now(UTC) + timedelta(days=7)).isoformat()

    path = (
        f"{CASES}/{case['id']}/analysis-runs/{run['id']}/findings/F-1/actions"
    )
    r = client.post(
        path,
        headers=h,
        json={"owner_membership_id": owner, "due_at": due},
    )
    assert r.status_code == 201, r.text
    item = r.json()
    assert item["source_analysis_run_id"] == run["id"]
    assert item["source_finding_code"] == "F-1"
    assert "Mapear o fluxo" in item["description"]
    assert "Atenção ao processo" in item["description"]
    assert item["action_kind"] == "improvement"

    # Duplicate
    dup = client.post(
        path,
        headers=h,
        json={"owner_membership_id": owner, "due_at": due},
    )
    assert dup.status_code == 409

    listed = client.get(f"{CASES}/{case['id']}/actions", headers=h)
    assert listed.status_code == 200
    body = listed.json()
    assert body["plan"]["improvement_case_id"] == case["id"]
    assert body["plan"]["assessment_id"] is None
    assert len(body["items"]) == 1

    # Second finding on same run — add via SQL then create would need another finding;
    # reusing plan: create second finding in a new run
    env2 = _envelope(org_id=org, case_id=case["id"])
    env2["findings"][0]["code"] = "F-2"
    env2["findings"][0]["title"] = "Segundo achado"
    mock = MagicMock()
    mock.analyze_problem.return_value = ProblemAnalysis.model_validate(env2)
    with patch(
        "app.modules.improvement_cases.analysis_service.OrganizationalIntelligenceClient",
        return_value=mock,
    ):
        run2 = client.post(f"{CASES}/{case['id']}/analysis-runs", headers=h).json()
    r2 = client.post(
        f"{CASES}/{case['id']}/analysis-runs/{run2['id']}/findings/F-2/actions",
        headers=h,
        json={"owner_membership_id": owner, "due_at": due},
    )
    assert r2.status_code == 201, r2.text
    listed2 = client.get(f"{CASES}/{case['id']}/actions", headers=h).json()
    assert listed2["plan"]["id"] == body["plan"]["id"]
    assert len(listed2["items"]) == 2


def test_wrong_case_run_and_reader(client: TestClient):
    sub = f"fa-x-{uuid.uuid4()}"
    org = _create_org(client, sub)
    h = _headers(sub, org)
    _fill_profile(client, h)
    case_a = _create_case(client, h)
    case_b = _create_case(client, h)
    run_a = _create_run(client, h, case_a["id"], org)
    owner = _membership_id(org, sub)
    due = (datetime.now(UTC) + timedelta(days=3)).isoformat()

    # run of A under case B → 404
    bad = client.post(
        f"{CASES}/{case_b['id']}/analysis-runs/{run_a['id']}/findings/F-1/actions",
        headers=h,
        json={"owner_membership_id": owner, "due_at": due},
    )
    assert bad.status_code == 404

    # missing finding
    miss = client.post(
        f"{CASES}/{case_a['id']}/analysis-runs/{run_a['id']}/findings/NOPE/actions",
        headers=h,
        json={"owner_membership_id": owner, "due_at": due},
    )
    assert miss.status_code == 404

    # reader
    reader_sub = f"reader-{uuid.uuid4()}"
    eng = create_engine(ADMIN_URL)
    with eng.begin() as conn:
        uid = conn.execute(
            text(
                """
                INSERT INTO users (idp_sub, email, status)
                VALUES (:s, :e, 'active') RETURNING id
                """
            ),
            {"s": reader_sub, "e": f"{reader_sub}@example.com"},
        ).scalar_one()
        conn.execute(
            text(
                """
                INSERT INTO memberships (organization_id, user_id, roles, status)
                VALUES (:org, :u, ARRAY['reader'], 'active')
                """
            ),
            {"org": org, "u": uid},
        )
    eng.dispose()
    rh = _headers(reader_sub, org)
    denied = client.post(
        f"{CASES}/{case_a['id']}/analysis-runs/{run_a['id']}/findings/F-1/actions",
        headers=rh,
        json={"owner_membership_id": owner, "due_at": due},
    )
    assert denied.status_code == 403


def test_creating_action_does_not_stale_analysis(client: TestClient):
    sub = f"fa-stale-{uuid.uuid4()}"
    org = _create_org(client, sub)
    h = _headers(sub, org)
    _fill_profile(client, h)
    case = _create_case(client, h)
    run = _create_run(client, h, case["id"], org)
    owner = _membership_id(org, sub)
    due = (datetime.now(UTC) + timedelta(days=5)).isoformat()
    assert (
        client.post(
            f"{CASES}/{case['id']}/analysis-runs/{run['id']}/findings/F-1/actions",
            headers=h,
            json={"owner_membership_id": owner, "due_at": due},
        ).status_code
        == 201
    )
    runs = client.get(f"{CASES}/{case['id']}/analysis-runs", headers=h).json()
    assert runs[0]["is_stale"] is False
    assert runs[0]["id"] == run["id"]


def test_openapi_finding_action_paths(client: TestClient):
    paths = client.get("/openapi.json").json()["paths"]
    assert (
        f"{CASES}/{{case_id}}/analysis-runs/{{run_id}}/findings/{{finding_code}}/actions"
        in paths
    )
    assert f"{CASES}/{{case_id}}/actions" in paths
