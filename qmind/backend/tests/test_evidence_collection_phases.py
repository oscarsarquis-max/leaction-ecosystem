"""Evidence collection allowed across draft→analysis; blocked after."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.main import app
from app.storage.memory import InMemoryObjectStorage
from tests.conftest import ADMIN_URL
from tests.test_assessment_ops import _create_draft_with_scope, _org_ctx
from tests.test_assessments import _bootstrap_org, _dev_headers
from tests.test_guided_evidence_links import _answer, _first_question


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


def _authorize(client: TestClient, h: dict, aid: str, size: int = 24):
    return client.post(
        "/api/v1/evidences/authorize",
        json={
            "assessment_id": aid,
            "content_type": "application/pdf",
            "declared_byte_size": size,
        },
        headers=h,
    )


@pytest.mark.parametrize(
    "status,expected_phase",
    [
        ("draft", "preparation"),
        ("planned", "planning"),
        ("in_progress", "field"),
        ("analysis", "analysis"),
    ],
)
def test_authorize_allowed_phases(client: TestClient, status: str, expected_phase: str):
    _headers, _org, h, model_id, sv_id, req_id = _org_ctx(client)
    aid = _create_draft_with_scope(client, h, model_id, sv_id, req_id)
    _force_status(aid, status)

    r = _authorize(client, h, aid)
    assert r.status_code == 201, r.text
    ev = r.json()["evidence"]
    assert ev["collected_phase"] == expected_phase
    assert ev["collected_at"]
    assert ev["collected_by"]
    if expected_phase == "field":
        assert ev["collection_origin"] == "Coletada em campo"
    elif expected_phase == "analysis":
        assert ev["collection_origin"] == "Complementação da análise"
    else:
        assert ev["collection_origin"] == "Disponível antecipadamente"


@pytest.mark.parametrize("status", ["actions", "report", "closed", "cancelled"])
def test_authorize_blocked_phases(client: TestClient, status: str):
    _headers, _org, h, model_id, sv_id, req_id = _org_ctx(client)
    aid = _create_draft_with_scope(client, h, model_id, sv_id, req_id)
    _force_status(aid, status)

    r = _authorize(client, h, aid)
    assert r.status_code == 409, r.text
    code = r.json()["code"]
    if status in ("closed", "cancelled"):
        assert code == "assessment_closed"
    else:
        assert code == "assessment_not_collecting"


def test_reuse_same_evidence_two_questions(client: TestClient):
    _headers, _org, h, model_id, sv_id, req_id = _org_ctx(client)
    aid = _create_draft_with_scope(client, h, model_id, sv_id, req_id)
    assert client.post(f"/api/v1/assessments/{aid}/transitions/plan", headers=h).status_code == 200
    assert client.post(f"/api/v1/assessments/{aid}/transitions/start", headers=h).status_code == 200

    cat = client.get("/api/v1/guided/catalog", headers=h).json()
    q1, q2 = cat["questions"][0], cat["questions"][1]
    _answer(client, h, aid, q1["id"], q1["version"])
    _answer(client, h, aid, q2["id"], q2["version"])

    data = b"%PDF-1.4 shared-ev"
    auth = _authorize(client, h, aid, size=len(data))
    assert auth.status_code == 201, auth.text
    eid = auth.json()["evidence"]["id"]
    InMemoryObjectStorage.instance().put_test_object(
        auth.json()["evidence"]["storage_key"], data, "application/pdf"
    )
    assert (
        client.post(f"/api/v1/evidences/{eid}/transitions/receive", headers=h).status_code
        == 200
    )

    for qid in (q1["id"], q2["id"]):
        linked = client.post(
            f"/api/v1/assessments/{aid}/guided/answers/{qid}/evidences/link",
            json={"evidence_id": eid},
            headers=h,
        )
        assert linked.status_code == 200, linked.text

    s = client.get(f"/api/v1/assessments/{aid}/guided", headers=h).json()
    linked_qs = [
        a["question_id"]
        for a in s["answers"]
        if any(l["evidence_id"] == eid for l in a.get("evidence_links", []))
    ]
    assert q1["id"] in linked_qs and q2["id"] in linked_qs


def test_provide_later_converted_to_link(client: TestClient):
    _headers, _org, h, model_id, sv_id, req_id = _org_ctx(client)
    aid = _create_draft_with_scope(client, h, model_id, sv_id, req_id)
    assert client.post(f"/api/v1/assessments/{aid}/transitions/plan", headers=h).status_code == 200
    assert client.post(f"/api/v1/assessments/{aid}/transitions/start", headers=h).status_code == 200
    qid, qver = _first_question(client, h)
    assert client.get(f"/api/v1/assessments/{aid}/guided", headers=h).status_code == 200

    put = client.put(
        f"/api/v1/assessments/{aid}/guided/answers/{qid}",
        json={
            "question_version": qver,
            "answer_value": "yes",
            "evidence_mode": "provide_later",
            "provide_later": True,
        },
        headers=h,
    )
    assert put.status_code == 200, put.text
    ans = next(a for a in put.json()["answers"] if a["question_id"] == qid)
    assert ans["provide_later"] is True

    data = b"%PDF-1.4 later"
    auth = client.post(
        f"/api/v1/assessments/{aid}/guided/answers/{qid}/evidences/authorize",
        json={
            "assessment_id": aid,
            "content_type": "application/pdf",
            "declared_byte_size": len(data),
        },
        headers=h,
    )
    assert auth.status_code == 201, auth.text
    eid = auth.json()["evidence"]["id"]
    InMemoryObjectStorage.instance().put_test_object(
        auth.json()["evidence"]["storage_key"], data, "application/pdf"
    )
    assert (
        client.post(f"/api/v1/evidences/{eid}/transitions/receive", headers=h).status_code
        == 200
    )
    done = client.post(
        f"/api/v1/assessments/{aid}/guided/answers/{qid}/evidences/{eid}/complete",
        headers=h,
    )
    assert done.status_code == 200, done.text
    ans2 = next(a for a in done.json()["answers"] if a["question_id"] == qid)
    assert ans2["provide_later"] is False
    assert len(ans2["evidence_links"]) == 1
    assert ans2["evidence_links"][0]["collected_phase"] == "field"


def test_collection_phase_cross_org(client: TestClient):
    _headers, _org, h_a, model_id, sv_id, req_id = _org_ctx(client)
    aid = _create_draft_with_scope(client, h_a, model_id, sv_id, req_id)
    hb0 = _dev_headers()
    org_b = _bootstrap_org(client, hb0)
    h_b = {**hb0, "X-Organization-Id": org_b}
    r = _authorize(client, h_b, aid)
    assert r.status_code == 404, r.text
