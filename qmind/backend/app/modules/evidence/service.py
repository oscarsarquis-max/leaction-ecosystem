"""Evidence lifecycle without real S3 — domain-docs-v0 §3."""

from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.audit import write_audit
from app.auth.context import OrgContext
from app.db import tenant_connection
from app.errors import AppError
from app.modules.evidence.schemas import (
    AuthorizeUploadIn,
    EvidenceOut,
    EvidenceTransitionResult,
    ReceiveUploadIn,
)
from app.modules.orgs.service import require_role

_AUTHORIZE_ROLES = (
    "org_admin",
    "consultant_auditor",
    "quality_manager",
    "process_owner",
    "action_owner",
)
_OPERATOR_ROLES = ("org_admin", "consultant_auditor", "quality_manager")


def _row_to_out(row) -> EvidenceOut:
    return EvidenceOut(
        id=row.id,
        organization_id=row.organization_id,
        assessment_id=row.assessment_id,
        status=row.status,
        classification=row.classification,
        content_type=row.content_type,
        byte_size=row.byte_size,
        content_hash=row.content_hash,
        storage_key=row.storage_key,
        version_no=row.version_no,
        legal_hold=row.legal_hold,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _lock_evidence(conn: Connection, org_id: UUID, evidence_id: UUID):
    row = conn.execute(
        text(
            """
            SELECT id, organization_id, assessment_id, status, classification,
                   content_type, byte_size, content_hash, storage_key, version_no,
                   legal_hold, created_at, updated_at
            FROM evidences
            WHERE id = :id AND organization_id = :org
            FOR UPDATE
            """
        ),
        {"id": evidence_id, "org": org_id},
    ).first()
    if row is None:
        raise AppError("not_found", "Evidence not found", status_code=404)
    return row


def authorize_upload(ctx: OrgContext, payload: AuthorizeUploadIn) -> EvidenceOut:
    require_role(ctx, *_AUTHORIZE_ROLES)
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
        if assess.status in ("closed", "cancelled"):
            raise AppError(
                "assessment_closed",
                "Cannot authorize upload on closed/cancelled assessment",
                status_code=409,
            )
        if assess.status not in ("in_progress", "analysis"):
            raise AppError(
                "assessment_not_collecting",
                f"Upload not allowed in assessment status {assess.status}",
                status_code=409,
            )

        evidence_id = uuid4()
        # Placeholder key — real presigned S3 URL comes in a later increment
        storage_key = f"qmind/{ctx.organization_id}/{payload.assessment_id}/{evidence_id}"
        row = conn.execute(
            text(
                """
                INSERT INTO evidences (
                  id, organization_id, assessment_id, status, classification,
                  content_type, byte_size, storage_key, version_no, lineage_id,
                  legal_hold, uploaded_by
                ) VALUES (
                  :id, :org, :assess, 'upload_pending', :class,
                  :ctype, :size, :key, 1, :id,
                  false, :uploader
                )
                RETURNING id, organization_id, assessment_id, status, classification,
                          content_type, byte_size, content_hash, storage_key, version_no,
                          legal_hold, created_at, updated_at
                """
            ),
            {
                "id": evidence_id,
                "org": ctx.organization_id,
                "assess": payload.assessment_id,
                "class": payload.classification,
                "ctype": payload.content_type,
                "size": payload.declared_byte_size,
                "key": storage_key,
                "uploader": ctx.membership_id,
            },
        ).one()
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="evidence.authorize_upload",
            resource_type="evidence",
            resource_id=evidence_id,
            to_status="upload_pending",
            metadata={"assessment_id": str(payload.assessment_id), "storage_key": storage_key},
        )
        conn.commit()
        return _row_to_out(row)


