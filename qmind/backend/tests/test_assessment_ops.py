"""Assessment ops — scope/team, start/reopen/cancel, mutation locks, roles, isolation."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.main import app
from tests.conftest import ADMIN_URL
from tests.test_assessments import _bootstrap_org, _catalog_ids, _dev_headers


@pytest.fixture()
def client():
    return TestClient(app)


def _org_ctx(client: TestClient):
    headers = _dev_headers()
    org_id = _bootstrap_org(client, headers)
    model_id, sv_id, req_id = _catalog_ids()
    h = {**headers, "X-Organization-Id": org_id}
    return headers, org_id, h, model_id, sv_id, req_id


def _create_draft_with_scope(client, h, model_id, sv_id, req_id):
    r = client.post(
        "/api/v1/assessments",
        json={
            "assessment_model_id": str(model_id),
            "standard_version_id": str(sv_id),
            "scope": [{"requirement_id": str(req_id)}],
        },
        headers=h,
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _second_membership(org_id: str, roles: list[str]) -> str:
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
            {"sub": f"mem-{uuid.uuid4()}", "email": f"{uuid.uuid4()}@ex.com"},
        ).scalar_one()
        mid = conn.execute(
            text(
                """
                INSERT INTO memberships (organization_id, user_id, roles, status)
                VALUES (:org, :user, :roles, 'active')
                RETURNING id
                """
            ),
            {"org": org_id, "user": user_id, "roles": roles},
        ).scalar_one()
    eng.dispose()
    return str(mid)


def test_scope_crud_and_blocked_after_plan(client: TestClient):
    _headers, _org, h, model_id, sv_id, req_id = _org_ctx(client)
    # create without scope then add
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
    aid = created.json()["id"]

    added = client.post(
        f"/api/v1/assessments/{aid}/scopes",
        json={"requirement_id": str(req_id)},
        headers=h,
    )
    assert added.status_code == 201, added.text
    scope_id = added.json()["id"]

    assert client.get(f"/api/v1/assessments/{aid}/scopes", headers=h).json()

    assert client.post(f"/api/v1/assessments/{aid}/transitions/plan", headers=h).status_code == 200

    blocked = client.post(
        f"/api/v1/assessments/{aid}/scopes",
        json={"requirement_id": str(req_id)},
        headers=h,
    )
    assert blocked.status_code == 409
    assert blocked.json()["code"] == "mutation_blocked"

    del_blocked = client.delete(f"/api/v1/assessments/{aid}/scopes/{scope_id}", headers=h)
    assert del_blocked.status_code == 409


def test_start_reopen_draft_cancel(client: TestClient):
    _headers, _org, h, model_id, sv_id, req_id = _org_ctx(client)
    aid = _create_draft_with_scope(client, h, model_id, sv_id, req_id)

    assert client.post(f"/api/v1/assessments/{aid}/transitions/plan", headers=h).status_code == 200
    started = client.post(f"/api/v1/assessments/{aid}/transitions/start", headers=h)
    assert started.status_code == 200
    assert started.json()["to_status"] == "in_progress"
    assert started.json()["assessment"]["started_at"] is not None

    # cancel from in_progress
    cancelled = client.post(f"/api/v1/assessments/{aid}/transitions/cancel", headers=h)
    assert cancelled.status_code == 200
    assert cancelled.json()["to_status"] == "cancelled"

    # new assessment for reopen path
    aid2 = _create_draft_with_scope(client, h, model_id, sv_id, req_id)
    client.post(f"/api/v1/assessments/{aid2}/transitions/plan", headers=h)
    reopened = client.post(f"/api/v1/assessments/{aid2}/transitions/reopen_draft", headers=h)
    assert reopened.status_code == 200
    assert reopened.json()["to_status"] == "draft"

    # scope editable again
    assert (
        client.post(
            f"/api/v1/assessments/{aid2}/scopes",
            json={"requirement_id": str(req_id)},
            headers=h,
        ).status_code
        == 201
    )


def test_cancel_from_planned(client: TestClient):
    _h, _o, h, model_id, sv_id, req_id = _org_ctx(client)
    aid = _create_draft_with_scope(client, h, model_id, sv_id, req_id)
    client.post(f"/api/v1/assessments/{aid}/transitions/plan", headers=h)
    r = client.post(f"/api/v1/assessments/{aid}/transitions/cancel", headers=h)
    assert r.status_code == 200
    assert r.json()["assessment"]["status"] == "cancelled"


def test_invalid_transition_start_from_draft(client: TestClient):
    _h, _o, h, model_id, sv_id, req_id = _org_ctx(client)
    aid = _create_draft_with_scope(client, h, model_id, sv_id, req_id)
    r = client.post(f"/api/v1/assessments/{aid}/transitions/start", headers=h)
    assert r.status_code == 409
    assert r.json()["code"] == "invalid_transition"


def test_reader_cannot_plan(client: TestClient):
    """SoD/roles: reader membership cannot mutate assessment."""
    admin_headers = _dev_headers()
    org_id = _bootstrap_org(client, admin_headers)
    model_id, sv_id, req_id = _catalog_ids()
    admin_h = {**admin_headers, "X-Organization-Id": org_id}
    aid = _create_draft_with_scope(client, admin_h, model_id, sv_id, req_id)

    # Create reader user+membership and auth as that user
    eng = create_engine(ADMIN_URL)
    sub = f"reader-{uuid.uuid4()}"
    with eng.begin() as conn:
        uid = conn.execute(
            text(
                "INSERT INTO users (idp_sub, email, status) VALUES (:s, :e, 'active') RETURNING id"
            ),
            {"s": sub, "e": f"{sub}@ex.com"},
        ).scalar_one()
        conn.execute(
            text(
                """
                INSERT INTO memberships (organization_id, user_id, roles, status)
                VALUES (:org, :u, ARRAY['reader'], 'active')
                """
            ),
            {"org": org_id, "u": uid},
        )
    eng.dispose()

    reader_h = {
        "X-Dev-User-Sub": sub,
        "X-Dev-User-Email": f"{sub}@ex.com",
        "X-Organization-Id": org_id,
    }
    r = client.post(f"/api/v1/assessments/{aid}/transitions/plan", headers=reader_h)
    assert r.status_code == 403
    assert r.json()["code"] == "forbidden"


def test_team_add_and_blocked_after_plan(client: TestClient):
    _h, org_id, h, model_id, sv_id, req_id = _org_ctx(client)
    aid = _create_draft_with_scope(client, h, model_id, sv_id, req_id)
    mid = _second_membership(org_id, ["consultant_auditor"])
    added = client.post(
        f"/api/v1/assessments/{aid}/team",
        json={"membership_id": mid, "team_role": "auditor"},
        headers=h,
    )
    assert added.status_code == 201, added.text
    client.post(f"/api/v1/assessments/{aid}/transitions/plan", headers=h)
    blocked = client.post(
        f"/api/v1/assessments/{aid}/team",
        json={"membership_id": _second_membership(org_id, ["reader"]), "team_role": "x"},
        headers=h,
    )
    assert blocked.status_code == 409


def test_assessment_isolation_ops(client: TestClient):
    model_id, sv_id, req_id = _catalog_ids()
    h1 = _dev_headers()
    org1 = _bootstrap_org(client, h1)
    ctx1 = {**h1, "X-Organization-Id": org1}
    aid1 = _create_draft_with_scope(client, ctx1, model_id, sv_id, req_id)

    h2 = _dev_headers()
    org2 = _bootstrap_org(client, h2)
    ctx2 = {**h2, "X-Organization-Id": org2}

    # org2 cannot see/plan org1 assessment
    assert client.get(f"/api/v1/assessments/{aid1}", headers=ctx2).status_code == 404
    assert (
        client.post(f"/api/v1/assessments/{aid1}/transitions/plan", headers=ctx2).status_code
        == 404
    )
