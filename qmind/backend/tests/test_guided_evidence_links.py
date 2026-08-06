"""Guided answer ↔ evidence typed links — gates mínimos."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.storage.memory import InMemoryObjectStorage
from tests.test_assessment_ops import _create_draft_with_scope, _org_ctx
from tests.test_assessments import _bootstrap_org, _dev_headers


@pytest.fixture()
def client():
    return TestClient(app)


def _assessment_in_progress(client: TestClient):
    _headers, _org, h, model_id, sv_id, req_id = _org_ctx(client)
    aid = _create_draft_with_scope(client, h, model_id, sv_id, req_id)
    assert client.post(f"/api/v1/assessments/{aid}/transitions/plan", headers=h).status_code == 200
    assert client.post(f"/api/v1/assessments/{aid}/transitions/start", headers=h).status_code == 200
    return h, aid


def _first_question(client: TestClient, h: dict) -> tuple[str, str]:
    cat = client.get("/api/v1/guided/catalog", headers=h)
    assert cat.status_code == 200, cat.text
    q = cat.json()["questions"][0]
    return q["id"], q["version"]


def _answer(client: TestClient, h: dict, aid: str, qid: str, qver: str):
    sess = client.get(f"/api/v1/assessments/{aid}/guided", headers=h)
    assert sess.status_code == 200, sess.text
    put = client.put(
        f"/api/v1/assessments/{aid}/guided/answers/{qid}",
        json={
            "question_version": qver,
            "answer_value": "yes",
            "description": "prática informada",
            "evidence_mode": "none",
        },
        headers=h,
    )
    assert put.status_code == 200, put.text
    return put.json()


def _upload_evidence(client: TestClient, h: dict, aid: str) -> str:
    data = b"%PDF-1.4 guided-link"
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
    body = auth.json()
    eid = body["evidence"]["id"]
    InMemoryObjectStorage.instance().put_test_object(
        body["evidence"]["storage_key"], data, "application/pdf"
    )
    recv = client.post(f"/api/v1/evidences/{eid}/transitions/receive", headers=h)
    assert recv.status_code == 200, recv.text
    return eid


def test_link_duplicate_unlink_and_status(client: TestClient):
    h, aid = _assessment_in_progress(client)
    qid, qver = _first_question(client, h)
    _answer(client, h, aid, qid, qver)
    eid = _upload_evidence(client, h, aid)

    linked = client.post(
        f"/api/v1/assessments/{aid}/guided/answers/{qid}/evidences/link",
        json={"evidence_id": eid},
        headers=h,
    )
    assert linked.status_code == 200, linked.text
    ans = next(a for a in linked.json()["answers"] if a["question_id"] == qid)
    assert eid in [str(x) for x in ans["evidence_ids"]]
    assert len(ans["evidence_links"]) == 1
    assert ans["evidence_links"][0]["situation"] in (
        "Em verificação",
        "Aguardando envio",
        "Aprovada",
    )

    dup = client.post(
        f"/api/v1/assessments/{aid}/guided/answers/{qid}/evidences/link",
        json={"evidence_id": eid},
        headers=h,
    )
    assert dup.status_code == 409, dup.text

    status = client.get(
        f"/api/v1/assessments/{aid}/guided/answers/{qid}/evidences/status",
        headers=h,
    )
    assert status.status_code == 200
    body = status.json()
    assert body["related"] == 1
    assert body["links"][0]["evidence_id"] == eid

    unlinked = client.delete(
        f"/api/v1/assessments/{aid}/guided/answers/{qid}/evidences/{eid}",
        headers=h,
    )
    assert unlinked.status_code == 200, unlinked.text
    ans2 = next(a for a in unlinked.json()["answers"] if a["question_id"] == qid)
    assert ans2["evidence_links"] == []
    assert ans2["evidence_ids"] == []


def test_wizard_authorize_receive_complete(client: TestClient):
    h, aid = _assessment_in_progress(client)
    qid, qver = _first_question(client, h)
    _answer(client, h, aid, qid, qver)

    data = b"%PDF-1.4 wizard-attach"
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
    ans = next(a for a in done.json()["answers"] if a["question_id"] == qid)
    assert len(ans["evidence_links"]) == 1
    assert ans["evidence_links"][0]["link_type"] == "attach"
    assert ans["evidence_mode"] == "attach"


def test_upsert_evidence_ids_creates_typed_links(client: TestClient):
    """Compat: evidence_ids no upsert sincroniza vínculos tipados."""
    h, aid = _assessment_in_progress(client)
    qid, qver = _first_question(client, h)
    assert client.get(f"/api/v1/assessments/{aid}/guided", headers=h).status_code == 200
    eid = _upload_evidence(client, h, aid)

    put = client.put(
        f"/api/v1/assessments/{aid}/guided/answers/{qid}",
        json={
            "question_version": qver,
            "answer_value": "yes",
            "description": "com ids legados",
            "evidence_mode": "link_existing",
            "evidence_ids": [eid],
        },
        headers=h,
    )
    assert put.status_code == 200, put.text
    ans = next(a for a in put.json()["answers"] if a["question_id"] == qid)
    assert len(ans["evidence_links"]) == 1
    assert ans["evidence_links"][0]["evidence_id"] == eid


def test_guided_evidence_cross_org_404(client: TestClient):
    h_a, aid = _assessment_in_progress(client)
    qid, qver = _first_question(client, h_a)
    _answer(client, h_a, aid, qid, qver)
    eid = _upload_evidence(client, h_a, aid)
    assert (
        client.post(
            f"/api/v1/assessments/{aid}/guided/answers/{qid}/evidences/link",
            json={"evidence_id": eid},
            headers=h_a,
        ).status_code
        == 200
    )

    hb0 = _dev_headers()
    org_b = _bootstrap_org(client, hb0)
    h_b = {**hb0, "X-Organization-Id": org_b}

    cross = client.get(
        f"/api/v1/assessments/{aid}/guided/answers/{qid}/evidences",
        headers=h_b,
    )
    assert cross.status_code == 404, cross.text

    cross_link = client.post(
        f"/api/v1/assessments/{aid}/guided/answers/{qid}/evidences/link",
        json={"evidence_id": eid},
        headers=h_b,
    )
    assert cross_link.status_code == 404, cross_link.text
