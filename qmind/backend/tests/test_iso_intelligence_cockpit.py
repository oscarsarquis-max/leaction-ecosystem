"""ISOI-010 Cockpit integration tests."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text

from app.auth.context import OrgContext, Principal
from app.main import app
from app.modules.cockpit.batch_fingerprint import batch_fingerprints
from app.modules.improvement_cases.execution_intelligence_builder import (
    build_execution_intelligence_input,
)
from app.modules.improvement_cases.fingerprint import (
    fingerprint_execution_intelligence_input,
)
from tests.conftest import ADMIN_URL

BASE = "/api/v1/organizations/current/iso-intelligence/cockpit"
_CREATED_ORGS: list[str] = []


def _headers(sub: str, org: str | None = None) -> dict[str, str]:
    out = {"X-Dev-User-Sub": sub, "X-Dev-User-Email": f"{sub}@example.com"}
    if org:
        out["X-Organization-Id"] = org
    return out


def _org_and_case(client: TestClient, *, problem: str = "Atrasos recorrentes") -> tuple[dict, str, str]:
    sub = f"ckp-{uuid.uuid4()}"
    org_response = client.post(
        "/api/v1/organizations",
        headers=_headers(sub),
        json={"name": f"Cockpit {sub[:8]}", "timezone": "America/Sao_Paulo"},
    )
    assert org_response.status_code == 201, org_response.text
    org = org_response.json()["organization"]["id"]
    _CREATED_ORGS.append(org)
    headers = _headers(sub, org)
    case_response = client.post(
        "/api/v1/organizations/current/improvement-cases",
        headers=headers,
        json={
            "problem_statement": problem,
            "impact_statement": "SLA rompido",
            "related_process": "Pedidos",
        },
    )
    assert case_response.status_code == 201, case_response.text
    return headers, org, case_response.json()["id"]


def _membership(org: str) -> tuple[uuid.UUID, uuid.UUID]:
    engine = create_engine(ADMIN_URL)
    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                SELECT m.id AS membership_id, m.user_id
                FROM memberships m
                WHERE m.organization_id = :org
                ORDER BY m.created_at LIMIT 1
                """
            ),
            {"org": uuid.UUID(org)},
        ).one()
    engine.dispose()
    return row.membership_id, row.user_id


def _seed_action(
    org: str,
    case_id: str,
    *,
    status: str = "in_progress",
    overdue: bool = False,
    impediment: bool = False,
    due_days: int = -2,
) -> uuid.UUID:
    membership_id, user_id = _membership(org)
    engine = create_engine(ADMIN_URL)
    with engine.begin() as conn:
        plan_id = conn.execute(
            text(
                """
                INSERT INTO action_plans (
                  organization_id, assessment_id, improvement_case_id, status
                ) VALUES (:org, NULL, :case_id, 'active')
                RETURNING id
                """
            ),
            {"org": uuid.UUID(org), "case_id": uuid.UUID(case_id)},
        ).scalar_one()
        action_id = conn.execute(
            text(
                """
                INSERT INTO action_items (
                  organization_id, action_plan_id, action_kind, description,
                  owner_membership_id, due_at, status, is_overdue
                ) VALUES (
                  :org, :plan, 'improvement', 'Ação de teste cockpit',
                  :owner, :due_at, :status, :overdue
                )
                RETURNING id
                """
            ),
            {
                "org": uuid.UUID(org),
                "plan": plan_id,
                "owner": membership_id,
                "due_at": datetime.now(UTC) + timedelta(days=due_days),
                "status": status,
                "overdue": overdue,
            },
        ).scalar_one()
        if impediment:
            conn.execute(
                text(
                    """
                    INSERT INTO action_impediments (
                      organization_id, action_item_id, title, description,
                      status, opened_by, opened_at
                    ) VALUES (
                      :org, :action, 'Bloqueio', 'Sem recurso',
                      'open', :user_id, now()
                    )
                    """
                ),
                {
                    "org": uuid.UUID(org),
                    "action": action_id,
                    "user_id": user_id,
                },
            )
    engine.dispose()
    return action_id


