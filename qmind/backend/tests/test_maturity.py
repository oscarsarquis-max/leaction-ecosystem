"""MaturityAssessment package — freeze, scores, SoD, supersede, recalc."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.main import app
from app.storage.memory import InMemoryObjectStorage
from tests.conftest import ADMIN_URL
from tests.test_assessment_ops import _create_draft_with_scope, _org_ctx
from tests.test_assessments import _bootstrap_org, _dev_headers
from tests.test_findings import _member_headers


@pytest.fixture()
def client():
    return TestClient(app)


def _analysis_ready(client: TestClient):
    _headers, org_id, h, model_id, sv_id, req_id = _org_ctx(client)
    aid = _create_draft_with_scope(client, h, model_id, sv_id, req_id)
    assert client.post(f"/api/v1/assessments/{aid}/transitions/plan", headers=h).status_code == 200
    assess = client.get(f"/api/v1/assessments/{aid}", headers=h).json()
    assert assess["maturity_model_id"]  # frozen at plan
    assert client.post(f"/api/v1/assessments/{aid}/transitions/start", headers=h).status_code == 200
    assert client.post(f"/api/v1/assessments/{aid}/transitions/begin_analysis", headers=h).status_code == 200
    return h, org_id, aid


def _approved_evidence(client, h, aid) -> str:
    data = b"%PDF-1.4 maturity"
    auth = client.post(
        "/api/v1/evidences/authorize",
        json={
            "assessment_id": aid,
            "content_type": "application/pdf",
            "declared_byte_size": len(data),
        },
        headers=h,
    )
    ev = auth.json()["evidence"]
    InMemoryObjectStorage.instance().put_test_object(ev["storage_key"], data, "application/pdf")
    eid = ev["id"]
    client.post(f"/api/v1/evidences/{eid}/transitions/receive", headers=h)
    client.post(f"/api/v1/evidences/{eid}/transitions/security_pass", headers=h)
    return eid


def _catalog_criteria():
    eng = create_engine(ADMIN_URL)
    with eng.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT c.id, c.code, d.code AS dim_code
                FROM maturity_criteria c
                JOIN maturity_dimensions d ON d.id = c.maturity_dimension_id
                JOIN maturity_models m ON m.id = d.maturity_model_id
                WHERE m.model_code = 'qmind_maturity_iso9001' AND m.model_version = '0.1.0'
                ORDER BY d.sort_order, c.sort_order
                """
            )
        ).all()
    eng.dispose()
    return rows


def _fill_all_level3(client, h, pid, eid, *, na_dim: str | None = None):
    criteria = _catalog_criteria()
    scores = []
    for c in criteria:
        if na_dim and c.dim_code == na_dim:
            scores.append(
                {
                    "criterion_id": str(c.id),
                    "applicability": "not_applicable",
                    "na_rationale": f"{c.code} out of scope",
                }
            )
        else:
            scores.append(
                {
                    "criterion_id": str(c.id),
                    "applicability": "applicable",
                    "level": 3,
                    "rationale": "managed practice",
                    "evidence_ids": [eid],
                }
            )
    r = client.put(f"/api/v1/maturity-assessments/{pid}/scores", json={"scores": scores}, headers=h)
    assert r.status_code == 200, r.text
    return r.json()


def test_plan_freezes_maturity_model(client: TestClient):
    h, _org, aid = _analysis_ready(client)
    assert client.get(f"/api/v1/assessments/{aid}", headers=h).json()["maturity_model_id"]


def test_server_recalc_rejects_client_aggregates_and_na_dimension(client: TestClient):
    h, org_id, aid = _analysis_ready(client)
    eid = _approved_evidence(client, h, aid)
    created = client.post(
        "/api/v1/maturity-assessments", json={"assessment_id": aid}, headers=h
    )
    assert created.status_code == 201, created.text
    pid = created.json()["id"]
    assert created.json()["version_no"] == 1
    assert len(created.json()["scores"]) == 18

    bad = client.put(
        f"/api/v1/maturity-assessments/{pid}/scores",
        json={
            "scores": [
                {
                    "criterion_id": str(_catalog_criteria()[0].id),
                    "applicability": "applicable",
                    "level": 3,
                    "evidence_ids": [eid],
                }
            ],
            "global_score": "9.99",
        },
        headers=h,
    )
    assert bad.status_code == 422
    assert bad.json()["code"] == "client_aggregates_forbidden"

    body = _fill_all_level3(client, h, pid, eid, na_dim="D4_operation")
    # 5 dimensions × 3.00 → global 3.00 (D4 excluded)
    assert Decimal(str(body["global_score"])) == Decimal("3.00")
    dim_codes = {d["dimension_code"] for d in body["dimension_scores"]}
    assert "D4_operation" not in dim_codes
    assert len(body["dimension_scores"]) == 5


