"""Process report_pdf_export jobs: render PDF, put S3, update report + job."""

from __future__ import annotations

import hashlib
import json
import logging
from uuid import UUID

from sqlalchemy import text

from app.audit import write_audit
from app.config import Settings, get_settings
from app.db import admin_connection
from app.storage.base import get_storage
from app.worker.jobs import ClaimedJob, mark_failed_or_retry, mark_succeeded
from app.worker.pdf_report import render_report_pdf

logger = logging.getLogger("qmind.worker")


def process_report_pdf_export(job: ClaimedJob, settings: Settings | None = None) -> str:
    """Returns final job status: succeeded | queued | failed."""
    settings = settings or get_settings()
    log = logging.LoggerAdapter(
        logger,
        {"job_id": str(job.id), "correlation_id": str(job.correlation_id)},
    )
    try:
        report_id = UUID(str(job.input_ref["report_id"]))
        version_no = int(job.input_ref["report_version_no"])
    except (KeyError, ValueError, TypeError) as exc:
        log.error("invalid_input_ref")
        return mark_failed_or_retry(
            settings,
            job,
            error_code="invalid_input_ref",
            error_safe_message=f"Invalid job input_ref: {exc.__class__.__name__}",
        )

    storage = get_storage(settings)
    key = storage.generate_report_pdf_key(
        str(job.organization_id), str(report_id), version_no
    )

    try:
        with admin_connection() as conn:
            report = conn.execute(
                text(
                    """
                    SELECT id, organization_id, version_no, status, structured_content,
                           export_storage_key
                    FROM reports
                    WHERE id = :id AND organization_id = :org
                    FOR UPDATE
                    """
                ),
                {"id": report_id, "org": job.organization_id},
            ).first()
            if report is None:
                conn.rollback()
                return mark_failed_or_retry(
                    settings,
                    job,
                    error_code="report_not_found",
                    error_safe_message="Report not found for job organization",
                )
            if report.status not in ("published", "archived", "superseded"):
                conn.rollback()
                return mark_failed_or_retry(
                    settings,
                    job,
                    error_code="report_not_exportable",
                    error_safe_message=f"Report status {report.status} not exportable",
                )
            if int(report.version_no) != version_no:
                conn.rollback()
                return mark_failed_or_retry(
                    settings,
                    job,
                    error_code="version_mismatch",
                    error_safe_message="Report version no longer matches job input",
                )

            # Idempotent success if object already present for this key
            if report.export_storage_key == key and storage.head(key).exists:
                head = storage.head(key)
                output = {
                    "storage_key": key,
                    "byte_size": head.content_length,
                    "content_type": "application/pdf",
                    "report_id": str(report_id),
                    "report_version_no": version_no,
                    "idempotent": True,
                }
                mark_succeeded(conn, settings=settings, job=job, output_ref=output)
                conn.commit()
                log.info("pdf_export_idempotent_success")
                return "succeeded"

            content = report.structured_content
            if isinstance(content, str):
                content = json.loads(content)
            if not isinstance(content, dict):
                conn.rollback()
                return mark_failed_or_retry(
                    settings,
                    job,
                    error_code="snapshot_missing",
                    error_safe_message="Report structured_content missing",
                )

            pdf_bytes = render_report_pdf(
                content, report_id=str(report_id), version_no=version_no
            )
            digest = hashlib.sha256(pdf_bytes).hexdigest()

            storage.put_bytes(key, pdf_bytes, content_type="application/pdf")

            conn.execute(
                text(
                    """
                    UPDATE reports
                    SET export_storage_key = :key,
                        updated_at = now()
                    WHERE id = :id AND organization_id = :org
                    """
                ),
                {"key": key, "id": report_id, "org": job.organization_id},
            )
            write_audit(
                conn,
                organization_id=job.organization_id,
                actor_type="service",
                actor_service_id=settings.worker_id,
                action="report.export_pdf_store",
                resource_type="report",
                resource_id=report_id,
                correlation_id=job.correlation_id,
                metadata={
                    "job_id": str(job.id),
                    "report_version_no": version_no,
                    "byte_size": len(pdf_bytes),
                    "content_hash_sha256": digest,
                    # storage_key is an object path, not a signed URL
                    "storage_key": key,
                },
            )
            output = {
                "storage_key": key,
                "byte_size": len(pdf_bytes),
                "content_type": "application/pdf",
                "content_hash_sha256": digest,
                "report_id": str(report_id),
                "report_version_no": version_no,
            }
            mark_succeeded(conn, settings=settings, job=job, output_ref=output)
            conn.commit()
            log.info("pdf_export_succeeded bytes=%s", len(pdf_bytes))
            return "succeeded"
    except Exception as exc:
        log.exception("pdf_export_failed")
        return mark_failed_or_retry(
            settings,
            job,
            error_code=exc.__class__.__name__[:80],
            error_safe_message="PDF export failed; see worker logs with job_id",
        )
