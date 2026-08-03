"""ActionPlan / ActionItem lifecycle + SoD validation vs execution."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.test_findings import _member_headers, _setup_in_progress
from tests.test_findings_lifecycle import _approve_finding


@pytest.fixture()
def client():
    return TestClient(app)


def _due():
    return (datetime.now(timezone.utc) + timedelta(days=14)).isoformat()


def _owner_membership_id(client: TestClient, h: dict, org_id: str) -> str:
    me = client.get("/api/v1/organizations/me/memberships", headers=h).json()
    return next(m["id"] for m in me if m["organization_id"] == org_id)


def _plan_ready(client: TestClient):
    h, org_id, aid, req_id = _setup_in_progress(client)
    fid, _approver = _approve_finding(client, h, org_id, aid, req_id)
    assert client.post(f"/api/v1/assessments/{aid}/transitions/begin_analysis", headers=h).status_code == 200
    assert client.post(f"/api/v1/assessments/{aid}/transitions/open_actions", headers=h).status_code == 200
    plan = client.post("/api/v1/action-plans", json={"assessment_id": aid}, headers=h)
    assert plan.status_code == 201, plan.text
    return h, org_id, aid, fid, plan.json()["id"]


def test_action_plan_activate_complete_cancel(client: TestClient):
    h, org_id, _aid, fid, pid = _plan_ready(client)
    owner = _owner_membership_id(client, h, org_id)
    item = client.post(
        f"/api/v1/action-plans/{pid}/items",
        json={
            "finding_id": fid,
            "action_kind": "improvement",
            "description": "Improve docs",
            "owner_membership_id": owner,
            "due_at": _due(),
            "efficacy_required": False,
        },
        headers=h,
    )
    assert item.status_code == 201, item.text
    iid = item.json()["id"]

    assert client.post(f"/api/v1/action-plans/{pid}/transitions/activate", headers=h).status_code == 200

    # owner executes
    assert client.post(f"/api/v1/action-items/{iid}/transitions/start", headers=h).status_code == 200
    assert (
        client.post(f"/api/v1/action-items/{iid}/transitions/mark_implemented", headers=h).status_code
        == 200
    )

    # SoD: owner cannot validate
    sod = client.post(f"/api/v1/action-items/{iid}/transitions/validate", headers=h)
    assert sod.status_code == 403
    assert sod.json()["code"] == "sod_violation"

    validator = _member_headers(org_id, ["quality_manager"])
    validated = client.post(f"/api/v1/action-items/{iid}/transitions/validate", headers=validator)
    assert validated.status_code == 200, validated.text
    assert validated.json()["to_status"] == "done"  # no efficacy required

    completed = client.post(f"/api/v1/action-plans/{pid}/transitions/complete", headers=h)
    assert completed.status_code == 200
    assert completed.json()["to_status"] == "completed"


def test_efficacy_path_and_reopen(client: TestClient):
    h, org_id, _aid, fid, pid = _plan_ready(client)
    owner_headers = _member_headers(org_id, ["action_owner"])
    owner_mid = next(
        m["id"]
        for m in client.get("/api/v1/organizations/me/memberships", headers=owner_headers).json()
        if m["organization_id"] == org_id
    )
    item = client.post(
        f"/api/v1/action-plans/{pid}/items",
        json={
            "finding_id": fid,
            "action_kind": "corrective_action",
            "description": "Corrective",
            "owner_membership_id": owner_mid,
            "due_at": _due(),
        },
        headers=h,
    ).json()
    iid = item["id"]
    assert item["efficacy_required"] is True

    assert client.post(f"/api/v1/action-plans/{pid}/transitions/activate", headers=h).status_code == 200
    assert client.post(f"/api/v1/action-items/{iid}/transitions/start", headers=owner_headers).status_code == 200
    assert (
        client.post(
            f"/api/v1/action-items/{iid}/transitions/mark_implemented", headers=owner_headers
        ).status_code
        == 200
    )

    qm = _member_headers(org_id, ["quality_manager"])
    # reject implementation then re-implement
    rejected = client.post(
        f"/api/v1/action-items/{iid}/transitions/reject_implementation",
        json={"reason": "Incomplete evidence"},
        headers=qm,
    )
    assert rejected.status_code == 200
    assert rejected.json()["to_status"] == "in_progress"
    assert (
        client.post(
            f"/api/v1/action-items/{iid}/transitions/mark_implemented", headers=owner_headers
        ).status_code
        == 200
    )
    assert client.post(f"/api/v1/action-items/{iid}/transitions/validate", headers=qm).json()[
        "to_status"
    ] == "validated"

    failed = client.post(
        f"/api/v1/action-items/{iid}/transitions/fail_efficacy",
        json={"reason": "Recurrence observed"},
        headers=qm,
    )
    assert failed.status_code == 200
    assert failed.json()["to_status"] == "ineffective"

    reopened = client.post(f"/api/v1/action-items/{iid}/transitions/reopen", headers=owner_headers)
    assert reopened.status_code == 200
    assert reopened.json()["to_status"] == "in_progress"

    # close another path: mark implemented → validate → fail → close
    assert (
        client.post(
            f"/api/v1/action-items/{iid}/transitions/mark_implemented", headers=owner_headers
        ).status_code
        == 200
    )
    assert client.post(f"/api/v1/action-items/{iid}/transitions/validate", headers=qm).status_code == 200
    client.post(
        f"/api/v1/action-items/{iid}/transitions/fail_efficacy",
        json={"reason": "still bad"},
        headers=qm,
    )
    closed = client.post(
        f"/api/v1/action-items/{iid}/transitions/close_ineffective", headers=qm
    )
    assert closed.status_code == 200
    assert closed.json()["to_status"] == "ineffective_closed"


def test_empty_plan_activate_and_cancel(client: TestClient):
    h, _org, aid, req_id = _setup_in_progress(client)
    # need analysis without findings for empty plan — use no_findings via SQL after analysis
    from sqlalchemy import create_engine, text

    from tests.conftest import ADMIN_URL

    assert client.post(f"/api/v1/assessments/{aid}/transitions/begin_analysis", headers=h).status_code == 200
    eng = create_engine(ADMIN_URL)
    with eng.begin() as conn:
        conn.execute(
            text("UPDATE assessments SET no_findings_declared = true WHERE id = :id"),
            {"id": aid},
        )
    eng.dispose()
    assert client.post(f"/api/v1/assessments/{aid}/transitions/open_actions", headers=h).status_code == 200

    plan = client.post(
        "/api/v1/action-plans",
        json={"assessment_id": aid, "empty_plan_rationale": "No NC found"},
        headers=h,
    )
    assert plan.status_code == 201
    pid = plan.json()["id"]
    assert client.post(f"/api/v1/action-plans/{pid}/transitions/activate", headers=h).status_code == 200
    cancelled = client.post(f"/api/v1/action-plans/{pid}/transitions/cancel", headers=h)
    assert cancelled.status_code == 200
    assert cancelled.json()["to_status"] == "cancelled"


def test_plan_cancel_blocked_by_published_report_and_audits_items(client: TestClient):
    from sqlalchemy import create_engine, text

    from tests.conftest import ADMIN_URL

    h, org_id, aid, fid, pid = _plan_ready(client)
    owner = _owner_membership_id(client, h, org_id)
    iid = client.post(
        f"/api/v1/action-plans/{pid}/items",
        json={
            "finding_id": fid,
            "action_kind": "improvement",
            "description": "Will be cancelled with plan",
            "owner_membership_id": owner,
            "due_at": _due(),
            "efficacy_required": False,
        },
        headers=h,
    ).json()["id"]
    assert client.post(f"/api/v1/action-plans/{pid}/transitions/activate", headers=h).status_code == 200

    publisher = _member_headers(org_id, ["quality_manager"])
    publisher_mid = next(
        m["id"]
        for m in client.get("/api/v1/organizations/me/memberships", headers=publisher).json()
        if m["organization_id"] == org_id
    )
    eng = create_engine(ADMIN_URL)
    with eng.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO reports (
                  organization_id, assessment_id, version_no, status,
                  structured_content, author_membership_id, published_by, published_at
                ) VALUES (
                  :org, :aid, 1, 'published', '{}'::jsonb, :author, :publisher, now()
                )
                """
            ),
            {"org": org_id, "aid": aid, "author": owner, "publisher": publisher_mid},
        )
    eng.dispose()

    blocked = client.post(f"/api/v1/action-plans/{pid}/transitions/cancel", headers=h)
    assert blocked.status_code == 409
    assert blocked.json()["code"] == "plan_cancel_blocked_published_report"

    # remove published report → cancel succeeds and audits items
    eng = create_engine(ADMIN_URL)
    with eng.begin() as conn:
        conn.execute(text("DELETE FROM reports WHERE assessment_id = :aid"), {"aid": aid})
    eng.dispose()

    cancelled = client.post(f"/api/v1/action-plans/{pid}/transitions/cancel", headers=h)
    assert cancelled.status_code == 200
    assert client.get(f"/api/v1/action-items/{iid}", headers=h).json()["status"] == "cancelled"

    eng = create_engine(ADMIN_URL)
    with eng.connect() as conn:
        item_audit = conn.execute(
            text(
                """
                SELECT from_status, to_status, metadata->>'cascaded_from' AS cascaded
                FROM platform_audit_events
                WHERE resource_id = :id AND action = 'action_item.cancel'
                ORDER BY created_at DESC, id DESC
                LIMIT 1
                """
            ),
            {"id": iid},
        ).one()
        assert item_audit.to_status == "cancelled"
        assert item_audit.cascaded == "action_plan.cancel"
        assert item_audit.from_status in ("open", "in_progress")
    eng.dispose()