def test_submit_blocks_insufficient_info_and_approve_sod(client: TestClient):
    h, org_id, aid = _analysis_ready(client)
    eid = _approved_evidence(client, h, aid)
    pid = client.post(
        "/api/v1/maturity-assessments", json={"assessment_id": aid}, headers=h
    ).json()["id"]

    # still all insufficient_info
    bad = client.post(f"/api/v1/maturity-assessments/{pid}/transitions/submit", headers=h)
    assert bad.status_code == 422
    assert bad.json()["code"] == "insufficient_info_forbidden"

    _fill_all_level3(client, h, pid, eid)
    assert client.post(f"/api/v1/maturity-assessments/{pid}/transitions/submit", headers=h).status_code == 200

    sod = client.post(f"/api/v1/maturity-assessments/{pid}/transitions/approve", headers=h)
    assert sod.status_code == 403
    assert sod.json()["code"] == "sod_violation"

    approver = _member_headers(org_id, ["quality_manager"])
    ok = client.post(f"/api/v1/maturity-assessments/{pid}/transitions/approve", headers=approver)
    assert ok.status_code == 200
    assert ok.json()["to_status"] == "approved"

    # immutable scores after approve
    blocked = client.put(
        f"/api/v1/maturity-assessments/{pid}/scores",
        json={
            "scores": [
                {
                    "criterion_id": str(_catalog_criteria()[0].id),
                    "applicability": "applicable",
                    "level": 5,
                    "rationale": "nope",
                    "evidence_ids": [eid],
                }
            ]
        },
        headers=h,
    )
    assert blocked.status_code == 409


def test_supersede_creates_version_plus_one(client: TestClient):
    h, org_id, aid = _analysis_ready(client)
    eid = _approved_evidence(client, h, aid)
    pid = client.post(
        "/api/v1/maturity-assessments", json={"assessment_id": aid}, headers=h
    ).json()["id"]
    _fill_all_level3(client, h, pid, eid)
    client.post(f"/api/v1/maturity-assessments/{pid}/transitions/submit", headers=h)
    approver = _member_headers(org_id, ["quality_manager"])
    client.post(f"/api/v1/maturity-assessments/{pid}/transitions/approve", headers=approver)
    frozen = client.get(f"/api/v1/maturity-assessments/{pid}", headers=h).json()
    frozen_global = frozen["global_score"]
    frozen_dims = frozen["dimension_scores"]

    supersede = client.post(
        f"/api/v1/maturity-assessments/{pid}/transitions/supersede",
        json={"reason": "Recalibrate scores"},
        headers=approver,
    )
    assert supersede.status_code == 200, supersede.text
    assert supersede.json()["event"] == "supersede"
    new_id = supersede.json()["package"]["id"]
    assert new_id != pid
    assert supersede.json()["package"]["version_no"] == 2
    assert supersede.json()["package"]["status"] == "draft"
    assert supersede.json()["package"]["supersedes_id"] == pid
    old = client.get(f"/api/v1/maturity-assessments/{pid}", headers=h).json()
    assert old["status"] == "superseded"
    # Approved version aggregates preserved (immutable content)
    assert old["global_score"] == frozen_global
    assert old["dimension_scores"] == frozen_dims


def test_level3_requires_approved_evidence(client: TestClient):
    h, _org, aid = _analysis_ready(client)
    pid = client.post(
        "/api/v1/maturity-assessments", json={"assessment_id": aid}, headers=h
    ).json()["id"]
    criteria = _catalog_criteria()
    scores = [
        {
            "criterion_id": str(c.id),
            "applicability": "applicable",
            "level": 3,
            "rationale": "managed",
            "evidence_ids": [],
        }
        for c in criteria
    ]
    client.put(f"/api/v1/maturity-assessments/{pid}/scores", json={"scores": scores}, headers=h)
    bad = client.post(f"/api/v1/maturity-assessments/{pid}/transitions/submit", headers=h)
    assert bad.status_code == 422
    assert bad.json()["code"] == "min_evidence_required"


def test_isolation_and_concurrent_submit(client: TestClient):
    h1, _org1, aid1 = _analysis_ready(client)
    eid = _approved_evidence(client, h1, aid1)
    pid = client.post(
        "/api/v1/maturity-assessments", json={"assessment_id": aid1}, headers=h1
    ).json()["id"]
    _fill_all_level3(client, h1, pid, eid)

    h2 = _dev_headers()
    org2 = _bootstrap_org(client, h2)
    ctx2 = {**h2, "X-Organization-Id": org2}
    assert client.get(f"/api/v1/maturity-assessments/{pid}", headers=ctx2).status_code == 404

    def _submit():
        c = TestClient(app)
        return c.post(
            f"/api/v1/maturity-assessments/{pid}/transitions/submit", headers=h1
        ).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        codes = list(pool.map(lambda _: _submit(), range(2)))
    assert 200 in codes
    assert codes.count(200) == 1
    assert client.get(f"/api/v1/maturity-assessments/{pid}", headers=h1).json()["status"] == "in_review"


def test_reject_rework(client: TestClient):
    h, org_id, aid = _analysis_ready(client)
    eid = _approved_evidence(client, h, aid)
    pid = client.post(
        "/api/v1/maturity-assessments", json={"assessment_id": aid}, headers=h
    ).json()["id"]
    _fill_all_level3(client, h, pid, eid)
    client.post(f"/api/v1/maturity-assessments/{pid}/transitions/submit", headers=h)
    qm = _member_headers(org_id, ["quality_manager"])
    assert (
        client.post(
            f"/api/v1/maturity-assessments/{pid}/transitions/reject",
            json={"reason": "Need better N/A rationale"},
            headers=qm,
        ).status_code
        == 200
    )
    assert client.post(f"/api/v1/maturity-assessments/{pid}/transitions/rework", headers=h).json()[
        "to_status"
    ] == "draft"
