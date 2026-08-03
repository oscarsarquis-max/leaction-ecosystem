"""MVP E2E — S3 storage variant (integration only).

Default suite uses memory (`test_mvp_e2e_gate.py`). Enable with:

  $env:QMIND_S3_INTEGRATION = "1"
  $env:STORAGE_BACKEND = "s3"
  # + S3_BUCKET / credentials

Runs the evidence authorize → PUT → HEAD/receive → security_pass slice against real S3,
then asserts org isolation headers still apply for a second org.
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration


@pytest.mark.skipif(
    os.environ.get("QMIND_S3_INTEGRATION") != "1",
    reason="Set QMIND_S3_INTEGRATION=1 with S3_BUCKET credentials to run",
)
def test_mvp_e2e_evidence_slice_on_s3():
    # Force S3 for this process before app settings are cached for storage.
    os.environ["STORAGE_BACKEND"] = "s3"
    from app.config import get_settings
    from app.main import app
    from app.storage import get_storage
    from tests.test_assessment_ops import _create_draft_with_scope, _org_ctx
    from tests.test_assessments import _bootstrap_org, _dev_headers

    get_settings.cache_clear()
    settings = get_settings()
    assert settings.storage_backend == "s3"
    assert settings.s3_bucket

    client = TestClient(app)
    _headers, org_a, h_a, model_id, sv_id, req_id = _org_ctx(client)
    aid = _create_draft_with_scope(client, h_a, model_id, sv_id, req_id)
    assert client.post(f"/api/v1/assessments/{aid}/transitions/plan", headers=h_a).status_code == 200
    assert client.post(f"/api/v1/assessments/{aid}/transitions/start", headers=h_a).status_code == 200

    data = b"%PDF-1.4 mvp-e2e-s3"
    auth = client.post(
        "/api/v1/evidences/authorize",
        json={
            "assessment_id": aid,
            "content_type": "application/pdf",
            "declared_byte_size": len(data),
        },
        headers=h_a,
    )
    assert auth.status_code == 201, auth.text
    body = auth.json()
    upload = body["upload"]
    assert upload["url"].startswith("http")
    eid = body["evidence"]["id"]
    key = body["evidence"]["storage_key"]

    import urllib.request

    req = urllib.request.Request(
        upload["url"],
        data=data,
        method=upload.get("method", "PUT"),
        headers=dict(upload.get("headers") or {}),
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status in (200, 204)

    # Retry PUT (idempotent overwrite)
    with urllib.request.urlopen(req) as resp2:
        assert resp2.status in (200, 204)

    recv = client.post(f"/api/v1/evidences/{eid}/transitions/receive", headers=h_a)
    assert recv.status_code == 200, recv.text
    assert recv.json()["evidence"]["content_hash"].startswith("sha256:")
    ok = client.post(f"/api/v1/evidences/{eid}/transitions/security_pass", headers=h_a)
    assert ok.status_code == 200
    assert ok.json()["to_status"] == "approved"

    # Cross-org denial
    hb = _dev_headers()
    org_b = _bootstrap_org(client, hb)
    h_b = {**hb, "X-Organization-Id": org_b}
    assert client.get(f"/api/v1/evidences/{eid}", headers=h_b).status_code == 404

    # Cleanup object (best effort)
    try:
        get_storage(settings).delete(key)
    except Exception:
        pass
    finally:
        get_settings.cache_clear()
        os.environ["STORAGE_BACKEND"] = "memory"
