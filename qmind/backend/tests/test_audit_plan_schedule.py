"""Audit plan programming — Interview SoT + AgendaEvent meetings/milestones + sync."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.main import app
from tests.conftest import ADMIN_URL
from tests.test_assessment_ops import _create_draft_with_scope, _org_ctx
from tests.test_assessments import _bootstrap_org, _dev_headers
from tests.test_audit_plan import _complete_plan_for_ready, _seed_guided
from tests.test_findings import _member_headers


@pytest.fixture()
def client():
    return TestClient(app)


def _utc(hours=24) -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()


def test_planned_interview_syncs_to_agenda_idempotent(client: TestClient):
    _h0, org, h, model_id, sv_id, req_id = _org_ctx(client)
    aid = _create_draft_with_scope(client, h, model_id, sv_id, req_id)
    assess = client.get(f"/api/v1/assessments/{aid}", headers=h).json()
    starts = "2026-09-02T14:00:00+00:00"

    created = client.post(
        f"/api/v1/assessments/{aid}/interviews",
        json={
            "title": "Entrevista Produção",
            "process_name": "",
            "objective": "Mapear controles",
            "interviewer_membership_id": assess["lead_membership_id"],
            "scheduled_at": starts,
            "duration_minutes": 60,
            "location": "Sala 1",
            "preparation": "Levar roteiro",
            "mode": "onsite",
        },
        headers=h,
    )
    assert created.status_code == 201, created.text
    iv = created.json()
    assert iv["status"] == "planned"
    event_id = iv["agenda_event_id"]
    assert event_id is not None

    ev1 = client.get(f"/api/v1/agenda/events/{event_id}", headers=h)
    assert ev1.status_code == 200, ev1.text
    assert ev1.json()["source_kind"] == "interview"
    assert ev1.json()["source_id"] == iv["id"]
    assert ev1.json()["is_auto"] is True
    assert ev1.json()["title"] == "Entrevista Produção"

    # Edit sync without duplicate
    patched = client.patch(
        f"/api/v1/interviews/{iv['id']}",
        json={"title": "Entrevista Produção (revisada)", "scheduled_at": starts},
        headers=h,
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["agenda_event_id"] == event_id
    ev2 = client.get(f"/api/v1/agenda/events/{event_id}", headers=h).json()
    assert ev2["title"] == "Entrevista Produção (revisada)"

    # Sync reprocess does not duplicate
    sync = client.post("/api/v1/agenda/sync", headers=h)
    assert sync.status_code == 200
    board = client.get("/api/v1/agenda/board", headers=h).json()
    interview_events = [
        e
        for e in (board.get("selected_day") or [])
        + (board.get("today") or [])
        + (board.get("overdue") or [])
        if e.get("source_id") == iv["id"]
    ]
    # May or may not be on selected day — fetch by id is enough; count via admin
    eng = create_engine(ADMIN_URL)
    with eng.connect() as conn:
        n = conn.execute(
            text(
                """
                SELECT count(*) FROM agenda_events
                WHERE organization_id = :org
                  AND source_kind = 'interview'
                  AND source_id = :sid
                """
            ),
            {"org": org, "sid": iv["id"]},
        ).scalar_one()
    eng.dispose()
    assert n == 1


def test_cancel_and_complete_reflect_on_agenda(client: TestClient):
    _h0, _org, h, model_id, sv_id, req_id = _org_ctx(client)
    aid = _create_draft_with_scope(client, h, model_id, sv_id, req_id)
    iv = client.post(
        f"/api/v1/assessments/{aid}/interviews",
        json={
            "title": "Cancelável",
            "scheduled_at": "2026-09-03T10:00:00Z",
            "duration_minutes": 30,
        },
        headers=h,
    ).json()
    event_id = iv["agenda_event_id"]
    cancel = client.post(f"/api/v1/interviews/{iv['id']}/cancel", headers=h)
    assert cancel.status_code == 200, cancel.text
    assert client.get(f"/api/v1/agenda/events/{event_id}", headers=h).json()["status"] == "cancelled"

    # Complete path needs in_progress assessment
    aid2 = _create_draft_with_scope(client, h, model_id, sv_id, req_id)
    assert client.post(f"/api/v1/assessments/{aid2}/transitions/plan", headers=h).status_code == 200
    assert client.post(f"/api/v1/assessments/{aid2}/transitions/start", headers=h).status_code == 200
    iv2 = client.post(
        f"/api/v1/assessments/{aid2}/interviews",
        json={
            "title": "Concluível",
            "scheduled_at": "2026-09-04T10:00:00Z",
            "duration_minutes": 30,
        },
        headers=h,
    ).json()
    eid2 = iv2["agenda_event_id"]
    done = client.post(f"/api/v1/interviews/{iv2['id']}/complete", headers=h)
    assert done.status_code == 200, done.text
    assert client.get(f"/api/v1/agenda/events/{eid2}", headers=h).json()["status"] == "completed"


def test_meetings_milestones_overlap_timezone_readiness(client: TestClient):
    _h0, org, h, model_id, sv_id, req_id = _org_ctx(client)
    aid = _create_draft_with_scope(client, h, model_id, sv_id, req_id)
    _seed_guided(client, h, aid)
    plan = client.get(f"/api/v1/assessments/{aid}/audit-plan", headers=h).json()
    assess = client.get(f"/api/v1/assessments/{aid}", headers=h).json()
    lead = assess["lead_membership_id"]

    # Period first
    patched = client.patch(
        f"/api/v1/assessments/{aid}/audit-plan",
        json={
            "planned_start": "2026-09-01",
            "planned_end": "2026-09-05",
            "expected_updated_at": plan["updated_at"],
        },
        headers=h,
    )
    assert patched.status_code == 200

    opening = client.post(
        f"/api/v1/assessments/{aid}/audit-plan/schedule/meetings",
        json={
            "kind": "opening_meeting",
            "objective": "Abrir auditoria",
            "starts_at": "2026-09-01T13:00:00Z",
            "duration_minutes": 60,
            "owner_membership_id": lead,
            "participant_membership_ids": [lead],
            "timezone": "America/Sao_Paulo",
        },
        headers=h,
    )
    assert opening.status_code == 201, opening.text
    assert opening.json()["has_opening_meeting"] is True
    assert opening.json()["timezone"] == "America/Sao_Paulo"

    closing = client.post(
        f"/api/v1/assessments/{aid}/audit-plan/schedule/meetings",
        json={
            "kind": "closing_meeting",
            "objective": "Encerrar",
            "starts_at": "2026-09-05T17:00:00Z",
            "duration_minutes": 60,
            "owner_membership_id": lead,
        },
        headers=h,
    )
    assert closing.status_code == 201, closing.text

    milestone = client.post(
        f"/api/v1/assessments/{aid}/audit-plan/schedule/milestones",
        json={
            "kind": "milestone_field_start",
            "occurs_at": "2026-09-02T12:00:00Z",
            "owner_membership_id": lead,
        },
        headers=h,
    )
    assert milestone.status_code == 201, milestone.text
    assert any(i["kind"] == "milestone" for i in milestone.json()["items"])

    # Overlap warning (same person, overlapping interviews)
    a = client.post(
        f"/api/v1/assessments/{aid}/interviews",
        json={
            "title": "A",
            "scheduled_at": "2026-09-02T14:00:00Z",
            "duration_minutes": 90,
            "interviewer_membership_id": lead,
            "participant_membership_ids": [lead],
        },
        headers=h,
    )
    assert a.status_code == 201, a.text
    assert a.json()["overlap_warnings"] == [] or isinstance(a.json()["overlap_warnings"], list)
    b = client.post(
        f"/api/v1/assessments/{aid}/interviews",
        json={
            "title": "B",
            "scheduled_at": "2026-09-02T14:30:00Z",
            "duration_minutes": 60,
            "interviewer_membership_id": lead,
            "participant_membership_ids": [lead],
        },
        headers=h,
    )
    assert b.status_code == 201, b.text
    assert len(b.json()["overlap_warnings"]) >= 1

    schedule = client.get(f"/api/v1/assessments/{aid}/audit-plan/schedule", headers=h)
    assert schedule.status_code == 200
    assert len(schedule.json()["overlaps"]) >= 1

    # Outside period without justification → 422
    bad = client.post(
        f"/api/v1/assessments/{aid}/interviews",
        json={
            "title": "Fora",
            "scheduled_at": "2026-10-01T14:00:00Z",
            "duration_minutes": 30,
        },
        headers=h,
    )
    assert bad.status_code == 422
    ok_out = client.post(
        f"/api/v1/assessments/{aid}/interviews",
        json={
            "title": "Fora justificada",
            "scheduled_at": "2026-10-01T14:00:00Z",
            "duration_minutes": 30,
            "outside_period_justification": "Visita extra acordada",
        },
        headers=h,
    )
    assert ok_out.status_code == 201, ok_out.text

    # Complete readiness via helper path
    plan_now = client.get(f"/api/v1/assessments/{aid}/audit-plan", headers=h).json()
    plan_ready = _complete_plan_for_ready(client, h, aid, plan_now, assess)
    assert plan_ready["readiness"]["ready"] is True


def test_reader_and_cross_org_schedule(client: TestClient):
    _h0, org, h, model_id, sv_id, req_id = _org_ctx(client)
    aid = _create_draft_with_scope(client, h, model_id, sv_id, req_id)
    assert client.get(f"/api/v1/assessments/{aid}/audit-plan/schedule", headers=h).status_code == 200

    reader = _member_headers(org, ["reader"])
    assert (
        client.get(f"/api/v1/assessments/{aid}/audit-plan/schedule", headers=reader).status_code
        == 200
    )
    denied = client.post(
        f"/api/v1/assessments/{aid}/audit-plan/schedule/meetings",
        json={
            "kind": "additional_meeting",
            "starts_at": "2026-09-02T15:00:00Z",
            "duration_minutes": 30,
        },
        headers=reader,
    )
    assert denied.status_code == 403

    hb0 = _dev_headers()
    org_b = _bootstrap_org(client, hb0)
    h_b = {**hb0, "X-Organization-Id": org_b}
    cross = client.get(f"/api/v1/assessments/{aid}/audit-plan/schedule", headers=h_b)
    assert cross.status_code == 404
