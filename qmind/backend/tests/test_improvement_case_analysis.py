"""ImprovementCase analysis runs — ISOI-003 Core integration tests."""

from __future__ import annotations

import copy
import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.main import app
from app.modules.improvement_cases.fingerprint import fingerprint_problem_context_input
from app.modules.improvement_cases.problem_context_builder import build_problem_context_input
from app.modules.improvement_cases.problem_schemas import ProblemAnalysis
from app.modules.orgs.schemas import OrganizationProfileOut
from tests.conftest import ADMIN_URL

BASE = "/api/v1/organizations/current/improvement-cases"


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
        json={"name": name or f"PA Org {sub[:8]}", "timezone": "America/Sao_Paulo"},
        headers=_headers(sub),
    )
    assert r.status_code == 201, r.text
    return r.json()["organization"]["id"]


def _create_case(client: TestClient, headers: dict[str, str]) -> dict:
    r = client.post(
        BASE,
        headers=headers,
        json={
            "problem_statement": "Atrasos recorrentes",
            "impact_statement": "Quebra de SLA",
            "related_process": "Pedidos",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def _fill_profile(client: TestClient, headers: dict[str, str]) -> None:
    r = client.patch(
        "/api/v1/organizations/current/profile",
        headers=headers,
        json={
            "trade_name": "Acme",
            "summary": "Laboratório regional",
            "industry": "Saúde",
            "business_model": "b2b",
            "employee_range": "51-200",
            "unit_count": 2,
            "certification_status": "in_progress",
            "quality_structure": "formal_partial",
        },
    )
    assert r.status_code == 200, r.text


def _analysis_envelope(*, org_id: str, case_id: str, request_id: str) -> dict:
    return {
        "schema_version": "1.0",
        "core_organization_id": org_id,
        "improvement_case_id": case_id,
        "analysis_id": str(uuid.uuid4()),
        "request_id": request_id,
        "correlation_id": request_id,
        "generated_at": "2026-08-19T15:00:00Z",
        "context_status": "ready_for_initial_analysis",
        "interpretation_summary": "Síntese interpretativa do problema declarado.",
        "hypotheses": [
            {
                "code": "H-1",
                "statement": "Hipótese de processo",
                "rationale": "Racional",
                "support_status": "requires_validation",
                "supporting_facts": ["problem.statement"],
                "missing_information": ["evidence.process_flow"],
                "iso_basis": ["4.1", "4.4"],
            }
        ],
        "findings": [
            {
                "code": "F-1",
                "title": "Atenção ao processo",
                "description": "Achado interpretativo",
                "relationship_to_problem": "Relação",
                "business_impact": "Impacto",
                "supporting_facts": ["problem.related_process"],
                "missing_information": [],
                "iso_basis": ["4.4"],
                "recommended_next_step": "Mapear o fluxo",
                "requires_human_validation": True,
            }
        ],
        "limitations": ["Sem evidências nesta versão."],
    }


@pytest.fixture()
def client():
    return TestClient(app)


def test_fingerprint_stable_and_ignores_ids():
    profile = OrganizationProfileOut(
        organization_id=uuid.uuid4(),
        trade_name="Acme",
        legal_name="",
        summary="Resumo",
        industry="Saúde",
        business_model="b2b",
        employee_range="11-50",
        unit_count=1,
        certification_status="none",
        quality_structure="formal",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    case_id = uuid.uuid4()
    org_id = uuid.uuid4()
    a = build_problem_context_input(
        case_id=case_id,
        problem_statement="P",
        impact_statement="I",
        related_process="R",
        profile=profile,
        core_organization_id=org_id,
        request_id="req-a",
        correlation_id="corr-a",
    )
    b = build_problem_context_input(
        case_id=case_id,
        problem_statement="P",
        impact_statement="I",
        related_process="R",
        profile=profile,
        core_organization_id=org_id,
        request_id="req-b",
        correlation_id="corr-b",
    )
    assert fingerprint_problem_context_input(a) == fingerprint_problem_context_input(b)


def test_create_analysis_run_persists_and_lists(client: TestClient):
    sub = f"pa-{uuid.uuid4()}"
    org = _create_org(client, sub)
    h = _headers(sub, org)
    _fill_profile(client, h)
    case = _create_case(client, h)
    cid = case["id"]

    envelope = _analysis_envelope(org_id=org, case_id=cid, request_id="req-1")

    mock_client = MagicMock()
    mock_client.analyze_problem.return_value = ProblemAnalysis.model_validate(envelope)

    with patch(
        "app.modules.improvement_cases.analysis_service.OrganizationalIntelligenceClient",
        return_value=mock_client,
    ):
        r = client.post(f"{BASE}/{cid}/analysis-runs", headers=h)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["improvement_case_id"] == cid
    assert body["analysis"]["context_status"] == "ready_for_initial_analysis"
    assert body["is_stale"] is False
    assert mock_client.analyze_problem.called

    listed = client.get(f"{BASE}/{cid}/analysis-runs", headers=h)
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    detail = client.get(f"{BASE}/{cid}/analysis-runs/{body['id']}", headers=h)
    assert detail.status_code == 200
    assert detail.json()["id"] == body["id"]


def test_failure_does_not_persist(client: TestClient):
    sub = f"pa-fail-{uuid.uuid4()}"
    org = _create_org(client, sub)
    h = _headers(sub, org)
    _fill_profile(client, h)
    case = _create_case(client, h)
    cid = case["id"]

    mock_client = MagicMock()
    from app.errors import AppError

    mock_client.analyze_problem.side_effect = AppError(
        "oi_timeout", "timeout", status_code=504
    )

    with patch(
        "app.modules.improvement_cases.analysis_service.OrganizationalIntelligenceClient",
        return_value=mock_client,
    ):
        r = client.post(f"{BASE}/{cid}/analysis-runs", headers=h)
    assert r.status_code == 504
    listed = client.get(f"{BASE}/{cid}/analysis-runs", headers=h)
    assert listed.json() == []


def test_org_and_case_mismatch_not_persisted(client: TestClient):
    sub = f"pa-mm-{uuid.uuid4()}"
    org = _create_org(client, sub)
    h = _headers(sub, org)
    _fill_profile(client, h)
    case = _create_case(client, h)
    cid = case["id"]

    bad_org = copy.deepcopy(
        _analysis_envelope(org_id=str(uuid.uuid4()), case_id=cid, request_id="r")
    )
    mock_client = MagicMock()
    mock_client.analyze_problem.return_value = ProblemAnalysis.model_validate(bad_org)
    with patch(
        "app.modules.improvement_cases.analysis_service.OrganizationalIntelligenceClient",
        return_value=mock_client,
    ):
        assert client.post(f"{BASE}/{cid}/analysis-runs", headers=h).status_code == 502

    bad_case = _analysis_envelope(org_id=org, case_id=str(uuid.uuid4()), request_id="r2")
    mock_client.analyze_problem.return_value = ProblemAnalysis.model_validate(bad_case)
    with patch(
        "app.modules.improvement_cases.analysis_service.OrganizationalIntelligenceClient",
        return_value=mock_client,
    ):
        assert client.post(f"{BASE}/{cid}/analysis-runs", headers=h).status_code == 502

    assert client.get(f"{BASE}/{cid}/analysis-runs", headers=h).json() == []


def test_stale_on_fact_change_not_on_status(client: TestClient):
    sub = f"pa-stale-{uuid.uuid4()}"
    org = _create_org(client, sub)
    h = _headers(sub, org)
    _fill_profile(client, h)
    case = _create_case(client, h)
    cid = case["id"]
    envelope = _analysis_envelope(org_id=org, case_id=cid, request_id="req-s")
    mock_client = MagicMock()
    mock_client.analyze_problem.return_value = ProblemAnalysis.model_validate(envelope)

    with patch(
        "app.modules.improvement_cases.analysis_service.OrganizationalIntelligenceClient",
        return_value=mock_client,
    ):
        created = client.post(f"{BASE}/{cid}/analysis-runs", headers=h)
    assert created.status_code == 201

    # Status-only change must not stale
    assert (
        client.patch(
            f"{BASE}/{cid}", headers=h, json={"status": "analyzing"}
        ).status_code
        == 200
    )
    runs = client.get(f"{BASE}/{cid}/analysis-runs", headers=h).json()
    assert runs[0]["is_stale"] is False

    # Fact change must stale
    assert (
        client.patch(
            f"{BASE}/{cid}",
            headers=h,
            json={"problem_statement": "Problema atualizado"},
        ).status_code
        == 200
    )
    runs = client.get(f"{BASE}/{cid}/analysis-runs", headers=h).json()
    assert runs[0]["is_stale"] is True

    # Reanalyze creates new run; previous retained
    envelope2 = _analysis_envelope(org_id=org, case_id=cid, request_id="req-s2")
    mock_client.analyze_problem.return_value = ProblemAnalysis.model_validate(envelope2)
    with patch(
        "app.modules.improvement_cases.analysis_service.OrganizationalIntelligenceClient",
        return_value=mock_client,
    ):
        second = client.post(f"{BASE}/{cid}/analysis-runs", headers=h)
    assert second.status_code == 201
    all_runs = client.get(f"{BASE}/{cid}/analysis-runs", headers=h).json()
    assert len(all_runs) == 2
    assert all_runs[0]["is_stale"] is False
    assert all_runs[0]["id"] != all_runs[1]["id"]


def test_reader_cannot_generate(client: TestClient):
    sub = f"pa-admin-{uuid.uuid4()}"
    org = _create_org(client, sub)
    admin_h = _headers(sub, org)
    _fill_profile(client, admin_h)
    case = _create_case(client, admin_h)
    cid = case["id"]

    reader_sub = f"reader-{uuid.uuid4()}"
    eng = create_engine(ADMIN_URL)
    with eng.begin() as conn:
        user_id = conn.execute(
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
                VALUES (:org, :user, ARRAY['reader'], 'active')
                """
            ),
            {"org": org, "user": user_id},
        )
    eng.dispose()
    rh = _headers(reader_sub, org)
    denied = client.post(f"{BASE}/{cid}/analysis-runs", headers=rh)
    assert denied.status_code == 403


def test_cross_tenant_analysis_hidden(client: TestClient):
    sub_a = f"pa-a-{uuid.uuid4()}"
    sub_b = f"pa-b-{uuid.uuid4()}"
    org_a = _create_org(client, sub_a, "PA A")
    org_b = _create_org(client, sub_b, "PA B")
    ha = _headers(sub_a, org_a)
    hb = _headers(sub_b, org_b)
    _fill_profile(client, ha)
    case_a = _create_case(client, ha)
    cid = case_a["id"]
    envelope = _analysis_envelope(org_id=org_a, case_id=cid, request_id="ra")
    mock_client = MagicMock()
    mock_client.analyze_problem.return_value = ProblemAnalysis.model_validate(envelope)
    with patch(
        "app.modules.improvement_cases.analysis_service.OrganizationalIntelligenceClient",
        return_value=mock_client,
    ):
        run = client.post(f"{BASE}/{cid}/analysis-runs", headers=ha).json()

    assert client.get(f"{BASE}/{cid}/analysis-runs", headers=hb).status_code == 404
    assert (
        client.get(f"{BASE}/{cid}/analysis-runs/{run['id']}", headers=hb).status_code
        == 404
    )


def test_openapi_includes_analysis_runs(client: TestClient):
    paths = client.get("/openapi.json").json()["paths"]
    assert f"{BASE}/{{case_id}}/analysis-runs" in paths
    assert f"{BASE}/{{case_id}}/analysis-runs/{{run_id}}" in paths
