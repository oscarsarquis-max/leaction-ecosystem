"""Claim / complete / fail jobs with transactional locking (admin DSN)."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.audit import write_audit
from app.config import Settings
from app.db import admin_connection

logger = logging.getLogger("qmind.worker")

_JOB_COLS = """
    id, organization_id, job_type, status, requested_by, idempotency_key,
    input_ref, error_code, error_safe_message, started_at, finished_at,
    attempt_count, max_attempts, locked_at, locked_by, next_run_at, output_ref,
    created_at, updated_at
"""

_JOB_COLS_J = """
    j.id, j.organization_id, j.job_type, j.status, j.requested_by, j.idempotency_key,
    j.input_ref, j.error_code, j.error_safe_message, j.started_at, j.finished_at,
    j.attempt_count, j.max_attempts, j.locked_at, j.locked_by, j.next_run_at, j.output_ref,
    j.created_at, j.updated_at
"""


@dataclass(frozen=True, slots=True)
class ClaimedJob:
    id: UUID
    organization_id: UUID
    job_type: str
    status: str
    idempotency_key: str
    input_ref: dict[str, Any]
    attempt_count: int
    max_attempts: int
    correlation_id: UUID


def recover_abandoned(settings: Settings) -> int:
    """Re-queue running jobs whose lease expired (worker crash / restart)."""
    lease = int(settings.worker_lease_seconds)
    with admin_connection() as conn:
        rows = conn.execute(
            text(
                """
                UPDATE jobs
                SET status = 'queued',
                    locked_at = NULL,
                    locked_by = NULL,
                    next_run_at = now(),
                    error_code = COALESCE(error_code, 'lease_expired'),
                    error_safe_message = COALESCE(
                      error_safe_message,
                      'Worker lease expired; re-queued for retry'
                    ),
                    updated_at = now()
                WHERE status = 'running'
                  AND locked_at IS NOT NULL
                  AND locked_at < (now() - (:lease * interval '1 second'))
                RETURNING id, organization_id
                """
            ),
            {"lease": lease},
        ).all()
        for row in rows:
            corr = uuid4()
            write_audit(
                conn,
                organization_id=row.organization_id,
                actor_type="service",
                actor_service_id=settings.worker_id,
                action="job.lease_recover",
                resource_type="job",
                resource_id=row.id,
                from_status="running",
                to_status="queued",
                result="success",
                correlation_id=corr,
                metadata={"lease_seconds": lease},
            )
            logger.warning(
                "recovered abandoned job",
                extra={"job_id": str(row.id), "correlation_id": str(corr)},
            )
        conn.commit()
        return len(rows)


def claim_next(settings: Settings, *, job_type: str = "report_pdf_export") -> ClaimedJob | None:
    """Atomically claim one queued job (FOR UPDATE SKIP LOCKED)."""
    with admin_connection() as conn:
        row = conn.execute(
            text(
                f"""
                WITH cte AS (
                  SELECT id
                  FROM jobs
                  WHERE job_type = :jtype
                    AND status = 'queued'
                    AND (next_run_at IS NULL OR next_run_at <= now())
                  ORDER BY created_at ASC
                  FOR UPDATE SKIP LOCKED
                  LIMIT 1
                )
                UPDATE jobs j
                SET status = 'running',
                    started_at = COALESCE(j.started_at, now()),
                    locked_at = now(),
                    locked_by = :worker,
                    attempt_count = j.attempt_count + 1,
                    error_code = NULL,
                    error_safe_message = NULL,
                    updated_at = now()
                FROM cte
                WHERE j.id = cte.id
                RETURNING {_JOB_COLS_J}
                """
            ),
            {"jtype": job_type, "worker": settings.worker_id},
        ).first()
        if row is None:
            conn.commit()
            return None
        return _finish_claim(conn, settings=settings, row=row)


def claim_job(settings: Settings, job_id: UUID) -> ClaimedJob | None:
    """Claim a specific queued job by id (used for local inline PDF processing)."""
    with admin_connection() as conn:
        row = conn.execute(
            text(
                f"""
                UPDATE jobs
                SET status = 'running',
                    started_at = COALESCE(started_at, now()),
                    locked_at = now(),
                    locked_by = :worker,
                    attempt_count = attempt_count + 1,
                    error_code = NULL,
                    error_safe_message = NULL,
                    updated_at = now()
                WHERE id = :id
                  AND status = 'queued'
                  AND (next_run_at IS NULL OR next_run_at <= now())
                RETURNING {_JOB_COLS}
                """
            ),
            {"id": job_id, "worker": settings.worker_id},
        ).first()
        if row is None:
            conn.commit()
            return None
        return _finish_claim(conn, settings=settings, row=row)


def _finish_claim(conn: Connection, *, settings: Settings, row: Any) -> ClaimedJob:
    corr = uuid4()
    write_audit(
        conn,
        organization_id=row.organization_id,
        actor_type="service",
        actor_service_id=settings.worker_id,
        action="job.claim",
        resource_type="job",
        resource_id=row.id,
        from_status="queued",
        to_status="running",
        correlation_id=corr,
        metadata={"attempt_count": row.attempt_count, "job_type": row.job_type},
    )
    conn.commit()
    inp = row.input_ref if isinstance(row.input_ref, dict) else json.loads(row.input_ref or "{}")
    return ClaimedJob(
        id=row.id,
        organization_id=row.organization_id,
        job_type=row.job_type,
        status=row.status,
        idempotency_key=row.idempotency_key,
        input_ref=inp,
        attempt_count=row.attempt_count,
        max_attempts=row.max_attempts,
        correlation_id=corr,
    )


def mark_succeeded(
    conn: Connection,
    *,
    settings: Settings,
    job: ClaimedJob,
    output_ref: dict[str, Any],
) -> None:
    conn.execute(
        text(
            """
            UPDATE jobs
            SET status = 'succeeded',
                finished_at = now(),
                locked_at = NULL,
                locked_by = NULL,
                next_run_at = NULL,
                output_ref = CAST(:out AS jsonb),
                error_code = NULL,
                error_safe_message = NULL,
                updated_at = now()
            WHERE id = :id AND organization_id = :org AND status = 'running'
            """
        ),
        {
            "id": job.id,
            "org": job.organization_id,
            "out": json.dumps(output_ref),
        },
    )
    write_audit(
        conn,
        organization_id=job.organization_id,
        actor_type="service",
        actor_service_id=settings.worker_id,
        action="job.succeed",
        resource_type="job",
        resource_id=job.id,
        from_status="running",
        to_status="succeeded",
        correlation_id=job.correlation_id,
        metadata={
            "byte_size": output_ref.get("byte_size"),
            "content_type": output_ref.get("content_type"),
            "report_version_no": output_ref.get("report_version_no"),
        },
    )


def mark_failed_or_retry(
    settings: Settings,
    job: ClaimedJob,
    *,
    error_code: str,
    error_safe_message: str,
) -> str:
    """Return terminal status applied: queued (retry) or failed."""
    safe = (error_safe_message or "job_failed")[:500]
    code = (error_code or "job_failed")[:120]
    with admin_connection() as conn:
        if job.attempt_count >= job.max_attempts:
            conn.execute(
                text(
                    """
                    UPDATE jobs
                    SET status = 'failed',
                        finished_at = now(),
                        locked_at = NULL,
                        locked_by = NULL,
                        error_code = :code,
                        error_safe_message = :msg,
                        updated_at = now()
                    WHERE id = :id AND organization_id = :org AND status = 'running'
                    """
                ),
                {"id": job.id, "org": job.organization_id, "code": code, "msg": safe},
            )
            write_audit(
                conn,
                organization_id=job.organization_id,
                actor_type="service",
                actor_service_id=settings.worker_id,
                action="job.fail",
                resource_type="job",
                resource_id=job.id,
                from_status="running",
                to_status="failed",
                result="error",
                correlation_id=job.correlation_id,
                metadata={"error_code": code, "attempt_count": job.attempt_count},
            )
            conn.commit()
            return "failed"

        delay = settings.worker_backoff_base_seconds * (2 ** max(job.attempt_count - 1, 0))
        delay = min(delay, 900.0)
        next_run = datetime.now(timezone.utc) + timedelta(seconds=delay)
        conn.execute(
            text(
                """
                UPDATE jobs
                SET status = 'queued',
                    locked_at = NULL,
                    locked_by = NULL,
                    next_run_at = :next_run,
                    error_code = :code,
                    error_safe_message = :msg,
                    updated_at = now()
                WHERE id = :id AND organization_id = :org AND status = 'running'
                """
            ),
            {
                "id": job.id,
                "org": job.organization_id,
                "next_run": next_run,
                "code": code,
                "msg": safe,
            },
        )
        write_audit(
            conn,
            organization_id=job.organization_id,
            actor_type="service",
            actor_service_id=settings.worker_id,
            action="job.retry_scheduled",
            resource_type="job",
            resource_id=job.id,
            from_status="running",
            to_status="queued",
            result="error",
            correlation_id=job.correlation_id,
            metadata={
                "error_code": code,
                "attempt_count": job.attempt_count,
                "backoff_seconds": delay,
            },
        )
        conn.commit()
        return "queued"