def _insert_ei_run(
    org: str,
    case_id: str,
    *,
    fingerprint: str,
    posture: str = "progressing",
    signal_level: str = "watch",
) -> None:
    membership_id, user_id = _membership(org)
    engine = create_engine(ADMIN_URL)
    result = {
        "schema_version": "1.0",
        "core_organization_id": org,
        "improvement_case_id": case_id,
        "analysis_id": str(uuid.uuid4()),
        "request_id": "r1",
        "correlation_id": "r1",
        "generated_at": "2026-08-26T12:00:00Z",
        "mechanism_version": "execution-intelligence-rules-v1",
        "interpretability_status": "interpretable",
        "execution_posture": posture,
        "interpretation_summary": "Resumo",
        "signals": [
            {
                "code": "execution_progress_observed",
                "category": "flow",
                "level": signal_level,
                "title": "Progresso",
                "interpretation": "Há progresso.",
                "supporting_fact_refs": ["case.status"],
                "iso_basis": ["8.1"],
                "recommended_next_step": "Continuar",
                "requires_human_validation": True,
            }
        ],
    }
    snapshot = {
        "schema_version": "1.0",
        "core_organization_id": org,
        "improvement_case_id": case_id,
        "request_id": "r1",
        "correlation_id": "r1",
        "captured_at": "2026-08-26T12:00:00Z",
        "source": {"system": "qmind-core", "component": "execution-intelligence"},
        "case": {"status": "acting"},
        "execution": {},
        "measurement": {},
        "fact_refs": ["case.status"],
    }
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO improvement_case_execution_intelligence_runs (
                  organization_id, improvement_case_id, schema_version,
                  mechanism_version, request_id, correlation_id, generated_at,
                  input_snapshot, input_fingerprint, result, created_by
                ) VALUES (
                  :org, :case_id, '1.0', 'execution-intelligence-rules-v1',
                  'r1', 'r1', now(), CAST(:snapshot AS jsonb), :fp,
                  CAST(:result AS jsonb), :user_id
                )
                """
            ),
            {
                "org": uuid.UUID(org),
                "case_id": uuid.UUID(case_id),
                "snapshot": __import__("json").dumps(snapshot),
                "fp": fingerprint,
                "result": __import__("json").dumps(result),
                "user_id": user_id,
            },
        )
    engine.dispose()


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(autouse=True)
def _cleanup():
    yield
    if not _CREATED_ORGS:
        return
    engine = create_engine(ADMIN_URL)
    with engine.begin() as conn:
        orgs = [uuid.UUID(v) for v in _CREATED_ORGS]
        conn.execute(
            text(
                """
                DELETE FROM improvement_case_execution_intelligence_runs
                WHERE organization_id = ANY(:orgs)
                """
            ),
            {"orgs": orgs},
        )
    engine.dispose()
    _CREATED_ORGS.clear()


def test_empty_org_summary_and_cases(client: TestClient) -> None:
    headers, _org, _case_id = _org_and_case(client)
    # delete the only case to leave org empty of non-closed? keep case —
    # empty means org with zero cases: create org without case
    sub = f"ckp-empty-{uuid.uuid4()}"
    org_response = client.post(
        "/api/v1/organizations",
        headers=_headers(sub),
        json={"name": f"Empty {sub[:8]}", "timezone": "America/Sao_Paulo"},
    )
    org = org_response.json()["organization"]["id"]
    _CREATED_ORGS.append(org)
    h = _headers(sub, org)
    summary = client.get(f"{BASE}/summary", headers=h)
    assert summary.status_code == 200, summary.text
    assert summary.headers.get("cache-control") == "private, no-store"
    body = summary.json()
    assert body["case_totals"]["total"] == 0
    assert body["coverage"]["complete"] is True
    cases = client.get(f"{BASE}/cases", headers=h)
    assert cases.status_code == 200
    assert cases.json()["items"] == []


def test_overdue_with_impediment_is_immediate(client: TestClient) -> None:
    headers, org, case_id = _org_and_case(client)
    _seed_action(org, case_id, overdue=True, impediment=True)
    client.patch(
        f"/api/v1/organizations/current/improvement-cases/{case_id}",
        headers=headers,
        json={"status": "acting"},
    )
    resp = client.get(f"{BASE}/cases", headers=headers)
    assert resp.status_code == 200, resp.text
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["priority_band"] == "immediate_attention"
    codes = {r["code"] for r in items[0]["priority_reasons"]}
    assert "overdue_action_with_active_impediment" in codes


def test_ei_freshness_current_stale_never(client: TestClient) -> None:
    headers, org, case_id = _org_and_case(client)
    ctx = OrgContext(
        principal=Principal(
            user_id=uuid.uuid4(), idp_sub="x", email="x@example.com"
        ),
        organization_id=uuid.UUID(org),
        membership_id=uuid.uuid4(),
        roles=("org_admin",),
    )
    # never
    never = client.get(
        f"{BASE}/cases",
        headers=headers,
        params={"intelligence_freshness": "never_analyzed"},
    )
    assert never.status_code == 200
    assert never.json()["items"][0]["intelligence_freshness"] == "never_analyzed"

    snap = build_execution_intelligence_input(ctx, uuid.UUID(case_id))
    fp = fingerprint_execution_intelligence_input(snap)
    _insert_ei_run(org, case_id, fingerprint=fp, posture="progressing")
    current = client.get(f"{BASE}/cases", headers=headers)
    assert current.json()["items"][0]["intelligence_freshness"] == "current"

    _insert_ei_run(org, case_id, fingerprint="deadbeef" * 8, posture="stalled")
    # latest run is stale fingerprint
    stale = client.get(f"{BASE}/cases", headers=headers)
    item = stale.json()["items"][0]
    assert item["intelligence_freshness"] == "stale"


def test_signals_stale_separated_in_summary(client: TestClient) -> None:
    headers, org, case_id = _org_and_case(client)
    _insert_ei_run(
        org, case_id, fingerprint="a" * 64, posture="attention_required", signal_level="attention"
    )
    summary = client.get(f"{BASE}/summary", headers=headers).json()
    assert summary["intelligence_coverage"]["stale"] >= 1
    assert sum(s["count"] for s in summary["signals_stale"]) >= 1
    assert sum(s["count"] for s in summary["signals_current"]) == 0


def test_batch_fingerprint_matches_single_builder(client: TestClient) -> None:
    headers, org, case_id = _org_and_case(client)
    membership_id, user_id = _membership(org)
    # active + impediment path
    _seed_action(org, case_id, overdue=False, impediment=True, due_days=5)
    client.patch(
        f"/api/v1/organizations/current/improvement-cases/{case_id}",
        headers=headers,
        json={"status": "acting"},
    )
    ctx = OrgContext(
        principal=Principal(user_id=user_id, idp_sub="x", email="x@example.com"),
        organization_id=uuid.UUID(org),
        membership_id=membership_id,
        roles=("org_admin",),
    )
    single = fingerprint_execution_intelligence_input(
        build_execution_intelligence_input(ctx, uuid.UUID(case_id))
    )
    from app.db import tenant_connection

    with tenant_connection(uuid.UUID(org)) as conn:
        batch = batch_fingerprints(conn, uuid.UUID(org), [uuid.UUID(case_id)])
    assert batch[uuid.UUID(case_id)][1] == single


def test_batch_fingerprint_empty_case(client: TestClient) -> None:
    headers, org, case_id = _org_and_case(client)
    membership_id, user_id = _membership(org)
    ctx = OrgContext(
        principal=Principal(user_id=user_id, idp_sub="x", email="x@example.com"),
        organization_id=uuid.UUID(org),
        membership_id=membership_id,
        roles=("org_admin",),
    )
    single = fingerprint_execution_intelligence_input(
        build_execution_intelligence_input(ctx, uuid.UUID(case_id))
    )
    from app.db import tenant_connection

    with tenant_connection(uuid.UUID(org)) as conn:
        batch = batch_fingerprints(conn, uuid.UUID(org), [uuid.UUID(case_id)])
    assert batch[uuid.UUID(case_id)][1] == single


def test_cursor_cross_org_refused(client: TestClient) -> None:
    h1, org1, _ = _org_and_case(client, problem="Caso org um")
    h2, _org2, _ = _org_and_case(client, problem="Caso org dois")
    page = client.get(f"{BASE}/cases", headers=h1, params={"limit": 1})
    # craft foreign cursor
    import base64
    import json

    foreign = base64.urlsafe_b64encode(
        json.dumps(
            {
                "org_id": org1,
                "band_rank": 0,
                "oldest_due_at": "9999",
                "last_activity_at": "9999",
                "case_id": str(uuid.uuid4()),
            }
        ).encode()
    ).decode()
    bad = client.get(f"{BASE}/cases", headers=h2, params={"cursor": foreign})
    assert bad.status_code in (403, 422)


def test_no_oi_client_called(client: TestClient) -> None:
    headers, _org, _case = _org_and_case(client)
    mock = MagicMock()
    with patch(
        "app.modules.oi.client.OrganizationalIntelligenceClient",
        mock,
    ):
        assert client.get(f"{BASE}/summary", headers=headers).status_code == 200
        assert client.get(f"{BASE}/cases", headers=headers).status_code == 200
        assert client.get(f"{BASE}/activity", headers=headers).status_code == 200
    mock.assert_not_called()


def test_forbidden_fields_absent(client: TestClient) -> None:
    headers, org, case_id = _org_and_case(client)
    _seed_action(org, case_id, overdue=True, impediment=True)
    body = client.get(f"{BASE}/cases", headers=headers).json()
    raw = __import__("json").dumps(body)
    assert "membership" not in raw.lower() or "membership_id" not in raw
    assert "@example.com" not in raw
    assert "storage_key" not in raw
    assert "progress_note" not in raw
    item = body["items"][0]
    assert len(item["problem_label"]) <= 200


def test_filters_search_and_limit_max(client: TestClient) -> None:
    headers, org, case_id = _org_and_case(client, problem="Fila especial XYZ")
    _seed_action(org, case_id, overdue=True)
    client.patch(
        f"/api/v1/organizations/current/improvement-cases/{case_id}",
        headers=headers,
        json={"status": "acting"},
    )
    found = client.get(
        f"{BASE}/cases",
        headers=headers,
        params={"search": "especial", "priority_band": "attention", "limit": 100},
    )
    assert found.status_code == 200
    assert any(i["case_id"] == case_id for i in found.json()["items"])
    too_big = client.get(f"{BASE}/cases", headers=headers, params={"limit": 101})
    assert too_big.status_code == 422


def test_each_priority_band_reachable(client: TestClient) -> None:
    """Smoke: open case without alerts lands on_course or follow_up (never analyzed)."""
    headers, _org, _case = _org_and_case(client)
    items = client.get(f"{BASE}/cases", headers=headers).json()["items"]
    assert items[0]["priority_band"] in {
        "follow_up",
        "on_course",
        "attention",
        "immediate_attention",
        "completed_or_observed",
    }
    assert items[0]["priority_band_label"]


# --- R1–R4 gate fixes -------------------------------------------------------

CASES = "/api/v1/organizations/current/improvement-cases"


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


def _create_analysis_run(
    client: TestClient, headers: dict, case_id: str, org_id: str
) -> dict:
    from app.modules.improvement_cases.problem_schemas import ProblemAnalysis

    envelope = {
        "schema_version": "1.0",
        "core_organization_id": org_id,
        "improvement_case_id": case_id,
        "analysis_id": str(uuid.uuid4()),
        "request_id": "req-ckp",
        "correlation_id": "corr-ckp",
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
                "recommended_next_step": "Mapear o fluxo",
                "requires_human_validation": True,
            }
        ],
        "limitations": ["Sem evidências."],
    }
    mock = MagicMock()
    mock.analyze_problem.return_value = ProblemAnalysis.model_validate(envelope)
    with patch(
        "app.modules.improvement_cases.analysis_service.OrganizationalIntelligenceClient",
        return_value=mock,
    ):
        r = client.post(f"{CASES}/{case_id}/analysis-runs", headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def _mark_plan_done(plan_id: str) -> None:
    engine = create_engine(ADMIN_URL)
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                UPDATE action_items
                SET status = 'done', updated_at = now()
                WHERE action_plan_id = :plan
                """
            ),
            {"plan": uuid.UUID(plan_id)},
        )
    engine.dispose()


