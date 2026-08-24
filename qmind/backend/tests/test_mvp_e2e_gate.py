"""MVP end-to-end gate — two orgs, full domain journey on real PostgreSQL.

Storage: memory (default suite). S3 path: tests/test_mvp_e2e_s3_integration.py
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine, text

from app.config import Settings
from app.main import app
from app.modules.reports import service as report_service
from app.storage.memory import InMemoryObjectStorage
from tests.alembic_support import alembic_head
from tests.conftest import ADMIN_URL, APP_URL
from tests.test_assessment_ops import _second_membership
from tests.test_assessments import _bootstrap_org, _catalog_ids, _dev_headers
from tests.test_findings import _member_headers
from tests.test_maturity import _fill_all_level3


@pytest.fixture()
def client():
    return TestClient(app)


def _due() -> str:
    return (datetime.now(timezone.utc) + timedelta(days=10)).isoformat()


def _assert_cross_org_denied(client: TestClient, h_b: dict, method: str, path: str, **kwargs):
    """Org B must not read/write Org A aggregates (API returns 404)."""
    fn = getattr(client, method)
    r = fn(path, headers=h_b, **kwargs)
    assert r.status_code == 404, f"{method.upper()} {path} -> {r.status_code} {r.text}"


def _rls_cannot_see(app_engine, org_b, table: str, row_id):
    with app_engine.connect() as conn:
        conn.execute(
            text("SELECT set_config('app.organization_id', :org, true)"),
            {"org": str(org_b)},
        )
        n = conn.execute(
            text(f"SELECT count(*) FROM {table} WHERE id = :id"),
            {"id": row_id},
        ).scalar_one()
    assert n == 0, f"RLS leak: org B sees {table}.{row_id}"


def _rls_can_see(app_engine, org_a, table: str, row_id):
    with app_engine.connect() as conn:
        conn.execute(
            text("SELECT set_config('app.organization_id', :org, true)"),
            {"org": str(org_a)},
        )
        n = conn.execute(
            text(f"SELECT count(*) FROM {table} WHERE id = :id"),
            {"id": row_id},
        ).scalar_one()
    assert n == 1, f"RLS deny own row: {table}.{row_id}"


def _approve_evidence(client: TestClient, h: dict, aid: str, payload: bytes | None = None) -> str:
    data = payload or b"%PDF-1.4 mvp-e2e-evidence"
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
    key = ev["storage_key"]
    # Upload PUT is retry-safe (same key/bytes).
    store = InMemoryObjectStorage.instance()
    store.put_test_object(key, data, "application/pdf")
    store.put_test_object(key, data, "application/pdf")
    eid = ev["id"]
    recv = client.post(f"/api/v1/evidences/{eid}/transitions/receive", headers=h)
    assert recv.status_code == 200, recv.text
    # Second receive must not mutate (status guard).
    again = client.post(f"/api/v1/evidences/{eid}/transitions/receive", headers=h)
    assert again.status_code == 409
    ok = client.post(f"/api/v1/evidences/{eid}/transitions/security_pass", headers=h)
    assert ok.status_code == 200, ok.text
    assert ok.json()["to_status"] == "approved"
    return eid


_TENANT_DELETE_ORDER = (
    "break_glass_sessions",
    "platform_audit_events",
    "ai_suggestions",
    "jobs",
    "reports",
    "action_items",
    "action_plans",
    "maturity_score_evidence_links",
    "maturity_dimension_scores",
    "maturity_scores",
    "maturity_assessments",
    "finding_evidences",
    "finding_requirements",
    "findings",
    "evidence_links",
    "evidences",
    "answers",
    "interviews",
    "assessment_team_members",
    "assessment_scopes",
    "assessments",
    "org_processes",
    "person_contacts",
    "memberships",
    "units",
)


def _cleanup_orgs(*org_ids: str) -> None:
    """Deterministic admin cleanup of tenant rows + orgs + orphan users."""
    ids = [o for o in org_ids if o]
    if not ids:
        return
    eng = create_engine(ADMIN_URL)
    with eng.begin() as conn:
        user_ids: list = []
        for org in ids:
            user_ids.extend(
                conn.execute(
                    text("SELECT user_id FROM memberships WHERE organization_id = :o"),
                    {"o": org},
                )
                .scalars()
                .all()
            )
            for table in _TENANT_DELETE_ORDER:
                conn.execute(
                    text(f"DELETE FROM {table} WHERE organization_id = :o"),
                    {"o": org},
                )
            conn.execute(text("DELETE FROM organizations WHERE id = :o"), {"o": org})
        for uid in set(user_ids):
            still = conn.execute(
                text("SELECT count(*) FROM memberships WHERE user_id = :u"),
                {"u": uid},
            ).scalar_one()
            if still == 0:
                conn.execute(text("DELETE FROM users WHERE id = :u"), {"u": uid})
    eng.dispose()


def _bootstrap_pair(client: TestClient):
    """Two independent orgs with memberships (caller must `_cleanup_orgs`)."""
    ha = _dev_headers()
    org_a = _bootstrap_org(client, ha)
    h_a = {**ha, "X-Organization-Id": org_a}
    qm_a = _member_headers(org_a, ["quality_manager"])

    hb = _dev_headers()
    org_b = _bootstrap_org(client, hb)
    h_b = {**hb, "X-Organization-Id": org_b}
    # Org B also gets a draft assessment so isolation is bidirectional.
    model_id, sv_id, req_id = _catalog_ids()
    aid_b = client.post(
        "/api/v1/assessments",
        json={
            "assessment_model_id": str(model_id),
            "standard_version_id": str(sv_id),
            "scope": [{"requirement_id": str(req_id)}],
        },
        headers=h_b,
    ).json()["id"]
    return {
        "h_a": h_a,
        "qm_a": qm_a,
        "org_a": org_a,
        "h_b": h_b,
        "org_b": org_b,
        "aid_b": aid_b,
        "model_id": model_id,
        "sv_id": sv_id,
        "req_id": req_id,
    }


def test_mvp_end_to_end_two_orgs_memory(client: TestClient, app_engine, monkeypatch):
    """Full journey Org A + continuous cross-org denial from Org B."""
    ctx = _bootstrap_pair(client)
    h_a, qm_a, h_b = ctx["h_a"], ctx["qm_a"], ctx["h_b"]
    org_a, org_b = ctx["org_a"], ctx["org_b"]
    model_id, sv_id, req_id = ctx["model_id"], ctx["sv_id"], ctx["req_id"]
    try:
        _mvp_e2e_body(
            client, app_engine, monkeypatch, h_a, qm_a, h_b, org_a, org_b, model_id, sv_id, req_id
        )
    finally:
        _cleanup_orgs(org_a, org_b)


def _mvp_e2e_body(
    client, app_engine, monkeypatch, h_a, qm_a, h_b, org_a, org_b, model_id, sv_id, req_id
):

    # --- Organization / Membership ---
    mems = client.get("/api/v1/organizations/me/memberships", headers=h_a).json()
    assert any(m["organization_id"] == org_a for m in mems)
    lead_mid = next(m["id"] for m in mems if m["organization_id"] == org_a)

    # --- Assessment.draft + scope ---
    created = client.post(
        "/api/v1/assessments",
        json={
            "assessment_model_id": str(model_id),
            "standard_version_id": str(sv_id),
            "scope": [{"requirement_id": str(req_id)}],
        },
        headers=h_a,
    )
    assert created.status_code == 201, created.text
    aid = created.json()["id"]
    assert created.json()["status"] == "draft"
    _assert_cross_org_denied(client, h_b, "get", f"/api/v1/assessments/{aid}")
    _rls_can_see(app_engine, org_a, "assessments", aid)
    _rls_cannot_see(app_engine, org_b, "assessments", aid)

    # --- team ---
    auditor_mid = _second_membership(org_a, ["consultant_auditor"])
    team = client.post(
        f"/api/v1/assessments/{aid}/team",
        json={"membership_id": auditor_mid, "team_role": "auditor"},
        headers=h_a,
    )
    assert team.status_code == 201, team.text
    assert client.get(f"/api/v1/assessments/{aid}/team", headers=h_a).status_code == 200
    _assert_cross_org_denied(client, h_b, "get", f"/api/v1/assessments/{aid}/team")

    # --- plan / start ---
    planned = client.post(f"/api/v1/assessments/{aid}/transitions/plan", headers=h_a)
    assert planned.status_code == 200
    assert planned.json()["to_status"] == "planned"
    assert client.get(f"/api/v1/assessments/{aid}", headers=h_a).json()["maturity_model_id"]
    started = client.post(f"/api/v1/assessments/{aid}/transitions/start", headers=h_a)
    assert started.status_code == 200
    assert started.json()["to_status"] == "in_progress"
    _assert_cross_org_denied(
        client, h_b, "post", f"/api/v1/assessments/{aid}/transitions/start"
    )

    # --- Evidence.approved ---
    eid = _approve_evidence(client, h_a, aid)
    _assert_cross_org_denied(client, h_b, "get", f"/api/v1/evidences/{eid}")
    _rls_cannot_see(app_engine, org_b, "evidences", eid)

    # --- Finding.approved (SoD) ---
    fid = client.post(
        "/api/v1/findings",
        json={
            "assessment_id": aid,
            "finding_type": "conformity",
            "title": "MVP E2E conformity",
            "body": "Documented process confirmed.",
            "requirement_ids": [str(req_id)],
            "evidence_ids": [eid],
        },
        headers=h_a,
    ).json()["id"]
    assert client.post(f"/api/v1/findings/{fid}/transitions/submit", headers=h_a).status_code == 200
    sod_f = client.post(f"/api/v1/findings/{fid}/transitions/approve", headers=h_a)
    assert sod_f.status_code == 403
    assert sod_f.json()["code"] == "sod_violation"
    assert (
        client.post(f"/api/v1/findings/{fid}/transitions/approve", headers=qm_a).status_code
        == 200
    )
    _assert_cross_org_denied(client, h_b, "get", f"/api/v1/findings/{fid}")
    _rls_cannot_see(app_engine, org_b, "findings", fid)

    assert client.post(f"/api/v1/assessments/{aid}/transitions/begin_analysis", headers=h_a).status_code == 200

    # --- MaturityAssessment.approved (SoD) ---
    mid = client.post(
        "/api/v1/maturity-assessments", json={"assessment_id": aid}, headers=h_a
    ).json()["id"]
    _fill_all_level3(client, h_a, mid, eid)
    assert (
        client.post(f"/api/v1/maturity-assessments/{mid}/transitions/submit", headers=h_a).status_code
        == 200
    )
    sod_m = client.post(f"/api/v1/maturity-assessments/{mid}/transitions/approve", headers=h_a)
    assert sod_m.status_code == 403
    assert sod_m.json()["code"] == "sod_violation"
    assert (
        client.post(
            f"/api/v1/maturity-assessments/{mid}/transitions/approve", headers=qm_a
        ).status_code
        == 200
    )
    _assert_cross_org_denied(client, h_b, "get", f"/api/v1/maturity-assessments/{mid}")
    _rls_cannot_see(app_engine, org_b, "maturity_assessments", mid)

    # --- ActionPlan / ActionItem.done (SoD) ---
    assert client.post(f"/api/v1/assessments/{aid}/transitions/open_actions", headers=h_a).status_code == 200
    plan_id = client.post("/api/v1/action-plans", json={"assessment_id": aid}, headers=h_a).json()[
        "id"
    ]
    item = client.post(
        f"/api/v1/action-plans/{plan_id}/items",
        json={
            "finding_id": fid,
            "action_kind": "improvement",
            "description": "Close E2E action",
            "owner_membership_id": lead_mid,
            "due_at": _due(),
            "efficacy_required": False,
        },
        headers=h_a,
    )
    assert item.status_code == 201, item.text
    iid = item.json()["id"]
    assert client.post(f"/api/v1/action-plans/{plan_id}/transitions/activate", headers=h_a).status_code == 200
    assert client.post(f"/api/v1/action-items/{iid}/transitions/start", headers=h_a).status_code == 200
    assert (
        client.post(f"/api/v1/action-items/{iid}/transitions/mark_implemented", headers=h_a).status_code
        == 200
    )
    sod_a = client.post(f"/api/v1/action-items/{iid}/transitions/validate", headers=h_a)
    assert sod_a.status_code == 403
    assert sod_a.json()["code"] == "sod_violation"
    done = client.post(f"/api/v1/action-items/{iid}/transitions/validate", headers=qm_a)
    assert done.status_code == 200
    assert done.json()["to_status"] == "done"
    assert (
        client.post(f"/api/v1/action-plans/{plan_id}/transitions/complete", headers=h_a).status_code
        == 200
    )
    _assert_cross_org_denied(client, h_b, "get", f"/api/v1/action-plans/{plan_id}")
    _rls_cannot_see(app_engine, org_b, "action_plans", plan_id)
    _rls_cannot_see(app_engine, org_b, "action_items", iid)

    assert client.post(f"/api/v1/assessments/{aid}/transitions/begin_report", headers=h_a).status_code == 200

    # --- Report.published (SoD + snapshot + single current + job idempotency) ---
    r1 = client.post(
        "/api/v1/reports",
        json={"assessment_id": aid, "include_maturity": True, "include_action_plan": True},
        headers=h_a,
    )
    assert r1.status_code == 201, r1.text
    rid1 = r1.json()["id"]
    snap1 = r1.json()["structured_content"]
    assert snap1["immutable"] is True
    assert fid in snap1["finding_ids"]
    assert snap1["maturity"]["id"] == mid
    assert snap1["maturity"]["version_no"] == 1
    assert snap1["action_plan"]["id"] == plan_id
    assert iid in snap1["action_plan"]["item_ids"]

    assert client.post(f"/api/v1/reports/{rid1}/transitions/submit", headers=h_a).status_code == 200
    sod_r = client.post(f"/api/v1/reports/{rid1}/transitions/publish", headers=h_a)
    assert sod_r.status_code == 403
    assert sod_r.json()["code"] == "sod_violation"
    pub1 = client.post(f"/api/v1/reports/{rid1}/transitions/publish", headers=qm_a)
    assert pub1.status_code == 200
    assert pub1.json()["to_status"] == "published"
    # publish idempotency
    pub1b = client.post(f"/api/v1/reports/{rid1}/transitions/publish", headers=qm_a)
    assert pub1b.status_code == 200
    assert pub1b.json()["to_status"] == "published"

    job1 = client.post(f"/api/v1/reports/{rid1}/export-pdf", headers=h_a)
    assert job1.status_code == 202
    assert job1.json()["job_type"] == "report_pdf_export"
    assert job1.json()["organization_id"] == org_a
    assert job1.json()["input_ref"]["report_version_no"] == 1
    job1b = client.post(f"/api/v1/reports/{rid1}/export-pdf", headers=h_a)
    assert job1b.json()["id"] == job1.json()["id"]
    _assert_cross_org_denied(client, h_b, "get", f"/api/v1/reports/{rid1}")
    _assert_cross_org_denied(client, h_b, "post", f"/api/v1/reports/{rid1}/export-pdf")
    _rls_cannot_see(app_engine, org_b, "reports", rid1)
    _rls_cannot_see(app_engine, org_b, "jobs", job1.json()["id"])

    # Snapshot immutability after source change
    eng = create_engine(ADMIN_URL)
    with eng.begin() as conn:
        conn.execute(
            text("UPDATE findings SET title = 'MUTATED AFTER PUBLISH' WHERE id = :id"),
            {"id": fid},
        )
    eng.dispose()
    frozen = client.get(f"/api/v1/reports/{rid1}", headers=h_a).json()["structured_content"]
    assert frozen["findings"][0]["title"] == "MVP E2E conformity"
    assert frozen["findings"][0]["title"] != "MUTATED AFTER PUBLISH"

    # One published current
    with create_engine(ADMIN_URL).connect() as conn:
        n_pub = conn.execute(
            text(
                """
                SELECT count(*) FROM reports
                WHERE assessment_id = :aid AND status = 'published'
                """
            ),
            {"aid": aid},
        ).scalar_one()
    assert n_pub == 1

    # --- Assessment.closed (with published report) ---
    closed = client.post(f"/api/v1/assessments/{aid}/transitions/close", headers=h_a)
    assert closed.status_code == 200
    assert closed.json()["to_status"] == "closed"

    # --- Assessment.reopened (preserves history) ---
    reopened = client.post(
        f"/api/v1/assessments/{aid}/transitions/reopen",
        json={"reason": "Corrective addendum after client feedback"},
        headers=qm_a,
    )
    assert reopened.status_code == 200
    assert reopened.json()["to_status"] == "report"
    assert client.get(f"/api/v1/reports/{rid1}", headers=h_a).json()["status"] == "published"

    # --- Induced publish failure must not supersede prior ---
    r_fail = client.post("/api/v1/reports", json={"assessment_id": aid}, headers=h_a).json()
    rid_fail = r_fail["id"]
    assert r_fail["supersedes_report_id"] == rid1
    assert client.post(f"/api/v1/reports/{rid_fail}/transitions/submit", headers=h_a).status_code == 200
    real_audit = report_service.write_audit

    def _boom(*args, **kwargs):
        if kwargs.get("action") == "report.publish":
            raise RuntimeError("induced publish failure")
        return real_audit(*args, **kwargs)

    monkeypatch.setattr(report_service, "write_audit", _boom)
    fragile = TestClient(app, raise_server_exceptions=False)
    failed = fragile.post(f"/api/v1/reports/{rid_fail}/transitions/publish", headers=qm_a)
    assert failed.status_code == 500
    monkeypatch.setattr(report_service, "write_audit", real_audit)

    assert client.get(f"/api/v1/reports/{rid1}", headers=h_a).json()["status"] == "published"
    assert client.get(f"/api/v1/reports/{rid_fail}", headers=h_a).json()["status"] == "in_review"

    # Discard failed draft path (in_review → discard with reason) then publish successor
    discarded = client.post(
        f"/api/v1/reports/{rid_fail}/transitions/discard",
        json={"reason": "induced failure cleanup"},
        headers=h_a,
    )
    assert discarded.status_code == 200

    # --- novo Report.published → previous superseded ---
    r2 = client.post("/api/v1/reports", json={"assessment_id": aid}, headers=h_a).json()
    rid2 = r2["id"]
    assert r2["version_no"] == 3
    assert r2["supersedes_report_id"] == rid1
    assert client.post(f"/api/v1/reports/{rid2}/transitions/submit", headers=h_a).status_code == 200
    pub2 = client.post(f"/api/v1/reports/{rid2}/transitions/publish", headers=qm_a)
    assert pub2.status_code == 200
    assert client.get(f"/api/v1/reports/{rid1}", headers=h_a).json()["status"] == "superseded"
    assert client.get(f"/api/v1/reports/{rid2}", headers=h_a).json()["status"] == "published"
    with create_engine(ADMIN_URL).connect() as conn:
        n_pub2 = conn.execute(
            text(
                """
                SELECT count(*) FROM reports
                WHERE assessment_id = :aid AND status = 'published'
                """
            ),
            {"aid": aid},
        ).scalar_one()
    assert n_pub2 == 1

    # Close again after second publish
    assert (
        client.post(f"/api/v1/assessments/{aid}/transitions/close", headers=h_a).status_code == 200
    )

    # --- Audit chain + correlation + org isolation ---
    required_actions = {
        "assessment.create",
        "assessment.team.add",
        "assessment.plan",
        "assessment.start",
        "evidence.authorize_upload",
        "evidence.receive",
        "evidence.security_pass",
        "finding.create",
        "finding.approve",
        "maturity.create",
        "maturity.approve",
        "action_plan.create",
        "action_item.validate",
        "report.create",
        "report.publish",
        "report.supersede",
        "assessment.close",
        "assessment.reopen",
        "report.export_pdf_enqueue",
    }
    eng = create_engine(ADMIN_URL)
    with eng.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT action, correlation_id, organization_id, result
                FROM platform_audit_events
                WHERE organization_id = :org
                """
            ),
            {"org": org_a},
        ).all()
        reopen_meta = conn.execute(
            text(
                """
                SELECT metadata
                FROM platform_audit_events
                WHERE organization_id = :org AND action = 'assessment.reopen'
                ORDER BY created_at DESC LIMIT 1
                """
            ),
            {"org": org_a},
        ).scalar_one()
    eng.dispose()
    actions = {r.action for r in rows}
    missing = required_actions - actions
    assert not missing, f"Missing audit actions: {missing}"
    assert all(r.correlation_id is not None for r in rows)
    assert all(str(r.organization_id) == org_a for r in rows)

    meta = reopen_meta if isinstance(reopen_meta, dict) else json.loads(reopen_meta)
    assert meta.get("reinforced") is True
    assert rid1 in meta.get("preserved_report_ids", [])

    _rls_cannot_see_audit(app_engine, org_b, org_a)


