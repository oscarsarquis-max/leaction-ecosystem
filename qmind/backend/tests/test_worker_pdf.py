"""PDF worker: claim, succeed, retry, abandon recovery, download, cross-org."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.config import get_settings
from app.main import app
from app.storage.memory import InMemoryObjectStorage
from app.worker.jobs import claim_job, claim_next, recover_abandoned
from app.worker.process_pdf import process_report_pdf_export
from tests.conftest import ADMIN_URL
from tests.test_assessments import _bootstrap_org, _dev_headers
from tests.test_reports import _report_ready


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture()
def disable_inline_pdf():
    """Worker tests exercise the out-of-band claim path; disable memory inline."""
    with patch(
        "app.modules.reports.service._process_pdf_inline_local_memory",
        return_value=None,
    ):
        yield


def _drain_queued_jobs() -> None:
    """Isolate worker tests from leftover queued jobs in shared local DB."""
    with create_engine(ADMIN_URL).begin() as conn:
        conn.execute(
            text(
                """
                UPDATE jobs
                SET status = 'cancelled',
                    finished_at = COALESCE(finished_at, now()),
                    locked_at = NULL,
                    locked_by = NULL,
                    updated_at = now()
                WHERE job_type = 'report_pdf_export'
                  AND status IN ('queued', 'running')
                """
            )
        )


def _publish_report(client: TestClient):
    _drain_queued_jobs()
    h, org_id, aid, _fid, _pid, qm = _report_ready(client)
    r = client.post(
        "/api/v1/reports",
        json={"assessment_id": aid, "include_maturity": True, "include_action_plan": True},
        headers=h,
    )
    assert r.status_code == 201, r.text
    rid = r.json()["id"]
    assert client.post(f"/api/v1/reports/{rid}/transitions/submit", headers=h).status_code == 200
    assert client.post(f"/api/v1/reports/{rid}/transitions/publish", headers=qm).status_code == 200
    return h, org_id, aid, qm, rid


def test_worker_pdf_success_idempotent_download_and_cross_org(
    client: TestClient, disable_inline_pdf
):
    h, org_id, _aid, _qm, rid = _publish_report(client)
    job1 = client.post(f"/api/v1/reports/{rid}/export-pdf", headers=h)
    assert job1.status_code == 202
    job_id = job1.json()["id"]
    assert job1.json()["status"] == "queued"

    job2 = client.post(f"/api/v1/reports/{rid}/export-pdf", headers=h)
    assert job2.json()["id"] == job_id

    settings = get_settings()
    claimed = claim_next(settings)
    assert claimed is not None
    assert str(claimed.id) == job_id
    assert process_report_pdf_export(claimed, settings) == "succeeded"

    # second claim of same job must not happen
    assert claim_next(settings) is None

    # process again via re-queue would be idempotent; simulate get job
    got = client.get(f"/api/v1/jobs/{job_id}", headers=h)
    assert got.status_code == 200
    assert got.json()["status"] == "succeeded"
    assert got.json()["output_ref"]["byte_size"] > 0

    report = client.get(f"/api/v1/reports/{rid}", headers=h).json()
    assert report["export_storage_key"]
    assert report["export_storage_key"].endswith(f"/v{report['version_no']}.pdf")
    pdf = InMemoryObjectStorage.instance().get_bytes(report["export_storage_key"])
    assert pdf.startswith(b"%PDF")

    # Idempotent re-claim path: reset job to queued and reprocess
    eng = create_engine(ADMIN_URL)
    with eng.begin() as conn:
        conn.execute(
            text(
                """
                UPDATE jobs
                SET status = 'queued', finished_at = NULL, locked_at = NULL,
                    locked_by = NULL, next_run_at = NULL
                WHERE id = :id
                """
            ),
            {"id": job_id},
        )
    eng.dispose()
    claimed2 = claim_next(settings)
    assert claimed2 is not None
    assert process_report_pdf_export(claimed2, settings) == "succeeded"
    assert client.get(f"/api/v1/jobs/{job_id}", headers=h).json()["output_ref"].get("idempotent") is True

    dl = client.get(f"/api/v1/reports/{rid}/export-pdf/download-url", headers=h)
    assert dl.status_code == 200
    assert "memory://download/" in dl.json()["url"]
    assert "X-Amz-" not in (dl.json()["url"])

    # Org B control
    hb0 = _dev_headers()
    org_b = _bootstrap_org(client, hb0)
    h_b = {**hb0, "X-Organization-Id": org_b}
    assert client.get(f"/api/v1/reports/{rid}", headers=h_b).status_code == 404
    assert client.get(f"/api/v1/jobs/{job_id}", headers=h_b).status_code == 404
    assert client.get(f"/api/v1/reports/{rid}/export-pdf/download-url", headers=h_b).status_code == 404
    deny = client.post(f"/api/v1/reports/{rid}/export-pdf", headers=h_b)
    assert deny.status_code in (403, 404)


def test_worker_retry_then_fail(client: TestClient, monkeypatch, disable_inline_pdf):
    h, _org_id, _aid, _qm, rid = _publish_report(client)
    job_id = client.post(f"/api/v1/reports/{rid}/export-pdf", headers=h).json()["id"]

    eng = create_engine(ADMIN_URL)
    with eng.begin() as conn:
        conn.execute(
            text("UPDATE jobs SET max_attempts = 2 WHERE id = :id"),
            {"id": job_id},
        )
    eng.dispose()

    def _boom(*_a, **_k):
        raise RuntimeError("induced_render_failure")

    monkeypatch.setattr("app.worker.process_pdf.render_report_pdf", _boom)
    settings = get_settings()

    c1 = claim_next(settings)
    assert c1 is not None
    assert process_report_pdf_export(c1, settings) == "queued"
    st = client.get(f"/api/v1/jobs/{job_id}", headers=h).json()
    assert st["status"] == "queued"
    assert st["attempt_count"] == 1
    assert st["error_code"] == "RuntimeError"

    # clear next_run_at for immediate retry
    with create_engine(ADMIN_URL).begin() as conn:
        conn.execute(
            text("UPDATE jobs SET next_run_at = NULL WHERE id = :id"),
            {"id": job_id},
        )

    c2 = claim_next(settings)
    assert c2 is not None
    assert process_report_pdf_export(c2, settings) == "failed"
    st2 = client.get(f"/api/v1/jobs/{job_id}", headers=h).json()
    assert st2["status"] == "failed"
    assert st2["attempt_count"] == 2


def test_recover_abandoned_running_job(client: TestClient, disable_inline_pdf):
    h, _org_id, _aid, _qm, rid = _publish_report(client)
    job_id = client.post(f"/api/v1/reports/{rid}/export-pdf", headers=h).json()["id"]
    settings = get_settings()
    from uuid import UUID

    claimed = claim_job(settings, UUID(job_id))
    assert claimed is not None

    stale = datetime.now(timezone.utc) - timedelta(seconds=settings.worker_lease_seconds + 60)
    with create_engine(ADMIN_URL).begin() as conn:
        conn.execute(
            text(
                """
                UPDATE jobs
                SET status = 'running',
                    locked_at = :stale,
                    locked_by = 'dead-worker'
                WHERE id = :id
                """
            ),
            {"id": job_id, "stale": stale},
        )

    n = recover_abandoned(settings)
    assert n >= 1
    row = client.get(f"/api/v1/jobs/{job_id}", headers=h).json()
    assert row["status"] == "queued"

    claimed2 = claim_job(settings, UUID(job_id))
    assert claimed2 is not None
    assert str(claimed2.id) == job_id
    assert process_report_pdf_export(claimed2, settings) == "succeeded"


def test_export_pdf_inline_memory_materializes_bytes(client: TestClient):
    """STORAGE_BACKEND=memory must process inline so download works without worker."""
    h, _org_id, _aid, _qm, rid = _publish_report(client)
    job = client.post(f"/api/v1/reports/{rid}/export-pdf", headers=h)
    assert job.status_code == 202, job.text
    assert job.json()["status"] == "succeeded"
    dl = client.get(f"/api/v1/reports/{rid}/export-pdf/download-url", headers=h)
    assert dl.status_code == 200, dl.text
    assert dl.json()["url"].startswith("memory://")
    pdf = client.get(f"/api/v1/reports/{rid}/export-pdf/bytes", headers=h)
    assert pdf.status_code == 200, pdf.text
    assert pdf.content.startswith(b"%PDF")
