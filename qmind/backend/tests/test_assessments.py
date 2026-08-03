"""Assessment vertical — draft, tenant list isolation, plan transition."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.main import app
from tests.conftest import ADMIN_URL


@pytest.fixture()
def client():
    return TestClient(app)


def _dev_headers(sub: str | None = None) -> dict[str, str]:
    sub = sub or f"dev-{uuid.uuid4()}"
    return {"X-Dev-User-Sub": sub, "X-Dev-User-Email": f"{sub}@example.com"}


def _catalog_ids():
    eng = create_engine(ADMIN_URL)
    with eng.connect() as conn:
        model = conn.execute(
            text("SELECT id FROM assessment_models WHERE code = 'qmind_iso9001_diag' LIMIT 1")
        ).scalar_one()
        sv = conn.execute(
            text("SELECT id FROM standard_versions WHERE version_label = '2015' LIMIT 1")
        ).scalar_one()
        req = conn.execute(
            text("SELECT id FROM requirements WHERE standard_version_id = :sv LIMIT 1"),
            {"sv": sv},
        ).scalar_one()
    eng.dispose()
    return model, sv, req


def _bootstrap_org(client: TestClient, headers: dict) -> str:
    r = client.post(
        "/api/v1/organizations",
        json={"name": f"Assess Org {uuid.uuid4().hex[:8]}"},
        headers=headers,
    )
    assert r.status_code == 201, r.text
    return r.json()["organization"]["id"]


def test_create_list_plan_assessment(client: TestClient):
    headers = _dev_headers()
    org_id = _bootstrap_org(client, headers)
    model_id, sv_id, req_id = _catalog_ids()
    h = {**headers, "X-Organization-Id": org_id}

    created = client.post(
        "/api/v1/assessments",
        json={
            "assessment_model_id": str(model_id),
            "standard_version_id": str(sv_id),
            "type": "diagnosis",
            "scope": [{"requirement_id": str(req_id)}],
        },
        headers=h,
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["status"] == "draft"
    assert body["organization_id"] == org_id
    assess_id = body["id"]

    listed = client.get("/api/v1/assessments", headers=h)
    assert listed.status_code == 200
    assert any(a["id"] == assess_id for a in listed.json())

    planned = client.post(f"/api/v1/assessments/{assess_id}/transitions/plan", headers=h)
    assert planned.status_code == 200, planned.text
    assert planned.json()["from_status"] == "draft"
    assert planned.json()["to_status"] == "planned"
    assert planned.json()["assessment"]["status"] == "planned"

    # Audit trail exists (admin read)
    eng = create_engine(ADMIN_URL)
    with eng.connect() as conn:
        n = conn.execute(
            text(
                """
                SELECT count(*) FROM platform_audit_events
                WHERE resource_id = :id AND action = 'assessment.plan'
                """
            ),
            {"id": assess_id},
        ).scalar_one()
    eng.dispose()
    assert n >= 1


def test_list_assessments_isolated_between_orgs(client: TestClient):
    model_id, sv_id, req_id = _catalog_ids()

    h1 = _dev_headers()
    org1 = _bootstrap_org(client, h1)
    ctx1 = {**h1, "X-Organization-Id": org1}
    a1 = client.post(
        "/api/v1/assessments",
        json={
            "assessment_model_id": str(model_id),
            "standard_version_id": str(sv_id),
            "scope": [{"requirement_id": str(req_id)}],
        },
        headers=ctx1,
    )
    assert a1.status_code == 201
    id1 = a1.json()["id"]

    h2 = _dev_headers()
    org2 = _bootstrap_org(client, h2)
    ctx2 = {**h2, "X-Organization-Id": org2}
    a2 = client.post(
        "/api/v1/assessments",
        json={
            "assessment_model_id": str(model_id),
            "standard_version_id": str(sv_id),
            "scope": [{"requirement_id": str(req_id)}],
        },
        headers=ctx2,
    )
    assert a2.status_code == 201
    id2 = a2.json()["id"]

    list1 = {a["id"] for a in client.get("/api/v1/assessments", headers=ctx1).json()}
    list2 = {a["id"] for a in client.get("/api/v1/assessments", headers=ctx2).json()}
    assert id1 in list1 and id2 not in list1
    assert id2 in list2 and id1 not in list2


def test_plan_without_scope_rejected(client: TestClient):
    headers = _dev_headers()
    org_id = _bootstrap_org(client, headers)
    model_id, sv_id, _req = _catalog_ids()
    h = {**headers, "X-Organization-Id": org_id}
    created = client.post(
        "/api/v1/assessments",
        json={
            "assessment_model_id": str(model_id),
            "standard_version_id": str(sv_id),
            "scope": [],
        },
        headers=h,
    )
    assert created.status_code == 201
    assess_id = created.json()["id"]
    planned = client.post(f"/api/v1/assessments/{assess_id}/transitions/plan", headers=h)
    assert planned.status_code == 422
    assert planned.json()["code"] == "plan_guard_scope"
