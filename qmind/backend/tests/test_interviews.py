"""Interview + Answer field collection — org isolation and phase locks."""

from __future__ import annotations

import uuid

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


def _ensure_questions(model_id) -> str:
    eng = create_engine(ADMIN_URL)
    with eng.begin() as conn:
        qid = conn.execute(
            text(
                """
                INSERT INTO questions (assessment_model_id, code, prompt_text, sort_order)
                VALUES (:mid, :code, :prompt, 1)
                ON CONFLICT (assessment_model_id, code) DO UPDATE
                  SET prompt_text = EXCLUDED.prompt_text
                RETURNING id
                """
            ),
            {
                "mid": model_id,
                "code": "Q-TEST-01",
                "prompt": "Test interview prompt",
            },
        ).scalar_one()
    eng.dispose()
    return str(qid)


def _assessment_in_progress(client: TestClient):
    _headers, org_id, h, model_id, sv_id, req_id = _org_ctx(client)
    aid = _create_draft_with_scope(client, h, model_id, sv_id, req_id)
    assert client.post(f"/api/v1/assessments/{aid}/transitions/plan", headers=h).status_code == 200
    assert client.post(f"/api/v1/assessments/{aid}/transitions/start", headers=h).status_code == 200
    qid = _ensure_questions(model_id)
    return h, org_id, aid, req_id, qid


def test_start_blocked_for_reader(client: TestClient):
    _headers, org_id, h, model_id, sv_id, req_id = _org_ctx(client)
    aid = _create_draft_with_scope(client, h, model_id, sv_id, req_id)
    assert client.post(f"/api/v1/assessments/{aid}/transitions/plan", headers=h).status_code == 200

    sub = f"reader-{uuid.uuid4()}"
    email = f"{sub}@ex.com"
    eng = create_engine(ADMIN_URL)
    with eng.begin() as conn:
        user_id = conn.execute(
            text(
                """
                INSERT INTO users (idp_sub, email, status)
                VALUES (:sub, :email, 'active') RETURNING id
                """
            ),
            {"sub": sub, "email": email},
        ).scalar_one()
        conn.execute(
            text(
                """
                INSERT INTO memberships (organization_id, user_id, roles, status)
                VALUES (:org, :u, ARRAY['reader'], 'active')
                """
            ),
            {"org": org_id, "u": user_id},
        )
    eng.dispose()

    reader_h = {
        "X-Dev-User-Sub": sub,
        "X-Dev-User-Email": email,
        "X-Organization-Id": org_id,
    }
    r = client.post(f"/api/v1/assessments/{aid}/transitions/start", headers=reader_h)
    assert r.status_code == 403
    assert r.json()["code"] in ("forbidden", "role_forbidden", "insufficient_role")
    assert "correlation_id" in r.json()


def test_interview_answer_and_phase_lock(client: TestClient):
    h, _org, aid, _req, qid = _assessment_in_progress(client)

    qs = client.get(f"/api/v1/assessments/{aid}/questions", headers=h)
    assert qs.status_code == 200
    assert any(q["id"] == qid for q in qs.json())

    created = client.post(
        f"/api/v1/assessments/{aid}/interviews",
        json={"mode": "onsite"},
        headers=h,
    )
    assert created.status_code == 201, created.text
    iid = created.json()["id"]
    assert created.json()["status"] == "planned"

    ans = client.post(
        f"/api/v1/interviews/{iid}/answers",
        json={"body": "Observation from field", "question_id": qid},
        headers=h,
    )
    assert ans.status_code == 201, ans.text
    answer_id = ans.json()["id"]
    assert ans.json()["body"] == "Observation from field"

    listed = client.get(f"/api/v1/interviews/{iid}/answers", headers=h)
    assert listed.status_code == 200
    assert any(a["id"] == answer_id for a in listed.json())

    patched = client.patch(
        f"/api/v1/answers/{answer_id}",
        json={"body": "Updated observation"},
        headers=h,
    )
    assert patched.status_code == 200
    assert patched.json()["body"] == "Updated observation"

    done = client.post(f"/api/v1/interviews/{iid}/complete", headers=h)
    assert done.status_code == 200
    assert done.json()["to_status"] == "completed"

    late = client.post(
        f"/api/v1/interviews/{iid}/answers",
        json={"body": "too late"},
        headers=h,
    )
    assert late.status_code == 409
    assert late.json()["code"] == "interview_locked"
    assert "correlation_id" in late.json()

    late_patch = client.patch(
        f"/api/v1/answers/{answer_id}",
        json={"body": "still locked"},
        headers=h,
    )
    assert late_patch.status_code == 409


