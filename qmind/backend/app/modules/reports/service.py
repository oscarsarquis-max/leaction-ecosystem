"""Report drafts, review, publish — immutable snapshots (domain-docs-v0 §6)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.audit import write_audit
from app.auth.context import OrgContext
from app.db import tenant_connection
from app.errors import AppError
from app.modules.orgs.service import require_role
from app.config import get_settings
from app.modules.reports.schemas import (
    DiscardIn,
    DownloadUrlOut,
    JobOut,
    ReasonIn,
    ReportCreate,
    ReportOut,
    ReportTransitionResult,
)
from app.storage.base import get_storage

_ELABORATE_ROLES = ("org_admin", "consultant_auditor", "quality_manager")
_PUBLISH_ROLES = ("org_admin", "quality_manager")
_READ_ROLES = _ELABORATE_ROLES + ("reader", "process_owner")

_REPORT_COLS = """
    id, organization_id, assessment_id, version_no, status, structured_content,
    maturity_assessment_id, export_storage_key, supersedes_report_id, discard_reason,
    published_at, published_by, author_membership_id, created_at, updated_at
"""


def _row_to_out(row) -> ReportOut:
    content = row.structured_content
    if isinstance(content, str):
        content = json.loads(content)
    return ReportOut(
        id=row.id,
        organization_id=row.organization_id,
        assessment_id=row.assessment_id,
        version_no=row.version_no,
        status=row.status,
        structured_content=content or {},
        maturity_assessment_id=row.maturity_assessment_id,
        export_storage_key=row.export_storage_key,
        supersedes_report_id=row.supersedes_report_id,
        discard_reason=row.discard_reason,
        published_at=row.published_at,
        published_by=row.published_by,
        author_membership_id=row.author_membership_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _lock_report(conn: Connection, org_id: UUID, report_id: UUID):
    row = conn.execute(
        text(
            f"""
            SELECT {_REPORT_COLS}
            FROM reports
            WHERE id = :id AND organization_id = :org
            FOR UPDATE
            """
        ),
        {"id": report_id, "org": org_id},
    ).first()
    if row is None:
        raise AppError("not_found", "Report not found", status_code=404)
    return row


def _assert_editable(row) -> None:
    if row.status not in ("draft",):
        raise AppError(
            "report_immutable",
            f"Report content only editable in draft (current={row.status})",
            status_code=409,
        )


def build_snapshot(
    conn: Connection,
    org_id: UUID,
    assessment_id: UUID,
    *,
    include_maturity: bool,
    include_action_plan: bool,
) -> tuple[dict, UUID | None]:
    """Freeze Findings approved, maturity approved, and action plan into JSON."""
    findings = conn.execute(
        text(
            """
            SELECT id, finding_type, severity, status, title, body,
                   insufficient_evidence, approved_at, approved_by
            FROM findings
            WHERE assessment_id = :aid AND organization_id = :org
              AND status = 'approved'
            ORDER BY approved_at NULLS LAST, created_at
            """
        ),
        {"aid": assessment_id, "org": org_id},
    ).all()

    maturity_id = None
    maturity_blob = None
    if include_maturity:
        mat = conn.execute(
            text(
                """
                SELECT id, version_no, status, global_score, maturity_model_id
                FROM maturity_assessments
                WHERE assessment_id = :aid AND organization_id = :org
                  AND status = 'approved'
                LIMIT 1
                """
            ),
            {"aid": assessment_id, "org": org_id},
        ).first()
        if mat is None:
            raise AppError(
                "maturity_required",
                "No approved MaturityAssessment to snapshot (or set include_maturity=false)",
                status_code=422,
            )
        maturity_id = mat.id
        dims = conn.execute(
            text(
                """
                SELECT d.code, mds.score, mds.applicable_count
                FROM maturity_dimension_scores mds
                JOIN maturity_dimensions d ON d.id = mds.dimension_id
                WHERE mds.maturity_assessment_id = :pid
                ORDER BY d.sort_order
                """
            ),
            {"pid": mat.id},
        ).all()
        model = conn.execute(
            text(
                """
                SELECT model_code, model_version FROM maturity_models WHERE id = :id
                """
            ),
            {"id": mat.maturity_model_id},
        ).one()
        maturity_blob = {
            "id": str(mat.id),
            "version_no": mat.version_no,
            "status": mat.status,
            "global_score": str(mat.global_score) if mat.global_score is not None else None,
            "maturity_model_id": str(mat.maturity_model_id),
            "model_code": model.model_code,
            "model_version": model.model_version,
            "dimension_scores": [
                {
                    "code": d.code,
                    "score": str(d.score),
                    "applicable_count": d.applicable_count,
                }
                for d in dims
            ],
        }

    plan_blob = None
    if include_action_plan:
        plan = conn.execute(
            text(
                """
                SELECT id, status, empty_plan_rationale
                FROM action_plans
                WHERE assessment_id = :aid AND organization_id = :org
                  AND status IN ('active', 'completed', 'draft')
                ORDER BY
                  CASE status WHEN 'completed' THEN 0 WHEN 'active' THEN 1 ELSE 2 END,
                  created_at DESC
                LIMIT 1
                """
            ),
            {"aid": assessment_id, "org": org_id},
        ).first()
        if plan is None:
            raise AppError(
                "action_plan_required",
                "No ActionPlan to snapshot (or set include_action_plan=false)",
                status_code=422,
            )
        items = conn.execute(
            text(
                """
                SELECT id, finding_id, action_kind, description, status,
                       owner_membership_id, due_at, source_finding_withdrawn
                FROM action_items
                WHERE action_plan_id = :pid AND organization_id = :org
                ORDER BY created_at
                """
            ),
            {"pid": plan.id, "org": org_id},
        ).all()
        plan_blob = {
            "id": str(plan.id),
            "status": plan.status,
            "empty_plan_rationale": plan.empty_plan_rationale,
            "item_ids": [str(i.id) for i in items],
            "items": [
                {
                    "id": str(i.id),
                    "finding_id": str(i.finding_id) if i.finding_id else None,
                    "action_kind": i.action_kind,
                    "description": i.description,
                    "status": i.status,
                    "owner_membership_id": str(i.owner_membership_id),
                    "due_at": i.due_at.isoformat() if i.due_at else None,
                    "source_finding_withdrawn": bool(i.source_finding_withdrawn),
                }
                for i in items
            ],
        }

    snap = {
        "snapshot_at": datetime.now(timezone.utc).isoformat(),
        "assessment_id": str(assessment_id),
        "immutable": True,
        "finding_ids": [str(f.id) for f in findings],
        "findings": [
            {
                "id": str(f.id),
                "finding_type": f.finding_type,
                "severity": f.severity,
                "status": f.status,
                "title": f.title,
                "body": f.body,
                "insufficient_evidence": f.insufficient_evidence,
                "approved_at": f.approved_at.isoformat() if f.approved_at else None,
                "approved_by": str(f.approved_by) if f.approved_by else None,
            }
            for f in findings
        ],
        "maturity": maturity_blob,
        "maturity_assessment_id": str(maturity_id) if maturity_id else None,
        "action_plan": plan_blob,
        "action_plan_id": plan_blob["id"] if plan_blob else None,
    }
    return snap, maturity_id


def create_draft(ctx: OrgContext, payload: ReportCreate) -> ReportOut:
    require_role(ctx, *_ELABORATE_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        assess = conn.execute(
            text(
                """
                SELECT id, status FROM assessments
                WHERE id = :id AND organization_id = :org
                FOR UPDATE
                """
            ),
            {"id": payload.assessment_id, "org": ctx.organization_id},
        ).first()
        if assess is None:
            raise AppError("not_found", "Assessment not found", status_code=404)
        if assess.status not in ("report", "actions"):
            raise AppError(
                "assessment_not_ready",
                f"Report create requires assessment actions|report (current={assess.status})",
                status_code=409,
            )

        open_draft = conn.execute(
            text(
                """
                SELECT id FROM reports
                WHERE assessment_id = :aid AND organization_id = :org
                  AND status IN ('draft', 'in_review')
                LIMIT 1
                """
            ),
            {"aid": payload.assessment_id, "org": ctx.organization_id},
        ).first()
        if open_draft:
            raise AppError(
                "open_report_exists",
                "An open draft/in_review report already exists for this assessment",
                status_code=409,
            )

        published = conn.execute(
            text(
                """
                SELECT id, version_no FROM reports
                WHERE assessment_id = :aid AND organization_id = :org
                  AND status = 'published'
                LIMIT 1
                """
            ),
            {"aid": payload.assessment_id, "org": ctx.organization_id},
        ).first()

        max_v = conn.execute(
            text(
                """
                SELECT COALESCE(max(version_no), 0) FROM reports
                WHERE assessment_id = :aid
                """
            ),
            {"aid": payload.assessment_id},
        ).scalar_one()

        snap, maturity_id = build_snapshot(
            conn,
            ctx.organization_id,
            payload.assessment_id,
            include_maturity=payload.include_maturity,
            include_action_plan=payload.include_action_plan,
        )
        report_id = uuid4()
        row = conn.execute(
            text(
                f"""
                INSERT INTO reports (
                  id, organization_id, assessment_id, version_no, status,
                  structured_content, maturity_assessment_id, supersedes_report_id,
                  author_membership_id
                ) VALUES (
                  :id, :org, :aid, :v, 'draft',
                  CAST(:content AS jsonb), :mid, :prev,
                  :author
                )
                RETURNING {_REPORT_COLS}
                """
            ),
            {
                "id": report_id,
                "org": ctx.organization_id,
                "aid": payload.assessment_id,
                "v": int(max_v) + 1,
                "content": json.dumps(snap),
                "mid": maturity_id,
                "prev": published.id if published else None,
                "author": ctx.membership_id,
            },
        ).one()
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="report.create",
            resource_type="report",
            resource_id=report_id,
            to_status="draft",
            metadata={
                "version_no": int(max_v) + 1,
                "finding_count": len(snap["findings"]),
                "supersedes_report_id": str(published.id) if published else None,
            },
        )
        conn.commit()
    return _row_to_out(row)


def get_report(ctx: OrgContext, report_id: UUID) -> ReportOut:
    require_role(ctx, *_READ_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        return _row_to_out(_lock_report(conn, ctx.organization_id, report_id))


def list_reports(ctx: OrgContext, assessment_id: UUID) -> list[ReportOut]:
    require_role(ctx, *_READ_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        rows = conn.execute(
            text(
                f"""
                SELECT {_REPORT_COLS}
                FROM reports
                WHERE assessment_id = :aid AND organization_id = :org
                  AND status <> 'discarded'
                ORDER BY version_no DESC
                """
            ),
            {"aid": assessment_id, "org": ctx.organization_id},
        ).all()
    return [_row_to_out(r) for r in rows]


def refresh_snapshot(ctx: OrgContext, report_id: UUID) -> ReportOut:
    """Rebuild snapshot while draft (before submit freezes for review)."""
    require_role(ctx, *_ELABORATE_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        row = _lock_report(conn, ctx.organization_id, report_id)
        _assert_editable(row)
        content = row.structured_content
        if isinstance(content, str):
            content = json.loads(content)
        include_maturity = content.get("maturity") is not None or row.maturity_assessment_id is not None
        include_plan = content.get("action_plan") is not None
        snap, maturity_id = build_snapshot(
            conn,
            ctx.organization_id,
            row.assessment_id,
            include_maturity=include_maturity if content else True,
            include_action_plan=include_plan if content else True,
        )
        updated = conn.execute(
            text(
                f"""
                UPDATE reports
                SET structured_content = CAST(:content AS jsonb),
                    maturity_assessment_id = :mid,
                    updated_at = now()
                WHERE id = :id AND organization_id = :org AND status = 'draft'
                RETURNING {_REPORT_COLS}
                """
            ),
            {
                "content": json.dumps(snap),
                "mid": maturity_id,
                "id": report_id,
                "org": ctx.organization_id,
            },
        ).one()
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="report.refresh_snapshot",
            resource_type="report",
            resource_id=report_id,
        )
        conn.commit()
    return _row_to_out(updated)


def submit(ctx: OrgContext, report_id: UUID) -> ReportTransitionResult:
    require_role(ctx, *_ELABORATE_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        row = _lock_report(conn, ctx.organization_id, report_id)
        if row.status != "draft":
            raise AppError(
                "invalid_transition",
                f"submit requires draft (current={row.status})",
                status_code=409,
            )
        content = row.structured_content
        if isinstance(content, str):
            content = json.loads(content)
        if not content or "findings" not in content:
            raise AppError("snapshot_required", "Report snapshot incomplete", status_code=422)
        updated = conn.execute(
            text(
                f"""
                UPDATE reports
                SET status = 'in_review', updated_at = now()
                WHERE id = :id AND organization_id = :org AND status = 'draft'
                RETURNING {_REPORT_COLS}
                """
            ),
            {"id": report_id, "org": ctx.organization_id},
        ).first()
        if updated is None:
            raise AppError("conflict", "Concurrent status change", status_code=409)
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="report.submit",
            resource_type="report",
            resource_id=report_id,
            from_status="draft",
            to_status="in_review",
        )
        conn.commit()
    return ReportTransitionResult(
        report=_row_to_out(updated), from_status="draft", to_status="in_review", event="submit"
    )


def request_changes(ctx: OrgContext, report_id: UUID, payload: ReasonIn) -> ReportTransitionResult:
    require_role(ctx, *_PUBLISH_ROLES)
    reason = payload.reason.strip()
    with tenant_connection(ctx.organization_id) as conn:
        row = _lock_report(conn, ctx.organization_id, report_id)
        if row.status != "in_review":
            raise AppError(
                "invalid_transition",
                f"request_changes requires in_review (current={row.status})",
                status_code=409,
            )
        updated = conn.execute(
            text(
                f"""
                UPDATE reports
                SET status = 'draft', updated_at = now()
                WHERE id = :id AND organization_id = :org AND status = 'in_review'
                RETURNING {_REPORT_COLS}
                """
            ),
            {"id": report_id, "org": ctx.organization_id},
        ).first()
        if updated is None:
            raise AppError("conflict", "Concurrent status change", status_code=409)
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="report.request_changes",
            resource_type="report",
            resource_id=report_id,
            from_status="in_review",
            to_status="draft",
            metadata={"reason": reason},
        )
        conn.commit()
    return ReportTransitionResult(
        report=_row_to_out(updated),
        from_status="in_review",
        to_status="draft",
        event="request_changes",
    )


def discard(ctx: OrgContext, report_id: UUID, payload: DiscardIn | None = None) -> ReportTransitionResult:
    require_role(ctx, *_ELABORATE_ROLES)
    reason = (payload.reason.strip() if payload and payload.reason else None) or None
    with tenant_connection(ctx.organization_id) as conn:
        row = _lock_report(conn, ctx.organization_id, report_id)
        if row.status not in ("draft", "in_review"):
            raise AppError(
                "invalid_transition",
                f"discard requires draft|in_review (current={row.status})",
                status_code=409,
            )
        if row.status == "in_review" and not reason:
            raise AppError(
                "reason_required",
                "discard from in_review requires reason",
                status_code=422,
            )
        if row.published_at is not None:
            raise AppError("discard_guard", "Published reports cannot be discarded", status_code=409)
        from_status = row.status
        updated = conn.execute(
            text(
                f"""
                UPDATE reports
                SET status = 'discarded', discard_reason = :reason, updated_at = now()
                WHERE id = :id AND organization_id = :org AND status = :from_s
                RETURNING {_REPORT_COLS}
                """
            ),
            {
                "reason": reason,
                "id": report_id,
                "org": ctx.organization_id,
                "from_s": from_status,
            },
        ).first()
        if updated is None:
            raise AppError("conflict", "Concurrent status change", status_code=409)
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="report.discard",
            resource_type="report",
            resource_id=report_id,
            from_status=from_status,
            to_status="discarded",
            metadata={"reason": reason} if reason else {},
        )
        conn.commit()
    return ReportTransitionResult(
        report=_row_to_out(updated),
        from_status=from_status,
        to_status="discarded",
        event="discard",
    )


def publish(ctx: OrgContext, report_id: UUID) -> ReportTransitionResult:
    """Idempotent publish with SoD; supersedes prior published only after this version succeeds."""
    require_role(ctx, *_PUBLISH_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        row = _lock_report(conn, ctx.organization_id, report_id)
        if row.status == "published":
            # Idempotent: already published
            return ReportTransitionResult(
                report=_row_to_out(row),
                from_status="published",
                to_status="published",
                event="publish",
            )
        if row.status != "in_review":
            raise AppError(
                "invalid_transition",
                f"publish requires in_review (current={row.status})",
                status_code=409,
            )
        if row.author_membership_id == ctx.membership_id:
            raise AppError(
                "sod_violation",
                "Publisher must differ from report author",
                status_code=403,
            )

        # One published per assessment (partial unique index): supersede then publish
        # in the SAME transaction — any failure before commit rolls back both, so the
        # previous published version is never left superseded without a successor.
        prev_id = None
        if row.supersedes_report_id:
            prev = conn.execute(
                text(
                    f"""
                    SELECT {_REPORT_COLS}
                    FROM reports
                    WHERE id = :id AND organization_id = :org
                    FOR UPDATE
                    """
                ),
                {"id": row.supersedes_report_id, "org": ctx.organization_id},
            ).first()
            if prev and prev.status == "published":
                prev_id = prev.id
                conn.execute(
                    text(
                        """
                        UPDATE reports
                        SET status = 'superseded', updated_at = now()
                        WHERE id = :id AND status = 'published'
                        """
                    ),
                    {"id": prev.id},
                )
                write_audit(
                    conn,
                    organization_id=ctx.organization_id,
                    actor_type="system",
                    action="report.supersede",
                    resource_type="report",
                    resource_id=prev.id,
                    from_status="published",
                    to_status="superseded",
                    metadata={"replaced_by": str(report_id)},
                )

        updated = conn.execute(
            text(
                f"""
                UPDATE reports
                SET status = 'published',
                    published_at = now(),
                    published_by = :pub,
                    updated_at = now()
                WHERE id = :id AND organization_id = :org AND status = 'in_review'
                RETURNING {_REPORT_COLS}
                """
            ),
            {
                "pub": ctx.membership_id,
                "id": report_id,
                "org": ctx.organization_id,
            },
        ).first()
        if updated is None:
            raise AppError("conflict", "Concurrent status change", status_code=409)

        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="report.publish",
            resource_type="report",
            resource_id=report_id,
            from_status="in_review",
            to_status="published",
            metadata={
                "version_no": updated.version_no,
                "superseded_report_id": str(prev_id) if prev_id else None,
            },
        )
        conn.commit()
    return ReportTransitionResult(
        report=_row_to_out(updated),
        from_status="in_review",
        to_status="published",
        event="publish",
    )


def archive(ctx: OrgContext, report_id: UUID) -> ReportTransitionResult:
    require_role(ctx, *_PUBLISH_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        row = _lock_report(conn, ctx.organization_id, report_id)
        if row.status != "published":
            raise AppError(
                "invalid_transition",
                f"archive requires published (current={row.status})",
                status_code=409,
            )
        assess = conn.execute(
            text(
                """
                SELECT status FROM assessments
                WHERE id = :id AND organization_id = :org
                """
            ),
            {"id": row.assessment_id, "org": ctx.organization_id},
        ).one()
        if assess.status != "closed":
            raise AppError(
                "assessment_not_closed",
                "archive requires Assessment closed",
                status_code=409,
            )
        updated = conn.execute(
            text(
                f"""
                UPDATE reports
                SET status = 'archived', updated_at = now()
                WHERE id = :id AND organization_id = :org AND status = 'published'
                RETURNING {_REPORT_COLS}
                """
            ),
            {"id": report_id, "org": ctx.organization_id},
        ).first()
        if updated is None:
            raise AppError("conflict", "Concurrent status change", status_code=409)
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="report.archive",
            resource_type="report",
            resource_id=report_id,
            from_status="published",
            to_status="archived",
        )
        conn.commit()
    return ReportTransitionResult(
        report=_row_to_out(updated),
        from_status="published",
        to_status="archived",
        event="archive",
    )


_JOB_COLS = """
    id, organization_id, job_type, status, requested_by, idempotency_key,
    input_ref, error_code, error_safe_message, started_at, finished_at,
    attempt_count, max_attempts, locked_at, locked_by, next_run_at, output_ref,
    created_at, updated_at