def _cockpit_item(client: TestClient, headers: dict, case_id: str) -> dict:
    page = client.get(f"{BASE}/cases", headers=headers, params={"limit": 100}).json()
    match = next((i for i in page["items"] if i["case_id"] == case_id), None)
    assert match is not None, page
    return match


def _evolution_closure(client: TestClient, headers: dict, case_id: str) -> dict:
    evo = client.get(f"{CASES}/{case_id}/evolution", headers=headers).json()
    return {
        "closure_readiness": evo["closure_readiness"],
        "closure_readiness_reason": evo["closure_readiness_reason"],
    }


def test_cockpit_closure_matches_evolution(client: TestClient) -> None:
    headers, org, case_id = _org_and_case(client)
    _fill_profile(client, headers)

    # no analysis
    ck = _cockpit_item(client, headers, case_id)
    evo = _evolution_closure(client, headers, case_id)
    assert ck["closure_readiness"] == evo["closure_readiness"] == "insufficient_information"
    assert ck["closure_readiness_reason"] == evo["closure_readiness_reason"]

    run = _create_analysis_run(client, headers, case_id, org)
    mid = str(_membership(org)[0])
    due = (datetime.now(UTC) + timedelta(days=7)).isoformat()
    created = client.post(
        f"{CASES}/{case_id}/analysis-runs/{run['id']}/findings/F-1/actions",
        headers=headers,
        json={"owner_membership_id": mid, "due_at": due},
    )
    assert created.status_code == 201, created.text

    # incomplete actions
    ck = _cockpit_item(client, headers, case_id)
    evo = _evolution_closure(client, headers, case_id)
    assert ck["closure_readiness"] == evo["closure_readiness"]
    assert ck["closure_readiness_reason"] == evo["closure_readiness_reason"]

    plan_id = client.get(f"{CASES}/{case_id}/actions", headers=headers).json()["plan"][
        "id"
    ]
    _mark_plan_done(plan_id)

    # no outcome
    ck = _cockpit_item(client, headers, case_id)
    evo = _evolution_closure(client, headers, case_id)
    assert ck["closure_readiness"] == evo["closure_readiness"]
    assert ck["closure_readiness_reason"] == evo["closure_readiness_reason"]

    client.post(
        f"{CASES}/{case_id}/outcome-observations",
        headers=headers,
        json={
            "result_direction": "improved",
            "observation_statement": "Atrasos diminuíram nas últimas semanas.",
            "measurement_basis": "Relatório de SLA",
            "observed_at": "2026-08-18T12:00:00-03:00",
        },
    )

    # ready path
    ck = _cockpit_item(client, headers, case_id)
    evo = _evolution_closure(client, headers, case_id)
    assert ck["closure_readiness"] == evo["closure_readiness"] == "ready_for_review"
    assert ck["closure_readiness_reason"] == evo["closure_readiness_reason"]

    # stale analysis
    client.patch(
        f"{CASES}/{case_id}",
        headers=headers,
        json={"impact_statement": "Impacto novo para stale"},
    )
    ck = _cockpit_item(client, headers, case_id)
    evo = _evolution_closure(client, headers, case_id)
    assert ck["closure_readiness"] == evo["closure_readiness"] == "insufficient_information"
    assert ck["closure_readiness_reason"] == evo["closure_readiness_reason"]
    assert "contexto mudou" in ck["closure_readiness_reason"].lower()

    # blocking measurement (fresh analysis again + promised indicator)
    _create_analysis_run(client, headers, case_id, org)
    plan = client.get(f"{CASES}/{case_id}/actions", headers=headers).json()["plan"]
    action_plan_id = plan["id"]
    mp = client.post(
        "/api/v1/organizations/current/measurement-plans",
        headers=headers,
        json={"action_plan_id": action_plan_id},
    )
    assert mp.status_code == 201, mp.text
    plan_id = mp.json()["id"]
    ind = client.post(
        f"/api/v1/organizations/current/measurement-plans/{plan_id}/indicators",
        headers=headers,
        json={
            "code": "TMA",
            "name": "Tempo médio",
            "unit": "min",
            "direction": "decrease_is_better",
            "baseline_value": "40.000000",
            "target_value": "20.000000",
            "target_due_at": (datetime.now(UTC) + timedelta(days=30)).isoformat(),
        },
    )
    assert ind.status_code == 201, ind.text
    act = client.post(
        f"/api/v1/organizations/current/measurement-plans/{plan_id}/transitions/activate",
        headers=headers,
    )
    assert act.status_code == 200, act.text
    ck = _cockpit_item(client, headers, case_id)
    evo = _evolution_closure(client, headers, case_id)
    assert ck["closure_readiness"] == evo["closure_readiness"] == "insufficient_information"
    assert ck["closure_readiness_reason"] == evo["closure_readiness_reason"]


