"""Evidence authorize → quarantine → approve|reject (no S3)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.test_assessment_ops import _create_draft_with_scope, _org_ctx
from tests.test_assessments import _dev_headers, _bootstrap_org, _catalog_ids


@pytest.fixture()
def client():
    return TestClient(app)


def _assessment_in_progress(client: TestClient):
    _headers, _org, h, model_id, sv_id, req_id = _org_ctx(client)
    aid = _create_draft_with_scope(client, h, model_id, sv_id, req_id)
    assert client.post(f"/api/v1/assessments/{aid}/transitions/plan", headers=h).status_code == 200
    assert client.post(f"/api/v1/assessments/{aid}/transitions/start", headers=h).status_code == 200
    return h, aid


def test_evidence_approve_path(client: TestClient):
    h, aid = _assessment_in_progress(client)
    auth = client.post(
        "/api/v1/evidences/authorize",
        json={"assessment_id": aid, "content_type": "application/pdf"},
        headers=h,
    )
    assert auth.status_code == 201, auth.text
    assert auth.json()["status"] == "upload_pending"
    eid = auth.json()["id"]
    assert auth.json()["storage_key"]

    recv = client.post(
        f"/api/v1/evidences/{eid}/transitions/receive",
        json={
            "content_hash": "sha256:deadbeefcafebabe",
            "content_type": "application/pdf",
            "byte_size": 1024,
        },
        headers=h,
    )
    assert recv.status_code == 200, recv.text
    assert recv.json()["to_status"] == "quarantined"

    ok = client.post(f"/api/v1/evidences/{eid}/transitions/security_pass", headers=h)
    assert ok.status_code == 200
    assert ok.json()["to_status"] == "approved"
    assert client.get(f"/api/v1/evidences/{eid}", headers=h).json()["status"] == "approved"


def test_evidence_reject_path(client: TestClient):
    h, aid = _assessment_in_progress(client)
    eid = client.post(
        "/api/v1/evidences/authorize",
        json={"assessment_id": aid},
        headers=h,
    ).json()["id"]
    client.post(
        f"/api/v1/evidences/{eid}/transitions/receive",
        json={"content_hash": "sha256:badfile0001", "byte_size": 10},
        headers=h,
    )
    fail = client.post(f"/api/v1/evidences/{eid}/transitions/security_fail", headers=h)
    assert fail.status_code == 200
    assert fail.json()["to_status"] == "rejected"


def test_authorize_blocked_before_start(client: TestClient):
    _headers, _org, h, model_id, sv_id, req_id = _org_ctx(client)
    aid = _create_draft_with_scope(client, h, model_id, sv_id, req_id)
    client.post(f"/api/v1/assessments/{aid}/transitions/plan", headers=h)
    r = client.post(
        "/api/v1/evidences/authorize",
        json={"assessment_id": aid},
        headers=h,
    )
    assert r.status_code == 409
    assert r.json()["code"] == "assessment_not_collecting"


def test_evidence_isolation(client: TestClient):
    h1, aid1 = _assessment_in_progress(client)
    eid = client.post(
        "/api/v1/evidences/authorize",
        json={"assessment_id": aid1},
        headers=h1,
    ).json()["id"]

    h2 = _dev_headers()
    org2 = _bootstrap_org(client, h2)
    ctx2 = {**h2, "X-Organization-Id": org2}
    assert client.get(f"/api/v1/evidences/{eid}", headers=ctx2).status_code == 404
