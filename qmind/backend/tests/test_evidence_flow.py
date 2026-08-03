"""Evidence authorize → object in storage → HEAD receive → approve|reject."""

from __future__ import annotations

import hashlib

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.main import app
from app.storage.memory import InMemoryObjectStorage
from tests.conftest import ADMIN_URL
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


def _authorize_and_put(client: TestClient, h: dict, aid: str, data: bytes | None = None):
    data = data if data is not None else b"%PDF-1.4 evidence-bytes"
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
    assert "upload" in body and "evidence" in body
    assert body["upload"]["url"]
    assert "memory://" in body["upload"]["url"] or body["upload"]["url"].startswith("http")
    ev = body["evidence"]
    assert ev["status"] == "upload_pending"
    assert ev["storage_key"].startswith("org/")
    assert str(aid) in (ev["assessment_id"] if isinstance(ev["assessment_id"], str) else "")
    InMemoryObjectStorage.instance().put_test_object(
        ev["storage_key"], data, "application/pdf"
    )
    return body, data


def test_evidence_approve_path_with_storage(client: TestClient):
    h, aid = _assessment_in_progress(client)
    body, data = _authorize_and_put(client, h, aid)
    eid = body["evidence"]["id"]

    recv = client.post(f"/api/v1/evidences/{eid}/transitions/receive", headers=h)
    assert recv.status_code == 200, recv.text
    assert recv.json()["to_status"] == "quarantined"
    expected_hash = "sha256:" + hashlib.sha256(data).hexdigest()
    assert recv.json()["evidence"]["content_hash"] == expected_hash
    assert recv.json()["evidence"]["byte_size"] == len(data)

    ok = client.post(f"/api/v1/evidences/{eid}/transitions/security_pass", headers=h)
    assert ok.status_code == 200
    assert ok.json()["to_status"] == "approved"
    assert client.get(f"/api/v1/evidences/{eid}", headers=h).json()["status"] == "approved"

    dl = client.get(f"/api/v1/evidences/{eid}/download-url", headers=h)
    assert dl.status_code == 200, dl.text
    assert dl.json()["url"].startswith("memory://download/")

    # Audit must not store signed URL
    eng = create_engine(ADMIN_URL)
    with eng.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT action, metadata::text AS meta
                FROM platform_audit_events
                WHERE resource_id = :id
                  AND action IN ('evidence.authorize_upload', 'evidence.download_url')
                """
            ),
            {"id": eid},
        ).all()
    eng.dispose()
    assert rows
    for r in rows:
        assert "memory://upload" not in (r.meta or "")
        assert "memory://download" not in (r.meta or "")
        assert "X-Amz-Signature" not in (r.meta or "")


def test_receive_without_object_fails(client: TestClient):
    h, aid = _assessment_in_progress(client)
    auth = client.post(
        "/api/v1/evidences/authorize",
        json={
            "assessment_id": aid,
            "content_type": "application/pdf",
            "declared_byte_size": 100,
        },
        headers=h,
    )
    eid = auth.json()["evidence"]["id"]
    recv = client.post(f"/api/v1/evidences/{eid}/transitions/receive", headers=h)
    assert recv.status_code == 422
    assert recv.json()["code"] == "object_missing"


def test_receive_rejects_expired_size_and_type_mismatch(client: TestClient):
    h, aid = _assessment_in_progress(client)

    # expired
    body, data = _authorize_and_put(client, h, aid, data=b"expire-recv")
    eid = body["evidence"]["id"]
    eng = create_engine(ADMIN_URL)
    with eng.begin() as conn:
        conn.execute(
            text("UPDATE evidences SET upload_expires_at = now() - interval '1 minute' WHERE id = :id"),
            {"id": eid},
        )
    eng.dispose()
    expired = client.post(f"/api/v1/evidences/{eid}/transitions/receive", headers=h)
    assert expired.status_code == 410
    assert expired.json()["code"] == "upload_expired"

    # size mismatch
    body2, _ = _authorize_and_put(client, h, aid, data=b"twelve-bytes!")  # 13
    eid2 = body2["evidence"]["id"]
    InMemoryObjectStorage.instance().put_test_object(
        body2["evidence"]["storage_key"], b"xx", "application/pdf"
    )
    size_bad = client.post(f"/api/v1/evidences/{eid2}/transitions/receive", headers=h)
    assert size_bad.status_code == 422
    assert size_bad.json()["code"] == "size_mismatch"

    # type mismatch
    body3, data3 = _authorize_and_put(client, h, aid, data=b"typed")
    eid3 = body3["evidence"]["id"]
    InMemoryObjectStorage.instance().put_test_object(
        body3["evidence"]["storage_key"], data3, "image/png"
    )
    type_bad = client.post(f"/api/v1/evidences/{eid3}/transitions/receive", headers=h)
    assert type_bad.status_code == 422
    assert type_bad.json()["code"] == "content_type_mismatch"


def test_cleanup_does_not_touch_approved_or_fresh_pending(client: TestClient):
    h, aid = _assessment_in_progress(client)
    body, data = _authorize_and_put(client, h, aid)
    eid = body["evidence"]["id"]
    assert client.post(f"/api/v1/evidences/{eid}/transitions/receive", headers=h).status_code == 200
    assert client.post(f"/api/v1/evidences/{eid}/transitions/security_pass", headers=h).status_code == 200

    fresh = client.post(
        "/api/v1/evidences/authorize",
        json={
            "assessment_id": aid,
            "content_type": "application/pdf",
            "declared_byte_size": 5,
        },
        headers=h,
    )
    fresh_id = fresh.json()["evidence"]["id"]

    cleaned = client.post("/api/v1/evidences/cleanup-expired", headers=h)
    assert cleaned.status_code == 200
    assert client.get(f"/api/v1/evidences/{eid}", headers=h).json()["status"] == "approved"
    assert client.get(f"/api/v1/evidences/{fresh_id}", headers=h).json()["status"] == "upload_pending"


def test_content_hash_is_sha256_not_etag(client: TestClient):
    h, aid = _assessment_in_progress(client)
    data = b"not-an-etag-source"
    body, _ = _authorize_and_put(client, h, aid, data=data)
    eid = body["evidence"]["id"]
    # Poison memory etag-like value by ensuring head.etag != sha256
    key = body["evidence"]["storage_key"]
    head = InMemoryObjectStorage.instance().head(key)
    recv = client.post(f"/api/v1/evidences/{eid}/transitions/receive", headers=h)
    digest = recv.json()["evidence"]["content_hash"]
    assert digest == "sha256:" + hashlib.sha256(data).hexdigest()
    assert head.etag is not None
    assert digest.replace("sha256:", "") not in (head.etag or "")


def test_evidence_reject_path(client: TestClient):
    h, aid = _assessment_in_progress(client)
    body, _data = _authorize_and_put(client, h, aid, data=b"bad-file")
    eid = body["evidence"]["id"]
    assert client.post(f"/api/v1/evidences/{eid}/transitions/receive", headers=h).status_code == 200
    fail = client.post(f"/api/v1/evidences/{eid}/transitions/security_fail", headers=h)
    assert fail.status_code == 200
    assert fail.json()["to_status"] == "rejected"


def test_authorize_blocked_before_start(client: TestClient):
    _headers, _org, h, model_id, sv_id, req_id = _org_ctx(client)
    aid = _create_draft_with_scope(client, h, model_id, sv_id, req_id)
    client.post(f"/api/v1/assessments/{aid}/transitions/plan", headers=h)
    r = client.post(
        "/api/v1/evidences/authorize",
        json={
            "assessment_id": aid,
            "content_type": "application/pdf",
            "declared_byte_size": 10,
        },
        headers=h,
    )
    assert r.status_code == 409
    assert r.json()["code"] == "assessment_not_collecting"


def test_content_type_not_allowed(client: TestClient):
    h, aid = _assessment_in_progress(client)
    r = client.post(
        "/api/v1/evidences/authorize",
        json={
            "assessment_id": aid,
            "content_type": "application/x-msdownload",
            "declared_byte_size": 10,
        },
        headers=h,
    )
    assert r.status_code == 422
    assert r.json()["code"] == "content_type_not_allowed"


def test_abandon_and_cleanup_expired(client: TestClient):
    h, aid = _assessment_in_progress(client)
    body, _ = _authorize_and_put(client, h, aid, data=b"pending")
    eid = body["evidence"]["id"]
    key = body["evidence"]["storage_key"]
    abandoned = client.post(f"/api/v1/evidences/{eid}/transitions/abandon", headers=h)
    assert abandoned.status_code == 200
    assert abandoned.json()["to_status"] == "disposed"
    assert not InMemoryObjectStorage.instance().head(key).exists

    body2, _ = _authorize_and_put(client, h, aid, data=b"expire-me")
    eid2 = body2["evidence"]["id"]
    eng = create_engine(ADMIN_URL)
    with eng.begin() as conn:
        conn.execute(
            text(
                """
                UPDATE evidences
                SET upload_expires_at = now() - interval '1 minute'
                WHERE id = :id
                """
            ),
            {"id": eid2},
        )
    eng.dispose()
    cleaned = client.post("/api/v1/evidences/cleanup-expired", headers=h)
    assert cleaned.status_code == 200, cleaned.text
    assert cleaned.json()["disposed_count"] >= 1
    assert client.get(f"/api/v1/evidences/{eid2}", headers=h).json()["status"] == "disposed"


def test_evidence_isolation(client: TestClient):
    h1, aid1 = _assessment_in_progress(client)
    body, _ = _authorize_and_put(client, h1, aid1)
    eid = body["evidence"]["id"]

    h2 = _dev_headers()
    org2 = _bootstrap_org(client, h2)
    ctx2 = {**h2, "X-Organization-Id": org2}
    assert client.get(f"/api/v1/evidences/{eid}", headers=ctx2).status_code == 404
