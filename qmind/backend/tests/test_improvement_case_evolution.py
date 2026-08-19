"""ISOI-005 — OutcomeObservation + Evolution projection tests."""

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
        json={"name": name or f"Evo Org {sub[:8]}", "timezone": "America/Sao_Paulo"},
        headers=_headers(sub),
    )
    assert r.status_code == 201, r.text
    return r.json()["organization"]["id"]


def _reader_headers(org_id: str) -> dict[str, str]:
    sub = f"reader-{uuid.uuid4()}"
    eng = create_engine(ADMIN_URL)
    with eng.begin() as conn:
        uid = conn.execute(
            text(
                """
                INSERT INTO users (idp_sub, email, display_name)
                VALUES (:s, :e, 'Reader')
                RETURNING id
                """
            ),
            {"s": sub, "e": f"{sub}@example.com"},
        ).scalar_one()
        conn.execute(
            text(
                """
                INSERT INTO memberships (organization_id, user_id, roles, status)
                VALUES (:org, :user, ARRAY['reader'], 'active')
                """
            ),
            {"org": org_id, "user": uid},
        )
    eng.dispose()
    return _headers(sub, org_id)


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


def _envelope(
    *,
    org_id: str,
    case_id: str,
    findings: list[dict] | None = None,
    limitations: list[str] | None = None,
    missing: list[str] | None = None,
    context_status: str = "ready_for_initial_analysis",
) -> dict:
    f = findings or [
        {
            "code": "F-1",
            "title": "Atenção ao processo",
            "description": "Desc",
            "relationship_to_problem": "Relação",
            "business_impact": "Impacto",
            "supporting_facts": [],
            "missing_information": missing or [],
            "iso_basis": ["4.4"],
            "recommended_next_step": "Mapear o fluxo",
            "requires_human_validation": True,
        }
    ]
    return {
        "schema_version": "1.0",
        "core_organization_id": org_id,
        "improvement_case_id": case_id,
        "analysis_id": str(uuid.uuid4()),
        "request_id": "req-evo",
        "correlation_id": "corr-evo",
        "generated_at": "2026-08-19T15:00:00Z",
        "context_status": context_status,
        "interpretation_summary": "Síntese",
        "hypotheses": [],
        "findings": f,
        "limitations": limitations if limitations is not None else ["Sem evidências."],
    }


