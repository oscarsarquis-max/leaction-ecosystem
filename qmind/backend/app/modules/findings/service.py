"""Finding transitions — domain-docs-v0 §4 / §4.1."""

from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.audit import write_audit
from app.auth.context import OrgContext
from app.db import tenant_connection
from app.errors import AppError
from app.modules.findings.schemas import (
    DiscardIn,
    FindingCreate,
    FindingOut,
    FindingTransitionResult,
    RejectIn,
    WithdrawIn,
)
from app.modules.orgs.service import require_role

_CREATE_ROLES = ("org_admin", "consultant_auditor", "quality_manager")
_SUBMIT_ROLES = ("org_admin", "consultant_auditor", "quality_manager")
_REVIEW_ROLES = ("org_admin", "quality_manager")
_REWORK_ROLES = ("org_admin", "consultant_auditor", "quality_manager")
_WITHDRAW_ROLES = ("org_admin", "quality_manager")
_READ_ROLES = _CREATE_ROLES + ("reader", "process_owner")

_FINDING_COLS = """
    id, organization_id, assessment_id, finding_type, severity, status,
    title, body, insufficient_evidence, insufficient_evidence_rationale,
    author_membership_id, submitted_at, approved_at, approved_by,
    withdrawn_reason, discard_reason, rework_of_finding_id,
    created_at, updated_at
"""


def _load_links(conn: Connection, finding_id: UUID) -> tuple[list[UUID], list[UUID]]:
    reqs = [
        r.requirement_id
        for r in conn.execute(
            text(
                """
                SELECT requirement_id FROM finding_requirements
                WHERE finding_id = :fid
                ORDER BY requirement_id
                """
            ),
            {"fid": finding_id},
        ).all()
    ]
    evids = [
        r.evidence_id
        for r in conn.execute(
            text(
                """
                SELECT evidence_id FROM finding_evidences
                WHERE finding_id = :fid
                ORDER BY evidence_id
                """
            ),
            {"fid": finding_id},
        ).all()
    ]
    return reqs, evids


