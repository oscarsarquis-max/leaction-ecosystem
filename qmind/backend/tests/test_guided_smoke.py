"""Guided wizard smoke — resume position + cross-org isolation."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.test_assessments import _bootstrap_org, _catalog_ids, _dev_headers


@pytest.fixture()
def client():
    return TestClient(app)


def _create_assessment(client: TestClient, h: dict) -> str:
    model_id, sv_id, req_id = _catalog_ids()
    created = client.post(
        "/api/v1/assessments",
        json={
            "assessment_model_id": str(model_id),
            "standard_version_id": str(sv_id),
            "type": "diagnosis",
            "scope": [{"requirement_id": str(req_id)}],
        },
        headers=h,
    )
    assert created.status_code == 201, created.text
    return created.json()["id"]


def test_guided_resume_and_cross_org(client: TestClient):
    ha0 = _dev_headers()
    org_a = _bootstrap_org(client, ha0)
    h_a = {**ha0, "X-Organization-Id": org_a}
    aid = _create_assessment(client, h_a)

    cat = client.get("/api/v1/guided/catalog", headers=h_a)
    assert cat.status_code == 200, cat.text
    body = cat.json()
    assert body["catalog_version"] == "iso9001-2015-c4c10-v1"
    assert len(body["questions"]) >= 50
    qid = body["questions"][0]["id"]

    s1 = client.get(f"/api/v1/assessments/{aid}/guided", headers=h_a)
    assert s1.status_code == 200, s1.text
    session = s1.json()
    assert session["catalog_version"] == "iso9001-2015-c4c10-v1"
    assert session["question_count"] >= 1

    put = client.put(
        f"/api/v1/assessments/{aid}/guided/answers/{qid}",
        json={
            "question_version": "1",
            "answer_value": "yes",
            "description": "smoke resume",
            "evidence_mode": "none",
        },
        headers=h_a,
    )
    assert put.status_code == 200, put.text
    assert put.json()["current_question_id"] == qid
    assert put.json()["answered_count"] >= 1

    # Retomada: mesma sessão, posição e resposta preservadas
    s2 = client.get(f"/api/v1/assessments/{aid}/guided", headers=h_a)
    assert s2.status_code == 200
    again = s2.json()
    assert again["id"] == session["id"]
    assert again["current_question_id"] == qid
    assert any(
        a["question_id"] == qid and a["answer_value"] == "yes"
        for a in again["answers"]
    )

    # Cross-org: org B não lê sessão/roteiro da org A
    hb0 = _dev_headers()
    org_b = _bootstrap_org(client, hb0)
    h_b = {**hb0, "X-Organization-Id": org_b}
    cross = client.get(f"/api/v1/assessments/{aid}/guided", headers=h_b)
    assert cross.status_code == 404, cross.text
