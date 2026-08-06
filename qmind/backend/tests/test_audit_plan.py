"""Audit plan — derived fill, ready gate, roles, cross-org, amendment."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.main import app
from tests.conftest import ADMIN_URL
from tests.test_assessment_ops import _create_draft_with_scope, _org_ctx
from tests.test_assessments import _bootstrap_org, _dev_headers


@pytest.fixture()
def client():
    return TestClient(app)


def _force_status(aid: str, status: str) -> None:
    eng = create_engine(ADMIN_URL)
    with eng.begin() as conn:
        conn.execute(
            text("UPDATE assessments SET status = :s, updated_at = now() WHERE id = :id"),
            {"s": status, "id": aid},
        )
    eng.dispose()


def _seed_guided(client: TestClient, h: dict, aid: str) -> None:
    assert client.get(f"/api/v1/assessments/{aid}/guided", headers=h).status_code == 200
    patch = client.patch(
        f"/api/v1/assessments/{aid}/guided",
        json={
            "context": {
                "organization_profile": {
                    "trade_name": "Acme Qualidade",
                    "summary": "Indústria",
                    "size_band": "M",
                },
                "qms_scope": {
                    "description": "Fabricação de componentes",
                    "exclusions": "8.3",
                    "exclusion_justification": "Sem projeto",
                },
                "products_services": [{"name": "Peça X", "notes": ""}],
                "sites": [{"name": "Planta 1", "location": "SP", "notes": ""}],
                "processes": [
                    {"name": "Produção", "owner": "João", "notes": ""},
                    {"name": "Compras", "owner": "Ana", "notes": ""},
                ],
                "stakeholders": [],
            },
            "current_step": "route",
        },
        headers=h,
    )
    assert patch.status_code == 200, patch.text


def test_create_derived_from_wizard_and_manual_preserved(client: TestClient):
    _h0, _org, h, model_id, sv_id, req_id = _org_ctx(client)
    aid = _create_draft_with_scope(client, h, model_id, sv_id, req_id)
    _seed_guided(client, h, aid)

    created = client.get(f"/api/v1/assessments/{aid}/audit-plan", headers=h)
    assert created.status_code == 200, created.text
    plan = created.json()
    assert "Acme" in plan["objective"] or "qualidade" in plan["objective"].lower()
    assert "Fabricação" in plan["scope_text"]
    assert len(plan["processes"]) >= 2
    assert plan["processes"][0]["from_preparation"] is True
    assert plan["field_sources"].get("scope_text") == "preparation"
    assert plan["plan_status"] == "draft"
    assert plan["readiness"]["pending_count"] >= 1

    updated_at = plan["updated_at"]
    manual = client.patch(
        f"/api/v1/assessments/{aid}/audit-plan",
        json={
            "objective": "Objetivo revisado pela equipe",
            "expected_updated_at": updated_at,
        },
        headers=h,
    )
    assert manual.status_code == 200, manual.text
    assert manual.json()["objective"] == "Objetivo revisado pela equipe"
    assert manual.json()["field_sources"]["objective"] == "manual"

    # Refresh must not overwrite manual objective
    refreshed = client.post(
        f"/api/v1/assessments/{aid}/audit-plan/refresh-from-preparation",
        json={},
        headers=h,
    )
    assert refreshed.status_code == 200, refreshed.text
    assert refreshed.json()["objective"] == "Objetivo revisado pela equipe"


def test_mark_ready_validation_and_success(client: TestClient):
    _h0, _org, h, model_id, sv_id, req_id = _org_ctx(client)
    aid = _create_draft_with_scope(client, h, model_id, sv_id, req_id)
    _seed_guided(client, h, aid)
    plan = client.get(f"/api/v1/assessments/{aid}/audit-plan", headers=h).json()
    assess = client.get(f"/api/v1/assessments/{aid}", headers=h).json()

    bad = client.post(f"/api/v1/assessments/{aid}/audit-plan/ready", headers=h)
    assert bad.status_code == 422, bad.text

    body = {
        "objective": "Avaliar SGQ da planta",
        "scope_text": plan["scope_text"] or "Escopo completo",
        "criteria": {
            "iso9001_2015": True,
            "internal_processes": True,
            "legal_contractual": False,
            "legal_contractual_text": "",
            "additional_text": "",
        },
        "processes": plan["processes"] or [{"name": "Produção", "owner": "", "notes": "", "from_preparation": False}],
        "lead_membership_id": assess["lead_membership_id"],
        "planned_start": "2026-09-01",
        "planned_end": "2026-09-05",
        "expected_updated_at": plan["updated_at"],
    }
    patched = client.patch(
        f"/api/v1/assessments/{aid}/audit-plan", json=body, headers=h
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["readiness"]["ready"] is True

    ready = client.post(
        f"/api/v1/assessments/{aid}/audit-plan/ready",
        json={"expected_updated_at": patched.json()["updated_at"]},
        headers=h,
    )
    assert ready.status_code == 200, ready.text
    assert ready.json()["plan_status"] == "ready"


def test_reader_cannot_mutate(client: TestClient):
    from tests.test_findings import _member_headers

    _h0, org, h, model_id, sv_id, req_id = _org_ctx(client)
    aid = _create_draft_with_scope(client, h, model_id, sv_id, req_id)
    plan = client.get(f"/api/v1/assessments/{aid}/audit-plan", headers=h)
    assert plan.status_code == 200
    h_reader = _member_headers(org, ["reader"])
    # Reader may read
    assert (
        client.get(f"/api/v1/assessments/{aid}/audit-plan", headers=h_reader).status_code
        == 200
    )
    r = client.patch(
        f"/api/v1/assessments/{aid}/audit-plan",
        json={"objective": "x", "expected_updated_at": plan.json()["updated_at"]},
        headers=h_reader,
    )
    assert r.status_code == 403, r.text


def test_cross_org_blocked(client: TestClient):
    _h0, _org, h_a, model_id, sv_id, req_id = _org_ctx(client)
    aid = _create_draft_with_scope(client, h_a, model_id, sv_id, req_id)
    assert client.get(f"/api/v1/assessments/{aid}/audit-plan", headers=h_a).status_code == 200
    hb0 = _dev_headers()
    org_b = _bootstrap_org(client, hb0)
    h_b = {**hb0, "X-Organization-Id": org_b}
    cross = client.get(f"/api/v1/assessments/{aid}/audit-plan", headers=h_b)
    assert cross.status_code == 404, cross.text


def test_planned_ready_requires_amendment_reason(client: TestClient):
    _h0, _org, h, model_id, sv_id, req_id = _org_ctx(client)
    aid = _create_draft_with_scope(client, h, model_id, sv_id, req_id)
    _seed_guided(client, h, aid)
    plan = client.get(f"/api/v1/assessments/{aid}/audit-plan", headers=h).json()
    assess = client.get(f"/api/v1/assessments/{aid}", headers=h).json()
    patched = client.patch(
        f"/api/v1/assessments/{aid}/audit-plan",
        json={
            "objective": "Obj",
            "scope_text": "Escopo",
            "processes": [{"name": "P1", "owner": "", "notes": "", "from_preparation": False}],
            "lead_membership_id": assess["lead_membership_id"],
            "planned_start": "2026-10-01",
            "planned_end": "2026-10-03",
            "expected_updated_at": plan["updated_at"],
        },
        headers=h,
    )
    assert patched.status_code == 200
    assert (
        client.post(
            f"/api/v1/assessments/{aid}/audit-plan/ready",
            json={"expected_updated_at": patched.json()["updated_at"]},
            headers=h,
        ).status_code
        == 200
    )
    _force_status(aid, "planned")
    cur = client.get(f"/api/v1/assessments/{aid}/audit-plan", headers=h).json()
    assert cur["requires_amendment_reason"] is True

    no_reason = client.patch(
        f"/api/v1/assessments/{aid}/audit-plan",
        json={"objective": "Ajuste", "expected_updated_at": cur["updated_at"]},
        headers=h,
    )
    assert no_reason.status_code == 422, no_reason.text

    with_reason = client.patch(
        f"/api/v1/assessments/{aid}/audit-plan",
        json={
            "objective": "Ajuste operacional",
            "amendment_reason": "Mudança de turno da planta",
            "expected_updated_at": cur["updated_at"],
        },
        headers=h,
    )
    assert with_reason.status_code == 200, with_reason.text
    assert with_reason.json()["plan_status"] == "amended"


def test_in_progress_read_only_without_amendment(client: TestClient):
    _h0, _org, h, model_id, sv_id, req_id = _org_ctx(client)
    aid = _create_draft_with_scope(client, h, model_id, sv_id, req_id)
    assert client.get(f"/api/v1/assessments/{aid}/audit-plan", headers=h).status_code == 200
    _force_status(aid, "in_progress")
    cur = client.get(f"/api/v1/assessments/{aid}/audit-plan", headers=h).json()
    blocked = client.patch(
        f"/api/v1/assessments/{aid}/audit-plan",
        json={"objective": "x", "expected_updated_at": cur["updated_at"]},
        headers=h,
    )
    assert blocked.status_code == 422, blocked.text
    ok = client.patch(
        f"/api/v1/assessments/{aid}/audit-plan",
        json={
            "objective": "Emenda de campo",
            "amendment_reason": "Processo incluído na visita",
            "expected_updated_at": cur["updated_at"],
        },
        headers=h,
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["plan_status"] == "amended"

    _force_status(aid, "analysis")
    cur2 = client.get(f"/api/v1/assessments/{aid}/audit-plan", headers=h).json()
    assert cur2["editable"] is False
    ro = client.patch(
        f"/api/v1/assessments/{aid}/audit-plan",
        json={
            "objective": "não",
            "amendment_reason": "x",
            "expected_updated_at": cur2["updated_at"],
        },
        headers=h,
    )
    assert ro.status_code == 409, ro.text
