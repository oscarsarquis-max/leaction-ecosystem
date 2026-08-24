"""ISOI-008 — evidence outside the assessment world.

An evidence belongs to exactly one context: an assessment or an improvement
case. Everything it links to must live in that same context, and unlinking is a
soft removal because "this used to be the proof" is itself audit information.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.test_improvement_case_evolution import (
    _create_case,
    _create_org,
    _create_run,
    _fill_profile,
    _headers,
    _membership_id,
    _reader_headers,
)

CASES = "/api/v1/organizations/current/improvement-cases"
EVIDENCES = "/api/v1/evidences"
LINKS = "/api/v1/organizations/current/evidence-links"
PLANS = "/api/v1/organizations/current/measurement-plans"


@pytest.fixture()
def client():
    return TestClient(app)


def _ahead(days: int) -> str:
    return (datetime.now(UTC) + timedelta(days=days)).isoformat()


def _ago(days: int) -> str:
    return (datetime.now(UTC) - timedelta(days=days)).isoformat()


def _authorize_payload(**overrides) -> dict:
    base = {
        "content_type": "application/pdf",
        "declared_byte_size": 1024,
        "classification": "internal",
    }
    base.update(overrides)
    return base


def _case_with_action(client: TestClient, sub: str | None = None) -> dict:
    """OI path: case → analysis → action item, everything a link can point at."""
    sub = sub or f"evctx-{uuid.uuid4()}"
    org = _create_org(client, sub)
    h = _headers(sub, org)
    _fill_profile(client, h)
    case = _create_case(client, h)
    run = _create_run(client, h, case["id"], org)
    mid = _membership_id(org, sub)
    item = client.post(
        f"{CASES}/{case['id']}/analysis-runs/{run['id']}/findings/F-1/actions",
        headers=h,
        json={"owner_membership_id": mid, "due_at": _ahead(7)},
    )
    assert item.status_code == 201, item.text
    plan = client.get(f"{CASES}/{case['id']}/actions", headers=h).json()
    return {
        "headers": h,
        "org": org,
        "case_id": case["id"],
        "action_plan_id": plan["plan"]["id"],
        "action_item_id": plan["items"][0]["id"],
    }


# --- authorize in a case context ----------------------------------------


def test_case_authorize_creates_case_scoped_evidence(client: TestClient):
    world = _case_with_action(client)
    h = world["headers"]
    r = client.post(
        f"{CASES}/{world['case_id']}/evidences/authorize",
        headers=h,
        json=_authorize_payload(),
    )
    assert r.status_code == 201, r.text
    evidence = r.json()["evidence"]
    assert evidence["improvement_case_id"] == world["case_id"]
    assert evidence["assessment_id"] is None
    assert evidence["status"] == "upload_pending"
    assert r.json()["upload"]["url"]
    # R9: the case itself is a legitimate attachment target, so authorizing in a
    # case context already anchors the document to the case.
    link = r.json()["link"]
    assert link is not None
    assert link["target_type"] == "improvement_case"
    assert link["target_id"] == world["case_id"]


def test_action_authorize_links_in_the_same_step(client: TestClient):
    world = _case_with_action(client)
    h = world["headers"]
    r = client.post(
        f"/api/v1/organizations/current/actions/{world['action_item_id']}"
        "/evidences/authorize",
        headers=h,
        json=_authorize_payload(),
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["evidence"]["improvement_case_id"] == world["case_id"]
    assert body["link"] is not None
    assert body["link"]["target_type"] == "action_item"
    assert body["link"]["target_id"] == world["action_item_id"]
    assert body["link"]["removed_at"] is None

    listed = client.get(
        f"{LINKS}?target_type=action_item&target_id={world['action_item_id']}",
        headers=h,
    )
    assert listed.status_code == 200
    attachments = listed.json()
    assert [a["link"]["id"] for a in attachments] == [body["link"]["id"]]
    # The document summary travels with the link so the browser needs one call.
    assert attachments[0]["evidence"]["id"] == body["evidence"]["id"]
    assert attachments[0]["evidence"]["status"] == "upload_pending"


def test_action_authorize_is_idempotent(client: TestClient):
    world = _case_with_action(client)
    h = {**world["headers"], "Idempotency-Key": "evidence-run-1"}
    url = (
        f"/api/v1/organizations/current/actions/{world['action_item_id']}"
        "/evidences/authorize"
    )
    first = client.post(url, headers=h, json=_authorize_payload())
    second = client.post(url, headers=h, json=_authorize_payload())
    assert first.status_code == 201
    assert second.status_code in (200, 201)
    assert second.json()["evidence"]["id"] == first.json()["evidence"]["id"]
    assert second.json()["link"]["id"] == first.json()["link"]["id"]

    links = client.get(
        f"{LINKS}?target_type=action_item&target_id={world['action_item_id']}",
        headers=world["headers"],
    ).json()
    assert len(links) == 1


def test_authorize_key_reused_for_another_document_is_refused(client: TestClient):
    """Replaying is safe; reusing a key for a different file is not.

    Answering the second request with the first evidence would hand the caller
    an upload URL for a document it never described.
    """
    world = _case_with_action(client)
    h = {**world["headers"], "Idempotency-Key": "evidence-run-2"}
    url = (
        f"/api/v1/organizations/current/actions/{world['action_item_id']}"
        "/evidences/authorize"
    )
    first = client.post(url, headers=h, json=_authorize_payload())
    assert first.status_code == 201, first.text

    diverged = client.post(
        url,
        headers=h,
        json=_authorize_payload(content_type="image/png", declared_byte_size=4096),
    )
    assert diverged.status_code == 409, diverged.text
    assert diverged.json()["code"] == "idempotency_conflict"

    # And the first authorization is still the only one.
    links = client.get(
        f"{LINKS}?target_type=action_item&target_id={world['action_item_id']}",
        headers=world["headers"],
    ).json()
    assert len(links) == 1


def test_closed_case_stops_accepting_evidence(client: TestClient):
    world = _case_with_action(client)
    h = world["headers"]
    for status in ("analyzing", "acting", "reviewing", "closed"):
        step = client.patch(
            f"{CASES}/{world['case_id']}", headers=h, json={"status": status}
        )
        assert step.status_code == 200, step.text
    denied = client.post(
        f"{CASES}/{world['case_id']}/evidences/authorize",
        headers=h,
        json=_authorize_payload(),
    )
    assert denied.status_code == 409
    assert denied.json()["code"] == "improvement_case_closed"


def test_cross_org_authorize_is_not_found(client: TestClient):
    world = _case_with_action(client)
    other_sub = f"evctx-other-{uuid.uuid4()}"
    other_org = _create_org(client, other_sub, "Outra Org")
    oh = _headers(other_sub, other_org)

    assert (
        client.post(
            f"{CASES}/{world['case_id']}/evidences/authorize",
            headers=oh,
            json=_authorize_payload(),
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"/api/v1/organizations/current/actions/{world['action_item_id']}"
            "/evidences/authorize",
            headers=oh,
            json=_authorize_payload(),
        ).status_code
        == 404
    )


# --- context is a boundary, not a suggestion -----------------------------


def test_link_cannot_cross_improvement_cases(client: TestClient):
    world = _case_with_action(client)
    h = world["headers"]
    org = world["org"]
    # A second case in the same org, with its own action item.
    case_b = _create_case(client, h)
    run_b = _create_run(client, h, case_b["id"], org)
    mid = _membership_id(org, next(iter([h["X-Dev-User-Sub"]])))
    item_b = client.post(
        f"{CASES}/{case_b['id']}/analysis-runs/{run_b['id']}/findings/F-1/actions",
        headers=h,
        json={"owner_membership_id": mid, "due_at": _ahead(7)},
    )
    assert item_b.status_code == 201, item_b.text
    plan_b = client.get(f"{CASES}/{case_b['id']}/actions", headers=h).json()
    action_b = plan_b["items"][0]["id"]

    evidence = client.post(
        f"{CASES}/{world['case_id']}/evidences/authorize",
        headers=h,
        json=_authorize_payload(),
    ).json()["evidence"]

    denied = client.post(
        f"{EVIDENCES}/{evidence['id']}/links",
        headers=h,
        json={"target_type": "action_item", "target_id": action_b},
    )
    assert denied.status_code == 422
    assert denied.json()["code"] == "link_context_mismatch"

    allowed = client.post(
        f"{EVIDENCES}/{evidence['id']}/links",
        headers=h,
        json={"target_type": "action_item", "target_id": world["action_item_id"]},
    )
    assert allowed.status_code == 201, allowed.text


def test_link_to_check_in_and_measurement_and_observation(client: TestClient):
    world = _case_with_action(client)
    h = world["headers"]
    evidence = client.post(
        f"{CASES}/{world['case_id']}/evidences/authorize",
        headers=h,
        json=_authorize_payload(),
    ).json()["evidence"]

    check_in = client.post(
        f"/api/v1/organizations/current/actions/{world['action_item_id']}/check-ins",
        headers=h,
        json={"health": "on_track", "progress_note": "Piloto rodando"},
    )
    assert check_in.status_code == 201, check_in.text

    plan = client.post(
        PLANS, headers=h, json={"action_plan_id": world["action_plan_id"]}
    ).json()
    indicator = client.post(
        f"{PLANS}/{plan['id']}/indicators",
        headers=h,
        json={
            "code": "TMA",
            "name": "Tempo médio",
            "unit": "min",
            "direction": "decrease_is_better",
            "baseline_value": "40.000000",
            "target_value": "20.000000",
            "target_due_at": _ahead(30),
        },
    ).json()
    assert client.post(
        f"{PLANS}/{plan['id']}/transitions/activate", headers=h
    ).status_code == 200
    measurement = client.post(
        f"{PLANS}/{plan['id']}/measurements",
        headers=h,
        json={
            "indicator_definition_id": indicator["id"],
            "value": "18.000000",
            "measured_at": _ago(1),
        },
    )
    assert measurement.status_code == 201, measurement.text

    observation = client.post(
        f"{CASES}/{world['case_id']}/outcome-observations",
        headers=h,
        json={
            "result_direction": "improved",
            "observation_statement": "Tempo caiu",
            "measurement_basis": "Indicador TMA",
            "observed_at": _ago(1),
        },
    )
    assert observation.status_code == 201, observation.text

    for target_type, target_id in (
        ("action_check_in", check_in.json()["id"]),
        ("measurement_record", measurement.json()["id"]),
        ("outcome_observation", observation.json()["id"]),
    ):
        created = client.post(
            f"{EVIDENCES}/{evidence['id']}/links",
            headers=h,
            json={"target_type": target_type, "target_id": target_id},
        )
        assert created.status_code == 201, f"{target_type}: {created.text}"
        assert created.json()["target_type"] == target_type


def test_unknown_target_id_is_not_found(client: TestClient):
    world = _case_with_action(client)
    h = world["headers"]
    evidence = client.post(
        f"{CASES}/{world['case_id']}/evidences/authorize",
        headers=h,
        json=_authorize_payload(),
    ).json()["evidence"]
    r = client.post(
        f"{EVIDENCES}/{evidence['id']}/links",
        headers=h,
        json={"target_type": "measurement_record", "target_id": str(uuid.uuid4())},
    )
    assert r.status_code == 404


# --- soft delete ---------------------------------------------------------


def test_unlink_is_soft_and_relink_is_possible(client: TestClient):
    world = _case_with_action(client)
    h = world["headers"]
    authorized = client.post(
        f"/api/v1/organizations/current/actions/{world['action_item_id']}"
        "/evidences/authorize",
        headers=h,
        json=_authorize_payload(),
    ).json()
    evidence_id = authorized["evidence"]["id"]
    link_id = authorized["link"]["id"]

    removed = client.request(
        "DELETE",
        f"{EVIDENCES}/{evidence_id}/links/{link_id}",
        headers=h,
        json={"removal_reason": "Anexado ao item errado"},
    )
    assert removed.status_code == 204, removed.text

    active = client.get(f"{EVIDENCES}/{evidence_id}/links", headers=h).json()
    assert active == []
    history = client.get(
        f"{EVIDENCES}/{evidence_id}/links?include_removed=true", headers=h
    ).json()
    assert len(history) == 1
    assert history[0]["id"] == link_id
    assert history[0]["removed_at"] is not None
    assert history[0]["removed_by"] is not None
    assert history[0]["removal_reason"] == "Anexado ao item errado"

    by_target = client.get(
        f"{LINKS}?target_type=action_item&target_id={world['action_item_id']}",
        headers=h,
    ).json()
    assert by_target == []

    relinked = client.post(
        f"{EVIDENCES}/{evidence_id}/links",
        headers=h,
        json={"target_type": "action_item", "target_id": world["action_item_id"]},
    )
    assert relinked.status_code == 201, relinked.text
    assert relinked.json()["id"] != link_id
    assert (
        len(client.get(f"{EVIDENCES}/{evidence_id}/links", headers=h).json()) == 1
    )
    assert (
        len(
            client.get(
                f"{EVIDENCES}/{evidence_id}/links?include_removed=true", headers=h
            ).json()
        )
        == 2
    )


def test_unlink_twice_is_not_found(client: TestClient):
    world = _case_with_action(client)
    h = world["headers"]
    authorized = client.post(
        f"/api/v1/organizations/current/actions/{world['action_item_id']}"
        "/evidences/authorize",
        headers=h,
        json=_authorize_payload(),
    ).json()
    url = f"{EVIDENCES}/{authorized['evidence']['id']}/links/{authorized['link']['id']}"
    assert client.delete(url, headers=h).status_code == 204
    assert client.delete(url, headers=h).status_code == 404


def test_reader_reads_active_links_only(client: TestClient):
    world = _case_with_action(client)
    h = world["headers"]
    authorized = client.post(
        f"/api/v1/organizations/current/actions/{world['action_item_id']}"
        "/evidences/authorize",
        headers=h,
        json=_authorize_payload(),
    ).json()
    evidence_id = authorized["evidence"]["id"]
    rh = _reader_headers(world["org"])

    assert client.get(f"{EVIDENCES}/{evidence_id}/links", headers=rh).status_code == 200
    assert (
        client.get(
            f"{EVIDENCES}/{evidence_id}/links?include_removed=true", headers=rh
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"{EVIDENCES}/{evidence_id}/links",
            headers=rh,
            json={
                "target_type": "action_item",
                "target_id": world["action_item_id"],
            },
        ).status_code
        == 403
    )
    assert (
        client.delete(
            f"{EVIDENCES}/{evidence_id}/links/{authorized['link']['id']}", headers=rh
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"{CASES}/{world['case_id']}/evidences/authorize",
            headers=rh,
            json=_authorize_payload(),
        ).status_code
        == 403
    )


def test_openapi_exposes_contextual_evidence_paths(client: TestClient):
    paths = client.get("/openapi.json").json()["paths"]
    assert (
        "/api/v1/organizations/current/actions/{action_item_id}/evidences/authorize"
        in paths
    )
    assert (
        "/api/v1/organizations/current/improvement-cases/{case_id}/evidences/authorize"
        in paths
    )
    assert LINKS in paths


def test_action_owner_authorize_only_own_action_item(client: TestClient):
    """Two action_owners in the same org: only the ActionItem owner may authorize."""
    from tests.test_findings import _member_headers

    world = _case_with_action(client)
    org = world["org"]
    action_item_id = world["action_item_id"]

    owner_h = _member_headers(org, ["action_owner"])
    other_h = _member_headers(org, ["action_owner"])
    owner_mid = next(
        m["id"]
        for m in client.get("/api/v1/organizations/me/memberships", headers=owner_h).json()
        if m["organization_id"] == org
    )

    # Transfer ownership to the first action_owner (admin created the item).
    from app.db import admin_connection
    from sqlalchemy import text

    with admin_connection() as conn:
        conn.execute(
            text(
                """
                UPDATE action_items
                SET owner_membership_id = :mid
                WHERE id = :id AND organization_id = :org
                """
            ),
            {"mid": owner_mid, "id": action_item_id, "org": org},
        )
        conn.commit()

    ok = client.post(
        f"/api/v1/organizations/current/actions/{action_item_id}/evidences/authorize",
        headers=owner_h,
        json=_authorize_payload(),
    )
    assert ok.status_code == 201, ok.text

    denied = client.post(
        f"/api/v1/organizations/current/actions/{action_item_id}/evidences/authorize",
        headers=other_h,
        json=_authorize_payload(),
    )
    assert denied.status_code == 403, denied.text
    assert denied.json()["code"] == "forbidden"