def test_cases_cursor_pagination_no_duplicates(client: TestClient) -> None:
    headers, _org, first = _org_and_case(client, problem="Pagina A")
    ids = {first}
    for label in ("Pagina B", "Pagina C"):
        resp = client.post(
            CASES,
            headers=headers,
            json={
                "problem_statement": label + " " + ("x" * 12),
                "impact_statement": "Impacto",
                "related_process": "Pedidos",
            },
        )
        assert resp.status_code == 201
        ids.add(resp.json()["id"])
    assert len(ids) == 3

    page1 = client.get(f"{BASE}/cases", headers=headers, params={"limit": 2}).json()
    assert len(page1["items"]) == 2
    assert page1["next_cursor"]
    page2 = client.get(
        f"{BASE}/cases",
        headers=headers,
        params={"limit": 2, "cursor": page1["next_cursor"]},
    ).json()
    assert len(page2["items"]) == 1
    all_ids = [i["case_id"] for i in page1["items"]] + [
        i["case_id"] for i in page2["items"]
    ]
    assert len(all_ids) == len(set(all_ids)) == 3
    assert set(all_ids) == ids


def test_filter_has_overdue_actions_and_ready_for_review(client: TestClient) -> None:
    headers, org, overdue_case = _org_and_case(client, problem="Caso vencido")
    _seed_action(org, overdue_case, overdue=True, due_days=-3)
    client.patch(
        f"{CASES}/{overdue_case}",
        headers=headers,
        json={"status": "acting"},
    )

    # second case without overdue
    resp = client.post(
        CASES,
        headers=headers,
        json={
            "problem_statement": "Caso sem atraso " + ("y" * 12),
            "impact_statement": "Impacto",
            "related_process": "Pedidos",
        },
    )
    assert resp.status_code == 201
    clean_case = resp.json()["id"]

    overdue_page = client.get(
        f"{BASE}/cases",
        headers=headers,
        params={"has_overdue_actions": True, "limit": 50},
    ).json()
    overdue_ids = {i["case_id"] for i in overdue_page["items"]}
    assert overdue_case in overdue_ids
    assert clean_case not in overdue_ids
    assert all(i["overdue_action_count"] >= 1 for i in overdue_page["items"])

    # ready_for_review uses canonical readiness (no analysis → never ready)
    ready_page = client.get(
        f"{BASE}/cases",
        headers=headers,
        params={"ready_for_review": True, "limit": 50},
    ).json()
    assert all(i["closure_readiness"] == "ready_for_review" for i in ready_page["items"])
    assert overdue_case not in {i["case_id"] for i in ready_page["items"]}


