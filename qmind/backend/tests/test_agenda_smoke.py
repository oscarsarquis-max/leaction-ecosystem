"""Agenda MVP — create/list + tenant isolation smoke."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.main import app


def _headers(sub: str, org_id: str | None = None) -> dict[str, str]:
    h = {
        "X-Dev-User-Sub": sub,
        "X-Dev-User-Email": f"{sub}@example.com",
    }
    if org_id:
        h["X-Organization-Id"] = org_id
    return h


def _create_org(client: TestClient, sub: str) -> str:
    r = client.post(
        "/api/v1/organizations",
        json={"name": f"Agenda Org {sub[:8]}", "timezone": "America/Sao_Paulo"},
        headers=_headers(sub),
    )
    assert r.status_code == 201, r.text
    return r.json()["organization"]["id"]


def test_agenda_board_create_and_isolation():
    client = TestClient(app)
    sub_a = f"agenda-a-{uuid.uuid4()}"
    sub_b = f"agenda-b-{uuid.uuid4()}"
    org_a = _create_org(client, sub_a)
    org_b = _create_org(client, sub_b)

    starts = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    created = client.post(
        "/api/v1/agenda/events",
        headers={
            **_headers(sub_a, org_a),
            "Idempotency-Key": str(uuid.uuid4()),
        },
        json={
            "title": "Entrevista com processo",
            "event_type": "interview",
            "starts_at": starts,
            "timezone": "America/Sao_Paulo",
            "description": "Smoke",
        },
    )
    assert created.status_code == 201, created.text
    event_id = created.json()["id"]
    assert created.json()["organization_id"] == org_a

    board_a = client.get(
        "/api/v1/agenda/board",
        headers=_headers(sub_a, org_a),
    )
    assert board_a.status_code == 200, board_a.text
    body = board_a.json()
    assert body["timezone"] == "America/Sao_Paulo"
    ids = {e["id"] for e in body["selected_day"] + body["today"] + body["overdue"]}
    if body["next_up"]:
        ids.add(body["next_up"]["id"])
    # event may be on selected day depending on local date
    day = client.get(
        f"/api/v1/agenda/events/{event_id}",
        headers=_headers(sub_a, org_a),
    )
    assert day.status_code == 200
    assert day.json()["title"] == "Entrevista com processo"

    # Org B cannot see
    denied = client.get(
        f"/api/v1/agenda/events/{event_id}",
        headers=_headers(sub_b, org_b),
    )
    assert denied.status_code == 404

    board_b = client.get(
        "/api/v1/agenda/board",
        headers=_headers(sub_b, org_b),
    )
    assert board_b.status_code == 200
    b_ids = {e["id"] for e in board_b.json()["selected_day"]}
    assert event_id not in b_ids

    milestone = client.post(
        "/api/v1/agenda/events",
        headers={
            **_headers(sub_a, org_a),
            "Idempotency-Key": str(uuid.uuid4()),
        },
        json={
            "title": "Marco de abertura",
            "event_type": "milestone",
            "starts_at": starts,
            "timezone": "America/Sao_Paulo",
        },
    )
    assert milestone.status_code == 201, milestone.text
