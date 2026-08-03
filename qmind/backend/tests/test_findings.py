"""Finding create → draft → in_review → approved|rejected → rework (§4.1)."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.main import app
from app.storage.memory import InMemoryObjectStorage
from tests.conftest import ADMIN_URL
from tests.test_assessment_ops import _create_draft_with_scope, _org_ctx
from tests.test_assessments import _dev_headers


@pytest.fixture()
def client():
    return TestClient(app)


def _member_headers(org_id: str, roles: list[str]) -> dict[str, str]:
    sub = f"dev-{uuid.uuid4()}"
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
                VALUES (:org, :user, :roles, 'active')
                """
            ),
            {"org": org_id, "user": user_id, "roles": roles},
        )
    eng.dispose()
    return {**_dev_headers(sub), "X-Organization-Id": org_id}


def _setup_in_progress(client: TestClient):
    headers, org_id, h, model_id, sv_id, req_id = _org_ctx(client)
    aid = _create_draft_with_scope(client, h, model_id, sv_id, req_id)
    assert client.post(f"/api/v1/assessments/{aid}/transitions/plan", headers=h).status_code == 200
    assert client.post(f"/api/v1/assessments/{aid}/transitions/start", headers=h).status_code == 200
    return h, org_id, aid, str(req_id)


def _approved_evidence(client: TestClient, h: dict, aid: str) -> str:
    data = b"%PDF-1.4 finding-base"
    auth = client.post(
        "/api/v1/evidences/authorize",
        json={
            "assessment_id": aid,
            "content_type": "application/pdf",
            "declared_byte_size": len(data),
        },
        headers=h,
    )
    assert auth.status_code == 201, auth.text
    ev = auth.json()["evidence"]
    InMemoryObjectStorage.instance().put_test_object(
        ev["storage_key"], data, "application/pdf"
    )
    eid = ev["id"]
    assert client.post(f"/api/v1/evidences/{eid}/transitions/receive", headers=h).status_code == 200
    assert (
        client.post(f"/api/v1/evidences/{eid}/transitions/security_pass", headers=h).status_code
        == 200
    )
    return eid


def test_finding_approve_requires_evidence_and_sod(client: TestClient):
    h, org_id, aid, req_id = _setup_in_progress(client)
    eid = _approved_evidence(client, h, aid)

    created = client.post(
        "/api/v1/findings",
        json={
            "assessment_id": aid,
            "finding_type": "conformity",
            "title": "Process documented",
            "body": "Evidence shows documented process.",
            "requirement_ids": [req_id],
            "evidence_ids": [eid],
        },
        headers=h,
    )
    assert created.status_code == 201, created.text
    fid = created.json()["id"]
    assert created.json()["status"] == "draft"

    submitted = client.post(f"/api/v1/findings/{fid}/transitions/submit", headers=h)
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["to_status"] == "in_review"

    # Author cannot approve (SoD)
    sod = client.post(f"/api/v1/findings/{fid}/transitions/approve", headers=h)
    assert sod.status_code == 403
    assert sod.json()["code"] == "sod_violation"

    approver = _member_headers(org_id, ["quality_manager"])
    approved = client.post(f"/api/v1/findings/{fid}/transitions/approve", headers=approver)
    assert approved.status_code == 200, approved.text
    assert approved.json()["to_status"] == "approved"
    assert approved.json()["finding"]["approved_by"]


def test_conformity_rejects_insufficient_flag(client: TestClient):
    h, _org, aid, req_id = _setup_in_progress(client)
    r = client.post(
        "/api/v1/findings",
        json={
            "assessment_id": aid,
            "finding_type": "conformity",
            "title": "Bad",
            "body": "body",
            "requirement_ids": [req_id],
            "insufficient_evidence": True,
            "insufficient_evidence_rationale": "should fail",
        },
        headers=h,
    )
    assert r.status_code == 422  # DB check or app — either is fine


def test_nonconformity_insufficient_evidence_path(client: TestClient):
    h, org_id, aid, req_id = _setup_in_progress(client)
    created = client.post(
        "/api/v1/findings",
        json={
            "assessment_id": aid,
            "finding_type": "nonconformity",
            "title": "Missing records",
            "body": "Required records not available.",
            "requirement_ids": [req_id],
            "evidence_ids": [],
            "insufficient_evidence": True,
            "insufficient_evidence_rationale": "No retention records for 4.2.1",
        },
        headers=h,
    )
    assert created.status_code == 201, created.text
    fid = created.json()["id"]
    assert client.post(f"/api/v1/findings/{fid}/transitions/submit", headers=h).status_code == 200
    approver = _member_headers(org_id, ["quality_manager"])
    assert (
        client.post(f"/api/v1/findings/{fid}/transitions/approve", headers=approver).status_code
        == 200
    )