def _rls_cannot_see_audit(app_engine, org_b, org_a):
    with app_engine.connect() as conn:
        conn.execute(
            text("SELECT set_config('app.organization_id', :org, true)"),
            {"org": str(org_b)},
        )
        n = conn.execute(
            text(
                "SELECT count(*) FROM platform_audit_events WHERE organization_id = :a"
            ),
            {"a": org_a},
        ).scalar_one()
    assert n == 0


def test_mvp_close_with_formal_waiver(client: TestClient):
    """Separate path: close Assessment with formal waiver (no published Report)."""
    ctx = _bootstrap_pair(client)
    org_a, org_b = ctx["org_a"], ctx["org_b"]
    try:
        h_a, qm_a = ctx["h_a"], ctx["qm_a"]
        model_id, sv_id, req_id = ctx["model_id"], ctx["sv_id"], ctx["req_id"]
        aid = client.post(
            "/api/v1/assessments",
            json={
                "assessment_model_id": str(model_id),
                "standard_version_id": str(sv_id),
                "scope": [{"requirement_id": str(req_id)}],
            },
            headers=h_a,
        ).json()["id"]
        client.post(f"/api/v1/assessments/{aid}/transitions/plan", headers=h_a)
        client.post(f"/api/v1/assessments/{aid}/transitions/start", headers=h_a)
        eid = _approve_evidence(client, h_a, aid, b"%PDF-1.4 waiver-path")
        fid = client.post(
            "/api/v1/findings",
            json={
                "assessment_id": aid,
                "finding_type": "conformity",
                "title": "Waiver path",
                "body": "body",
                "requirement_ids": [str(req_id)],
                "evidence_ids": [eid],
            },
            headers=h_a,
        ).json()["id"]
        client.post(f"/api/v1/findings/{fid}/transitions/submit", headers=h_a)
        client.post(f"/api/v1/findings/{fid}/transitions/approve", headers=qm_a)
        client.post(f"/api/v1/assessments/{aid}/transitions/begin_analysis", headers=h_a)
        mid = client.post(
            "/api/v1/maturity-assessments", json={"assessment_id": aid}, headers=h_a
        ).json()["id"]
        _fill_all_level3(client, h_a, mid, eid)
        client.post(f"/api/v1/maturity-assessments/{mid}/transitions/submit", headers=h_a)
        client.post(f"/api/v1/maturity-assessments/{mid}/transitions/approve", headers=qm_a)
        client.post(f"/api/v1/assessments/{aid}/transitions/open_actions", headers=h_a)
        plan = client.post("/api/v1/action-plans", json={"assessment_id": aid}, headers=h_a).json()
        owner = next(
            m["id"]
            for m in client.get("/api/v1/organizations/me/memberships", headers=h_a).json()
            if m["organization_id"] == org_a
        )
        iid = client.post(
            f"/api/v1/action-plans/{plan['id']}/items",
            json={
                "finding_id": fid,
                "action_kind": "improvement",
                "description": "waiver journey",
                "owner_membership_id": owner,
                "due_at": _due(),
                "efficacy_required": False,
            },
            headers=h_a,
        ).json()["id"]
        client.post(f"/api/v1/action-plans/{plan['id']}/transitions/activate", headers=h_a)
        client.post(f"/api/v1/action-items/{iid}/transitions/start", headers=h_a)
        client.post(f"/api/v1/action-items/{iid}/transitions/mark_implemented", headers=h_a)
        client.post(f"/api/v1/action-items/{iid}/transitions/validate", headers=qm_a)
        client.post(f"/api/v1/action-plans/{plan['id']}/transitions/complete", headers=h_a)
        client.post(f"/api/v1/assessments/{aid}/transitions/begin_report", headers=h_a)

        blocked = client.post(f"/api/v1/assessments/{aid}/transitions/close", headers=h_a)
        assert blocked.status_code == 422
        assert blocked.json()["code"] == "close_waiver_required"

        waived = client.post(
            f"/api/v1/assessments/{aid}/transitions/close",
            json={"waiver_reason": "Cliente dispensou relatório formal no piloto MVP"},
            headers=qm_a,
        )
        assert waived.status_code == 200
        assert waived.json()["to_status"] == "closed"

        eng = create_engine(ADMIN_URL)
        with eng.connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT close_waiver_reason, status FROM assessments WHERE id = :id
                    """
                ),
                {"id": aid},
            ).one()
            audit = conn.execute(
                text(
                    """
                    SELECT metadata FROM platform_audit_events
                    WHERE resource_id = :id AND action = 'assessment.close'
                    ORDER BY created_at DESC LIMIT 1
                    """
                ),
                {"id": aid},
            ).scalar_one()
        eng.dispose()
        assert row.status == "closed"
        assert row.close_waiver_reason and row.close_waiver_reason.strip()
        meta = audit if isinstance(audit, dict) else json.loads(audit)
        assert meta.get("close_waiver_reason")
    finally:
        _cleanup_orgs(org_a, org_b)


def test_mvp_prod_config_forbids_dev_auth_and_simulated_security():
    """Prod must reject AUTH_MODE=dev and ALLOW_SIMULATED_SECURITY_PASS."""
    base_urls = dict(
        database_url_admin=os.environ.get("DATABASE_URL_ADMIN", ADMIN_URL),
        database_url_app=os.environ.get("DATABASE_URL_APP", APP_URL),
    )
    with pytest.raises(ValidationError):
        Settings(environment="prod", auth_mode="dev", **base_urls)
    with pytest.raises(ValidationError):
        Settings(
            environment="prod",
            auth_mode="cognito",
            cognito_user_pool_id="pool",
            cognito_app_client_id="client",
            storage_backend="s3",
            s3_bucket="qmind-evidences-example",
            allow_simulated_security_pass=True,
            **base_urls,
        )
    with pytest.raises(ValidationError):
        Settings(
            environment="prod",
            auth_mode="cognito",
            cognito_user_pool_id="pool",
            cognito_app_client_id="client",
            storage_backend="memory",
            allow_simulated_security_pass=False,
            **base_urls,
        )


def test_database_is_migrated_to_the_current_head():
    """The database under test must be at whatever head the scripts declare.

    Pinning a literal revision here only meant the assertion had to be edited on
    every migration; what actually matters is that nobody is running the suite
    against a half-migrated database.
    """
    eng = create_engine(ADMIN_URL)
    with eng.connect() as conn:
        ver = conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    eng.dispose()
    assert ver == alembic_head()