def test_interview_planning_allowed_before_start_answers_blocked(client: TestClient):
    _headers, _org, h, model_id, sv_id, req_id = _org_ctx(client)
    aid = _create_draft_with_scope(client, h, model_id, sv_id, req_id)
    assert client.post(f"/api/v1/assessments/{aid}/transitions/plan", headers=h).status_code == 200
    r = client.post(
        f"/api/v1/assessments/{aid}/interviews",
        json={
            "mode": "remote",
            "title": "Entrevista planejada",
            "scheduled_at": "2026-09-02T14:00:00Z",
            "duration_minutes": 45,
        },
        headers=h,
    )
    assert r.status_code == 201, r.text
    iid = r.json()["id"]
    assert r.json()["agenda_event_id"] is not None
    # Answers still require assessment in_progress
    ans = client.post(
        f"/api/v1/interviews/{iid}/answers",
        json={"body": "too early"},
        headers=h,
    )
    assert ans.status_code == 409
    assert ans.json()["code"] == "interview_phase_closed"


def test_interview_isolated_between_orgs(client: TestClient):
    h1, _org1, aid1, _req1, _qid1 = _assessment_in_progress(client)
    iid = client.post(
        f"/api/v1/assessments/{aid1}/interviews",
        json={"mode": "hybrid"},
        headers=h1,
    ).json()["id"]

    h2 = _dev_headers()
    org2 = _bootstrap_org(client, h2)
    ctx2 = {**h2, "X-Organization-Id": org2}
    cross = client.get(f"/api/v1/interviews/{iid}", headers=ctx2)
    assert cross.status_code == 404
    assert "correlation_id" in cross.json()

    answers = client.get(f"/api/v1/interviews/{iid}/answers", headers=ctx2)
    assert answers.status_code == 404


def test_evidence_link_to_interview_and_question(client: TestClient):
    from app.storage.memory import InMemoryObjectStorage

    h, _org, aid, req_id, qid = _assessment_in_progress(client)
    iid = client.post(
        f"/api/v1/assessments/{aid}/interviews",
        json={"mode": "onsite"},
        headers=h,
    ).json()["id"]

    data = b"%PDF-1.4 link-test"
    auth = client.post(
        "/api/v1/evidences/authorize",
        json={
            "assessment_id": aid,
            "content_type": "application/pdf",
            "declared_byte_size": len(data),
        },
        headers=h,
    )
    assert auth.status_code == 201
    eid = auth.json()["evidence"]["id"]
    InMemoryObjectStorage.instance().put_test_object(
        auth.json()["evidence"]["storage_key"], data, "application/pdf"
    )
    assert client.post(f"/api/v1/evidences/{eid}/transitions/receive", headers=h).status_code == 200

    link_i = client.post(
        f"/api/v1/evidences/{eid}/links",
        json={"target_type": "interview", "target_id": iid},
        headers=h,
    )
    assert link_i.status_code == 201, link_i.text
    link_q = client.post(
        f"/api/v1/evidences/{eid}/links",
        json={"target_type": "question", "target_id": qid},
        headers=h,
    )
    assert link_q.status_code == 201
    link_r = client.post(
        f"/api/v1/evidences/{eid}/links",
        json={"target_type": "requirement", "target_id": str(req_id)},
        headers=h,
    )
    assert link_r.status_code == 201

    links = client.get(f"/api/v1/evidences/{eid}/links", headers=h)
    assert links.status_code == 200
    assert len(links.json()) == 3

    listed = client.get(f"/api/v1/assessments/{aid}/evidences", headers=h)
    assert listed.status_code == 200
    assert any(e["id"] == eid for e in listed.json())