"""


def _job_out(row) -> JobOut:
    inp = row.input_ref if isinstance(row.input_ref, dict) else json.loads(row.input_ref or "{}")
    out = row.output_ref if isinstance(row.output_ref, dict) else json.loads(row.output_ref or "{}")
    return JobOut(
        id=row.id,
        organization_id=row.organization_id,
        job_type=row.job_type,
        status=row.status,
        idempotency_key=row.idempotency_key,
        input_ref=inp,
        created_at=row.created_at,
        attempt_count=int(row.attempt_count or 0),
        max_attempts=int(row.max_attempts or 5),
        error_code=row.error_code,
        error_safe_message=row.error_safe_message,
        started_at=row.started_at,
        finished_at=row.finished_at,
        output_ref=out or {},
    )


def get_job(ctx: OrgContext, job_id: UUID) -> JobOut:
    require_role(ctx, *_READ_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        row = conn.execute(
            text(f"SELECT {_JOB_COLS} FROM jobs WHERE id = :id AND organization_id = :org"),
            {"id": job_id, "org": ctx.organization_id},
        ).first()
        if row is None:
            raise AppError("not_found", "Job not found", status_code=404)
    return _job_out(row)


def enqueue_pdf_export(ctx: OrgContext, report_id: UUID) -> JobOut:
    """Enqueue PDF export Job (worker generates bytes out-of-band).

    Download must re-check Membership + org isolation at access time;
    knowing a storage key/URL never grants permission by itself.
    """
    require_role(ctx, *_READ_ROLES)
    settings = get_settings()
    with tenant_connection(ctx.organization_id) as conn:
        row = _lock_report(conn, ctx.organization_id, report_id)
        if row.status not in ("published", "archived", "superseded"):
            raise AppError(
                "export_not_allowed",
                f"PDF export requires published|archived|superseded (current={row.status})",
                status_code=409,
            )
        idem = f"report_pdf:{ctx.organization_id}:{report_id}:v{row.version_no}"
        existing = conn.execute(
            text(
                f"""
                SELECT {_JOB_COLS}
                FROM jobs
                WHERE organization_id = :org AND idempotency_key = :key
                """
            ),
            {"org": ctx.organization_id, "key": idem},
        ).first()
        if existing:
            return _job_out(existing)
        job_id = uuid4()
        job = conn.execute(
            text(
                f"""
                INSERT INTO jobs (
                  id, organization_id, job_type, status, requested_by,
                  idempotency_key, input_ref, max_attempts
                ) VALUES (
                  :id, :org, 'report_pdf_export', 'queued', :req,
                  :key, CAST(:inp AS jsonb), :max_attempts
                )
                RETURNING {_JOB_COLS}
                """
            ),
            {
                "id": job_id,
                "org": ctx.organization_id,
                "req": ctx.membership_id,
                "key": idem,
                "max_attempts": settings.worker_max_attempts,
                "inp": json.dumps(
                    {
                        "organization_id": str(ctx.organization_id),
                        "report_id": str(report_id),
                        "report_version_no": row.version_no,
                        "assessment_id": str(row.assessment_id),
                        "requested_by_membership_id": str(ctx.membership_id),
                    }
                ),
            },
        ).one()
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="report.export_pdf_enqueue",
            resource_type="job",
            resource_id=job_id,
            metadata={
                "report_id": str(report_id),
                "report_version_no": row.version_no,
            },
        )
        conn.commit()
    return _job_out(job)


def export_pdf_download_url(ctx: OrgContext, report_id: UUID) -> DownloadUrlOut:
    """Presigned download after membership + RLS; never audit the signed URL."""
    require_role(ctx, *_READ_ROLES)
    settings = get_settings()
    storage = get_storage(settings)
    with tenant_connection(ctx.organization_id) as conn:
        row = conn.execute(
            text(
                f"""
                SELECT {_REPORT_COLS}
                FROM reports
                WHERE id = :id AND organization_id = :org
                """
            ),
            {"id": report_id, "org": ctx.organization_id},
        ).first()
        if row is None:
            raise AppError("not_found", "Report not found", status_code=404)
        if row.status not in ("published", "archived", "superseded"):
            raise AppError(
                "download_not_allowed",
                f"PDF download requires published|archived|superseded (current={row.status})",
                status_code=409,
            )
        if not row.export_storage_key:
            raise AppError(
                "export_not_ready",
                "PDF export not ready (worker pending or failed)",
                status_code=409,
            )
        head = storage.head(row.export_storage_key)
        if not head.exists:
            raise AppError(
                "object_missing",
                "PDF object missing in storage",
                status_code=409,
            )
        url = storage.presign_download(
            row.export_storage_key,
            expires_in=settings.report_pdf_download_expires_seconds,
        )
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="report.export_pdf_download_url",
            resource_type="report",
            resource_id=report_id,
            metadata={
                "expires_in": settings.report_pdf_download_expires_seconds,
                "report_version_no": row.version_no,
            },
        )
        conn.commit()
    return DownloadUrlOut(
        url=url,
        expires_in_seconds=settings.report_pdf_download_expires_seconds,
    )