def _row_to_out(conn: Connection, row) -> FindingOut:
    reqs, evids = _load_links(conn, row.id)
    return FindingOut(
        id=row.id,
        organization_id=row.organization_id,
        assessment_id=row.assessment_id,
        finding_type=row.finding_type,
        severity=row.severity,
        status=row.status,
        title=row.title,
        body=row.body,
        insufficient_evidence=row.insufficient_evidence,
        insufficient_evidence_rationale=row.insufficient_evidence_rationale,
        author_membership_id=row.author_membership_id,
        approved_by=row.approved_by,
        withdrawn_reason=getattr(row, "withdrawn_reason", None),
        discard_reason=getattr(row, "discard_reason", None),
        rework_of_finding_id=getattr(row, "rework_of_finding_id", None),
        requirement_ids=reqs,
        evidence_ids=evids,
        submitted_at=row.submitted_at,
        approved_at=row.approved_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _lock_finding(conn: Connection, org_id: UUID, finding_id: UUID):
    row = conn.execute(
        text(
            f"""
            SELECT {_FINDING_COLS}
            FROM findings
            WHERE id = :id AND organization_id = :org
            FOR UPDATE
            """
        ),
        {"id": finding_id, "org": org_id},
    ).first()
    if row is None:
        raise AppError("not_found", "Finding not found", status_code=404)
    return row


def _assert_base_section_41(conn: Connection, org_id: UUID, finding_id: UUID, row) -> None:
    req_count = conn.execute(
        text("SELECT count(*) FROM finding_requirements WHERE finding_id = :fid"),
        {"fid": finding_id},
    ).scalar_one()
    if req_count < 1:
        raise AppError("requirement_required", "Finding requires ≥1 requirement", status_code=422)

    approved_count = conn.execute(
        text(
            """
            SELECT count(*)
            FROM finding_evidences fe
            JOIN evidences e ON e.id = fe.evidence_id AND e.organization_id = fe.organization_id
            WHERE fe.finding_id = :fid
              AND fe.organization_id = :org
              AND e.status = 'approved'
            """
        ),
        {"fid": finding_id, "org": org_id},
    ).scalar_one()

    ftype = row.finding_type
    insuff = bool(row.insufficient_evidence)
    rationale = (row.insufficient_evidence_rationale or "").strip()

    if ftype in ("conformity", "opportunity") and insuff:
        raise AppError(
            "insufficient_evidence_forbidden",
            f"insufficient_evidence is forbidden for finding_type={ftype}",
            status_code=422,
        )

    if ftype == "conformity":
        if approved_count < 1:
            raise AppError(
                "evidence_base_required",
                "conformity requires ≥1 linked Evidence.approved",
                status_code=422,
            )
        return

    if ftype in ("nonconformity", "observation"):
        if approved_count >= 1:
            return
        if insuff and rationale:
            return
        raise AppError(
            "evidence_base_required",
            f"{ftype} requires ≥1 Evidence.approved or insufficient_evidence with rationale",
            status_code=422,
        )

    if ftype == "opportunity":
        if approved_count < 1:
            raise AppError(
                "evidence_base_required",
                "opportunity requires ≥1 Evidence.approved "
                "(Answer/interview base not implemented yet)",
                status_code=422,
            )
        return

    raise AppError("invalid_finding_type", f"Unknown finding_type={ftype}", status_code=422)


def _replace_links(
    conn: Connection,
    org_id: UUID,
    finding_id: UUID,
    requirement_ids: list[UUID],
    evidence_ids: list[UUID],
) -> None:
    conn.execute(text("DELETE FROM finding_requirements WHERE finding_id = :fid"), {"fid": finding_id})
    conn.execute(text("DELETE FROM finding_evidences WHERE finding_id = :fid"), {"fid": finding_id})
    for rid in requirement_ids:
        exists = conn.execute(
            text("SELECT 1 FROM requirements WHERE id = :id"),
            {"id": rid},
        ).first()
        if exists is None:
            raise AppError("not_found", f"Requirement not found: {rid}", status_code=404)
        conn.execute(
            text(
                """
                INSERT INTO finding_requirements (organization_id, finding_id, requirement_id)
                VALUES (:org, :fid, :rid)
                """
            ),
            {"org": org_id, "fid": finding_id, "rid": rid},
        )
    for eid in evidence_ids:
        ev = conn.execute(
            text(
                """
                SELECT id, status FROM evidences
                WHERE id = :id AND organization_id = :org
                """
            ),
            {"id": eid, "org": org_id},
        ).first()
        if ev is None:
            raise AppError("not_found", f"Evidence not found: {eid}", status_code=404)
        if ev.status != "approved":
            raise AppError(
                "evidence_not_approved",
                "Only approved Evidence may be linked to a Finding",
                status_code=422,
            )
        conn.execute(
            text(
                """
                INSERT INTO finding_evidences (organization_id, finding_id, evidence_id)
                VALUES (:org, :fid, :eid)
                """
            ),
            {"org": org_id, "fid": finding_id, "eid": eid},
        )


def _copy_links(conn: Connection, org_id: UUID, from_id: UUID, to_id: UUID) -> None:
    conn.execute(
        text(
            """
            INSERT INTO finding_requirements (organization_id, finding_id, requirement_id)
            SELECT organization_id, :to_id, requirement_id
            FROM finding_requirements WHERE finding_id = :from_id
            """
        ),
        {"to_id": to_id, "from_id": from_id},
    )
    conn.execute(
        text(
            """
            INSERT INTO finding_evidences (organization_id, finding_id, evidence_id)
            SELECT organization_id, :to_id, evidence_id
            FROM finding_evidences WHERE finding_id = :from_id
            """
        ),
        {"to_id": to_id, "from_id": from_id},
    )


def create_draft(ctx: OrgContext, payload: FindingCreate) -> FindingOut:
    require_role(ctx, *_CREATE_ROLES)
    if payload.finding_type in ("conformity", "opportunity") and payload.insufficient_evidence:
        raise AppError(
            "insufficient_evidence_forbidden",
            f"insufficient_evidence is forbidden for finding_type={payload.finding_type}",
            status_code=422,
        )
    if payload.insufficient_evidence and not (payload.insufficient_evidence_rationale or "").strip():
        raise AppError(
            "rationale_required",
            "insufficient_evidence requires rationale",
            status_code=422,
        )
    with tenant_connection(ctx.organization_id) as conn:
        assess = conn.execute(
            text(
                """
                SELECT id, status FROM assessments
                WHERE id = :id AND organization_id = :org
                """
            ),
            {"id": payload.assessment_id, "org": ctx.organization_id},
        ).first()
        if assess is None:
            raise AppError("not_found", "Assessment not found", status_code=404)
        if assess.status not in ("in_progress", "analysis", "actions"):
            raise AppError(
                "assessment_not_open",
                f"Finding create not allowed in assessment status {assess.status}",
                status_code=409,
            )

        finding_id = uuid4()
        row = conn.execute(
            text(
                f"""
                INSERT INTO findings (
                  id, organization_id, assessment_id, finding_type, severity, status,
                  title, body, insufficient_evidence, insufficient_evidence_rationale,
                  author_membership_id
                ) VALUES (
                  :id, :org, :assess, :ftype, :sev, 'draft',
                  :title, :body, :insuff, :rationale,
                  :author
                )
                RETURNING {_FINDING_COLS}
                """
            ),
            {
                "id": finding_id,
                "org": ctx.organization_id,
                "assess": payload.assessment_id,
                "ftype": payload.finding_type,
                "sev": payload.severity,
                "title": payload.title.strip(),
                "body": payload.body.strip(),
                "insuff": payload.insufficient_evidence,
                "rationale": (
                    payload.insufficient_evidence_rationale.strip()
                    if payload.insufficient_evidence_rationale
                    else None
                ),
                "author": ctx.membership_id,
            },
        ).one()
        _replace_links(
            conn,
            ctx.organization_id,
            finding_id,
            payload.requirement_ids,
            payload.evidence_ids,
        )
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="finding.create",
            resource_type="finding",
            resource_id=finding_id,
            to_status="draft",
            metadata={
                "assessment_id": str(payload.assessment_id),
                "finding_type": payload.finding_type,
            },
        )
        out = _row_to_out(conn, row)
        conn.commit()
    return out


