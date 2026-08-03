"""Report snapshot, SoD publish, supersede-on-publish, PDF job, Assessment.close."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.storage.memory import InMemoryObjectStorage
from tests.test_assessment_ops import _create_draft_with_scope, _org_ctx
from tests.test_findings import _member_headers
from tests.test_maturity import _catalog_criteria, _fill_all_level3


@pytest.fixture()
def client():
    return TestClient(app)


def _due():
    return (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()


def _approved_evidence(client, h, aid) -> str:
    data = b"%PDF-1.4 report"
    auth = client.post(
        "/api/v1/evidences/authorize",
        json={
            "assessment_id": aid,
            "content_type": "application/pdf",
            "declared_byte_size": len(data),
        },
        headers=h,
    )
    ev = auth.json()["evidence"]
    InMemoryObjectStorage.instance().put_test_object(ev["storage_key"], data, "application/pdf")
    eid = ev["id"]
    client.post(f"/api/v1/evidences/{eid}/transitions/receive", headers=h)
    client.post(f"/api/v1/evidences/{eid}/transitions/security_pass", headers=h)
    return eid


def _report_ready(client: TestClient):
    """Assessment in report with approved finding, maturity, and action plan."""
    _headers, org_id, h, model_id, sv_id, req_id = _org_ctx(client)
    aid = _create_draft_with_scope(client, h, model_id, sv_id, req_id)
    client.post(f"/api/v1/assessments/{aid}/transitions/plan", headers=h)
    client.post(f"/api/v1/assessments/{aid}/transitions/start", headers=h)
    eid = _approved_evidence(client, h, aid)

    # Finding approved
    fid = client.post(
        "/api/v1/findings",
        json={
            "assessment_id": aid,
            "finding_type": "conformity",
            "title": "OK",
            "body": "body",
            "requirement_ids": [str(req_id)],
            "evidence_ids": [eid],
        },
        headers=h,
    ).json()["id"]
    client.post(f"/api/v1/findings/{fid}/transitions/submit", headers=h)
    qm = _member_headers(org_id, ["quality_manager"])
    client.post(f"/api/v1/findings/{fid}/transitions/approve", headers=qm)

    client.post(f"/api/v1/assessments/{aid}/transitions/begin_analysis", headers=h)

    # Maturity approved
    pid = client.post(
        "/api/v1/maturity-assessments", json={"assessment_id": aid}, headers=h
    ).json()["id"]
    _fill_all_level3(client, h, pid, eid)
    client.post(f"/api/v1/maturity-assessments/{pid}/transitions/submit", headers=h)
    client.post(f"/api/v1/maturity-assessments/{pid}/transitions/approve", headers=qm)

    client.post(f"/api/v1/assessments/{aid}/transitions/open_actions", headers=h)
    plan = client.post("/api/v1/action-plans", json={"assessment_id": aid}, headers=h).json()
    owner = client.get("/api/v1/organizations/me/memberships", headers=h).json()
    owner_mid = next(m["id"] for m in owner if m["organization_id"] == org_id)
    client.post(
        f"/api/v1/action-plans/{plan['id']}/items",
        json={
            "finding_id": fid,
            "action_kind": "improvement",
            "description": "Improve",
            "owner_membership_id": owner_mid,
            "due_at": _due(),
            "efficacy_required": False,
        },
        headers=h,
    )
    client.post(f"/api/v1/action-plans/{plan['id']}/transitions/activate", headers=h)
    client.post(f"/api/v1/assessments/{aid}/transitions/begin_report", headers=h)
    return h, org_id, aid, fid, pid, qm


def test_report_publish_sod_snapshot_and_idempotent(client: TestClient):
    h, org_id, aid, fid, mid, qm = _report_ready(client)
    created = client.post(
        "/api/v1/reports",
        json={"assessment_id": aid, "include_maturity": True, "include_action_plan": True},
        headers=h,
    )
    assert created.status_code == 201, created.text
    rid = created.json()["id"]
    snap = created.json()["structured_content"]
    assert any(f["id"] == fid for f in snap["findings"])
    assert snap["maturity"]["id"] == mid
    assert snap["action_plan"]["items"]

    assert client.post(f"/api/v1/reports/{rid}/transitions/submit", headers=h).status_code == 200
    sod = client.post(f"/api/v1/reports/{rid}/transitions/publish", headers=h)
    assert sod.status_code == 403
    assert sod.json()["code"] == "sod_violation"

    pub = client.post(f"/api/v1/reports/{rid}/transitions/publish", headers=qm)
    assert pub.status_code == 200
    assert pub.json()["to_status"] == "published"

    again = client.post(f"/api/v1/reports/{rid}/transitions/publish", headers=qm)
    assert again.status_code == 200
    assert again.json()["to_status"] == "published"

    job = client.post(f"/api/v1/reports/{rid}/export-pdf", headers=h)
    assert job.status_code == 202
    assert job.json()["job_type"] == "report_pdf_export"
    assert job.json()["status"] == "queued"
    assert job.json()["organization_id"] == org_id
    assert job.json()["input_ref"]["report_id"] == rid
    assert job.json()["input_ref"]["report_version_no"] == 1
    assert job.json()["input_ref"]["organization_id"] == org_id
    job2 = client.post(f"/api/v1/reports/{rid}/export-pdf", headers=h)
    assert job2.json()["id"] == job.json()["id"]  # idempotent job


def test_request_changes_discard_and_close(client: TestClient):
    h, org_id, aid, _fid, _mid, qm = _report_ready(client)
    rid = client.post("/api/v1/reports", json={"assessment_id": aid}, headers=h).json()["id"]
    client.post(f"/api/v1/reports/{rid}/transitions/submit", headers=h)
    ch = client.post(
        f"/api/v1/reports/{rid}/transitions/request_changes",
        json={"reason": "Expand maturity section"},
        headers=qm,
    )
    assert ch.status_code == 200
    assert ch.json()["to_status"] == "draft"

    discarded = client.post(
        f"/api/v1/reports/{rid}/transitions/discard",
        json={"reason": "start over"},
        headers=h,
    )
    assert discarded.status_code == 200
    assert discarded.json()["to_status"] == "discarded"

    # new report → publish → close assessment
    rid2 = client.post("/api/v1/reports", json={"assessment_id": aid}, headers=h).json()["id"]
    client.post(f"/api/v1/reports/{rid2}/transitions/submit", headers=h)
    client.post(f"/api/v1/reports/{rid2}/transitions/publish", headers=qm)
    closed = client.post(f"/api/v1/assessments/{aid}/transitions/close", headers=h)
    assert closed.status_code == 200
    assert closed.json()["to_status"] == "closed"

    archived = client.post(f"/api/v1/reports/{rid2}/transitions/archive", headers=qm)
    assert archived.status_code == 200
    assert archived.json()["to_status"] == "archived"


def test_close_with_waiver_without_published(client: TestClient):
    h, org_id, aid, _fid, _mid, qm = _report_ready(client)
    blocked = client.post(f"/api/v1/assessments/{aid}/transitions/close", headers=h)
    assert blocked.status_code == 422
    assert blocked.json()["code"] == "close_waiver_required"

    empty = client.post(
        f"/api/v1/assessments/{aid}/transitions/close",
        json={"waiver_reason": "   "},
        headers=qm,
    )
    assert empty.status_code == 422

    consultant = _member_headers(org_id, ["consultant_auditor"])
    forbidden = client.post(
        f"/api/v1/assessments/{aid}/transitions/close",
        json={"waiver_reason": "try"},
        headers=consultant,
    )
    assert forbidden.status_code == 403

    waived = client.post(
        f"/api/v1/assessments/{aid}/transitions/close",
        json={"waiver_reason": "Client declined formal report"},
        headers=qm,
    )
    assert waived.status_code == 200
    assert waived.json()["to_status"] == "closed"


def test_supersede_only_when_new_published(client: TestClient):
    h, org_id, aid, _fid, _mid, qm = _report_ready(client)
    r1 = client.post("/api/v1/reports", json={"assessment_id": aid}, headers=h).json()["id"]
    client.post(f"/api/v1/reports/{r1}/transitions/submit", headers=h)
    client.post(f"/api/v1/reports/{r1}/transitions/publish", headers=qm)
    assert client.get(f"/api/v1/reports/{r1}", headers=h).json()["status"] == "published"

    r2 = client.post("/api/v1/reports", json={"assessment_id": aid}, headers=h).json()
    assert r2["supersedes_report_id"] == r1
    assert r2["version_no"] == 2
    # v1 still published until v2 publishes
    assert client.get(f"/api/v1/reports/{r1}", headers=h).json()["status"] == "published"
    client.post(f"/api/v1/reports/{r2['id']}/transitions/submit", headers=h)
    client.post(f"/api/v1/reports/{r2['id']}/transitions/publish", headers=qm)
    assert client.get(f"/api/v1/reports/{r1}", headers=h).json()["status"] == "superseded"
    assert client.get(f"/api/v1/reports/{r2['id']}", headers=h).json()["status"] == "published"


def test_published_snapshot_immutable_after_source_change(client: TestClient):
    from sqlalchemy import create_engine, text

    from tests.conftest import ADMIN_URL

    h, _org, aid, fid, mid, qm = _report_ready(client)
    rid = client.post("/api/v1/reports", json={"assessment_id": aid}, headers=h).json()["id"]
    snap_title = client.get(f"/api/v1/reports/{rid}", headers=h).json()["structured_content"][
        "findings"
    ][0]["title"]
    client.post(f"/api/v1/reports/{rid}/transitions/submit", headers=h)
    client.post(f"/api/v1/reports/{rid}/transitions/publish", headers=qm)

    eng = create_engine(ADMIN_URL)
    with eng.begin() as conn:
        conn.execute(
            text("UPDATE findings SET title = 'CHANGED AFTER PUBLISH' WHERE id = :id"),
            {"id": fid},
        )
    eng.dispose()

    frozen = client.get(f"/api/v1/reports/{rid}", headers=h).json()["structured_content"]
    assert frozen["findings"][0]["title"] == snap_title
    assert frozen["findings"][0]["title"] != "CHANGED AFTER PUBLISH"
    assert frozen["maturity"]["id"] == mid
    assert frozen["maturity"]["version_no"] == 1
    assert frozen["maturity"]["model_version"] == "0.1.0"
    assert frozen["finding_ids"] == [fid]
    assert frozen["action_plan_id"]
    assert frozen["immutable"] is True

    # draft-only refresh blocked on published
    assert client.post(f"/api/v1/reports/{rid}/refresh-snapshot", headers=h).status_code == 409


def test_concurrent_publish(client: TestClient):
    h, org_id, aid, _fid, _mid, qm = _report_ready(client)
    rid = client.post("/api/v1/reports", json={"assessment_id": aid}, headers=h).json()["id"]
    client.post(f"/api/v1/reports/{rid}/transitions/submit", headers=h)

    def _pub():
        c = TestClient(app)
        return c.post(f"/api/v1/reports/{rid}/transitions/publish", headers=qm).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        codes = list(pool.map(lambda _: _pub(), range(2)))
    assert 200 in codes
    assert codes.count(200) >= 1  # one success; second may be idempotent 200
    assert client.get(f"/api/v1/reports/{rid}", headers=h).json()["status"] == "published"