def test_confirm_efficacy_happy_path(client: TestClient):
    h, org_id, _aid, fid, pid = _plan_ready(client)
    owner_h = _member_headers(org_id, ["action_owner"])
    owner_mid = next(
        m["id"]
        for m in client.get("/api/v1/organizations/me/memberships", headers=owner_h).json()
        if m["organization_id"] == org_id
    )
    iid = client.post(
        f"/api/v1/action-plans/{pid}/items",
        json={
            "finding_id": fid,
            "action_kind": "corrective_action",
            "description": "Fix",
            "owner_membership_id": owner_mid,
            "due_at": _due(),
        },
        headers=h,
    ).json()["id"]
    client.post(f"/api/v1/action-plans/{pid}/transitions/activate", headers=h)
    client.post(f"/api/v1/action-items/{iid}/transitions/start", headers=owner_h)
    client.post(f"/api/v1/action-items/{iid}/transitions/mark_implemented", headers=owner_h)
    qm = _member_headers(org_id, ["quality_manager"])
    assert client.post(f"/api/v1/action-items/{iid}/transitions/validate", headers=qm).json()[
        "to_status"
    ] == "validated"
    done = client.post(f"/api/v1/action-items/{iid}/transitions/confirm_efficacy", headers=qm)
    assert done.status_code == 200
    assert done.json()["to_status"] == "done"
