"""Finding discard / withdraw / rework history / listing / concurrency."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.main import app
from tests.conftest import ADMIN_URL
from tests.test_assessments import _bootstrap_org, _dev_headers
from tests.test_findings import _approved_evidence, _member_headers, _setup_in_progress


@pytest.fixture()
def client():
    return TestClient(app)


def _approve_finding(client, h, org_id, aid, req_id):
    eid = _approved_evidence(client, h, aid)
    fid = client.post(
        "/api/v1/findings",
        json={
            "assessment_id": aid,
            "finding_type": "conformity",
            "title": "Approved finding",
            "body": "body",
            "requirement_ids": [req_id],
            "evidence_ids": [eid],
        },
        headers=h,
    ).json()["id"]
    assert client.post(f"/api/v1/findings/{fid}/transitions/submit", headers=h).status_code == 200
    approver = _member_headers(org_id, ["quality_manager"])
    assert client.post(f"/api/v1/findings/{fid}/transitions/approve", headers=approver).status_code == 200
    return fid, approver


def test_discard_hidden_from_list(client: TestClient):
    h, _org, aid, req_id = _setup_in_progress(client)
    fid = client.post(
        "/api/v1/findings",
        json={
            "assessment_id": aid,
            "finding_type": "observation",
            "title": "Draft discard",
            "body": "body",
            "requirement_ids": [req_id],
            "insufficient_evidence": True,
            "insufficient_evidence_rationale": "no records",
        },
        headers=h,
    ).json()["id"]
    discarded = client.post(
        f"/api/v1/findings/{fid}/transitions/discard",
        json={"reason": "duplicate"},
        headers=h,
    )
    assert discarded.status_code == 200
    assert discarded.json()["to_status"] == "discarded"

    listed = client.get(f"/api/v1/findings?assessment_id={aid}", headers=h)
    assert listed.status_code == 200
    assert all(f["id"] != fid for f in listed.json())

    with_disc = client.get(
        f"/api/v1/findings?assessment_id={aid}&include_discarded=true", headers=h
    )
    assert any(f["id"] == fid for f in with_disc.json())

    # cannot discard non-draft
    assert (
        client.post(f"/api/v1/findings/{fid}/transitions/discard", headers=h).status_code == 409
    )


def test_withdraw_signals_items_and_blocks_when_closed(client: TestClient):
    h, org_id, aid, req_id = _setup_in_progress(client)
    fid, approver = _approve_finding(client, h, org_id, aid, req_id)

    # move assessment to analysis/actions and create linked item
    assert client.post(f"/api/v1/assessments/{aid}/transitions/begin_analysis", headers=h).status_code == 200
    assert client.post(f"/api/v1/assessments/{aid}/transitions/open_actions", headers=h).status_code == 200
    plan = client.post("/api/v1/action-plans", json={"assessment_id": aid}, headers=h)
    assert plan.status_code == 201, plan.text
    pid = plan.json()["id"]
    # owner = author membership via me
    me = client.get("/api/v1/organizations/me/memberships", headers=h).json()
    owner_mid = next(m["id"] for m in me if m["organization_id"] == org_id)

    item = client.post(
        f"/api/v1/action-plans/{pid}/items",
        json={
            "finding_id": fid,
            "action_kind": "corrective_action",
            "description": "Fix process",
            "owner_membership_id": owner_mid,
            "due_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        },
        headers=h,
    )
    assert item.status_code == 201, item.text
    iid = item.json()["id"]

    withdrawn = client.post(
        f"/api/v1/findings/{fid}/transitions/withdraw",
        json={"reason": "Incorrect scope"},
        headers=approver,
    )
    assert withdrawn.status_code == 200, withdrawn.text
    assert withdrawn.json()["to_status"] == "withdrawn"
    assert client.get(f"/api/v1/action-items/{iid}", headers=h).json()["source_finding_withdrawn"] is True

    eng = create_engine(ADMIN_URL)
    with eng.connect() as conn:
        audit = conn.execute(
            text(
                """
                SELECT from_status, to_status, metadata->>'reason' AS reason
                FROM platform_audit_events
                WHERE resource_id = :id AND action = 'finding.withdraw'
                """
            ),
            {"id": fid},
        ).one()
        assert audit.from_status == "approved"
        assert audit.to_status == "withdrawn"
        assert audit.reason == "Incorrect scope"
    eng.dispose()

    # closed assessment blocks withdraw on another finding
    # reopen assessment to analysis so we can approve another finding, then force closed
    eng = create_engine(ADMIN_URL)
    with eng.begin() as conn:
        conn.execute(text("UPDATE assessments SET status = 'analysis' WHERE id = :id"), {"id": aid})
    eng.dispose()
    fid2, approver2 = _approve_finding(client, h, org_id, aid, req_id)
    eng = create_engine(ADMIN_URL)
    with eng.begin() as conn:
        conn.execute(text("UPDATE assessments SET status = 'closed' WHERE id = :id"), {"id": aid})
    eng.dispose()
    blocked = client.post(
        f"/api/v1/findings/{fid2}/transitions/withdraw",
        json={"reason": "too late"},
        headers=approver2,
    )
    assert blocked.status_code == 409
    assert blocked.json()["code"] == "assessment_closed"


def test_rework_from_withdrawn_preserves_history(client: TestClient):
    h, org_id, aid, req_id = _setup_in_progress(client)
    fid, approver = _approve_finding(client, h, org_id, aid, req_id)
    assert (
        client.post(
            f"/api/v1/findings/{fid}/transitions/withdraw",
            json={"reason": "rework needed"},
            headers=approver,
        ).status_code
        == 200
    )
    reworked = client.post(f"/api/v1/findings/{fid}/transitions/rework", headers=h)
    assert reworked.status_code == 200, reworked.text
    body = reworked.json()
    assert body["to_status"] == "draft"
    assert body["preserved_finding_id"] == fid
    new_id = body["finding"]["id"]
    assert new_id != fid
    assert body["finding"]["rework_of_finding_id"] == fid
    assert client.get(f"/api/v1/findings/{fid}", headers=h).json()["status"] == "withdrawn"
    assert client.get(f"/api/v1/findings/{new_id}", headers=h).json()["status"] == "draft"


def test_isolation_and_invalid_states(client: TestClient):
    h1, org1, aid1, req_id = _setup_in_progress(client)
    fid, _ = _approve_finding(client, h1, org1, aid1, req_id)

    h2 = _dev_headers()
    org2 = _bootstrap_org(client, h2)
    ctx2 = {**h2, "X-Organization-Id": org2}
    assert client.get(f"/api/v1/findings/{fid}", headers=ctx2).status_code == 404

    bad = client.post(f"/api/v1/findings/{fid}/transitions/submit", headers=h1)
    assert bad.status_code == 409


def test_concurrent_withdraw(client: TestClient):
    h, org_id, aid, req_id = _setup_in_progress(client)
    fid, approver = _approve_finding(client, h, org_id, aid, req_id)

    def _withdraw():
        c = TestClient(app)
        return c.post(
            f"/api/v1/findings/{fid}/transitions/withdraw",
            json={"reason": "race"},
            headers=approver,
        ).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        codes = list(pool.map(lambda _: _withdraw(), range(2)))
    assert 200 in codes
    assert codes.count(200) == 1
    assert any(c in (409, 200) for c in codes)
    assert client.get(f"/api/v1/findings/{fid}", headers=h).json()["status"] == "withdrawn"
