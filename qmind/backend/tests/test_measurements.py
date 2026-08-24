"""ISOI-008 — measurement plans, indicators, records and target evaluation.

The through-line of these tests: measuring is how an action proves it worked,
and no measurement result is ever allowed to decide efficacy by itself.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.main import app
from app.storage.memory import InMemoryObjectStorage
from tests.conftest import ADMIN_URL
from tests.test_actions import _owner_membership_id, _plan_ready
from tests.test_findings import _member_headers
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
PLANS = "/api/v1/organizations/current/measurement-plans"


@pytest.fixture()
def client():
    return TestClient(app)


def _ago(days: int) -> str:
    return (datetime.now(UTC) - timedelta(days=days)).isoformat()


def _ahead(days: int) -> str:
    return (datetime.now(UTC) + timedelta(days=days)).isoformat()


def _case_with_action_plan(client: TestClient) -> tuple[dict, str, str, str]:
    """An improvement case that already has an action plan, the OI path."""
    sub = f"meas-{uuid.uuid4()}"
    org = _create_org(client, sub)
    h = _headers(sub, org)
    _fill_profile(client, h)
    case = _create_case(client, h)
    run = _create_run(client, h, case["id"], org)
    mid = _membership_id(org, sub)
    created = client.post(
        f"{CASES}/{case['id']}/analysis-runs/{run['id']}/findings/F-1/actions",
        headers=h,
        json={"owner_membership_id": mid, "due_at": _ahead(7)},
    )
    assert created.status_code == 201, created.text
    plan = client.get(f"{CASES}/{case['id']}/actions", headers=h).json()["plan"]
    return h, org, case["id"], plan["id"]


def _indicator_payload(**overrides) -> dict:
    base = {
        "code": "TMA",
        "name": "Tempo médio de atendimento",
        "question": "O atendimento ficou mais rápido?",
        "unit_kind": "duration_minutes",
        "direction": "lower_is_better",
        "baseline_value": "48.500000",
        "baseline_at": _ago(30),
        "target_value": "24.000000",
        "target_due_at": _ahead(30),
        "data_source": "Relatório do service desk",
    }
    base.update(overrides)
    return base


def _active_plan_with_indicator(
    client: TestClient, h: dict, action_plan_id: str, **indicator_overrides
) -> tuple[str, str]:
    plan = client.post(
        PLANS,
        headers=h,
        json={
            "action_plan_id": action_plan_id,
            "objective": "Provar que o atendimento ficou mais rápido",
        },
    )
    assert plan.status_code == 201, plan.text
    plan_id = plan.json()["id"]
    ind = client.post(
        f"{PLANS}/{plan_id}/indicators",
        headers=h,
        json=_indicator_payload(**indicator_overrides),
    )
    assert ind.status_code == 201, ind.text
    activated = client.post(f"{PLANS}/{plan_id}/transitions/activate", headers=h)
    assert activated.status_code == 200, activated.text
    return plan_id, ind.json()["id"]


def _measure(
    client: TestClient, h: dict, plan_id: str, indicator_id: str, value: str, **extra
) -> dict:
    body = {
        "indicator_definition_id": indicator_id,
        "value": value,
        "measured_at": _ago(1),
    }
    body.update(extra)
    r = client.post(f"{PLANS}/{plan_id}/measurements", headers=h, json=body)
    assert r.status_code == 201, r.text
    return r.json()


def _observations(client: TestClient, h: dict, plan_id: str, **query) -> list[dict]:
    """Only the readings taken after the action — never the baseline."""
    qs = "&".join(f"{k}={v}" for k, v in query.items())
    url = f"{PLANS}/{plan_id}/measurements" + (f"?{qs}" if qs else "")
    listed = client.get(url, headers=h)
    assert listed.status_code == 200, listed.text
    return [r for r in listed.json() if r["measurement_kind"] == "observation"]


def _approve_evidence_for_measurement(
    client: TestClient, h: dict, action_item_id: str, measurement_id: str
) -> str:
    """Authorize, upload and approve a document, then attach it to a reading."""
    data = b"%PDF-1.4 measurement-proof"
    authorized = client.post(
        f"/api/v1/organizations/current/actions/{action_item_id}/evidences/authorize",
        headers=h,
        json={
            "content_type": "application/pdf",
            "declared_byte_size": len(data),
            "classification": "internal",
        },
    )
    assert authorized.status_code == 201, authorized.text
    evidence = authorized.json()["evidence"]
    InMemoryObjectStorage.instance().put_test_object(
        evidence["storage_key"], data, "application/pdf"
    )
    eid = evidence["id"]
    assert (
        client.post(
            f"/api/v1/evidences/{eid}/transitions/receive", headers=h
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/v1/evidences/{eid}/transitions/security_pass", headers=h
        ).status_code
        == 200
    )
    linked = client.post(
        f"/api/v1/evidences/{eid}/links",
        headers=h,
        json={"target_type": "measurement_record", "target_id": measurement_id},
    )
    assert linked.status_code == 201, linked.text
    return eid


# --- migration -----------------------------------------------------------


@pytest.mark.parametrize(
    "table",
    [
        "action_measurement_plans",
        "indicator_definitions",
        "measurement_records",
        "outcome_observation_measurements",
    ],
)
def test_migration_rls_forced_on_new_tables(table: str):
    eng = create_engine(ADMIN_URL)
    with eng.connect() as conn:
        rls = conn.execute(
            text(
                """
                SELECT relrowsecurity, relforcerowsecurity
                FROM pg_class WHERE relname = :t
                """
            ),
            {"t": table},
        ).one()
        assert rls.relrowsecurity is True
        assert rls.relforcerowsecurity is True
        pol = conn.execute(
            text(
                "SELECT polname FROM pg_policy WHERE polrelid = CAST(:t AS regclass)"
            ),
            {"t": table},
        ).scalar()
        assert pol == "tenant_isolation"
    eng.dispose()


def test_migration_measurements_cannot_be_deleted_by_app_role():
    """Append-only is enforced by the grant, not only by the service layer.

    A measurement is never rewritten, so the application role has neither
    DELETE nor UPDATE on it: a correction can only be a new row. An evidence
    link keeps UPDATE because removing one is a soft delete that stamps who
    removed it and why, and an evidence keeps UPDATE because disposal is a
    status change — but no table in the trail can lose a row.
    """
    eng = create_engine(ADMIN_URL)
    with eng.connect() as conn:
        no_write = {
            "measurement_records": (False, False),
            "outcome_observation_measurements": (False, False),
            "evidence_links": (False, True),
            "evidences": (False, True),
            "action_measurement_plans": (False, True),
            "indicator_definitions": (False, True),
        }
        for table, (may_delete, may_update) in no_write.items():
            allowed = conn.execute(
                text(
                    "SELECT has_table_privilege('qmind_app', :t, 'DELETE') AS d, "
                    "has_table_privilege('qmind_app', :t, 'UPDATE') AS u"
                ),
                {"t": table},
            ).one()
            assert allowed.d is may_delete, table
            assert allowed.u is may_update, table
    eng.dispose()


def test_migration_measurement_value_is_numeric_not_float():
    eng = create_engine(ADMIN_URL)
    with eng.connect() as conn:
        dtype = conn.execute(
            text(
                """
                SELECT data_type FROM information_schema.columns
                WHERE table_name = 'measurement_records' AND column_name = 'value'
                """
            )
        ).scalar_one()
        assert dtype == "numeric"
    eng.dispose()


# --- plan lifecycle ------------------------------------------------------


def test_plan_create_inherits_context_and_blocks_second_open_plan(client: TestClient):
    h, org, case_id, action_plan_id = _case_with_action_plan(client)
    created = client.post(
        PLANS,
        headers=h,
        json={"action_plan_id": action_plan_id, "objective": "Provar o efeito"},
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["improvement_case_id"] == case_id
    assert body["assessment_id"] is None
    assert body["status"] == "draft"
    assert body["organization_id"] == org
    assert body["objective"] == "Provar o efeito"
    # Whoever creates the plan answers for it until it is handed over, so the
    # plan is never left without a name behind it.
    assert body["owner_membership_id"] is not None
    assert body["owner_display_name"]

    dup = client.post(PLANS, headers=h, json={"action_plan_id": action_plan_id})
    assert dup.status_code == 409
    assert dup.json()["code"] == "measurement_plan_exists"

    closed = client.post(
        f"{PLANS}/{body['id']}/transitions/close",
        headers=h,
        json={"closure_reason": "Ação abandonada"},
    )
    assert closed.status_code == 200
    # once closed, the action plan may be measured again from scratch
    again = client.post(PLANS, headers=h, json={"action_plan_id": action_plan_id})
    assert again.status_code == 201, again.text


def test_activate_requires_indicator_with_settled_baseline(client: TestClient):
    h, _org, _case_id, action_plan_id = _case_with_action_plan(client)
    plan_id = client.post(
        PLANS, headers=h, json={"action_plan_id": action_plan_id}
    ).json()["id"]

    empty = client.post(f"{PLANS}/{plan_id}/transitions/activate", headers=h)
    assert empty.status_code == 422
    assert empty.json()["code"] == "measurement_plan_without_indicator"

    ind = client.post(
        f"{PLANS}/{plan_id}/indicators",
        headers=h,
        json=_indicator_payload(baseline_value=None, baseline_at=None),
    )
    assert ind.status_code == 201, ind.text
    blocked = client.post(f"{PLANS}/{plan_id}/transitions/activate", headers=h)
    assert blocked.status_code == 422
    assert blocked.json()["code"] == "indicator_baseline_required"

    # documenting *why* the baseline is missing is enough to go live
    revised = client.post(
        f"/api/v1/organizations/current/indicators/{ind.json()['id']}/revise",
        headers=h,
        json={
            "revision_reason": "Sem histórico anterior",
            "baseline_unavailable_reason": "O sistema só passou a registrar agora.",
        },
    )
    assert revised.status_code == 200, revised.text
    ok = client.post(f"{PLANS}/{plan_id}/transitions/activate", headers=h)
    assert ok.status_code == 200, ok.text
    assert ok.json()["status"] == "active"
    assert ok.json()["activated_at"]


def test_indicator_code_unique_while_active(client: TestClient):
    h, _org, _case_id, action_plan_id = _case_with_action_plan(client)
    plan_id = client.post(
        PLANS, headers=h, json={"action_plan_id": action_plan_id}
    ).json()["id"]
    first = client.post(
        f"{PLANS}/{plan_id}/indicators", headers=h, json=_indicator_payload()
    )
    assert first.status_code == 201
    dup = client.post(
        f"{PLANS}/{plan_id}/indicators", headers=h, json=_indicator_payload()
    )
    assert dup.status_code == 409
    assert dup.json()["code"] == "indicator_code_taken"

    retired = client.post(
        f"/api/v1/organizations/current/indicators/{first.json()['id']}/retire",
        headers=h,
        json={"retired_reason": "Indicador trocado"},
    )
    assert retired.status_code == 200
    assert retired.json()["status"] == "retired"
    reused = client.post(
        f"{PLANS}/{plan_id}/indicators", headers=h, json=_indicator_payload()
    )
    assert reused.status_code == 201, reused.text


def test_range_indicator_rejects_a_single_target(client: TestClient):
    """A band and a single number are two different indicators."""
    h, _org, _case_id, action_plan_id = _case_with_action_plan(client)
    plan_id = client.post(
        PLANS, headers=h, json={"action_plan_id": action_plan_id}
    ).json()["id"]
    bad = client.post(
        f"{PLANS}/{plan_id}/indicators",
        headers=h,
        json=_indicator_payload(direction="within_range", target_value="24.0"),
    )
    assert bad.status_code == 422


def test_half_a_range_can_be_drafted_but_not_activated(client: TestClient):
    """An incomplete target is a legitimate draft — teams negotiate the band.

    It just cannot go live: an active indicator with only a lower bound would
    collect numbers nobody can judge.
    """
    h, _org, _case_id, action_plan_id = _case_with_action_plan(client)
    plan_id = client.post(
        PLANS, headers=h, json={"action_plan_id": action_plan_id}
    ).json()["id"]
    drafted = client.post(
        f"{PLANS}/{plan_id}/indicators",
        headers=h,
        json=_indicator_payload(
            direction="within_range", target_value=None, target_min="1.0"
        ),
    )
    assert drafted.status_code == 201, drafted.text

    blocked = client.post(f"{PLANS}/{plan_id}/transitions/activate", headers=h)
    assert blocked.status_code == 422
    assert blocked.json()["code"] == "indicator_target_required"

    completed = client.post(
        f"/api/v1/organizations/current/indicators/{drafted.json()['id']}/revise",
        headers=h,
        json={"revision_reason": "Faixa acordada", "target_max": "9.0"},
    )
    assert completed.status_code == 200, completed.text
    assert client.post(
        f"{PLANS}/{plan_id}/transitions/activate", headers=h
    ).status_code == 200


def test_withdrawn_field_names_still_work(client: TestClient):
    """Callers built against the first ISOI-008 draft keep working.

    `purpose`, the free-text `unit` and the arithmetic direction names were all
    renamed. They are accepted and folded onto the canonical shape, so an
    integration written before revision 001 is not broken by it.
    """
    h, _org, _case_id, action_plan_id = _case_with_action_plan(client)
    plan = client.post(
        PLANS,
        headers=h,
        json={"action_plan_id": action_plan_id, "purpose": "Provar o efeito"},
    )
    assert plan.status_code == 201, plan.text
    assert plan.json()["objective"] == "Provar o efeito"

    indicator = client.post(
        f"{PLANS}/{plan.json()['id']}/indicators",
        headers=h,
        json=_indicator_payload(unit_kind=None, unit="min", direction="decrease_is_better"),
    )
    assert indicator.status_code == 201, indicator.text
    body = indicator.json()
    assert body["unit_kind"] == "duration_minutes"
    assert body["unit_label"] == "min"
    assert body["direction"] == "lower_is_better"


def test_baseline_is_recorded_as_the_first_measurement(client: TestClient):
    """The baseline is a reading, so it carries an author and a date.

    Storing it on the definition made "we started at 48.5" a claim nobody
    signed. It is echoed on the indicator for convenience, but it lives in the
    measurement history.
    """
    h, _org, _case_id, action_plan_id = _case_with_action_plan(client)
    plan_id, ind_id = _active_plan_with_indicator(client, h, action_plan_id)

    indicator = client.get(f"{PLANS}/{plan_id}/indicators", headers=h).json()[0]
    assert indicator["baseline_status"] == "recorded"
    assert indicator["baseline_value"] == "48.500000"
    assert indicator["baseline_measurement_id"]
    # ...and no reading after the action yet
    assert indicator["measurement_count"] == 0

    history = client.get(f"{PLANS}/{plan_id}/measurements", headers=h).json()
    baseline = next(r for r in history if r["measurement_kind"] == "baseline")
    assert baseline["id"] == indicator["baseline_measurement_id"]
    assert baseline["value"] == "48.500000"
    assert baseline["recorded_by"]

    second = client.post(
        f"{PLANS}/{plan_id}/measurements",
        headers=h,
        json={
            "indicator_definition_id": ind_id,
            "value": "50.000000",
            "measured_at": _ago(29),
            "measurement_kind": "baseline",
        },
    )
    assert second.status_code == 409
    assert second.json()["code"] == "baseline_already_recorded"


def test_measurement_cannot_be_dated_in_the_future(client: TestClient):
    h, _org, _case_id, action_plan_id = _case_with_action_plan(client)
    plan_id, ind_id = _active_plan_with_indicator(client, h, action_plan_id)
    r = client.post(
        f"{PLANS}/{plan_id}/measurements",
        headers=h,
        json={
            "indicator_definition_id": ind_id,
            "value": "10.0",
            "measured_at": _ahead(1),
        },
    )
    assert r.status_code == 422
    assert r.json()["code"] == "measured_at_in_future"


# --- measurement records -------------------------------------------------


def test_measurement_requires_active_plan(client: TestClient):
    h, _org, _case_id, action_plan_id = _case_with_action_plan(client)
    plan_id = client.post(
        PLANS, headers=h, json={"action_plan_id": action_plan_id}
    ).json()["id"]
    ind = client.post(
        f"{PLANS}/{plan_id}/indicators", headers=h, json=_indicator_payload()
    ).json()
    denied = client.post(
        f"{PLANS}/{plan_id}/measurements",
        headers=h,
        json={
            "indicator_definition_id": ind["id"],
            "value": "30.0",
            "measured_at": _ago(1),
        },
    )
    assert denied.status_code == 409
    assert denied.json()["code"] == "measurement_plan_not_active"


def test_measurement_decimal_precision_survives_round_trip(client: TestClient):
    h, _org, _case_id, action_plan_id = _case_with_action_plan(client)
    plan_id, ind_id = _active_plan_with_indicator(client, h, action_plan_id)
    created = _measure(client, h, plan_id, ind_id, "0.100000")
    second = _measure(client, h, plan_id, ind_id, "0.200000", measured_at=_ago(2))
    assert created["value"] == "0.100000"
    assert second["value"] == "0.200000"
    assert {r["value"] for r in _observations(client, h, plan_id)} == {
        "0.100000",
        "0.200000",
    }


def test_measurement_idempotency_key_replays_same_record(client: TestClient):
    h, _org, _case_id, action_plan_id = _case_with_action_plan(client)
    plan_id, ind_id = _active_plan_with_indicator(client, h, action_plan_id)
    body = {
        "indicator_definition_id": ind_id,
        "value": "22.000000",
        "measured_at": _ago(1),
    }
    first = client.post(
        f"{PLANS}/{plan_id}/measurements",
        headers={**h, "Idempotency-Key": "reading-2026-08"},
        json=body,
    )
    second = client.post(
        f"{PLANS}/{plan_id}/measurements",
        headers={**h, "Idempotency-Key": "reading-2026-08"},
        json=body,
    )
    assert first.status_code == 201
    assert second.status_code in (200, 201)
    assert second.json()["id"] == first.json()["id"]
    assert len(_observations(client, h, plan_id)) == 1

    # The same key with a different reading is a new command, not a retry:
    # replaying the first answer would report a number nobody asked for.
    diverged = client.post(
        f"{PLANS}/{plan_id}/measurements",
        headers={**h, "Idempotency-Key": "reading-2026-08"},
        json={**body, "value": "23.000000"},
    )
    assert diverged.status_code == 409
    assert diverged.json()["code"] == "idempotency_conflict"


def test_correction_supersedes_and_keeps_history(client: TestClient):
    h, _org, _case_id, action_plan_id = _case_with_action_plan(client)
    plan_id, ind_id = _active_plan_with_indicator(client, h, action_plan_id)
    wrong = _measure(client, h, plan_id, ind_id, "99.000000")
    corrected = client.post(
        f"/api/v1/organizations/current/measurements/{wrong['id']}/correct",
        headers=h,
        json={"value": "20.000000", "correction_reason": "Planilha errada"},
    )
    assert corrected.status_code == 201, corrected.text
    body = corrected.json()
    assert body["supersedes_measurement_id"] == wrong["id"]
    assert body["correction_reason"] == "Planilha errada"

    assert body["status"] == "active"
    assert [r["id"] for r in _observations(client, h, plan_id)] == [body["id"]]
    history = _observations(client, h, plan_id, include_superseded="true")
    assert {r["id"] for r in history} == {wrong["id"], body["id"]}
    superseded = next(r for r in history if r["id"] == wrong["id"])
    assert superseded["status"] == "superseded"
    assert superseded["superseded_by_measurement_id"] == body["id"]
    # the wrong number is still exactly what was reported
    assert superseded["value"] == "99.000000"

    twice = client.post(
        f"/api/v1/organizations/current/measurements/{wrong['id']}/correct",
        headers=h,
        json={"value": "1.0", "correction_reason": "de novo"},
    )
    assert twice.status_code == 409
    assert twice.json()["code"] == "measurement_already_superseded"


def test_revise_after_measurement_creates_new_version(client: TestClient):
    h, _org, _case_id, action_plan_id = _case_with_action_plan(client)
    plan_id, ind_id = _active_plan_with_indicator(client, h, action_plan_id)

    # before any data, revising edits in place
    edited = client.post(
        f"/api/v1/organizations/current/indicators/{ind_id}/revise",
        headers=h,
        json={"revision_reason": "Nome mais claro", "name": "TMA do suporte"},
    )
    assert edited.status_code == 200
    assert edited.json()["id"] == ind_id
    assert edited.json()["version"] == 1

    _measure(client, h, plan_id, ind_id, "30.000000")
    revised = client.post(
        f"/api/v1/organizations/current/indicators/{ind_id}/revise",
        headers=h,
        json={"revision_reason": "Meta renegociada", "target_value": "20.000000"},
    )
    assert revised.status_code == 200, revised.text
    new = revised.json()
    assert new["id"] != ind_id
    assert new["version"] == 2
    assert new["supersedes_indicator_id"] == ind_id
    assert new["lineage_id"] == edited.json()["lineage_id"]

    active = client.get(f"{PLANS}/{plan_id}/indicators", headers=h).json()
    assert [i["id"] for i in active] == [new["id"]]
    with_history = client.get(
        f"{PLANS}/{plan_id}/indicators?include_superseded=true", headers=h
    ).json()
    assert {i["id"] for i in with_history} == {ind_id, new["id"]}


# --- target evaluation ---------------------------------------------------


def test_summary_without_plan_says_not_planned(client: TestClient):
    h, _org, _case_id, action_plan_id = _case_with_action_plan(client)
    summary = client.get(
        f"/api/v1/action-plans/{action_plan_id}/measurement-summary", headers=h
    )
    assert summary.status_code == 200, summary.text
    body = summary.json()
    assert body["plan"] is None
    assert body["measurement_posture"] == "not_planned"
    assert body["target_posture"] == "unknown"
    assert body["substantiation"] == "none"
    assert body["headline"]
    assert body["what_to_do_next"]


def test_summary_states_awaiting_then_met(client: TestClient):
    h, _org, _case_id, action_plan_id = _case_with_action_plan(client)
    plan_id, ind_id = _active_plan_with_indicator(client, h, action_plan_id)
    url = f"/api/v1/action-plans/{action_plan_id}/measurement-summary"

    awaiting = client.get(url, headers=h).json()
    assert awaiting["measurement_posture"] == "awaiting_measurement"
    assert awaiting["target_posture"] == "unknown"
    assert awaiting["substantiation"] == "none"
    assert awaiting["baseline_status"] == "recorded"
    assert awaiting["evaluations"][0]["state"] == "awaiting_measurement"

    _measure(client, h, plan_id, ind_id, "40.000000")
    on_track = client.get(url, headers=h).json()
    assert on_track["evaluations"][0]["state"] == "on_track"
    assert on_track["target_posture"] == "unknown"

    _measure(client, h, plan_id, ind_id, "18.000000", measured_at=_ago(0))
    met = client.get(url, headers=h).json()
    ev = met["evaluations"][0]
    assert ev["state"] == "target_met"
    assert ev["latest_value"] == "18.000000"
    assert met["target_posture"] == "met"
    assert met["measurement_posture"] == "on_time"
    # A met target with nothing behind it is a claim, not a result.
    assert met["substantiation"] == "none"
    assert "comprova" in ev["what_to_do_next"].lower()


def test_substantiation_comes_only_from_attached_evidence(client: TestClient):
    """Reaching the target proves nothing until a document backs the reading."""
    h, _org, case_id, action_plan_id = _case_with_action_plan(client)
    action_item_id = client.get(f"{CASES}/{case_id}/actions", headers=h).json()[
        "items"
    ][0]["id"]
    plan_id, ind_id = _active_plan_with_indicator(client, h, action_plan_id)
    url = f"/api/v1/action-plans/{action_plan_id}/measurement-summary"

    measurement = _measure(client, h, plan_id, ind_id, "18.000000")
    assert client.get(url, headers=h).json()["substantiation"] == "none"

    _approve_evidence_for_measurement(client, h, action_item_id, measurement["id"])
    proven = client.get(url, headers=h).json()
    assert proven["substantiation"] == "verified"
    ev = proven["evaluations"][0]
    assert ev["evidence_link_count"] == 1
    assert ev["verified_evidence_count"] == 1
    assert "eficácia" in ev["what_to_do_next"].lower()


def test_unapproved_document_is_not_proof_yet(client: TestClient):
    h, _org, case_id, action_plan_id = _case_with_action_plan(client)
    action_item_id = client.get(f"{CASES}/{case_id}/actions", headers=h).json()[
        "items"
    ][0]["id"]
    plan_id, ind_id = _active_plan_with_indicator(client, h, action_plan_id)
    measurement = _measure(client, h, plan_id, ind_id, "18.000000")

    authorized = client.post(
        f"/api/v1/organizations/current/actions/{action_item_id}/evidences/authorize",
        headers=h,
        json={
            "content_type": "application/pdf",
            "declared_byte_size": 2048,
            "classification": "internal",
        },
    )
    assert authorized.status_code == 201, authorized.text
    linked = client.post(
        f"/api/v1/evidences/{authorized.json()['evidence']['id']}/links",
        headers=h,
        json={"target_type": "measurement_record", "target_id": measurement["id"]},
    )
    assert linked.status_code == 201, linked.text

    summary = client.get(
        f"/api/v1/action-plans/{action_plan_id}/measurement-summary", headers=h
    ).json()
    assert summary["substantiation"] == "partial"
    assert summary["evaluations"][0]["verified_evidence_count"] == 0


def test_summary_target_not_met_after_due_date(client: TestClient):
    h, _org, _case_id, action_plan_id = _case_with_action_plan(client)
    plan_id, ind_id = _active_plan_with_indicator(
        client, h, action_plan_id, target_due_at=_ago(2)
    )
    _measure(client, h, plan_id, ind_id, "45.000000")
    summary = client.get(
        f"/api/v1/action-plans/{action_plan_id}/measurement-summary", headers=h
    ).json()
    assert summary["evaluations"][0]["state"] == "target_not_met"
    assert summary["target_posture"] == "not_met"
    # not meeting the target is information, not a verdict
    assert "eficácia" in summary["evaluations"][0]["what_to_do_next"].lower()


def test_summary_overdue_when_cadence_is_missed(client: TestClient):
    h, _org, _case_id, action_plan_id = _case_with_action_plan(client)
    plan_id, ind_id = _active_plan_with_indicator(
        client, h, action_plan_id, measurement_frequency_days=7
    )
    _measure(client, h, plan_id, ind_id, "40.000000", measured_at=_ago(30))
    summary = client.get(
        f"/api/v1/action-plans/{action_plan_id}/measurement-summary", headers=h
    ).json()
    assert summary["measurement_posture"] == "overdue"
    assert summary["overdue_indicator_count"] == 1
    assert summary["evaluations"][0]["is_measurement_overdue"] is True
    assert summary["evaluations"][0]["next_measurement_due_at"]


def test_summary_mixed_targets(client: TestClient):
    h, _org, _case_id, action_plan_id = _case_with_action_plan(client)
    plan_id, met_id = _active_plan_with_indicator(client, h, action_plan_id)
    late = client.post(
        f"{PLANS}/{plan_id}/indicators",
        headers=h,
        json=_indicator_payload(code="SLA", name="SLA", target_due_at=_ago(1)),
    )
    assert late.status_code == 201, late.text
    _measure(client, h, plan_id, met_id, "10.000000")
    _measure(client, h, plan_id, late.json()["id"], "90.000000")
    summary = client.get(
        f"/api/v1/action-plans/{action_plan_id}/measurement-summary", headers=h
    ).json()
    assert summary["target_posture"] == "mixed"
    assert summary["indicator_count"] == 2


# --- authorization -------------------------------------------------------


def test_reader_can_read_but_not_write(client: TestClient):
    h, org, _case_id, action_plan_id = _case_with_action_plan(client)
    plan_id, ind_id = _active_plan_with_indicator(client, h, action_plan_id)
    rh = _reader_headers(org)

    assert client.get(f"{PLANS}/{plan_id}", headers=rh).status_code == 200
    assert (
        client.get(
            f"/api/v1/action-plans/{action_plan_id}/measurement-summary", headers=rh
        ).status_code
        == 200
    )
    assert (
        client.post(
            PLANS, headers=rh, json={"action_plan_id": action_plan_id}
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"{PLANS}/{plan_id}/measurements",
            headers=rh,
            json={
                "indicator_definition_id": ind_id,
                "value": "1.0",
                "measured_at": _ago(1),
            },
        ).status_code
        == 403
    )


def test_cross_org_measurement_plan_is_not_found(client: TestClient):
    h, _org, _case_id, action_plan_id = _case_with_action_plan(client)
    plan_id, ind_id = _active_plan_with_indicator(client, h, action_plan_id)
    other_sub = f"meas-other-{uuid.uuid4()}"
    other_org = _create_org(client, other_sub, "Outra Org")
    oh = _headers(other_sub, other_org)

    assert client.get(f"{PLANS}/{plan_id}", headers=oh).status_code == 404
    assert (
        client.get(
            f"/api/v1/action-plans/{action_plan_id}/measurement-summary", headers=oh
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"{PLANS}/{plan_id}/measurements",
            headers=oh,
            json={
                "indicator_definition_id": ind_id,
                "value": "1.0",
                "measured_at": _ago(1),
            },
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"/api/v1/organizations/current/indicators/{ind_id}/retire",
            headers=oh,
            json={"retired_reason": "x"},
        ).status_code
        == 404
    )


# --- end to end ----------------------------------------------------------


def test_e2e_oi_finding_measurement_to_efficacy(client: TestClient):
    """From an OI finding to a human efficacy decision, with proof attached.

    The point of the flow: at no moment does a met target move the action by
    itself. The number becomes visible on the board and in the case, and a
    second person still has to decide.
    """
    h, org, case_id, action_plan_id = _case_with_action_plan(client)
    items = client.get(f"{CASES}/{case_id}/actions", headers=h).json()
    action_item_id = items["items"][0]["id"]
    if items["plan"]["status"] == "draft":
        client.post(
            f"/api/v1/action-plans/{action_plan_id}/transitions/activate", headers=h
        )

    plan_id, indicator_id = _active_plan_with_indicator(client, h, action_plan_id)

    assert (
        client.post(
            f"/api/v1/action-items/{action_item_id}/transitions/start", headers=h
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/v1/action-items/{action_item_id}/transitions/mark_implemented",
            headers=h,
        ).status_code
        == 200
    )

    measurement = _measure(client, h, plan_id, indicator_id, "18.000000")

    # the reading is proof only once a document backs it
    authorized = client.post(
        f"/api/v1/organizations/current/actions/{action_item_id}/evidences/authorize",
        headers=h,
        json={
            "content_type": "application/pdf",
            "declared_byte_size": 2048,
            "classification": "internal",
        },
    )
    assert authorized.status_code == 201, authorized.text
    evidence_id = authorized.json()["evidence"]["id"]
    linked = client.post(
        f"/api/v1/evidences/{evidence_id}/links",
        headers=h,
        json={
            "target_type": "measurement_record",
            "target_id": measurement["id"],
        },
    )
    assert linked.status_code == 201, linked.text

    board = client.get(
        "/api/v1/organizations/current/agile/board", headers=h
    ).json()
    card = next(
        c
        for col in board["columns"]
        for c in col["cards"]
        if c["action_item_id"] == action_item_id
    )
    assert card["measurement_posture"] == "on_time"
    assert card["target_posture"] == "met"
    assert card["indicator_count"] == 1
    assert card["evidence_count_total"] == 1
    assert card["evidence_count_approved"] == 0  # still upload_pending

    # meeting the target changed nothing about the item's status
    assert (
        client.get(f"/api/v1/action-items/{action_item_id}", headers=h).json()["status"]
        == "implemented"
    )
    # ...and the person who implemented it still cannot bless it
    sod = client.post(
        f"/api/v1/action-items/{action_item_id}/transitions/validate", headers=h
    )
    assert sod.status_code == 403
    assert sod.json()["code"] == "sod_violation"

    validator = _member_headers(org, ["quality_manager"])
    validated = client.post(
        f"/api/v1/action-items/{action_item_id}/transitions/validate", headers=validator
    )
    assert validated.status_code == 200, validated.text

    observation = client.post(
        f"{CASES}/{case_id}/outcome-observations",
        headers=h,
        json={
            "result_direction": "improved",
            "observation_statement": "O tempo de atendimento caiu abaixo da meta.",
            "measurement_basis": "Indicador TMA",
            "observed_at": _ago(1),
            "measurement_record_ids": [measurement["id"]],
        },
    )
    assert observation.status_code == 201, observation.text

    evolution = client.get(f"{CASES}/{case_id}/evolution", headers=h).json()
    assert evolution["measurement_summary"]["target_posture"] == "met"
    # The document is attached but still in the upload queue, so the reading is
    # backed by something that nobody has verified yet.
    assert evolution["measurement_summary"]["substantiation"] == "partial"
    assert evolution["latest_outcome_observation"]["measurement_record_ids"] == [
        measurement["id"]
    ]
    assert evolution["closure_readiness"] in (
        "ready_for_review",
        "insufficient_information",
    )
    assert evolution["case"]["status"] != "closed"


def test_e2e_assessment_measurement_path(client: TestClient):
    """The same machinery, anchored on an assessment instead of a case."""
    h, org, _aid, fid, action_plan_id = _plan_ready(client)
    owner = _owner_membership_id(client, h, org)
    item = client.post(
        f"/api/v1/action-plans/{action_plan_id}/items",
        headers=h,
        json={
            "finding_id": fid,
            "action_kind": "corrective_action",
            "description": "Padronizar o registro de ocorrências",
            "owner_membership_id": owner,
            "due_at": _ahead(14),
        },
    )
    assert item.status_code == 201, item.text
    action_item_id = item.json()["id"]
    assert (
        client.post(
            f"/api/v1/action-plans/{action_plan_id}/transitions/activate", headers=h
        ).status_code
        == 200
    )

    plan = client.post(
        PLANS, headers=h, json={"action_plan_id": action_plan_id}
    )
    assert plan.status_code == 201, plan.text
    assert plan.json()["assessment_id"] is not None
    assert plan.json()["improvement_case_id"] is None
    plan_id = plan.json()["id"]
    indicator_id = client.post(
        f"{PLANS}/{plan_id}/indicators", headers=h, json=_indicator_payload()
    ).json()["id"]
    assert (
        client.post(f"{PLANS}/{plan_id}/transitions/activate", headers=h).status_code
        == 200
    )
    measurement = _measure(client, h, plan_id, indicator_id, "12.000000")

    authorized = client.post(
        f"/api/v1/organizations/current/actions/{action_item_id}/evidences/authorize",
        headers=h,
        json={
            "content_type": "application/pdf",
            "declared_byte_size": 2048,
            "classification": "internal",
        },
    )
    assert authorized.status_code == 201, authorized.text
    evidence = authorized.json()["evidence"]
    assert evidence["assessment_id"] is not None
    assert evidence["improvement_case_id"] is None
    assert (
        client.post(
            f"/api/v1/evidences/{evidence['id']}/links",
            headers=h,
            json={
                "target_type": "measurement_record",
                "target_id": measurement["id"],
            },
        ).status_code
        == 201
    )

    summary = client.get(
        f"/api/v1/action-plans/{action_plan_id}/measurement-summary", headers=h
    ).json()
    assert summary["target_posture"] == "met"
    assert summary["plan"]["assessment_id"] is not None
    assert (
        client.get(f"/api/v1/action-items/{action_item_id}", headers=h).json()["status"]
        == "open"
    )


def test_openapi_exposes_measurement_paths(client: TestClient):
    paths = client.get("/openapi.json").json()["paths"]
    assert PLANS in paths
    assert f"{PLANS}/{{plan_id}}/indicators" in paths
    assert f"{PLANS}/{{plan_id}}/measurements" in paths
    assert "/api/v1/action-plans/{action_plan_id}/measurement-summary" in paths
