"""Handoff Planejamento → Campo: conclude planning, amendment, opening, start field."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.test_assessment_ops import _create_draft_with_scope, _org_ctx
from tests.test_audit_plan import _complete_plan_for_ready, _seed_guided


@pytest.fixture()
def client():
    return TestClient(app)


def _opening_id(client: TestClient, h: dict, aid: str) -> str:
    sched = client.get(f"/api/v1/assessments/{aid}/audit-plan/schedule", headers=h).json()
    opening = next(
        i
        for i in sched["items"]
        if i.get("plan_activity_kind") == "opening_meeting" and i["status"] != "cancelled"
    )
    return opening["id"]


def test_mark_ready_does_not_change_assessment_status(client: TestClient):
    _h0, _org, h, model_id, sv_id, req_id = _org_ctx(client)
    aid = _create_draft_with_scope(client, h, model_id, sv_id, req_id)
    _seed_guided(client, h, aid)
    plan = client.get(f"/api/v1/assessments/{aid}/audit-plan", headers=h).json()
    assess = client.get(f"/api/v1/assessments/{aid}", headers=h).json()
    plan2 = _complete_plan_for_ready(client, h, aid, plan, assess)

    ready = client.post(
        f"/api/v1/assessments/{aid}/audit-plan/ready",
        json={"expected_updated_at": plan2["updated_at"]},
        headers=h,
    )
    assert ready.status_code == 200, ready.text
    assert ready.json()["plan_status"] == "ready"
    assert client.get(f"/api/v1/assessments/{aid}", headers=h).json()["status"] == "draft"


def test_conclude_planning_draft_to_planned(client: TestClient):
    _h0, _org, h, model_id, sv_id, req_id = _org_ctx(client)
    aid = _create_draft_with_scope(client, h, model_id, sv_id, req_id)
    _seed_guided(client, h, aid)
    plan = client.get(f"/api/v1/assessments/{aid}/audit-plan", headers=h).json()
    assess = client.get(f"/api/v1/assessments/{aid}", headers=h).json()
    _complete_plan_for_ready(client, h, aid, plan, assess)

    out = client.post(
        f"/api/v1/assessments/{aid}/audit-plan/conclude-planning",
        json={},
        headers=h,
    )
    assert out.status_code == 200, out.text
    body = out.json()
    assert body["plan"]["plan_status"] == "ready"
    assert body["transition"]["to_status"] == "planned"
    assert client.get(f"/api/v1/assessments/{aid}", headers=h).json()["status"] == "planned"


def test_plan_transition_blocked_when_plan_draft(client: TestClient):
    _h0, _org, h, model_id, sv_id, req_id = _org_ctx(client)
    aid = _create_draft_with_scope(client, h, model_id, sv_id, req_id)
    _seed_guided(client, h, aid)
    # Creating plan without completing checklist
    assert client.get(f"/api/v1/assessments/{aid}/audit-plan", headers=h).status_code == 200

    blocked = client.post(f"/api/v1/assessments/{aid}/transitions/plan", headers=h)
    assert blocked.status_code == 422, blocked.text
    assert blocked.json()["code"] == "plan_not_ready"


def test_amendment_blocks_start_until_reconfirm(client: TestClient):
    _h0, _org, h, model_id, sv_id, req_id = _org_ctx(client)
    aid = _create_draft_with_scope(client, h, model_id, sv_id, req_id)
    _seed_guided(client, h, aid)
    plan = client.get(f"/api/v1/assessments/{aid}/audit-plan", headers=h).json()
    assess = client.get(f"/api/v1/assessments/{aid}", headers=h).json()
    plan2 = _complete_plan_for_ready(client, h, aid, plan, assess)
    assert (
        client.post(
            f"/api/v1/assessments/{aid}/audit-plan/conclude-planning",
            json={},
            headers=h,
        ).status_code
        == 200
    )

    # Amend while planned
    amended = client.patch(
        f"/api/v1/assessments/{aid}/audit-plan",
        json={
            "objective": "Objetivo emendado após planejamento",
            "amendment_reason": "Mudança de turno da planta visitada",
            "expected_updated_at": client.get(
                f"/api/v1/assessments/{aid}/audit-plan", headers=h
            ).json()["updated_at"],
        },
        headers=h,
    )
    assert amended.status_code == 200, amended.text
    assert amended.json()["plan_status"] == "amended"
    assert client.get(f"/api/v1/assessments/{aid}", headers=h).json()["status"] == "planned"

    opening = _opening_id(client, h, aid)
    client.post(
        f"/api/v1/assessments/{aid}/audit-plan/schedule/meetings/{opening}/perform",
        json={"observations": "Ok"},
        headers=h,
    )

    blocked = client.post(
        f"/api/v1/assessments/{aid}/audit-plan/start-field",
        json={},
        headers=h,
    )
    assert blocked.status_code == 422, blocked.text
    assert blocked.json()["code"] == "plan_amended_requires_reconfirm"

    # Reconfirm plan
    reconfirm = client.post(
        f"/api/v1/assessments/{aid}/audit-plan/ready",
        json={
            "expected_updated_at": client.get(
                f"/api/v1/assessments/{aid}/audit-plan", headers=h
            ).json()["updated_at"]
        },
        headers=h,
    )
    assert reconfirm.status_code == 200, reconfirm.text
    assert reconfirm.json()["plan_status"] == "ready"

    started = client.post(
        f"/api/v1/assessments/{aid}/audit-plan/start-field",
        json={},
        headers=h,
    )
    assert started.status_code == 200, started.text
    assert started.json()["transition"]["to_status"] == "in_progress"
    assert "/work" in started.json()["redirect_href"]


def test_opening_waive_requires_reason_and_unlocks_start(client: TestClient):
    _h0, _org, h, model_id, sv_id, req_id = _org_ctx(client)
    aid = _create_draft_with_scope(client, h, model_id, sv_id, req_id)
    _seed_guided(client, h, aid)
    plan = client.get(f"/api/v1/assessments/{aid}/audit-plan", headers=h).json()
    assess = client.get(f"/api/v1/assessments/{aid}", headers=h).json()
    _complete_plan_for_ready(client, h, aid, plan, assess)
    assert (
        client.post(
            f"/api/v1/assessments/{aid}/audit-plan/conclude-planning",
            json={},
            headers=h,
        ).status_code
        == 200
    )

    opening = _opening_id(client, h, aid)
    bad = client.post(
        f"/api/v1/assessments/{aid}/audit-plan/schedule/meetings/{opening}/waive",
        json={"waiver_reason": "curto"},
        headers=h,
    )
    assert bad.status_code == 422, bad.text

    blocked = client.post(
        f"/api/v1/assessments/{aid}/audit-plan/start-field", json={}, headers=h
    )
    assert blocked.status_code == 422
    assert blocked.json()["code"] == "opening_meeting_required"

    waived = client.post(
        f"/api/v1/assessments/{aid}/audit-plan/schedule/meetings/{opening}/waive",
        json={"waiver_reason": "Equipe já alinhada em kickoff prévio documentado"},
        headers=h,
    )
    assert waived.status_code == 200, waived.text
    assert waived.json()["status"] == "waived"

    started = client.post(
        f"/api/v1/assessments/{aid}/audit-plan/start-field", json={}, headers=h
    )
    assert started.status_code == 200, started.text
    assert started.json()["transition"]["to_status"] == "in_progress"


def test_reader_blocked_from_handoff_mutations(client: TestClient):
    from tests.test_findings import _member_headers

    _h0, org, h, model_id, sv_id, req_id = _org_ctx(client)
    aid = _create_draft_with_scope(client, h, model_id, sv_id, req_id)
    _seed_guided(client, h, aid)
    plan = client.get(f"/api/v1/assessments/{aid}/audit-plan", headers=h).json()
    assess = client.get(f"/api/v1/assessments/{aid}", headers=h).json()
    _complete_plan_for_ready(client, h, aid, plan, assess)

    h_reader = _member_headers(org, ["reader"])
    blocked = client.post(
        f"/api/v1/assessments/{aid}/audit-plan/conclude-planning",
        json={},
        headers=h_reader,
    )
    assert blocked.status_code == 403, blocked.text


def test_start_field_idempotent(client: TestClient):
    _h0, _org, h, model_id, sv_id, req_id = _org_ctx(client)
    aid = _create_draft_with_scope(client, h, model_id, sv_id, req_id)
    _seed_guided(client, h, aid)
    plan = client.get(f"/api/v1/assessments/{aid}/audit-plan", headers=h).json()
    assess = client.get(f"/api/v1/assessments/{aid}", headers=h).json()
    _complete_plan_for_ready(client, h, aid, plan, assess)
    client.post(f"/api/v1/assessments/{aid}/audit-plan/conclude-planning", json={}, headers=h)
    opening = _opening_id(client, h, aid)
    client.post(
        f"/api/v1/assessments/{aid}/audit-plan/schedule/meetings/{opening}/perform",
        json={},
        headers=h,
    )
    first = client.post(f"/api/v1/assessments/{aid}/audit-plan/start-field", json={}, headers=h)
    assert first.status_code == 200, first.text
    second = client.post(f"/api/v1/assessments/{aid}/audit-plan/start-field", json={}, headers=h)
    assert second.status_code == 200, second.text
    assert second.json()["transition"]["to_status"] == "in_progress"