def test_reject_then_rework(client: TestClient):
    h, org_id, aid, req_id = _setup_in_progress(client)
    eid = _approved_evidence(client, h, aid)
    fid = client.post(
        "/api/v1/findings",
        json={
            "assessment_id": aid,
            "finding_type": "observation",
            "title": "Obs",
            "body": "body",
            "requirement_ids": [req_id],
            "evidence_ids": [eid],
        },
        headers=h,
    ).json()["id"]
    assert client.post(f"/api/v1/findings/{fid}/transitions/submit", headers=h).status_code == 200
    approver = _member_headers(org_id, ["org_admin"])
    rejected = client.post(
        f"/api/v1/findings/{fid}/transitions/reject",
        json={"reason": "Needs clearer link to requirement"},
        headers=approver,
    )
    assert rejected.status_code == 200
    assert rejected.json()["to_status"] == "rejected"
    reworked = client.post(f"/api/v1/findings/{fid}/transitions/rework", headers=h)
    assert reworked.status_code == 200
    assert reworked.json()["to_status"] == "draft"


def test_update_draft_and_conformity_rejects_insufficient_flag(client: TestClient):
    h, _org, aid, req_id = _setup_in_progress(client)
    eid = _approved_evidence(client, h, aid)
    created = client.post(
        "/api/v1/findings",
        json={
            "assessment_id": aid,
            "finding_type": "observation",
            "title": "Draft obs",
            "body": "initial",
            "requirement_ids": [req_id],
            "evidence_ids": [],
            "insufficient_evidence": True,
            "insufficient_evidence_rationale": "No sample yet",
        },
        headers=h,
    )
    assert created.status_code == 201, created.text
    fid = created.json()["id"]

    patched = client.patch(
        f"/api/v1/findings/{fid}",
        json={
            "finding_type": "conformity",
            "title": "Now conformity",
            "body": "updated body",
            "requirement_ids": [req_id],
            "evidence_ids": [eid],
            "insufficient_evidence": False,
        },
        headers=h,
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["finding_type"] == "conformity"
    assert patched.json()["evidence_ids"] == [eid]
    assert "correlation_id" not in patched.json() or patched.status_code == 200

    bad = client.patch(
        f"/api/v1/findings/{fid}",
        json={
            "finding_type": "conformity",
            "title": "Bad",
            "body": "body",
            "requirement_ids": [req_id],
            "evidence_ids": [eid],
            "insufficient_evidence": True,
            "insufficient_evidence_rationale": "not allowed",
        },
        headers=h,
    )
    assert bad.status_code == 422
    assert bad.json()["code"] == "insufficient_evidence_forbidden"
    assert "correlation_id" in bad.json()

    assert client.post(f"/api/v1/findings/{fid}/transitions/submit", headers=h).status_code == 200
    locked = client.patch(
        f"/api/v1/findings/{fid}",
        json={
            "finding_type": "conformity",
            "title": "locked",
            "body": "body",
            "requirement_ids": [req_id],
            "evidence_ids": [eid],
        },
        headers=h,
    )
    assert locked.status_code == 409


def test_submit_without_approved_evidence_fails_for_conformity(client: TestClient):
    h, _org, aid, req_id = _setup_in_progress(client)
    # authorize → receive (quarantined) — must not be linkable to Finding
    data = b"pending-only"
    auth = client.post(
        "/api/v1/evidences/authorize",
        json={
            "assessment_id": aid,
            "content_type": "application/pdf",
            "declared_byte_size": len(data),
        },
        headers=h,
    )
    eid = auth.json()["evidence"]["id"]
    InMemoryObjectStorage.instance().put_test_object(
        auth.json()["evidence"]["storage_key"], data, "application/pdf"
    )
    client.post(f"/api/v1/evidences/{eid}/transitions/receive", headers=h)

    blocked = client.post(
        "/api/v1/findings",
        json={
            "assessment_id": aid,
            "finding_type": "conformity",
            "title": "Premature",
            "body": "body",
            "requirement_ids": [req_id],
            "evidence_ids": [eid],
        },
        headers=h,
    )
    assert blocked.status_code == 422
    assert blocked.json()["code"] == "evidence_not_approved"
    assert "correlation_id" in blocked.json()

    # Finding without evidence_ids can be created; submit still requires approved base
    fid = client.post(
        "/api/v1/findings",
        json={
            "assessment_id": aid,
            "finding_type": "conformity",
            "title": "Premature",
            "body": "body",
            "requirement_ids": [req_id],
            "evidence_ids": [],
        },
        headers=h,
    ).json()["id"]
    bad = client.post(f"/api/v1/findings/{fid}/transitions/submit", headers=h)
    assert bad.status_code == 422
    assert bad.json()["code"] == "evidence_base_required"