def receive_upload(ctx: OrgContext, evidence_id: UUID, payload: ReceiveUploadIn) -> EvidenceTransitionResult:
    """Simulates `receive` (normally sys/worker after S3 PUT)."""
    require_role(ctx, *_OPERATOR_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        row = _lock_evidence(conn, ctx.organization_id, evidence_id)
        if row.status != "upload_pending":
            raise AppError(
                "invalid_transition",
                f"receive requires upload_pending (current={row.status})",
                status_code=409,
            )
        updated = conn.execute(
            text(
                """
                UPDATE evidences
                SET status = 'quarantined',
                    content_hash = :hash,
                    content_type = :ctype,
                    byte_size = :size,
                    updated_at = now()
                WHERE id = :id AND organization_id = :org AND status = 'upload_pending'
                RETURNING id, organization_id, assessment_id, status, classification,
                          content_type, byte_size, content_hash, storage_key, version_no,
                          legal_hold, created_at, updated_at
                """
            ),
            {
                "hash": payload.content_hash,
                "ctype": payload.content_type,
                "size": payload.byte_size,
                "id": evidence_id,
                "org": ctx.organization_id,
            },
        ).one()
        # Machine marks receive as sys; API stub records system actor for the transition
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="system",
            action="evidence.receive",
            resource_type="evidence",
            resource_id=evidence_id,
            from_status="upload_pending",
            to_status="quarantined",
            metadata={"triggered_by_membership_id": str(ctx.membership_id)},
        )
        conn.commit()
    return EvidenceTransitionResult(
        evidence=_row_to_out(updated),
        from_status="upload_pending",
        to_status="quarantined",
        event="receive",
    )


def security_pass(ctx: OrgContext, evidence_id: UUID) -> EvidenceTransitionResult:
    require_role(ctx, *_OPERATOR_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        row = _lock_evidence(conn, ctx.organization_id, evidence_id)
        if row.status != "quarantined":
            raise AppError(
                "invalid_transition",
                f"security_pass requires quarantined (current={row.status})",
                status_code=409,
            )
        updated = conn.execute(
            text(
                """
                UPDATE evidences
                SET status = 'approved', updated_at = now()
                WHERE id = :id AND organization_id = :org AND status = 'quarantined'
                RETURNING id, organization_id, assessment_id, status, classification,
                          content_type, byte_size, content_hash, storage_key, version_no,
                          legal_hold, created_at, updated_at
                """
            ),
            {"id": evidence_id, "org": ctx.organization_id},
        ).one()
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="evidence.security_pass",
            resource_type="evidence",
            resource_id=evidence_id,
            from_status="quarantined",
            to_status="approved",
        )
        conn.commit()
    return EvidenceTransitionResult(
        evidence=_row_to_out(updated),
        from_status="quarantined",
        to_status="approved",
        event="security_pass",
    )


def security_fail(ctx: OrgContext, evidence_id: UUID) -> EvidenceTransitionResult:
    require_role(ctx, *_OPERATOR_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        row = _lock_evidence(conn, ctx.organization_id, evidence_id)
        if row.status != "quarantined":
            raise AppError(
                "invalid_transition",
                f"security_fail requires quarantined (current={row.status})",
                status_code=409,
            )
        updated = conn.execute(
            text(
                """
                UPDATE evidences
                SET status = 'rejected', updated_at = now()
                WHERE id = :id AND organization_id = :org AND status = 'quarantined'
                RETURNING id, organization_id, assessment_id, status, classification,
                          content_type, byte_size, content_hash, storage_key, version_no,
                          legal_hold, created_at, updated_at
                """
            ),
            {"id": evidence_id, "org": ctx.organization_id},
        ).one()
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="evidence.security_fail",
            resource_type="evidence",
            resource_id=evidence_id,
            from_status="quarantined",
            to_status="rejected",
        )
        conn.commit()
    return EvidenceTransitionResult(
        evidence=_row_to_out(updated),
        from_status="quarantined",
        to_status="rejected",
        event="security_fail",
    )


def get_evidence(ctx: OrgContext, evidence_id: UUID) -> EvidenceOut:
    require_role(ctx, *_AUTHORIZE_ROLES, "reader")
    with tenant_connection(ctx.organization_id) as conn:
        row = _lock_evidence(conn, ctx.organization_id, evidence_id)
    return _row_to_out(row)