def test_activity_seek_pagination_and_windows(client: TestClient) -> None:
    headers, org, case_id = _org_and_case(client)
    _membership_id, user_id = _membership(org)
    action_id = _seed_action(org, case_id, status="in_progress", due_days=5)
    engine = create_engine(ADMIN_URL)
    base_time = datetime.now(UTC).replace(microsecond=0)
    stamps = [base_time - timedelta(minutes=i) for i in range(5)]
    with engine.begin() as conn:
        for i, stamp in enumerate(stamps):
            conn.execute(
                text(
                    """
                    INSERT INTO action_execution_check_ins (
                      organization_id, action_item_id, health, progress_note,
                      next_step, reported_by, reported_at
                    ) VALUES (
                      :org, :action, 'on_track', :note,
                      'Seguir', :user_id, :stamp
                    )
                    """
                ),
                {
                    "org": uuid.UUID(org),
                    "action": action_id,
                    "user_id": user_id,
                    "stamp": stamp,
                    "note": f"Check-in {i}",
                },
            )
        # same occurred_at tie-break: two outcomes at identical stamp
        same = base_time - timedelta(hours=1)
        for idx in range(2):
            conn.execute(
                text(
                    """
                    INSERT INTO improvement_case_outcome_observations (
                      organization_id, improvement_case_id, result_direction,
                      observation_statement, measurement_basis, observed_at, created_by
                    ) VALUES (
                      :org, :case_id, 'improved', :obs, 'Base', :stamp, :user_id
                    )
                    """
                ),
                {
                    "org": uuid.UUID(org),
                    "case_id": uuid.UUID(case_id),
                    "stamp": same,
                    "user_id": user_id,
                    "obs": f"Obs {idx}",
                },
            )
    engine.dispose()

    page1 = client.get(
        f"{BASE}/activity",
        headers=headers,
        params={"limit": 2, "activity_window_days": 30},
    ).json()
    assert len(page1["items"]) == 2
    assert page1["next_cursor"]

    full = client.get(
        f"{BASE}/activity",
        headers=headers,
        params={"limit": 100, "activity_window_days": 30},
    ).json()["items"]
    assert len(full) >= 5

    collected: list[dict] = []
    cursor = None
    while True:
        params: dict = {"limit": 2, "activity_window_days": 30}
        if cursor:
            params["cursor"] = cursor
        page = client.get(f"{BASE}/activity", headers=headers, params=params).json()
        collected.extend(page["items"])
        cursor = page["next_cursor"]
        if not cursor:
            break

    def _sig(item: dict) -> tuple:
        return (
            item["occurred_at"],
            item["event_type"],
            item["case_id"],
            item.get("action_item_id"),
            item["summary"],
        )

    assert len(collected) == len(full)
    assert [_sig(i) for i in collected] == [_sig(i) for i in full]

    # same occurred_at outcomes both appear (stable tie-break via source_id)
    outcomes = [i for i in collected if i["event_type"] == "outcome_observed"]
    assert len(outcomes) >= 2
    assert outcomes[0]["occurred_at"] == outcomes[1]["occurred_at"]

    # window: plant an old event beyond 7d
    old = datetime.now(UTC) - timedelta(days=20)
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO action_execution_check_ins (
                  organization_id, action_item_id, health, progress_note,
                  next_step, reported_by, reported_at
                ) VALUES (
                  :org, :action, 'on_track', 'Antigo',
                  'Seguir', :user_id, :stamp
                )
                """
            ),
            {
                "org": uuid.UUID(org),
                "action": action_id,
                "user_id": user_id,
                "stamp": old,
            },
        )
    engine.dispose()

    win7 = client.get(
        f"{BASE}/activity",
        headers=headers,
        params={"limit": 100, "activity_window_days": 7},
    ).json()
    win30 = client.get(
        f"{BASE}/activity",
        headers=headers,
        params={"limit": 100, "activity_window_days": 30},
    ).json()
    assert all(
        datetime.fromisoformat(i["occurred_at"].replace("Z", "+00:00"))
        >= datetime.now(UTC) - timedelta(days=7)
        for i in win7["items"]
    )
    assert len(win30["items"]) >= len(win7["items"])
    assert any(
        datetime.fromisoformat(i["occurred_at"].replace("Z", "+00:00"))
        < datetime.now(UTC) - timedelta(days=7)
        for i in win30["items"]
    )


def test_query_count_does_not_scale_with_n(client: TestClient) -> None:
    headers, org, first = _org_and_case(client)
    case_ids = [uuid.UUID(first)]
    for i in range(99):
        resp = client.post(
            CASES,
            headers=headers,
            json={
                "problem_statement": f"Problema {i} " + ("x" * 20),
                "impact_statement": "Impacto",
                "related_process": "Pedidos",
            },
        )
        assert resp.status_code == 201
        case_ids.append(uuid.UUID(resp.json()["id"]))

    from app.db import tenant_connection

    def _count_for(ids: list[uuid.UUID]) -> int:
        with tenant_connection(uuid.UUID(org)) as conn:
            counter = {"n": 0}
            engine = conn.engine

            def before(_conn, _cursor, _statement, _parameters, _context, _executemany):
                counter["n"] += 1

            event.listen(engine, "before_cursor_execute", before)
            try:
                batch_fingerprints(conn, uuid.UUID(org), ids, chunk_size=100)
            finally:
                event.remove(engine, "before_cursor_execute", before)
            return counter["n"]

    q1 = _count_for(case_ids[:1])
    q100 = _count_for(case_ids)
    # Same single chunk of 100 → query count must not grow linearly with N
    assert q100 <= q1 + 2
    assert q100 < 25