def _create_run(
    client: TestClient,
    headers: dict[str, str],
    case_id: str,
    org_id: str,
    *,
    envelope: dict | None = None,
) -> dict:
    body = envelope or _envelope(org_id=org_id, case_id=case_id)
    mock = MagicMock()
    mock.analyze_problem.return_value = ProblemAnalysis.model_validate(body)
    with patch(
        "app.modules.improvement_cases.analysis_service.OrganizationalIntelligenceClient",
        return_value=mock,
    ):
        r = client.post(f"{CASES}/{case_id}/analysis-runs", headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def _obs_payload(**overrides) -> dict:
    base = {
        "result_direction": "improved",
        "observation_statement": "Atrasos diminuíram nas últimas semanas.",
        "measurement_basis": "Relatório de SLA",
        "observed_at": "2026-08-18T12:00:00-03:00",
    }
    base.update(overrides)
    return base


def _mark_items_done(plan_id: str) -> None:
    eng = create_engine(ADMIN_URL)
    with eng.begin() as conn:
        conn.execute(
            text(
                """
                UPDATE action_items
                SET status = 'done', updated_at = now()
                WHERE action_plan_id = :plan
                """
            ),
            {"plan": plan_id},
        )
    eng.dispose()


@pytest.fixture()
def client():
    return TestClient(app)


def test_migration_rls_outcome_observations():
    eng = create_engine(ADMIN_URL)
    with eng.connect() as conn:
        exists = conn.execute(
            text(
                """
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'improvement_case_outcome_observations'
                """
            )
        ).scalar()
        assert exists == 1
        rls = conn.execute(
            text(
                """
                SELECT relrowsecurity, relforcerowsecurity
                FROM pg_class
                WHERE relname = 'improvement_case_outcome_observations'
                """
            )
        ).one()
        assert rls.relrowsecurity is True
        assert rls.relforcerowsecurity is True
        pol = conn.execute(
            text(
                """
                SELECT polname FROM pg_policy
                WHERE polrelid = 'improvement_case_outcome_observations'::regclass
                """
            )
        ).scalar()
        assert pol == "tenant_isolation"
    eng.dispose()


def test_create_each_result_direction(client: TestClient):
    sub = f"evo-dir-{uuid.uuid4()}"
    org = _create_org(client, sub)
    h = _headers(sub, org)
    case = _create_case(client, h)
    for direction in ("improved", "unchanged", "worsened", "not_yet_measured"):
        r = client.post(
            f"{CASES}/{case['id']}/outcome-observations",
            headers=h,
            json=_obs_payload(result_direction=direction),
        )
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["result_direction"] == direction
        assert body["organization_id"] == org
        assert body["improvement_case_id"] == case["id"]
        assert body["created_by"]


def test_reject_blank_texts_and_naive_observed_at(client: TestClient):
    sub = f"evo-val-{uuid.uuid4()}"
    org = _create_org(client, sub)
    h = _headers(sub, org)
    case = _create_case(client, h)
    for bad in (
        _obs_payload(observation_statement="   "),
        _obs_payload(measurement_basis=""),
        _obs_payload(observed_at="2026-08-18T12:00:00"),
    ):
        r = client.post(
            f"{CASES}/{case['id']}/outcome-observations",
            headers=h,
            json=bad,
        )
        assert r.status_code == 422, r.text


def test_org_from_context_not_payload(client: TestClient):
    sub = f"evo-org-{uuid.uuid4()}"
    org = _create_org(client, sub)
    h = _headers(sub, org)
    case = _create_case(client, h)
    payload = _obs_payload()
    payload["organization_id"] = str(uuid.uuid4())
    payload["created_by"] = str(uuid.uuid4())
    r = client.post(
        f"{CASES}/{case['id']}/outcome-observations",
        headers=h,
        json=payload,
    )
    assert r.status_code == 422, r.text


def test_list_newest_first_and_empty(client: TestClient):
    sub = f"evo-list-{uuid.uuid4()}"
    org = _create_org(client, sub)
    h = _headers(sub, org)
    case = _create_case(client, h)
    empty = client.get(f"{CASES}/{case['id']}/outcome-observations", headers=h)
    assert empty.status_code == 200
    assert empty.json() == []

    client.post(
        f"{CASES}/{case['id']}/outcome-observations",
        headers=h,
        json=_obs_payload(observed_at="2026-08-10T12:00:00Z"),
    )
    client.post(
        f"{CASES}/{case['id']}/outcome-observations",
        headers=h,
        json=_obs_payload(
            observation_statement="Mais recente",
            observed_at="2026-08-18T12:00:00Z",
        ),
    )
    listed = client.get(f"{CASES}/{case['id']}/outcome-observations", headers=h)
    assert listed.status_code == 200
    rows = listed.json()
    assert len(rows) == 2
    assert rows[0]["observation_statement"] == "Mais recente"


def test_reader_cannot_create_can_list(client: TestClient):
    sub = f"evo-rd-{uuid.uuid4()}"
    org = _create_org(client, sub)
    h = _headers(sub, org)
    case = _create_case(client, h)
    client.post(
        f"{CASES}/{case['id']}/outcome-observations",
        headers=h,
        json=_obs_payload(),
    )
    rh = _reader_headers(org)
    denied = client.post(
        f"{CASES}/{case['id']}/outcome-observations",
        headers=rh,
        json=_obs_payload(observation_statement="Reader try"),
    )
    assert denied.status_code == 403
    ok = client.get(f"{CASES}/{case['id']}/outcome-observations", headers=rh)
    assert ok.status_code == 200
    assert len(ok.json()) == 1
    evo = client.get(f"{CASES}/{case['id']}/evolution", headers=rh)
    assert evo.status_code == 200


def test_cross_tenant_blocked(client: TestClient):
    sub_a = f"evo-a-{uuid.uuid4()}"
    sub_b = f"evo-b-{uuid.uuid4()}"
    org_a = _create_org(client, sub_a, "Org A")
    org_b = _create_org(client, sub_b, "Org B")
    ha = _headers(sub_a, org_a)
    hb = _headers(sub_b, org_b)
    case_a = _create_case(client, ha)
    client.post(
        f"{CASES}/{case_a['id']}/outcome-observations",
        headers=ha,
        json=_obs_payload(),
    )
    assert (
        client.get(f"{CASES}/{case_a['id']}/outcome-observations", headers=hb).status_code
        == 404
    )
    assert (
        client.post(
            f"{CASES}/{case_a['id']}/outcome-observations",
            headers=hb,
            json=_obs_payload(),
        ).status_code
        == 404
    )
    assert client.get(f"{CASES}/{case_a['id']}/evolution", headers=hb).status_code == 404


def test_append_only_no_update_endpoint(client: TestClient):
    sub = f"evo-ao-{uuid.uuid4()}"
    org = _create_org(client, sub)
    h = _headers(sub, org)
    case = _create_case(client, h)
    created = client.post(
        f"{CASES}/{case['id']}/outcome-observations",
        headers=h,
        json=_obs_payload(),
    ).json()
    oid = created["id"]
    patch_r = client.patch(
        f"{CASES}/{case['id']}/outcome-observations/{oid}",
        headers=h,
        json={"observation_statement": "hack"},
    )
    delete_r = client.delete(
        f"{CASES}/{case['id']}/outcome-observations/{oid}",
        headers=h,
    )
    assert patch_r.status_code in (404, 405)
    assert delete_r.status_code in (404, 405)
    listed = client.get(f"{CASES}/{case['id']}/outcome-observations", headers=h).json()
    assert len(listed) == 1
    assert listed[0]["observation_statement"] == created["observation_statement"]


def test_observation_does_not_change_status_or_stale(client: TestClient):
    sub = f"evo-stale-{uuid.uuid4()}"
    org = _create_org(client, sub)
    h = _headers(sub, org)
    _fill_profile(client, h)
    case = _create_case(client, h)
    run = _create_run(client, h, case["id"], org)
    assert run["is_stale"] is False
    fp = run["input_fingerprint"]
    status_before = client.get(f"{CASES}/{case['id']}", headers=h).json()["status"]
    client.post(
        f"{CASES}/{case['id']}/outcome-observations",
        headers=h,
        json=_obs_payload(),
    )
    after = client.get(f"{CASES}/{case['id']}/analysis-runs/{run['id']}", headers=h).json()
    assert after["input_fingerprint"] == fp
    assert after["is_stale"] is False
    case_after = client.get(f"{CASES}/{case['id']}", headers=h).json()
    assert case_after["status"] == status_before


def test_evolution_empty_and_one_run(client: TestClient):
    sub = f"evo-empty-{uuid.uuid4()}"
    org = _create_org(client, sub)
    h = _headers(sub, org)
    _fill_profile(client, h)
    case = _create_case(client, h)
    e0 = client.get(f"{CASES}/{case['id']}/evolution", headers=h).json()
    assert e0["analysis_summary"]["total_runs"] == 0
    assert e0["analysis_summary"]["comparison"] is None
    assert e0["action_summary"]["total"] == 0
    assert e0["latest_outcome_observation"] is None
    assert e0["closure_readiness"] == "insufficient_information"

    _create_run(client, h, case["id"], org)
    e1 = client.get(f"{CASES}/{case['id']}/evolution", headers=h).json()
    assert e1["analysis_summary"]["total_runs"] == 1
    assert e1["analysis_summary"]["latest_run"] is not None
    assert e1["analysis_summary"]["previous_run"] is None
    assert e1["analysis_summary"]["comparison"] is None
    assert e1["closure_readiness"] == "insufficient_information"


def test_evolution_two_runs_comparison(client: TestClient):
    sub = f"evo-cmp-{uuid.uuid4()}"
    org = _create_org(client, sub)
    h = _headers(sub, org)
    _fill_profile(client, h)
    case = _create_case(client, h)
    _create_run(
        client,
        h,
        case["id"],
        org,
        envelope=_envelope(
            org_id=org,
            case_id=case["id"],
            findings=[
                {
                    "code": "F-1",
                    "title": "A",
                    "description": "d",
                    "relationship_to_problem": "r",
                    "business_impact": "i",
                    "supporting_facts": [],
                    "missing_information": ["dado-x"],
                    "iso_basis": ["4.1"],
                    "recommended_next_step": "step",
                    "requires_human_validation": True,
                },
                {
                    "code": "F-2",
                    "title": "B",
                    "description": "d",
                    "relationship_to_problem": "r",
                    "business_impact": "i",
                    "supporting_facts": [],
                    "missing_information": [],
                    "iso_basis": ["4.4"],
                    "recommended_next_step": "step",
                    "requires_human_validation": True,
                },
            ],
            limitations=["L1", "L2"],
            context_status="ready_for_initial_analysis",
        ),
    )
    # Change problem so second run is allowed (non-stale path still creates new run)
    client.patch(
        f"{CASES}/{case['id']}",
        headers=h,
        json={"problem_statement": "Atrasos atualizados"},
    )
    _create_run(
        client,
        h,
        case["id"],
        org,
        envelope=_envelope(
            org_id=org,
            case_id=case["id"],
            findings=[
                {
                    "code": "F-1",
                    "title": "A",
                    "description": "d",
                    "relationship_to_problem": "r",
                    "business_impact": "i",
                    "supporting_facts": [],
                    "missing_information": ["dado-y"],
                    "iso_basis": ["4.1"],
                    "recommended_next_step": "step",
                    "requires_human_validation": True,
                },
                {
                    "code": "F-3",
                    "title": "C",
                    "description": "d",
                    "relationship_to_problem": "r",
                    "business_impact": "i",
                    "supporting_facts": [],
                    "missing_information": [],
                    "iso_basis": ["4.4"],
                    "recommended_next_step": "step",
                    "requires_human_validation": True,
                },
            ],
            limitations=["L1", "L3"],
            context_status="insufficient_context",
        ),
    )
    evo = client.get(f"{CASES}/{case['id']}/evolution", headers=h).json()
    cmp_ = evo["analysis_summary"]["comparison"]
    assert cmp_ is not None
    assert cmp_["context_status_before"] == "ready_for_initial_analysis"
    assert cmp_["context_status_after"] == "insufficient_context"
    assert set(cmp_["findings_added"]) == {"F-3"}
    assert set(cmp_["findings_removed"]) == {"F-2"}
    assert set(cmp_["findings_persisting"]) == {"F-1"}
    assert set(cmp_["missing_information_added"]) == {"dado-y"}
    assert set(cmp_["missing_information_removed"]) == {"dado-x"}
    assert set(cmp_["limitations_added"]) == {"L3"}
    assert set(cmp_["limitations_removed"]) == {"L2"}
    assert "resolvido" not in str(cmp_).lower()


def test_action_summary_and_completed_not_efficacy(client: TestClient):
    sub = f"evo-act-{uuid.uuid4()}"
    org = _create_org(client, sub)
    h = _headers(sub, org)
    _fill_profile(client, h)
    case = _create_case(client, h)
    run = _create_run(client, h, case["id"], org)
    mid = _membership_id(org, sub)
    due = (datetime.now(UTC) + timedelta(days=7)).isoformat()
    created = client.post(
        f"{CASES}/{case['id']}/analysis-runs/{run['id']}/findings/F-1/actions",
        headers=h,
        json={"owner_membership_id": mid, "due_at": due},
    )
    assert created.status_code == 201, created.text
    evo = client.get(f"{CASES}/{case['id']}/evolution", headers=h).json()
    assert evo["action_summary"]["total"] == 1
    assert evo["action_summary"]["completed"] == 0
    assert evo["closure_readiness"] == "insufficient_information"
    plan_id = evo["action_summary"]["plan"]["id"]
    _mark_items_done(plan_id)
    evo2 = client.get(f"{CASES}/{case['id']}/evolution", headers=h).json()
    assert evo2["action_summary"]["completed"] == 1
    # Completed action alone is not efficacy / not ready without observation
    assert evo2["closure_readiness"] == "insufficient_information"


def test_closure_readiness_matrix(client: TestClient):
    sub = f"evo-cl-{uuid.uuid4()}"
    org = _create_org(client, sub)
    h = _headers(sub, org)
    _fill_profile(client, h)
    case = _create_case(client, h)

    # no analysis
    assert (
        client.get(f"{CASES}/{case['id']}/evolution", headers=h).json()[
            "closure_readiness"
        ]
        == "insufficient_information"
    )

    run = _create_run(client, h, case["id"], org)
    mid = _membership_id(org, sub)
    due = (datetime.now(UTC) + timedelta(days=7)).isoformat()
    client.post(
        f"{CASES}/{case['id']}/analysis-runs/{run['id']}/findings/F-1/actions",
        headers=h,
        json={"owner_membership_id": mid, "due_at": due},
    )
    # pending action
    assert (
        client.get(f"{CASES}/{case['id']}/evolution", headers=h).json()[
            "closure_readiness"
        ]
        == "insufficient_information"
    )

    plan = client.get(f"{CASES}/{case['id']}/actions", headers=h).json()["plan"]
    _mark_items_done(plan["id"])
    # no observation
    assert (
        client.get(f"{CASES}/{case['id']}/evolution", headers=h).json()[
            "closure_readiness"
        ]
        == "insufficient_information"
    )

    client.post(
        f"{CASES}/{case['id']}/outcome-observations",
        headers=h,
        json=_obs_payload(result_direction="not_yet_measured"),
    )
    assert (
        client.get(f"{CASES}/{case['id']}/evolution", headers=h).json()[
            "closure_readiness"
        ]
        == "insufficient_information"
    )

    client.post(
        f"{CASES}/{case['id']}/outcome-observations",
        headers=h,
        json=_obs_payload(result_direction="improved"),
    )
    evo = client.get(f"{CASES}/{case['id']}/evolution", headers=h).json()
    assert evo["closure_readiness"] == "ready_for_review"
    assert evo["case"]["status"] == "open"  # no auto status change

    # stale latest → insufficient
    client.patch(
        f"{CASES}/{case['id']}",
        headers=h,
        json={"impact_statement": "Impacto novo"},
    )
    evo_stale = client.get(f"{CASES}/{case['id']}/evolution", headers=h).json()
    assert evo_stale["analysis_summary"]["latest_run"]["is_stale"] is True
    assert evo_stale["closure_readiness"] == "insufficient_information"


def test_openapi_evolution_paths(client: TestClient):
    paths = client.get("/openapi.json").json()["paths"]
    assert f"{CASES}/{{case_id}}/outcome-observations" in paths
    assert f"{CASES}/{{case_id}}/evolution" in paths
    obs = paths[f"{CASES}/{{case_id}}/outcome-observations"]
    assert "post" in obs and "get" in obs
    assert "get" in paths[f"{CASES}/{{case_id}}/evolution"]
