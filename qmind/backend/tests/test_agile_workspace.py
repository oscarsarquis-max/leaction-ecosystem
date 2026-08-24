"""Agile Action Execution Workspace (ISOI-007) tests."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.main import app
from tests.conftest import ADMIN_URL
from tests.test_actions import _due, _owner_membership_id, _plan_ready
from tests.test_finding_to_action import (
    CASES,
    _create_case,
    _create_org,
    _create_run,
    _fill_profile,
    _headers,
    _membership_id,
)
from tests.test_findings import _member_headers

AGILE = "/api/v1/organizations/current/agile"
ACTIONS = "/api/v1/organizations/current/actions"


@pytest.fixture()
def client():
    return TestClient(app)


def _revoked_membership_id(org_id: str) -> str:
    sub = f"revoked-{uuid.uuid4()}"
    eng = create_engine(ADMIN_URL)
    with eng.begin() as conn:
        user_id = conn.execute(
            text(
                """
                INSERT INTO users (idp_sub, email, status)
                VALUES (:sub, :email, 'active') RETURNING id
                """
            ),
            {"sub": sub, "email": f"{sub}@example.com"},
        ).scalar_one()
        mid = conn.execute(
            text(
                """
                INSERT INTO memberships (organization_id, user_id, roles, status)
                VALUES (:org, :user, ARRAY['reader'], 'revoked') RETURNING id
                """
            ),
            {"org": org_id, "user": user_id},
        ).scalar_one()
    eng.dispose()
    return str(mid)


def _new_sprint(client: TestClient, h: dict, squad_id: str, name: str) -> str:
    starts = datetime.now(timezone.utc)
    r = client.post(
        f"{AGILE}/sprints",
        json={
            "squad_id": squad_id,
            "name": name,
            "goal": f"Goal {name}",
            "starts_at": starts.isoformat(),
            "ends_at": (starts + timedelta(days=14)).isoformat(),
        },
        headers=h,
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _agile_base(client: TestClient):
    h, org_id, _aid, fid, pid = _plan_ready(client)
    owner = _owner_membership_id(client, h, org_id)
    item = client.post(
        f"/api/v1/action-plans/{pid}/items",
        json={
            "finding_id": fid,
            "action_kind": "improvement",
            "description": "Agile workspace action",
            "owner_membership_id": owner,
            "due_at": _due(),
            "efficacy_required": False,
        },
        headers=h,
    )
    assert item.status_code == 201, item.text
    iid = item.json()["id"]
    assert client.post(f"/api/v1/action-plans/{pid}/transitions/activate", headers=h).status_code == 200

    squad = client.post(
        "/api/v1/organizations/current/agile/squads",
        json={
            "name": "Quality Squad",
            "purpose": "Execute improvements",
            "value_owner_membership_id": owner,
        },
        headers=h,
    )
    assert squad.status_code == 201, squad.text
    sid = squad.json()["id"]

    starts = datetime.now(timezone.utc)
    ends = starts + timedelta(days=14)
    sprint = client.post(
        "/api/v1/organizations/current/agile/sprints",
        json={
            "squad_id": sid,
            "name": "Sprint 1",
            "goal": "Close top findings",
            "starts_at": starts.isoformat(),
            "ends_at": ends.isoformat(),
        },
        headers=h,
    )
    assert sprint.status_code == 201, sprint.text
    spid = sprint.json()["id"]
    return h, org_id, sid, spid, iid, owner


def _second_org(client: TestClient):
    sub = f"agile-b-{uuid.uuid4()}"
    headers = {
        "X-Dev-User-Sub": sub,
        "X-Dev-User-Email": f"{sub}@example.com",
    }
    r = client.post(
        "/api/v1/organizations",
        json={"name": "Agile Org B", "timezone": "America/Sao_Paulo"},
        headers=headers,
    )
    assert r.status_code == 201
    org_id = r.json()["organization"]["id"]
    return {**headers, "X-Organization-Id": org_id}


def test_tenant_isolation(client: TestClient):
    h, org_id, sid, spid, _iid, _owner = _agile_base(client)
    h_b = _second_org(client)
    denied = client.get(
        f"/api/v1/organizations/current/agile/squads/{sid}",
        headers=h_b,
    )
    assert denied.status_code == 404


def test_one_active_sprint_per_squad(client: TestClient):
    h, _org, sid, spid, iid, _owner = _agile_base(client)
    card = client.post(
        f"/api/v1/organizations/current/agile/sprints/{spid}/cards",
        json={"action_item_id": iid},
        headers=h,
    )
    assert card.status_code == 201, card.text
    assert (
        client.post(
            f"/api/v1/organizations/current/agile/sprints/{spid}/activate",
            headers=h,
        ).status_code
        == 200
    )

    starts = datetime.now(timezone.utc)
    ends = starts + timedelta(days=14)
    sprint2 = client.post(
        "/api/v1/organizations/current/agile/sprints",
        json={
            "squad_id": sid,
            "name": "Sprint 2",
            "goal": "Next",
            "starts_at": starts.isoformat(),
            "ends_at": ends.isoformat(),
        },
        headers=h,
    )
    sp2 = sprint2.json()["id"]
    blocked = client.post(
        f"/api/v1/organizations/current/agile/sprints/{sp2}/activate",
        json={"activation_skip_cards_rationale": "Empty sprint probe"},
        headers=h,
    )
    assert blocked.status_code == 409
    assert blocked.json()["code"] == "sprint_already_active"


def test_unique_card_allocation(client: TestClient):
    h, _org_id, _sid, spid, iid, _owner = _agile_base(client)
    assert (
        client.post(
            f"/api/v1/organizations/current/agile/sprints/{spid}/cards",
            json={"action_item_id": iid},
            headers=h,
        ).status_code
        == 201
    )
    dup = client.post(
        f"/api/v1/organizations/current/agile/sprints/{spid}/cards",
        json={"action_item_id": iid},
        headers=h,
    )
    assert dup.status_code == 409
    assert dup.json()["code"] == "card_already_allocated"


def test_carry_over_on_complete(client: TestClient):
    h, _org, sid, spid, iid, _owner = _agile_base(client)
    assert (
        client.post(
            f"/api/v1/organizations/current/agile/sprints/{spid}/cards",
            json={"action_item_id": iid},
            headers=h,
        ).status_code
        == 201
    )
    assert (
        client.post(
            f"/api/v1/organizations/current/agile/sprints/{spid}/activate",
            headers=h,
        ).status_code
        == 200
    )
    missing = client.post(
        f"/api/v1/organizations/current/agile/sprints/{spid}/complete",
        json={"carry_decisions": []},
        headers=h,
    )
    assert missing.status_code == 422
    assert missing.json()["code"] == "carry_decisions_required"

    done = client.post(
        f"/api/v1/organizations/current/agile/sprints/{spid}/complete",
        json={"carry_decisions": [{"action_item_id": iid, "decision": "backlog"}]},
        headers=h,
    )
    assert done.status_code == 200, done.text
    assert done.json()["status"] == "completed"


def test_impediment_and_board_blocked_badge(client: TestClient):
    h, org_id, sid, spid, iid, _owner = _agile_base(client)
    assert (
        client.post(
            f"/api/v1/organizations/current/agile/sprints/{spid}/cards",
            json={"action_item_id": iid},
            headers=h,
        ).status_code
        == 201
    )
    assert (
        client.post(
            f"/api/v1/organizations/current/agile/sprints/{spid}/activate",
            headers=h,
        ).status_code
        == 200
    )
    imp = client.post(
        f"/api/v1/organizations/current/actions/{iid}/impediments",
        json={"title": "Waiting for vendor", "severity": "high"},
        headers=h,
    )
    assert imp.status_code == 201, imp.text
    imp_id = imp.json()["id"]

    board = client.get(
        "/api/v1/organizations/current/agile/board",
        params={"squad_id": sid},
        headers=h,
    )
    assert board.status_code == 200
    cards = [c for col in board.json()["columns"] for c in col["cards"]]
    card = next(c for c in cards if c["action_item_id"] == iid)
    assert card["has_open_impediment"] is True

    resolved = client.patch(
        f"/api/v1/organizations/current/actions/{iid}/impediments/{imp_id}",
        json={"status": "resolved", "resolution_note": "Vendor delivered"},
        headers=h,
    )
    assert resolved.status_code == 200


def test_dependency_cycle_rejection(client: TestClient):
    h, org_id, sid, spid, iid, owner = _agile_base(client)
    # second item on same plan (no extra finding required)
    plans = client.get("/api/v1/action-plans", headers=h).json()
    pid = plans[0]["id"]
    item_b = client.post(
        f"/api/v1/action-plans/{pid}/items",
        json={
            "action_kind": "improvement",
            "description": "Action B",
            "owner_membership_id": owner,
            "due_at": _due(),
        },
        headers=h,
    ).json()["id"]

    assert (
        client.post(
            f"/api/v1/organizations/current/actions/{item_b}/dependencies",
            json={
                "predecessor_action_item_id": iid,
                "dependent_action_item_id": item_b,
                "dependency_type": "blocks",
            },
            headers=h,
        ).status_code
        == 201
    )
    cycle = client.post(
        f"/api/v1/organizations/current/actions/{iid}/dependencies",
        json={
            "predecessor_action_item_id": item_b,
            "dependent_action_item_id": iid,
            "dependency_type": "blocks",
        },
        headers=h,
    )
    assert cycle.status_code == 409
    assert cycle.json()["code"] == "dependency_cycle"


def test_check_in_idempotency(client: TestClient):
    h, _org, _sid, _spid, iid, _owner = _agile_base(client)
    key = f"checkin-{uuid.uuid4()}"
    body = {
        "health": "on_track",
        "progress_note": "Started work",
        "idempotency_key": key,
    }
    first = client.post(
        f"/api/v1/organizations/current/actions/{iid}/check-ins",
        json=body,
        headers=h,
    )
    assert first.status_code == 201, first.text
    second = client.post(
        f"/api/v1/organizations/current/actions/{iid}/check-ins",
        json=body,
        headers=h,
    )
    assert second.status_code == 201
    assert second.json()["id"] == first.json()["id"]


def test_reader_cannot_mutate(client: TestClient):
    h, org_id, sid, _spid, _iid, owner = _agile_base(client)
    reader = _member_headers(org_id, ["reader"])
    blocked = client.post(
        "/api/v1/organizations/current/agile/squads",
        json={"name": "Reader squad", "value_owner_membership_id": owner},
        headers=reader,
    )
    assert blocked.status_code == 403


def test_sprint_complete_does_not_auto_done_cards(client: TestClient):
    h, org_id, sid, spid, iid, owner = _agile_base(client)
    assert (
        client.post(
            f"/api/v1/organizations/current/agile/sprints/{spid}/cards",
            json={"action_item_id": iid},
            headers=h,
        ).status_code
        == 201
    )
    assert (
        client.post(
            f"/api/v1/organizations/current/agile/sprints/{spid}/activate",
            headers=h,
        ).status_code
        == 200
    )
    assert client.post(f"/api/v1/action-items/{iid}/transitions/start", headers=h).status_code == 200
    assert (
        client.post(
            f"/api/v1/organizations/current/agile/sprints/{spid}/complete",
            json={"carry_decisions": [{"action_item_id": iid, "decision": "backlog"}]},
            headers=h,
        ).status_code
        == 200
    )
    item = client.get(f"/api/v1/action-items/{iid}", headers=h)
    assert item.status_code == 200
    assert item.json()["status"] == "in_progress"


def test_board_columns_mapping(client: TestClient):
    h, org_id, sid, spid, iid, owner = _agile_base(client)
    assert (
        client.post(
            f"/api/v1/organizations/current/agile/sprints/{spid}/cards",
            json={"action_item_id": iid},
            headers=h,
        ).status_code
        == 201
    )
    assert (
        client.post(
            f"/api/v1/organizations/current/agile/sprints/{spid}/activate",
            headers=h,
        ).status_code
        == 200
    )

    board = client.get(
        "/api/v1/organizations/current/agile/board",
        params={"squad_id": sid},
        headers=h,
    )
    assert board.status_code == 200
    cols = {c["key"]: c["cards"] for c in board.json()["columns"]}
    assert any(c["action_item_id"] == iid for c in cols["selected"])
    assert not any(c["action_item_id"] == iid for c in cols["backlog"])

    assert client.post(f"/api/v1/action-items/{iid}/transitions/start", headers=h).status_code == 200
    board2 = client.get(
        "/api/v1/organizations/current/agile/board",
        params={"squad_id": sid},
        headers=h,
    )
    cols2 = {c["key"]: c["cards"] for c in board2.json()["columns"]}
    assert any(c["action_item_id"] == iid for c in cols2["in_progress"])
    assert cols2["in_progress"][0]["owner_display_name"]
    assert cols2["in_progress"][0]["owner_email"]


def test_board_move_requires_impediment_override(client: TestClient):
    h, org_id, sid, spid, iid, owner = _agile_base(client)
    assert (
        client.post(
            f"/api/v1/organizations/current/agile/sprints/{spid}/cards",
            json={"action_item_id": iid},
            headers=h,
        ).status_code
        == 201
    )
    assert (
        client.post(
            f"/api/v1/organizations/current/agile/sprints/{spid}/activate",
            headers=h,
        ).status_code
        == 200
    )
    client.post(
        f"/api/v1/organizations/current/actions/{iid}/impediments",
        json={"title": "Blocked"},
        headers=h,
    )
    blocked = client.post(
        "/api/v1/organizations/current/agile/board/move",
        json={"action_item_id": iid, "target_column": "in_progress"},
        headers=h,
    )
    assert blocked.status_code == 409
    assert blocked.json()["code"] == "impediment_override_required"

    ok = client.post(
        "/api/v1/organizations/current/agile/board/move",
        json={
            "action_item_id": iid,
            "target_column": "in_progress",
            "impediment_override_justification": "Critical deadline",
        },
        headers=h,
    )
    assert ok.status_code == 200, ok.text


def test_e2e_assessment_finding_to_efficacy_via_board(client: TestClient):
    """ISOI-007 E2E (assessment origin): finding → ActionItem → squad/sprint/board →
    check-in → impediment → execução → SoD validation → efficacy → ceremony → carry-over."""
    h, org_id, _aid, fid, pid = _plan_ready(client)
    # Owner = same membership as org admin (h) so SoD applies on validate.
    owner_mid = _owner_membership_id(client, h, org_id)
    qm = _member_headers(org_id, ["quality_manager"])

    item = client.post(
        f"/api/v1/action-plans/{pid}/items",
        json={
            "finding_id": fid,
            "action_kind": "corrective_action",
            "description": "E2E corrective via board",
            "owner_membership_id": owner_mid,
            "due_at": _due(),
        },
        headers=h,
    )
    assert item.status_code == 201, item.text
    iid = item.json()["id"]
    assert item.json()["efficacy_required"] is True
    assert client.post(f"/api/v1/action-plans/{pid}/transitions/activate", headers=h).status_code == 200

    squad = client.post(
        "/api/v1/organizations/current/agile/squads",
        json={
            "name": "E2E Squad",
            "purpose": "Full flow",
            "value_owner_membership_id": owner_mid,
        },
        headers=h,
    ).json()
    sid = squad["id"]

    starts = datetime.now(timezone.utc)
    ends = starts + timedelta(days=14)
    spid = client.post(
        "/api/v1/organizations/current/agile/sprints",
        json={
            "squad_id": sid,
            "name": "E2E Sprint",
            "goal": "Close corrective",
            "starts_at": starts.isoformat(),
            "ends_at": ends.isoformat(),
            "wip_limit_in_progress": 5,
        },
        headers=h,
    ).json()["id"]
    assert (
        client.post(
            f"/api/v1/organizations/current/agile/sprints/{spid}/cards",
            json={"action_item_id": iid, "priority": "high", "estimate_points": 3},
            headers=h,
        ).status_code
        == 201
    )
    assert (
        client.post(
            f"/api/v1/organizations/current/agile/sprints/{spid}/activate",
            headers=h,
        ).status_code
        == 200
    )

    board = client.get(
        "/api/v1/organizations/current/agile/board",
        params={"squad_id": sid, "sprint_id": spid},
        headers=h,
    )
    assert board.status_code == 200
    selected = next(c for c in board.json()["columns"] if c["key"] == "selected")
    assert any(c["action_item_id"] == iid for c in selected["cards"])

    assert (
        client.post(
            f"/api/v1/organizations/current/actions/{iid}/check-ins",
            json={
                "health": "on_track",
                "progress_note": "Started remediation",
                "next_step": "Patch config",
                "sprint_id": spid,
                "idempotency_key": "e2e-checkin-1",
            },
            headers=h,
        ).status_code
        == 201
    )

    imp = client.post(
        f"/api/v1/organizations/current/actions/{iid}/impediments",
        json={"title": "Vendor delay", "severity": "high", "sprint_id": spid},
        headers=h,
    )
    assert imp.status_code == 201, imp.text
    imp_id = imp.json()["id"]

    move = client.post(
        "/api/v1/organizations/current/agile/board/move",
        json={"action_item_id": iid, "target_column": "in_progress"},
        headers=h,
    )
    assert move.status_code == 409

    assert (
        client.post(
            "/api/v1/organizations/current/agile/board/move",
            json={
                "action_item_id": iid,
                "target_column": "in_progress",
                "impediment_override_justification": "Work around vendor",
            },
            headers=h,
        ).status_code
        == 200
    )

    assert (
        client.patch(
            f"/api/v1/organizations/current/actions/{iid}/impediments/{imp_id}",
            json={"status": "resolved", "resolution_note": "Vendor delivered"},
            headers=h,
        ).status_code
        == 200
    )

    assert (
        client.post(
            "/api/v1/organizations/current/agile/board/move",
            json={"action_item_id": iid, "target_column": "implemented"},
            headers=h,
        ).status_code
        == 200
    )

    sod = client.post(
        "/api/v1/organizations/current/agile/board/move",
        json={"action_item_id": iid, "target_column": "validated"},
        headers=h,
    )
    assert sod.status_code == 403
    assert sod.json()["code"] == "sod_violation"

    assert (
        client.post(
            "/api/v1/organizations/current/agile/board/move",
            json={"action_item_id": iid, "target_column": "validated"},
            headers=qm,
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/v1/organizations/current/agile/board/move",
            json={"action_item_id": iid, "target_column": "done"},
            headers=qm,
        ).status_code
        == 200
    )

    evt = client.post(
        "/api/v1/agenda/events",
        json={
            "title": "Sprint review E2E",
            "event_type": "sprint_review",
            "starts_at": starts.isoformat(),
            "ends_at": (starts + timedelta(hours=1)).isoformat(),
            "sprint_id": spid,
        },
        headers=h,
    )
    assert evt.status_code == 201, evt.text
    assert (
        client.post(
            f"/api/v1/organizations/current/agile/sprints/{spid}/ceremony-records",
            json={
                "agenda_event_id": evt.json()["id"],
                "ceremony_type": "sprint_review",
                "summary": "Corrective closed",
                "decisions": "Accept outcome",
                "follow_up": "None",
            },
            headers=h,
        ).status_code
        == 201
    )

    metrics = client.get(
        f"/api/v1/organizations/current/agile/sprints/{spid}/metrics",
        headers=h,
    )
    assert metrics.status_code == 200
    body = metrics.json()
    assert body["completed_cards"] >= 1
    assert body["throughput"] >= 1

    item2 = client.post(
        f"/api/v1/action-plans/{pid}/items",
        json={
            "finding_id": fid,
            "action_kind": "improvement",
            "description": "Carry-over item",
            "owner_membership_id": owner_mid,
            "due_at": _due(),
            "efficacy_required": False,
        },
        headers=h,
    ).json()
    iid2 = item2["id"]
    assert (
        client.post(
            f"/api/v1/organizations/current/agile/sprints/{spid}/cards",
            json={"action_item_id": iid2},
            headers=h,
        ).status_code
        == 201
    )

    next_sp = client.post(
        "/api/v1/organizations/current/agile/sprints",
        json={
            "squad_id": sid,
            "name": "E2E Sprint 2",
            "goal": "Carry leftovers",
            "starts_at": (ends + timedelta(hours=1)).isoformat(),
            "ends_at": (ends + timedelta(days=14)).isoformat(),
        },
        headers=h,
    ).json()["id"]

    completed = client.post(
        f"/api/v1/organizations/current/agile/sprints/{spid}/complete",
        json={
            "carry_decisions": [
                {"action_item_id": iid2, "decision": str(next_sp)}
            ]
        },
        headers=h,
    )
    assert completed.status_code == 200, completed.text

    item_final = client.get(f"/api/v1/action-items/{iid}", headers=h)
    assert item_final.status_code == 200
    assert item_final.json()["status"] == "done"


# --- R1: squad creation is transactional and always has a value_owner ---


def test_squad_create_registers_value_owner(client: TestClient):
    h, org_id, sid, _spid, _iid, owner = _agile_base(client)
    members = client.get(f"{AGILE}/squads/{sid}/memberships", headers=h)
    assert members.status_code == 200, members.text
    body = members.json()
    assert len(body) == 1
    assert body[0]["membership_id"] == owner
    assert body[0]["agile_role"] == "value_owner"
    assert body[0]["status"] == "active"
    assert client.get(f"{AGILE}/squads/{sid}", headers=h).json()["status"] == "active"


def test_squad_create_rejects_unknown_value_owner(client: TestClient):
    h, _org_id, _sid, _spid, _iid, _owner = _agile_base(client)
    before = len(client.get(f"{AGILE}/squads", headers=h).json())
    r = client.post(
        f"{AGILE}/squads",
        json={
            "name": "Ghost owner squad",
            "value_owner_membership_id": str(uuid.uuid4()),
        },
        headers=h,
    )
    assert r.status_code == 404
    assert r.json()["code"] == "not_found"
    after = client.get(f"{AGILE}/squads", headers=h).json()
    assert len(after) == before
    assert not any(s["name"] == "Ghost owner squad" for s in after)


def test_squad_create_rejects_inactive_value_owner(client: TestClient):
    h, org_id, _sid, _spid, _iid, _owner = _agile_base(client)
    revoked = _revoked_membership_id(org_id)
    r = client.post(
        f"{AGILE}/squads",
        json={"name": "Revoked owner squad", "value_owner_membership_id": revoked},
        headers=h,
    )
    assert r.status_code == 409
    assert r.json()["code"] == "membership_inactive"
    squads = client.get(f"{AGILE}/squads", headers=h).json()
    assert not any(s["name"] == "Revoked owner squad" for s in squads)


def test_squad_create_rejects_cross_org_value_owner(client: TestClient):
    h, _org_id, _sid, _spid, _iid, _owner = _agile_base(client)
    h_b = _second_org(client)
    foreign_owner = _owner_membership_id(client, h_b, h_b["X-Organization-Id"])
    r = client.post(
        f"{AGILE}/squads",
        json={"name": "Cross org squad", "value_owner_membership_id": foreign_owner},
        headers=h,
    )
    assert r.status_code == 404
    squads = client.get(f"{AGILE}/squads", headers=h).json()
    assert not any(s["name"] == "Cross org squad" for s in squads)


def test_cannot_inactivate_last_value_owner(client: TestClient):
    h, _org_id, sid, _spid, _iid, _owner = _agile_base(client)
    membership = client.get(f"{AGILE}/squads/{sid}/memberships", headers=h).json()[0]
    r = client.patch(
        f"{AGILE}/squads/{sid}/memberships/{membership['id']}",
        json={"status": "inactive"},
        headers=h,
    )
    assert r.status_code == 409
    assert r.json()["code"] == "squad_missing_value_owner"
    still = client.get(f"{AGILE}/squads/{sid}/memberships", headers=h).json()[0]
    assert still["status"] == "active"


def test_cannot_demote_last_value_owner(client: TestClient):
    h, _org_id, sid, _spid, _iid, _owner = _agile_base(client)
    membership = client.get(f"{AGILE}/squads/{sid}/memberships", headers=h).json()[0]
    r = client.patch(
        f"{AGILE}/squads/{sid}/memberships/{membership['id']}",
        json={"agile_role": "facilitator"},
        headers=h,
    )
    assert r.status_code == 409
    assert r.json()["code"] == "squad_missing_value_owner"
    still = client.get(f"{AGILE}/squads/{sid}/memberships", headers=h).json()[0]
    assert still["agile_role"] == "value_owner"


def test_can_demote_value_owner_when_another_exists(client: TestClient):
    h, org_id, sid, _spid, _iid, _owner = _agile_base(client)
    second = _member_headers(org_id, ["quality_manager"])
    second_mid = _owner_membership_id(client, second, org_id)
    assert (
        client.post(
            f"{AGILE}/squads/{sid}/memberships",
            json={"membership_id": second_mid, "agile_role": "value_owner"},
            headers=h,
        ).status_code
        == 201
    )
    first = next(
        m
        for m in client.get(f"{AGILE}/squads/{sid}/memberships", headers=h).json()
        if m["membership_id"] != second_mid
    )
    ok = client.patch(
        f"{AGILE}/squads/{sid}/memberships/{first['id']}",
        json={"agile_role": "facilitator"},
        headers=h,
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["agile_role"] == "facilitator"


# --- R2: execution records must match a live sprint allocation ---


def _allocated_and_active(client: TestClient):
    h, org_id, sid, spid, iid, owner = _agile_base(client)
    assert (
        client.post(
            f"{AGILE}/sprints/{spid}/cards",
            json={"action_item_id": iid},
            headers=h,
        ).status_code
        == 201
    )
    assert client.post(f"{AGILE}/sprints/{spid}/activate", headers=h).status_code == 200
    return h, org_id, sid, spid, iid, owner


def test_check_in_accepts_allocated_sprint(client: TestClient):
    h, _org, _sid, spid, iid, _owner = _allocated_and_active(client)
    r = client.post(
        f"{ACTIONS}/{iid}/check-ins",
        json={"health": "on_track", "progress_note": "Em dia", "sprint_id": spid},
        headers=h,
    )
    assert r.status_code == 201, r.text
    assert r.json()["sprint_id"] == spid


def test_check_in_rejects_other_sprint(client: TestClient):
    h, _org, sid, _spid, iid, _owner = _allocated_and_active(client)
    other = _new_sprint(client, h, sid, "Sprint sem o card")
    r = client.post(
        f"{ACTIONS}/{iid}/check-ins",
        json={"health": "on_track", "progress_note": "Nota", "sprint_id": other},
        headers=h,
    )
    assert r.status_code == 409
    assert r.json()["code"] == "action_sprint_mismatch"


def test_check_in_rejects_other_org_sprint(client: TestClient):
    h, _org, _sid, _spid, iid, _owner = _allocated_and_active(client)
    h_b = _second_org(client)
    owner_b = _owner_membership_id(client, h_b, h_b["X-Organization-Id"])
    squad_b = client.post(
        f"{AGILE}/squads",
        json={"name": "Squad B", "value_owner_membership_id": owner_b},
        headers=h_b,
    ).json()["id"]
    sprint_b = _new_sprint(client, h_b, squad_b, "Sprint B")
    r = client.post(
        f"{ACTIONS}/{iid}/check-ins",
        json={"health": "on_track", "progress_note": "Nota", "sprint_id": sprint_b},
        headers=h,
    )
    assert r.status_code == 409
    assert r.json()["code"] == "action_sprint_mismatch"


def test_impediment_rejects_removed_allocation_but_keeps_history(client: TestClient):
    h, _org, _sid, spid, iid, _owner = _allocated_and_active(client)
    created = client.post(
        f"{ACTIONS}/{iid}/impediments",
        json={"title": "Antes da remoção", "sprint_id": spid},
        headers=h,
    )
    assert created.status_code == 201, created.text
    assert (
        client.request(
            "DELETE",
            f"{AGILE}/sprints/{spid}/cards/{iid}",
            json={"removal_reason": "descope"},
            headers=h,
        ).status_code
        == 204
    )

    blocked = client.post(
        f"{ACTIONS}/{iid}/impediments",
        json={"title": "Depois da remoção", "sprint_id": spid},
        headers=h,
    )
    assert blocked.status_code == 409
    assert blocked.json()["code"] == "action_sprint_mismatch"

    blocked_check_in = client.post(
        f"{ACTIONS}/{iid}/check-ins",
        json={"health": "blocked", "progress_note": "Sem card", "sprint_id": spid},
        headers=h,
    )
    assert blocked_check_in.status_code == 409
    assert blocked_check_in.json()["code"] == "action_sprint_mismatch"

    history = client.get(f"{ACTIONS}/{iid}/impediments", headers=h)
    assert history.status_code == 200
    assert [i["title"] for i in history.json()] == ["Antes da remoção"]


def test_check_in_without_sprint_is_allowed(client: TestClient):
    h, _org, _sid, _spid, iid, _owner = _agile_base(client)
    r = client.post(
        f"{ACTIONS}/{iid}/check-ins",
        json={"health": "attention", "progress_note": "Fora de sprint"},
        headers=h,
    )
    assert r.status_code == 201, r.text
    assert r.json()["sprint_id"] is None


# --- R3: ceremonies are always bound to one sprint ---


def _ceremony_event(
    client: TestClient, h: dict, *, sprint_id: str | None, event_type: str = "sprint_review"
):
    starts = datetime.now(timezone.utc)
    body = {
        "title": f"Cerimônia {event_type}",
        "event_type": event_type,
        "starts_at": starts.isoformat(),
        "ends_at": (starts + timedelta(hours=1)).isoformat(),
    }
    if sprint_id:
        body["sprint_id"] = sprint_id
    return client.post("/api/v1/agenda/events", json=body, headers=h)


def test_agenda_ceremony_event_requires_sprint(client: TestClient):
    h, _org, _sid, _spid, _iid, _owner = _agile_base(client)
    r = _ceremony_event(client, h, sprint_id=None)
    assert r.status_code == 422
    assert r.json()["code"] == "ceremony_sprint_required"


def test_agenda_update_to_ceremony_requires_sprint(client: TestClient):
    h, _org, _sid, spid, _iid, _owner = _agile_base(client)
    starts = datetime.now(timezone.utc)
    evt = client.post(
        "/api/v1/agenda/events",
        json={
            "title": "Reunião comum",
            "event_type": "meeting",
            "starts_at": starts.isoformat(),
            "ends_at": (starts + timedelta(hours=1)).isoformat(),
        },
        headers=h,
    )
    assert evt.status_code == 201, evt.text
    bad = client.patch(
        f"/api/v1/agenda/events/{evt.json()['id']}",
        json={"event_type": "retrospective"},
        headers=h,
    )
    assert bad.status_code == 422
    assert bad.json()["code"] == "ceremony_sprint_required"

    ok = client.patch(
        f"/api/v1/agenda/events/{evt.json()['id']}",
        json={"event_type": "retrospective", "sprint_id": spid},
        headers=h,
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["sprint_id"] == spid


def test_ceremony_record_rejects_other_sprint(client: TestClient):
    h, _org, sid, spid, _iid, _owner = _agile_base(client)
    other = _new_sprint(client, h, sid, "Sprint da cerimônia")
    evt = _ceremony_event(client, h, sprint_id=other)
    assert evt.status_code == 201, evt.text
    r = client.post(
        f"{AGILE}/sprints/{spid}/ceremony-records",
        json={"agenda_event_id": evt.json()["id"], "ceremony_type": "sprint_review"},
        headers=h,
    )
    assert r.status_code == 409
    assert r.json()["code"] == "ceremony_sprint_mismatch"


def test_ceremony_record_rejects_type_divergence(client: TestClient):
    h, _org, _sid, spid, _iid, _owner = _agile_base(client)
    evt = _ceremony_event(client, h, sprint_id=spid, event_type="retrospective")
    assert evt.status_code == 201, evt.text
    r = client.post(
        f"{AGILE}/sprints/{spid}/ceremony-records",
        json={"agenda_event_id": evt.json()["id"], "ceremony_type": "sprint_review"},
        headers=h,
    )
    assert r.status_code == 422
    assert r.json()["code"] == "ceremony_type_mismatch"


def test_ceremony_record_is_append_only_by_revision(client: TestClient):
    h, _org, _sid, spid, _iid, _owner = _agile_base(client)
    evt = _ceremony_event(client, h, sprint_id=spid)
    eid = evt.json()["id"]
    first = client.post(
        f"{AGILE}/sprints/{spid}/ceremony-records",
        json={
            "agenda_event_id": eid,
            "ceremony_type": "sprint_review",
            "summary": "Primeira ata",
        },
        headers=h,
    )
    assert first.status_code == 201, first.text
    assert first.json()["revision"] == 1
    second = client.post(
        f"{AGILE}/sprints/{spid}/ceremony-records",
        json={
            "agenda_event_id": eid,
            "ceremony_type": "sprint_review",
            "summary": "Ata corrigida",
        },
        headers=h,
    )
    assert second.status_code == 201, second.text
    assert second.json()["revision"] == 2
    assert second.json()["id"] != first.json()["id"]
    listed = client.get(
        f"{AGILE}/sprints/{spid}/ceremony-records", headers=h
    ).json()
    assert len(listed) == 2
    assert {r["summary"] for r in listed} == {"Primeira ata", "Ata corrigida"}


# --- R4: dependencies are soft-deleted ---


def _two_items(client: TestClient, h: dict, owner: str, iid: str) -> str:
    pid = client.get("/api/v1/action-plans", headers=h).json()[0]["id"]
    return client.post(
        f"/api/v1/action-plans/{pid}/items",
        json={
            "action_kind": "improvement",
            "description": "Ação dependente",
            "owner_membership_id": owner,
            "due_at": _due(),
        },
        headers=h,
    ).json()["id"]


def test_dependency_soft_delete_keeps_history(client: TestClient):
    h, _org, _sid, _spid, iid, owner = _agile_base(client)
    item_b = _two_items(client, h, owner, iid)
    created = client.post(
        f"{ACTIONS}/{item_b}/dependencies",
        json={
            "predecessor_action_item_id": iid,
            "dependent_action_item_id": item_b,
            "dependency_type": "blocks",
        },
        headers=h,
    )
    assert created.status_code == 201, created.text
    dep_id = created.json()["id"]
    assert created.json()["status"] == "active"

    assert (
        client.delete(f"{ACTIONS}/{item_b}/dependencies/{dep_id}", headers=h).status_code
        == 204
    )
    assert client.get(f"{ACTIONS}/{item_b}/dependencies", headers=h).json() == []

    history = client.get(
        f"{ACTIONS}/{item_b}/dependencies",
        params={"include_removed": "true"},
        headers=h,
    ).json()
    assert len(history) == 1
    assert history[0]["id"] == dep_id
    assert history[0]["status"] == "removed"
    assert history[0]["removed_at"] is not None
    assert history[0]["removed_by"] is not None

    # Deleting twice is not found — the edge is already gone from the board.
    assert (
        client.delete(f"{ACTIONS}/{item_b}/dependencies/{dep_id}", headers=h).status_code
        == 404
    )


def test_dependency_can_be_recreated_after_removal(client: TestClient):
    h, _org, _sid, _spid, iid, owner = _agile_base(client)
    item_b = _two_items(client, h, owner, iid)
    body = {
        "predecessor_action_item_id": iid,
        "dependent_action_item_id": item_b,
        "dependency_type": "blocks",
    }
    first = client.post(f"{ACTIONS}/{item_b}/dependencies", json=body, headers=h)
    assert first.status_code == 201
    dup = client.post(f"{ACTIONS}/{item_b}/dependencies", json=body, headers=h)
    assert dup.status_code == 409
    assert dup.json()["code"] == "dependency_duplicate"

    assert (
        client.delete(
            f"{ACTIONS}/{item_b}/dependencies/{first.json()['id']}", headers=h
        ).status_code
        == 204
    )
    again = client.post(f"{ACTIONS}/{item_b}/dependencies", json=body, headers=h)
    assert again.status_code == 201, again.text
    assert again.json()["id"] != first.json()["id"]

    history = client.get(
        f"{ACTIONS}/{item_b}/dependencies",
        params={"include_removed": "true"},
        headers=h,
    ).json()
    assert len(history) == 2
    assert {d["status"] for d in history} == {"active", "removed"}


def test_removed_dependency_no_longer_blocks_or_cycles(client: TestClient):
    h, _org, sid, spid, iid, owner = _agile_base(client)
    item_b = _two_items(client, h, owner, iid)
    dep = client.post(
        f"{ACTIONS}/{item_b}/dependencies",
        json={
            "predecessor_action_item_id": iid,
            "dependent_action_item_id": item_b,
            "dependency_type": "blocks",
        },
        headers=h,
    )
    assert dep.status_code == 201

    reverse_blocked = client.post(
        f"{ACTIONS}/{iid}/dependencies",
        json={
            "predecessor_action_item_id": item_b,
            "dependent_action_item_id": iid,
            "dependency_type": "blocks",
        },
        headers=h,
    )
    assert reverse_blocked.status_code == 409
    assert reverse_blocked.json()["code"] == "dependency_cycle"

    assert (
        client.delete(
            f"{ACTIONS}/{item_b}/dependencies/{dep.json()['id']}", headers=h
        ).status_code
        == 204
    )
    reverse_ok = client.post(
        f"{ACTIONS}/{iid}/dependencies",
        json={
            "predecessor_action_item_id": item_b,
            "dependent_action_item_id": iid,
            "dependency_type": "blocks",
        },
        headers=h,
    )
    assert reverse_ok.status_code == 201, reverse_ok.text

    board = client.get(f"{AGILE}/board", params={"squad_id": sid}, headers=h).json()
    cards = {c["action_item_id"]: c for col in board["columns"] for c in col["cards"]}
    assert cards[item_b]["blocking_dependency_count"] == 0
    assert cards[item_b]["has_blocking_dependency"] is False
    assert cards[iid]["blocking_dependency_count"] == 1
    assert cards[iid]["has_blocking_dependency"] is True


# --- R5: the board answers without follow-up calls ---


def test_board_card_carries_execution_signals(client: TestClient):
    h, _org, sid, spid, iid, owner = _agile_base(client)
    item_b = _two_items(client, h, owner, iid)
    assert (
        client.post(
            f"{AGILE}/sprints/{spid}/cards",
            json={"action_item_id": iid},
            headers=h,
        ).status_code
        == 201
    )
    assert client.post(f"{AGILE}/sprints/{spid}/activate", headers=h).status_code == 200
    assert (
        client.post(
            f"{ACTIONS}/{iid}/check-ins",
            json={
                "health": "attention",
                "progress_note": "Aguardando fornecedor",
                "sprint_id": spid,
            },
            headers=h,
        ).status_code
        == 201
    )
    for title in ("Impedimento 1", "Impedimento 2"):
        assert (
            client.post(
                f"{ACTIONS}/{iid}/impediments",
                json={"title": title, "sprint_id": spid},
                headers=h,
            ).status_code
            == 201
        )
    assert (
        client.post(
            f"{ACTIONS}/{iid}/dependencies",
            json={
                "predecessor_action_item_id": item_b,
                "dependent_action_item_id": iid,
                "dependency_type": "blocks",
            },
            headers=h,
        ).status_code
        == 201
    )

    board = client.get(f"{AGILE}/board", params={"squad_id": sid}, headers=h)
    assert board.status_code == 200, board.text
    card = next(
        c
        for col in board.json()["columns"]
        for c in col["cards"]
        if c["action_item_id"] == iid
    )
    assert card["open_impediment_count"] == 2
    assert card["has_open_impediment"] is True
    assert card["blocking_dependency_count"] == 1
    assert card["has_blocking_dependency"] is True
    assert card["latest_check_in_at"] is not None
    assert card["latest_check_in_health"] == "attention"
    # Assessment-origin action: no OI analysis provenance to report.
    assert card["source_analysis_run_id"] is None
    assert card["source_finding_code"] is None
    assert card["source_analysis_is_stale"] is None


def test_board_card_without_activity_reports_zeroes(client: TestClient):
    h, _org, sid, spid, iid, _owner = _agile_base(client)
    assert (
        client.post(
            f"{AGILE}/sprints/{spid}/cards",
            json={"action_item_id": iid},
            headers=h,
        ).status_code
        == 201
    )
    board = client.get(f"{AGILE}/board", params={"squad_id": sid}, headers=h).json()
    card = next(
        c
        for col in board["columns"]
        for c in col["cards"]
        if c["action_item_id"] == iid
    )
    assert card["open_impediment_count"] == 0
    assert card["blocking_dependency_count"] == 0
    assert card["latest_check_in_at"] is None
    assert card["latest_check_in_health"] is None


# --- R7: sprint metrics ---


def test_metrics_are_null_without_sample(client: TestClient):
    h, _org, _sid, spid, iid, _owner = _allocated_and_active(client)
    m = client.get(f"{AGILE}/sprints/{spid}/metrics", headers=h)
    assert m.status_code == 200, m.text
    body = m.json()
    assert body["average_cycle_time_hours"] is None
    assert body["median_cycle_time_hours"] is None
    assert body["blocked_time_hours"] is None
    assert body["review_outcome"] is None
    assert body["check_in_stale_window_hours"] == 72
    assert body["cards_without_recent_check_in"] == 1
    assert body["oldest_in_progress_age_hours"] is None


def test_metrics_cycle_time_blocked_time_and_review(client: TestClient):
    h, org_id, _sid, spid, iid, _owner = _allocated_and_active(client)
    validator = _member_headers(org_id, ["quality_manager"])
    assert (
        client.post(
            f"{ACTIONS}/{iid}/check-ins",
            json={"health": "on_track", "progress_note": "Andando", "sprint_id": spid},
            headers=h,
        ).status_code
        == 201
    )
    open_imp = client.post(
        f"{ACTIONS}/{iid}/impediments",
        json={"title": "Bloqueio aberto", "sprint_id": spid},
        headers=h,
    )
    assert open_imp.status_code == 201

    assert (
        client.post(f"/api/v1/action-items/{iid}/transitions/start", headers=h).status_code
        == 200
    )
    in_flight = client.get(f"{AGILE}/sprints/{spid}/metrics", headers=h).json()
    assert in_flight["oldest_in_progress_age_hours"] is not None
    assert in_flight["oldest_in_progress_age_hours"] >= 0
    assert in_flight["blocked_time_hours"] is not None
    assert in_flight["cards_without_recent_check_in"] == 0

    assert (
        client.post(
            f"/api/v1/action-items/{iid}/transitions/mark_implemented", headers=h
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/v1/action-items/{iid}/transitions/validate", headers=validator
        ).status_code
        == 200
    )

    evt = _ceremony_event(client, h, sprint_id=spid)
    assert (
        client.post(
            f"{AGILE}/sprints/{spid}/ceremony-records",
            json={
                "agenda_event_id": evt.json()["id"],
                "ceremony_type": "sprint_review",
                "summary": "Meta atingida com um bloqueio",
            },
            headers=h,
        ).status_code
        == 201
    )

    done = client.get(f"{AGILE}/sprints/{spid}/metrics", headers=h).json()
    assert done["completed_cards"] == 1
    assert done["average_cycle_time_hours"] is not None
    assert done["average_cycle_time_hours"] >= 0
    assert done["median_cycle_time_hours"] == done["average_cycle_time_hours"]
    assert done["oldest_in_progress_age_hours"] is None
    assert done["review_outcome"] == "Meta atingida com um bloqueio"


def test_metrics_count_carry_over_cards(client: TestClient):
    h, _org, sid, spid, iid, _owner = _allocated_and_active(client)
    target = _new_sprint(client, h, sid, "Sprint destino")
    assert (
        client.post(
            f"{AGILE}/sprints/{spid}/complete",
            json={"carry_decisions": [{"action_item_id": iid, "decision": target}]},
            headers=h,
        ).status_code
        == 200
    )
    m = client.get(f"{AGILE}/sprints/{target}/metrics", headers=h).json()
    assert m["carry_over_cards"] == 1
    assert m["planned_cards"] == 1
    assert m["average_cycle_time_hours"] is None


# --- R9: OI finding origin end to end ---


def test_e2e_oi_finding_to_efficacy_via_board(client: TestClient):
    """ISOI-007 E2E (OI origin): improvement case → mocked OI analysis run →
    action from finding → squad/sprint/board → check-in → impediment →
    dependency → execution → SoD validation → ceremony → metrics → history.

    The OI client is mocked exactly like the ISOI-004 tests: no live qmind-oi.
    """
    sub = f"oi-e2e-{uuid.uuid4()}"
    org_id = _create_org(client, sub)
    h = _headers(sub, org_id)
    _fill_profile(client, h)
    owner_mid = _membership_id(org_id, sub)
    validator = _member_headers(org_id, ["quality_manager"])

    case = _create_case(client, h)
    run = _create_run(client, h, case["id"], org_id)
    run_two = _create_run(client, h, case["id"], org_id)

    def _action_from_finding(run_id: str) -> dict:
        r = client.post(
            f"{CASES}/{case['id']}/analysis-runs/{run_id}/findings/F-1/actions",
            json={"owner_membership_id": owner_mid, "due_at": _due()},
            headers=h,
        )
        assert r.status_code == 201, r.text
        return r.json()

    item = _action_from_finding(run["id"])
    iid = item["id"]
    assert item["source_analysis_run_id"] == run["id"]
    assert item["source_finding_code"] == "F-1"
    blocker = _action_from_finding(run_two["id"])

    squad = client.post(
        f"{AGILE}/squads",
        json={
            "name": "OI Squad",
            "purpose": "Executar achados da IA",
            "value_owner_membership_id": owner_mid,
        },
        headers=h,
    )
    assert squad.status_code == 201, squad.text
    sid = squad.json()["id"]
    spid = _new_sprint(client, h, sid, "OI Sprint")
    assert (
        client.post(
            f"{AGILE}/sprints/{spid}/cards",
            json={"action_item_id": iid, "priority": "high", "estimate_points": 3},
            headers=h,
        ).status_code
        == 201
    )
    assert client.post(f"{AGILE}/sprints/{spid}/activate", headers=h).status_code == 200

    assert (
        client.post(
            f"{ACTIONS}/{iid}/check-ins",
            json={
                "health": "attention",
                "progress_note": "Mapeando o fluxo",
                "next_step": "Entrevistar o dono do processo",
                "sprint_id": spid,
                "idempotency_key": "oi-e2e-checkin-1",
            },
            headers=h,
        ).status_code
        == 201
    )
    imp = client.post(
        f"{ACTIONS}/{iid}/impediments",
        json={"title": "Dono do processo em férias", "severity": "high", "sprint_id": spid},
        headers=h,
    )
    assert imp.status_code == 201, imp.text
    dep = client.post(
        f"{ACTIONS}/{iid}/dependencies",
        json={
            "predecessor_action_item_id": blocker["id"],
            "dependent_action_item_id": iid,
            "dependency_type": "blocks",
        },
        headers=h,
    )
    assert dep.status_code == 201, dep.text

    board = client.get(
        f"{AGILE}/board", params={"squad_id": sid, "sprint_id": spid}, headers=h
    )
    assert board.status_code == 200, board.text
    selected = next(c for c in board.json()["columns"] if c["key"] == "selected")
    card = next(c for c in selected["cards"] if c["action_item_id"] == iid)
    assert card["improvement_case_id"] == case["id"]
    assert card["source_analysis_run_id"] == run["id"]
    assert card["source_finding_code"] == "F-1"
    assert card["source_analysis_is_stale"] is False
    assert card["open_impediment_count"] == 1
    assert card["blocking_dependency_count"] == 1
    assert card["latest_check_in_health"] == "attention"

    # Case context changed → the analysis behind this card is no longer current.
    assert (
        client.patch(
            f"{CASES}/{case['id']}",
            json={"problem_statement": "Atrasos recorrentes na entrega"},
            headers=h,
        ).status_code
        == 200
    )
    stale_card = next(
        c
        for col in client.get(f"{AGILE}/board", params={"squad_id": sid}, headers=h).json()[
            "columns"
        ]
        for c in col["cards"]
        if c["action_item_id"] == iid
    )
    assert stale_card["source_analysis_is_stale"] is True

    blocked = client.post(
        f"{AGILE}/board/move",
        json={"action_item_id": iid, "target_column": "in_progress"},
        headers=h,
    )
    assert blocked.status_code == 409
    assert blocked.json()["code"] == "impediment_override_required"
    assert (
        client.patch(
            f"{ACTIONS}/{iid}/impediments/{imp.json()['id']}",
            json={"status": "resolved", "resolution_note": "Substituto designado"},
            headers=h,
        ).status_code
        == 200
    )
    assert (
        client.delete(
            f"{ACTIONS}/{iid}/dependencies/{dep.json()['id']}", headers=h
        ).status_code
        == 204
    )
    assert (
        client.post(
            f"{AGILE}/board/move",
            json={"action_item_id": iid, "target_column": "in_progress"},
            headers=h,
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"{AGILE}/board/move",
            json={"action_item_id": iid, "target_column": "implemented"},
            headers=h,
        ).status_code
        == 200
    )

    sod = client.post(
        f"{AGILE}/board/move",
        json={"action_item_id": iid, "target_column": "validated"},
        headers=h,
    )
    assert sod.status_code == 403
    assert sod.json()["code"] == "sod_violation"

    # Actions derived from OI findings are improvements: validation closes them.
    assert item["efficacy_required"] is False
    validated = client.post(
        f"{AGILE}/board/move",
        json={"action_item_id": iid, "target_column": "done"},
        headers=validator,
    )
    assert validated.status_code == 200, validated.text
    assert validated.json()["item_status"] == "done"

    evt = _ceremony_event(client, h, sprint_id=spid)
    assert evt.status_code == 201, evt.text
    assert (
        client.post(
            f"{AGILE}/sprints/{spid}/ceremony-records",
            json={
                "agenda_event_id": evt.json()["id"],
                "ceremony_type": "sprint_review",
                "summary": "Achado da IA encerrado",
                "decisions": "Manter o novo fluxo",
            },
            headers=h,
        ).status_code
        == 201
    )

    metrics = client.get(f"{AGILE}/sprints/{spid}/metrics", headers=h).json()
    assert metrics["completed_cards"] == 1
    assert metrics["throughput"] == 1
    assert metrics["average_cycle_time_hours"] is not None
    assert metrics["blocked_time_hours"] is not None
    assert metrics["review_outcome"] == "Achado da IA encerrado"

    assert len(client.get(f"{ACTIONS}/{iid}/check-ins", headers=h).json()) == 1
    assert len(client.get(f"{ACTIONS}/{iid}/impediments", headers=h).json()) == 1
    assert client.get(f"{ACTIONS}/{iid}/dependencies", headers=h).json() == []
    history = client.get(
        f"{ACTIONS}/{iid}/dependencies",
        params={"include_removed": "true"},
        headers=h,
    ).json()
    assert [d["status"] for d in history] == ["removed"]
    assert client.get(f"/api/v1/action-items/{iid}", headers=h).json()["status"] == "done"