def get_finding(ctx: OrgContext, finding_id: UUID) -> FindingOut:
    require_role(ctx, *_READ_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        row = _lock_finding(conn, ctx.organization_id, finding_id)
        return _row_to_out(conn, row)


def list_findings(
    ctx: OrgContext,
    assessment_id: UUID | None = None,
    *,
    include_discarded: bool = False,
) -> list[FindingOut]:
    require_role(ctx, *_READ_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        clauses = ["organization_id = :org"]
        params: dict = {"org": ctx.organization_id}
        if assessment_id:
            clauses.append("assessment_id = :aid")
            params["aid"] = assessment_id
        if not include_discarded:
            clauses.append("status <> 'discarded'")
        rows = conn.execute(
            text(
                f"""
                SELECT {_FINDING_COLS}
                FROM findings
                WHERE {" AND ".join(clauses)}
                ORDER BY created_at DESC
                """
            ),
            params,
        ).all()
        return [_row_to_out(conn, r) for r in rows]


def submit(ctx: OrgContext, finding_id: UUID) -> FindingTransitionResult:
    require_role(ctx, *_SUBMIT_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        row = _lock_finding(conn, ctx.organization_id, finding_id)
        if row.status != "draft":
            raise AppError(
                "invalid_transition",
                f"submit requires draft (current={row.status})",
                status_code=409,
            )
        is_author = row.author_membership_id == ctx.membership_id
        if not is_author and not set(ctx.roles).intersection(("org_admin", "quality_manager")):
            raise AppError("forbidden", "Only author or QM/admin may submit", status_code=403)
        _assert_base_section_41(conn, ctx.organization_id, finding_id, row)
        updated = conn.execute(
            text(
                f"""
                UPDATE findings
                SET status = 'in_review', submitted_at = now(), updated_at = now()
                WHERE id = :id AND organization_id = :org AND status = 'draft'
                RETURNING {_FINDING_COLS}
                """
            ),
            {"id": finding_id, "org": ctx.organization_id},
        ).first()
        if updated is None:
            raise AppError("conflict", "Concurrent status change", status_code=409)
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="finding.submit",
            resource_type="finding",
            resource_id=finding_id,
            from_status="draft",
            to_status="in_review",
        )
        out = _row_to_out(conn, updated)
        conn.commit()
    return FindingTransitionResult(
        finding=out, from_status="draft", to_status="in_review", event="submit"
    )


def approve(ctx: OrgContext, finding_id: UUID) -> FindingTransitionResult:
    require_role(ctx, *_REVIEW_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        row = _lock_finding(conn, ctx.organization_id, finding_id)
        if row.status != "in_review":
            raise AppError(
                "invalid_transition",
                f"approve requires in_review (current={row.status})",
                status_code=409,
            )
        if row.author_membership_id == ctx.membership_id:
            raise AppError(
                "sod_violation",
                "Approver must differ from author (segregation of duties)",
                status_code=403,
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
        if assess.status == "cancelled":
            raise AppError("assessment_cancelled", "Assessment is cancelled", status_code=409)
        _assert_base_section_41(conn, ctx.organization_id, finding_id, row)
        updated = conn.execute(
            text(
                f"""
                UPDATE findings
                SET status = 'approved',
                    approved_at = now(),
                    approved_by = :approver,
                    updated_at = now()
                WHERE id = :id AND organization_id = :org AND status = 'in_review'
                RETURNING {_FINDING_COLS}
                """
            ),
            {
                "approver": ctx.membership_id,
                "id": finding_id,
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
            action="finding.approve",
            resource_type="finding",
            resource_id=finding_id,
            from_status="in_review",
            to_status="approved",
        )
        out = _row_to_out(conn, updated)
        conn.commit()
    return FindingTransitionResult(
        finding=out, from_status="in_review", to_status="approved", event="approve"
    )


def reject(ctx: OrgContext, finding_id: UUID, payload: RejectIn) -> FindingTransitionResult:
    require_role(ctx, *_REVIEW_ROLES)
    reason = payload.reason.strip()
    with tenant_connection(ctx.organization_id) as conn:
        row = _lock_finding(conn, ctx.organization_id, finding_id)
        if row.status != "in_review":
            raise AppError(
                "invalid_transition",
                f"reject requires in_review (current={row.status})",
                status_code=409,
            )
        updated = conn.execute(
            text(
                f"""
                UPDATE findings
                SET status = 'rejected', updated_at = now()
                WHERE id = :id AND organization_id = :org AND status = 'in_review'
                RETURNING {_FINDING_COLS}
                """
            ),
            {"id": finding_id, "org": ctx.organization_id},
        ).first()
        if updated is None:
            raise AppError("conflict", "Concurrent status change", status_code=409)
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="finding.reject",
            resource_type="finding",
            resource_id=finding_id,
            from_status="in_review",
            to_status="rejected",
            metadata={"reason": reason},
        )
        out = _row_to_out(conn, updated)
        conn.commit()
    return FindingTransitionResult(
        finding=out, from_status="in_review", to_status="rejected", event="reject"
    )


def discard(ctx: OrgContext, finding_id: UUID, payload: DiscardIn | None = None) -> FindingTransitionResult:
    """draft → discarded (soft-delete). Author, QM or org_admin."""
    require_role(ctx, "org_admin", "quality_manager", "consultant_auditor")
    reason = (payload.reason.strip() if payload and payload.reason else None) or None
    with tenant_connection(ctx.organization_id) as conn:
        row = _lock_finding(conn, ctx.organization_id, finding_id)
        if row.status != "draft":
            raise AppError(
                "invalid_transition",
                f"discard requires draft (current={row.status})",
                status_code=409,
            )
        if row.approved_at is not None:
            raise AppError(
                "discard_guard",
                "Cannot discard a finding that was approved",
                status_code=409,
            )
        is_author = row.author_membership_id == ctx.membership_id
        if not is_author and not set(ctx.roles).intersection(("org_admin", "quality_manager")):
            raise AppError(
                "forbidden",
                "Only author, quality_manager or org_admin may discard",
                status_code=403,
            )
        updated = conn.execute(
            text(
                f"""
                UPDATE findings
                SET status = 'discarded',
                    discard_reason = :reason,
                    updated_at = now()
                WHERE id = :id AND organization_id = :org AND status = 'draft'
                RETURNING {_FINDING_COLS}
                """
            ),
            {"reason": reason, "id": finding_id, "org": ctx.organization_id},
        ).first()
        if updated is None:
            raise AppError("conflict", "Concurrent status change", status_code=409)
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="finding.discard",
            resource_type="finding",
            resource_id=finding_id,
            from_status="draft",
            to_status="discarded",
            metadata={"reason": reason} if reason else {},
        )
        out = _row_to_out(conn, updated)
        conn.commit()
    return FindingTransitionResult(
        finding=out, from_status="draft", to_status="discarded", event="discard"
    )


def withdraw(ctx: OrgContext, finding_id: UUID, payload: WithdrawIn) -> FindingTransitionResult:
    require_role(ctx, *_WITHDRAW_ROLES)
    reason = payload.reason.strip()
    with tenant_connection(ctx.organization_id) as conn:
        row = _lock_finding(conn, ctx.organization_id, finding_id)
        if row.status != "approved":
            raise AppError(
                "invalid_transition",
                f"withdraw requires approved (current={row.status})",
                status_code=409,
            )
        assess = conn.execute(
            text(
                """
                SELECT status FROM assessments
                WHERE id = :id AND organization_id = :org
                FOR UPDATE
                """
            ),
            {"id": row.assessment_id, "org": ctx.organization_id},
        ).one()
        if assess.status == "closed":
            raise AppError(
                "assessment_closed",
                "Cannot withdraw finding while Assessment is closed "
                "(requires formal reopen closed→report first)",
                status_code=409,
            )
        if assess.status == "cancelled":
            raise AppError("assessment_cancelled", "Assessment is cancelled", status_code=409)

        updated = conn.execute(
            text(
                f"""
                UPDATE findings
                SET status = 'withdrawn',
                    withdrawn_reason = :reason,
                    updated_at = now()
                WHERE id = :id AND organization_id = :org AND status = 'approved'
                RETURNING {_FINDING_COLS}
                """
            ),
            {"reason": reason, "id": finding_id, "org": ctx.organization_id},
        ).first()
        if updated is None:
            raise AppError("conflict", "Concurrent status change", status_code=409)

        signaled = conn.execute(
            text(
                """
                UPDATE action_items
                SET source_finding_withdrawn = true, updated_at = now()
                WHERE finding_id = :fid AND organization_id = :org
                RETURNING id
                """
            ),
            {"fid": finding_id, "org": ctx.organization_id},
        ).all()
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="finding.withdraw",
            resource_type="finding",
            resource_id=finding_id,
            from_status="approved",
            to_status="withdrawn",
            metadata={
                "reason": reason,
                "signaled_action_item_ids": [str(r.id) for r in signaled],
            },
        )
        out = _row_to_out(conn, updated)
        conn.commit()
    return FindingTransitionResult(
        finding=out, from_status="approved", to_status="withdrawn", event="withdraw"
    )


def rework(ctx: OrgContext, finding_id: UUID) -> FindingTransitionResult:
    """rejected → draft in-place; withdrawn → new draft (preserves withdrawn history)."""
    require_role(ctx, *_REWORK_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        row = _lock_finding(conn, ctx.organization_id, finding_id)
        if row.status == "rejected":
            updated = conn.execute(
                text(
                    f"""
                    UPDATE findings
                    SET status = 'draft',
                        submitted_at = NULL,
                        approved_at = NULL,
                        approved_by = NULL,
                        updated_at = now()
                    WHERE id = :id AND organization_id = :org AND status = 'rejected'
                    RETURNING {_FINDING_COLS}
                    """
                ),
                {"id": finding_id, "org": ctx.organization_id},
            ).first()
            if updated is None:
                raise AppError("conflict", "Concurrent status change", status_code=409)
            write_audit(
                conn,
                organization_id=ctx.organization_id,
                actor_type="user",
                actor_user_id=ctx.principal.user_id,
                actor_membership_id=ctx.membership_id,
                action="finding.rework",
                resource_type="finding",
                resource_id=finding_id,
                from_status="rejected",
                to_status="draft",
            )
            out = _row_to_out(conn, updated)
            conn.commit()
            return FindingTransitionResult(
                finding=out, from_status="rejected", to_status="draft", event="rework"
            )

        if row.status == "withdrawn":
            # Preserve withdrawn row; open a new draft cycle linked via rework_of_finding_id
            new_id = uuid4()
            created = conn.execute(
                text(
                    f"""
                    INSERT INTO findings (
                      id, organization_id, assessment_id, finding_type, severity, status,
                      title, body, insufficient_evidence, insufficient_evidence_rationale,
                      author_membership_id, rework_of_finding_id
                    ) VALUES (
                      :id, :org, :assess, :ftype, :sev, 'draft',
                      :title, :body, :insuff, :rationale,
                      :author, :prev
                    )
                    RETURNING {_FINDING_COLS}
                    """
                ),
                {
                    "id": new_id,
                    "org": ctx.organization_id,
                    "assess": row.assessment_id,
                    "ftype": row.finding_type,
                    "sev": row.severity,
                    "title": row.title,
                    "body": row.body,
                    "insuff": row.insufficient_evidence,
                    "rationale": row.insufficient_evidence_rationale,
                    "author": ctx.membership_id,
                    "prev": finding_id,
                },
            ).one()
            _copy_links(conn, ctx.organization_id, finding_id, new_id)
            write_audit(
                conn,
                organization_id=ctx.organization_id,
                actor_type="user",
                actor_user_id=ctx.principal.user_id,
                actor_membership_id=ctx.membership_id,
                action="finding.rework",
                resource_type="finding",
                resource_id=new_id,
                from_status="withdrawn",
                to_status="draft",
                metadata={
                    "preserved_finding_id": str(finding_id),
                    "note": "withdrawn version kept immutable",
                },
            )
            # Audit trail on preserved row
            write_audit(
                conn,
                organization_id=ctx.organization_id,
                actor_type="user",
                actor_user_id=ctx.principal.user_id,
                actor_membership_id=ctx.membership_id,
                action="finding.rework_spawned",
                resource_type="finding",
                resource_id=finding_id,
                from_status="withdrawn",
                to_status="withdrawn",
                metadata={"new_draft_finding_id": str(new_id)},
            )
            out = _row_to_out(conn, created)
            conn.commit()
            return FindingTransitionResult(
                finding=out,
                from_status="withdrawn",
                to_status="draft",
                event="rework",
                preserved_finding_id=finding_id,
            )

        raise AppError(
            "invalid_transition",
            f"rework requires rejected|withdrawn (current={row.status})",
            status_code=409,
        )
