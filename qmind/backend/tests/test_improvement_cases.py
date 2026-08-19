"""ImprovementCase — ISOI-002 Core foundation tests."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.main import app
from tests.conftest import ADMIN_URL


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
        json={"name": name or f"IC Org {sub[:8]}", "timezone": "America/Sao_Paulo"},
        headers=_headers(sub),
    )
    assert r.status_code == 201, r.text
    return r.json()["organization"]["id"]


def _create_case(
    client: TestClient,
    headers: dict[str, str],
    *,
    problem: str = "Atrasos recorrentes nas entregas",
    impact: str = "Quebra de SLA e reclamações",
    process: str = "Atendimento de pedidos",
) -> dict:
    r = client.post(
        "/api/v1/organizations/current/improvement-cases",
        headers=headers,
        json={
            "problem_statement": problem,
            "impact_statement": impact,
            "related_process": process,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def _reader_headers(org_id: str) -> dict[str, str]:
    sub = f"reader-{uuid.uuid4()}"
    eng = create_engine(ADMIN_URL)
    with eng.begin() as conn:
        user_id = conn.execute(
            text(
                """
                INSERT INTO users (idp_sub, email, status)
                VALUES (:sub, :email, 'active')
                RETURNING id
                """
            ),
            {"sub": sub, "email": f"{sub}@example.com"},
        ).scalar_one()
        conn.execute(
            text(
                """
                INSERT INTO memberships (organization_id, user_id, roles, status)
                VALUES (:org, :user, ARRAY['reader'], 'active')
                """
            ),
            {"org": org_id, "user": user_id},
        )
    eng.dispose()
    return _headers(sub, org_id)


@pytest.fixture()
def client():
    return TestClient(app)


def test_create_lists_orders_and_get_detail(client: TestClient):
    sub = f"ic-{uuid.uuid4()}"
    org = _create_org(client, sub)
    h = _headers(sub, org)

    first = _create_case(client, h, problem="Problema A")
    assert first["status"] == "open"
    assert first["organization_id"] == org
    assert first["problem_statement"] == "Problema A"
    assert first["created_by"]

    second = _create_case(client, h, problem="Problema B")
    listed = client.get("/api/v1/organizations/current/improvement-cases", headers=h)
    assert listed.status_code == 200, listed.text
    items = listed.json()
    assert [i["problem_statement"] for i in items[:2]] == ["Problema B", "Problema A"]

    detail = client.get(
        f"/api/v1/organizations/current/improvement-cases/{second['id']}",
        headers=h,
    )
    assert detail.status_code == 200
    assert detail.json()["id"] == second["id"]


def test_rejects_blank_and_whitespace(client: TestClient):
    sub = f"ic-blank-{uuid.uuid4()}"
    org = _create_org(client, sub)
    h = _headers(sub, org)
    bad = client.post(
        "/api/v1/organizations/current/improvement-cases",
        headers=h,
        json={
            "problem_statement": "   ",
            "impact_statement": "impacto",
            "related_process": "processo",
        },
    )
    assert bad.status_code == 422


def test_rejects_organization_id_in_body(client: TestClient):
    sub = f"ic-orgid-{uuid.uuid4()}"
    org = _create_org(client, sub)
    h = _headers(sub, org)
    bad = client.post(
        "/api/v1/organizations/current/improvement-cases",
        headers=h,
        json={
            "organization_id": str(uuid.uuid4()),
            "problem_statement": "p",
            "impact_statement": "i",
            "related_process": "r",
        },
    )
    assert bad.status_code == 422


def test_patch_facts_and_valid_transitions(client: TestClient):
    sub = f"ic-tr-{uuid.uuid4()}"
    org = _create_org(client, sub)
    h = _headers(sub, org)
    case = _create_case(client, h)
    cid = case["id"]

    patched = client.patch(
        f"/api/v1/organizations/current/improvement-cases/{cid}",
        headers=h,
        json={"problem_statement": "Atualizado", "impact_statement": "Novo impacto"},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["problem_statement"] == "Atualizado"

    for nxt in ("analyzing", "acting", "reviewing", "closed"):
        r = client.patch(
            f"/api/v1/organizations/current/improvement-cases/{cid}",
            headers=h,
            json={"status": nxt},
        )
        assert r.status_code == 200, r.text
        assert r.json()["status"] == nxt

    reopen = client.patch(
        f"/api/v1/organizations/current/improvement-cases/{cid}",
        headers=h,
        json={"status": "reviewing"},
    )
    assert reopen.status_code == 200
    assert reopen.json()["status"] == "reviewing"


def test_invalid_transition_and_immutable_fields(client: TestClient):
    sub = f"ic-bad-{uuid.uuid4()}"
    org = _create_org(client, sub)
    h = _headers(sub, org)
    case = _create_case(client, h)
    cid = case["id"]

    jump = client.patch(
        f"/api/v1/organizations/current/improvement-cases/{cid}",
        headers=h,
        json={"status": "closed"},
    )
    assert jump.status_code == 409

    immutable = client.patch(
        f"/api/v1/organizations/current/improvement-cases/{cid}",
        headers=h,
        json={"created_by": str(uuid.uuid4())},
    )
    assert immutable.status_code == 422


def test_reader_can_list_not_write(client: TestClient):
    sub = f"ic-admin-{uuid.uuid4()}"
    org = _create_org(client, sub)
    admin_h = _headers(sub, org)
    _create_case(client, admin_h)
    rh = _reader_headers(org)

    listed = client.get("/api/v1/organizations/current/improvement-cases", headers=rh)
    assert listed.status_code == 200
    assert len(listed.json()) >= 1

    denied = client.post(
        "/api/v1/organizations/current/improvement-cases",
        headers=rh,
        json={
            "problem_statement": "x",
            "impact_statement": "y",
            "related_process": "z",
        },
    )
    assert denied.status_code == 403

    cid = listed.json()[0]["id"]
    patch_denied = client.patch(
        f"/api/v1/organizations/current/improvement-cases/{cid}",
        headers=rh,
        json={"status": "analyzing"},
    )
    assert patch_denied.status_code == 403


def test_http_isolation_cross_tenant(client: TestClient):
    sub_a = f"ic-a-{uuid.uuid4()}"
    sub_b = f"ic-b-{uuid.uuid4()}"
    org_a = _create_org(client, sub_a, "IC Org A")
    org_b = _create_org(client, sub_b, "IC Org B")
    ha = _headers(sub_a, org_a)
    hb = _headers(sub_b, org_b)

    case_a = _create_case(client, ha, problem="Só A")
    _create_case(client, hb, problem="Só B")

    assert [
        i["problem_statement"]
        for i in client.get(
            "/api/v1/organizations/current/improvement-cases", headers=ha
        ).json()
    ] == ["Só A"]

    # A cannot open B's case id under A's org → 404 (indistinguishable)
    missing = client.get(
        f"/api/v1/organizations/current/improvement-cases/{case_a['id']}",
        headers=hb,
    )
    assert missing.status_code == 404

    # A cannot use B org header without membership
    denied = client.get(
        "/api/v1/organizations/current/improvement-cases",
        headers=_headers(sub_a, org_b),
    )
    assert denied.status_code == 403


def test_rls_sql_isolation(app_engine, admin_engine, two_orgs):
    org_a = two_orgs["org_a"]
    org_b = two_orgs["org_b"]

    with admin_engine.begin() as conn:
        user_a = conn.execute(
            text(
                """
                INSERT INTO users (idp_sub, email, status)
                VALUES (:s, :e, 'active') RETURNING id
                """
            ),
            {
                "s": f"rls-a-{uuid.uuid4()}",
                "e": f"rls-a-{uuid.uuid4()}@example.com",
            },
        ).scalar_one()
        user_b = conn.execute(
            text(
                """
                INSERT INTO users (idp_sub, email, status)
                VALUES (:s, :e, 'active') RETURNING id
                """
            ),
            {
                "s": f"rls-b-{uuid.uuid4()}",
                "e": f"rls-b-{uuid.uuid4()}@example.com",
            },
        ).scalar_one()
        conn.execute(
            text(
                """
                INSERT INTO improvement_cases (
                  organization_id, problem_statement, impact_statement,
                  related_process, status, created_by
                ) VALUES
                  (:a, 'A', 'ia', 'pa', 'open', :ua),
                  (:b, 'B', 'ib', 'pb', 'open', :ub)
                """
            ),
            {"a": org_a, "b": org_b, "ua": user_a, "ub": user_b},
        )

    with app_engine.connect() as conn:
        conn.execute(
            text("SELECT set_config('app.organization_id', :org, true)"),
            {"org": str(org_a)},
        )
        problems = conn.execute(
            text("SELECT problem_statement FROM improvement_cases ORDER BY problem_statement")
        ).scalars().all()
        assert problems == ["A"]

        leaked = conn.execute(
            text(
                "UPDATE improvement_cases SET problem_statement = 'leak' WHERE organization_id = :b"
            ),
            {"b": org_b},
        ).rowcount
        assert leaked == 0
        conn.commit()


def test_openapi_includes_improvement_cases(client: TestClient):
    schema = client.get("/openapi.json").json()
    paths = schema["paths"]
    assert "/api/v1/organizations/current/improvement-cases" in paths
    assert "/api/v1/organizations/current/improvement-cases/{case_id}" in paths
