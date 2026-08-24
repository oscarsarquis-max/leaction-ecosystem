"""Evidence + object storage — domain-docs-v0 §3 / ADR-007."""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import IntegrityError

from app.audit import write_audit
from app.auth.context import OrgContext
from app.config import get_settings
from app.db import admin_connection, tenant_connection
from app.errors import AppError
from app.idempotency import assert_same_request, key_hash, request_fingerprint
from app.modules.evidence.collection import (
    ACTION_EXECUTION_PHASE,
    assert_assessment_allows_action_evidence,
    assert_assessment_allows_collection,
    collected_phase_for_status,
    public_collection_origin,
)
from app.modules.evidence.schemas import (
    AuthorizeUploadIn,
    AuthorizeUploadOut,
    CleanupResult,
    ContextualAuthorizeUploadIn,
    DownloadUrlOut,
    EvidenceAttachmentOut,
    EvidenceLinkCreate,
    EvidenceLinkOut,
    EvidenceOut,
    EvidenceTransitionResult,
    PresignedUploadOut,
)
from app.modules.orgs.service import require_role
from app.storage import get_storage

_AUTHORIZE_ROLES = (
    "org_admin",
    "consultant_auditor",
    "quality_manager",
    "process_owner",
    "action_owner",
)
_OPERATOR_ROLES = ("org_admin", "consultant_auditor", "quality_manager")
_READ_ROLES = _AUTHORIZE_ROLES + ("reader",)


def _row_to_out(row) -> EvidenceOut:
    phase = getattr(row, "collected_phase", None)
    return EvidenceOut(
        id=row.id,
        organization_id=row.organization_id,
        assessment_id=row.assessment_id,
        improvement_case_id=getattr(row, "improvement_case_id", None),
        status=row.status,
        classification=row.classification,
        content_type=row.content_type,
        byte_size=row.byte_size,
        content_hash=row.content_hash,
        storage_key=row.storage_key,
        version_no=row.version_no,
        legal_hold=row.legal_hold,
        upload_expires_at=getattr(row, "upload_expires_at", None),
        collected_phase=phase,
        collected_at=getattr(row, "collected_at", None),
        collected_by=getattr(row, "collected_by", None),
        collection_origin=public_collection_origin(phase),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


_EVIDENCE_COLS = """
    id, organization_id, assessment_id, improvement_case_id, status, classification,
    content_type, byte_size, content_hash, storage_key, version_no,
    legal_hold, upload_expires_at, collected_phase, collected_at, collected_by,
    created_at, updated_at
"""

_EVIDENCE_RETURNING = f"RETURNING {_EVIDENCE_COLS}"


def _fetch_evidence(conn: Connection, org_id: UUID, evidence_id: UUID, *, for_update: bool = False):
    sql = f"""
        SELECT {_EVIDENCE_COLS}
        FROM evidences
        WHERE id = :id AND organization_id = :org
        {"FOR UPDATE" if for_update else ""}
    """
    row = conn.execute(text(sql), {"id": evidence_id, "org": org_id}).first()
    if row is None:
        raise AppError("not_found", "Evidence not found", status_code=404)
    return row


def _lock_evidence(conn: Connection, org_id: UUID, evidence_id: UUID):
    return _fetch_evidence(conn, org_id, evidence_id, for_update=True)


def _assert_case_allows_collection(conn: Connection, org_id: UUID, case_id: UUID) -> None:
    row = conn.execute(
        text(
            """
            SELECT id, status FROM improvement_cases
            WHERE id = :id AND organization_id = :org
            """
        ),
        {"id": case_id, "org": org_id},
    ).first()
    if row is None:
        raise AppError("not_found", "Improvement case not found", status_code=404)
    if row.status == "closed":
        raise AppError(
            "improvement_case_closed",
            "Caso de melhoria encerrado: não aceita novas evidências.",
            status_code=409,
        )


def _authorize_upload_core(
    ctx: OrgContext,
    *,
    assessment_id: UUID | None,
    improvement_case_id: UUID | None,
    classification,
    content_type: str,
    declared_byte_size: int,
    supersedes_evidence_id: UUID | None,
    initial_link: tuple[str, UUID] | None = None,
    idempotency_key: str | None = None,
    idempotency_scope: str | None = None,
    for_action_execution: bool = False,
) -> AuthorizeUploadOut:
    require_role(ctx, *_AUTHORIZE_ROLES)
    settings = get_settings()
    ctype = content_type.lower().strip()
    if ctype not in settings.allowed_content_types:
        raise AppError("content_type_not_allowed", f"Content type not allowed: {ctype}", status_code=422)
    if declared_byte_size > settings.evidence_max_bytes:
        raise AppError(
            "file_too_large",
            f"Declared size exceeds max {settings.evidence_max_bytes} bytes",
            status_code=422,
        )
    if (assessment_id is None) == (improvement_case_id is None):
        raise AppError(
            "evidence_context_required",
            "Evidence belongs either to an assessment or to an improvement case",
            status_code=422,
        )

    storage = get_storage(settings)
    with tenant_connection(ctx.organization_id) as conn:
        collected_phase: str | None = None
        if assessment_id is not None:
            assess = conn.execute(
                text(
                    """
                    SELECT id, status FROM assessments
                    WHERE id = :id AND organization_id = :org
                    """
                ),
                {"id": assessment_id, "org": ctx.organization_id},
            ).first()
            if assess is None:
                raise AppError("not_found", "Assessment not found", status_code=404)
            if for_action_execution:
                assert_assessment_allows_action_evidence(assess.status)
                collected_phase = ACTION_EXECUTION_PHASE
            else:
                assert_assessment_allows_collection(assess.status)
                collected_phase = collected_phase_for_status(assess.status)
        else:
            _assert_case_allows_collection(conn, ctx.organization_id, improvement_case_id)
        collected_at = datetime.now(timezone.utc)

        key_digest: str | None = None
        fingerprint: str | None = None
        if idempotency_key and idempotency_scope:
            key_digest = key_hash(idempotency_key)
            fingerprint = request_fingerprint(
                idempotency_scope,
                {
                    "assessment_id": assessment_id,
                    "improvement_case_id": improvement_case_id,
                    "classification": classification,
                    "content_type": ctype,
                    "declared_byte_size": declared_byte_size,
                    "supersedes_evidence_id": supersedes_evidence_id,
                    "initial_link": (
                        [initial_link[0], str(initial_link[1])]
                        if initial_link
                        else None
                    ),
                },
            )
            replay = _find_idempotent_authorize(
                conn, ctx.organization_id, idempotency_scope, key_digest, fingerprint
            )
            if replay is not None:
                return replay

        version_no = 1
        lineage_id = None
        supersedes_id = supersedes_evidence_id
        if supersedes_id is not None:
            prev = conn.execute(
                text(
                    """
                    SELECT id, assessment_id, improvement_case_id, status,
                           version_no, lineage_id
                    FROM evidences
                    WHERE id = :id AND organization_id = :org
                    FOR UPDATE
                    """
                ),
                {"id": supersedes_id, "org": ctx.organization_id},
            ).first()
            same_context = prev is not None and (
                prev.assessment_id == assessment_id
                and prev.improvement_case_id == improvement_case_id
            )
            if not same_context:
                raise AppError("not_found", "Evidence not found", status_code=404)
            if prev.status in ("disposed", "pending_disposal"):
                raise AppError(
                    "conflict",
                    "Cannot supersede disposed evidence",
                    status_code=409,
                )
            version_no = int(prev.version_no or 1) + 1
            lineage_id = prev.lineage_id or prev.id

        evidence_id = uuid4()
        if lineage_id is None:
            lineage_id = evidence_id
        storage_key = storage.generate_key(
            str(ctx.organization_id), str(evidence_id), version_no
        )
        expires_at = datetime.now(timezone.utc) + timedelta(
            seconds=settings.evidence_upload_expires_seconds
        )
        insert = text(
            f"""
            INSERT INTO evidences (
              id, organization_id, assessment_id, improvement_case_id,
              status, classification,
              content_type, byte_size, storage_key, version_no, lineage_id,
              supersedes_evidence_id,
              legal_hold, uploaded_by, upload_expires_at,
              collected_phase, collected_at, collected_by,
              idempotency_scope, idempotency_key_hash, request_fingerprint
            ) VALUES (
              :id, :org, :assess, :case,
              'upload_pending', :class,
              :ctype, :size, :key, :ver, :lineage,
              :supersedes,
              false, :uploader, :expires,
              :cphase, :cat, :cby,
              :scope, :hash, :fingerprint
            )
            {_EVIDENCE_RETURNING}
            """
        )
        params = {
            "id": evidence_id,
            "org": ctx.organization_id,
            "assess": assessment_id,
            "case": improvement_case_id,
            "class": (
                classification.value
                if hasattr(classification, "value")
                else classification
            ),
            "ctype": ctype,
            "size": declared_byte_size,
            "key": storage_key,
            "ver": version_no,
            "lineage": lineage_id,
            "supersedes": supersedes_id,
            "uploader": ctx.membership_id,
            "expires": expires_at,
            "cphase": collected_phase,
            "cat": collected_at,
            "cby": ctx.membership_id,
            "scope": idempotency_scope if key_digest else None,
            "hash": key_digest,
            "fingerprint": fingerprint,
        }
        try:
            with conn.begin_nested():
                row = conn.execute(insert, params).one()
        except IntegrityError:
            # Two retries of the same key raced: the loser reads the winner's row
            # instead of authorizing a second upload for the same request.
            if key_digest is None:
                raise
            replay = _find_idempotent_authorize(
                conn, ctx.organization_id, idempotency_scope, key_digest, fingerprint
            )
            if replay is None:
                raise
            return replay

        link_row = None
        if initial_link is not None:
            target_type, target_id = initial_link
            link_row = _upsert_link(
                conn,
                ctx,
                evidence_id=evidence_id,
                target_type=target_type,
                target_id=target_id,
            )

        upload = storage.presign_upload(
            storage_key,
            content_type=ctype,
            max_bytes=settings.evidence_max_bytes,
            expires_in=settings.evidence_upload_expires_seconds,
        )
        # Audit MUST NOT include signed URL
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
            metadata={
                "assessment_id": str(assessment_id) if assessment_id else None,
                "improvement_case_id": (
                    str(improvement_case_id) if improvement_case_id else None
                ),
                "storage_key": storage_key,
                "content_type": ctype,
                "declared_byte_size": declared_byte_size,
                "upload_expires_at": expires_at.isoformat(),
                "collected_phase": collected_phase,
                "supersedes_evidence_id": str(supersedes_id) if supersedes_id else None,
                "initial_link_target_type": initial_link[0] if initial_link else None,
                "initial_link_target_id": (
                    str(initial_link[1]) if initial_link else None
                ),
            },
        )
        conn.commit()

    return AuthorizeUploadOut(
        evidence=_row_to_out(row),
        upload=PresignedUploadOut(
            url=upload.url,
            method=upload.method,
            headers=upload.headers,
            expires_in_seconds=upload.expires_in_seconds,
        ),
        link=_link_out(link_row) if link_row is not None else None,
    )


def authorize_upload(ctx: OrgContext, payload: AuthorizeUploadIn) -> AuthorizeUploadOut:
    """Assessment-scoped authorize — unchanged contract."""
    return _authorize_upload_core(
        ctx,
        assessment_id=payload.assessment_id,
        improvement_case_id=None,
        classification=payload.classification,
        content_type=payload.content_type,
        declared_byte_size=payload.declared_byte_size,
        supersedes_evidence_id=payload.supersedes_evidence_id,
    )


_PRIVILEGED_AUTHORIZE_ROLES = frozenset(
    {
        "org_admin",
        "quality_manager",
        "consultant_auditor",
        "process_owner",
        "platform_admin",
    }
)


def authorize_action_item_upload(
    ctx: OrgContext, action_item_id: UUID, payload: ContextualAuthorizeUploadIn
) -> AuthorizeUploadOut:
    """Authorize + link in one step; context is read from the action's plan."""
    require_role(ctx, *_AUTHORIZE_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        assessment_id, case_id, owner_membership_id = _action_item_context(
            conn, ctx.organization_id, action_item_id
        )
        # action_owner alone may only attach proof to their own ActionItem.
        if not any(r in _PRIVILEGED_AUTHORIZE_ROLES for r in ctx.roles):
            if ctx.membership_id != owner_membership_id:
                raise AppError(
                    "forbidden",
                    "action_owner may only authorize evidence for their own action item",
                    status_code=403,
                )
    return _authorize_upload_core(
        ctx,
        assessment_id=assessment_id,
        improvement_case_id=case_id,
        classification=payload.classification,
        content_type=payload.content_type,
        declared_byte_size=payload.declared_byte_size,
        supersedes_evidence_id=payload.supersedes_evidence_id,
        initial_link=("action_item", action_item_id),
        idempotency_key=payload.idempotency_key,
        idempotency_scope=f"evidence.authorize:action_item:{action_item_id}",
        for_action_execution=True,
    )


def authorize_improvement_case_upload(
    ctx: OrgContext, case_id: UUID, payload: ContextualAuthorizeUploadIn
) -> AuthorizeUploadOut:
    """Authorize + link to the case itself, so the file is never left orphaned."""
    return _authorize_upload_core(
        ctx,
        assessment_id=None,
        improvement_case_id=case_id,
        classification=payload.classification,
        content_type=payload.content_type,
        declared_byte_size=payload.declared_byte_size,
        supersedes_evidence_id=payload.supersedes_evidence_id,
        initial_link=("improvement_case", case_id),
        idempotency_key=payload.idempotency_key,
        idempotency_scope=f"evidence.authorize:improvement_case:{case_id}",
    )


def put_bytes_local(ctx: OrgContext, evidence_id: UUID, data: bytes, content_type: str) -> None:
    """Local/memory storage only — browser cannot PUT to memory:// URLs."""
    require_role(ctx, *_AUTHORIZE_ROLES)
    settings = get_settings()
    if settings.environment == "prod" or settings.storage_backend != "memory":
        raise AppError(
            "local_upload_disabled",
            "Direct byte upload is only available with STORAGE_BACKEND=memory outside prod",
            status_code=503,
        )
    if not data:
        raise AppError("invalid_object_size", "Empty body", status_code=422)
    if len(data) > settings.evidence_max_bytes:
        raise AppError(
            "file_too_large",
            f"Body exceeds max {settings.evidence_max_bytes} bytes",
            status_code=422,
        )
    ctype = (content_type or "").split(";")[0].strip().lower()
    if ctype not in settings.allowed_content_types:
        raise AppError(
            "content_type_not_allowed",
            f"Content type not allowed: {ctype}",
            status_code=422,
        )
    storage = get_storage(settings)
    with tenant_connection(ctx.organization_id) as conn:
        row = _lock_evidence(conn, ctx.organization_id, evidence_id)
        if row.status != "upload_pending":
            raise AppError(
                "invalid_transition",
                f"local put requires upload_pending (current={row.status})",
                status_code=409,
            )
        if row.upload_expires_at and row.upload_expires_at < datetime.now(timezone.utc):
            raise AppError("upload_expired", "Upload authorization expired", status_code=410)
        if row.content_type and ctype != row.content_type.lower():
            raise AppError(
                "content_type_mismatch",
                "Content type does not match authorized type",
                status_code=422,
            )
        if row.byte_size is not None and len(data) != row.byte_size:
            raise AppError(
                "size_mismatch",
                "Body size does not match declared size",
                status_code=422,
            )
        storage.put_test_object(row.storage_key, data, ctype)
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="evidence.local_put",
            resource_type="evidence",
            resource_id=evidence_id,
            metadata={"byte_size": len(data), "content_type": ctype},
        )
        conn.commit()


def receive_upload(ctx: OrgContext, evidence_id: UUID) -> EvidenceTransitionResult:
    """Confirm object via HEAD + hash bytes — never trust client size/type/hash."""
    require_role(ctx, *_OPERATOR_ROLES)
    settings = get_settings()
    storage = get_storage(settings)

    with tenant_connection(ctx.organization_id) as conn:
        row = _lock_evidence(conn, ctx.organization_id, evidence_id)
        if row.status != "upload_pending":
            raise AppError(
                "invalid_transition",
                f"receive requires upload_pending (current={row.status})",
                status_code=409,
            )
        if row.upload_expires_at and row.upload_expires_at < datetime.now(timezone.utc):
            raise AppError("upload_expired", "Upload authorization expired", status_code=410)

        head = storage.head(row.storage_key)
        if not head.exists:
            raise AppError("object_missing", "Object not found in storage", status_code=422)
        size = head.content_length or 0
        if size < 1 or size > settings.evidence_max_bytes:
            raise AppError("invalid_object_size", f"Object size invalid: {size}", status_code=422)
        if row.byte_size is not None and size != row.byte_size:
            # declared size must match actual object
            raise AppError(
                "size_mismatch",
                "Object size does not match declared size",
                status_code=422,
            )
        detected_type = (head.content_type or row.content_type or "").split(";")[0].strip().lower()
        if detected_type not in settings.allowed_content_types:
            raise AppError(
                "content_type_not_allowed",
                f"Detected content type not allowed: {detected_type}",
                status_code=422,
            )
        if row.content_type and detected_type != row.content_type.lower():
            raise AppError(
                "content_type_mismatch",
                "Detected content type does not match authorized type",
                status_code=422,
            )

        # Integrity: hash object bytes (or a future S3 ChecksumSHA256 / signed trailer).
        # Do NOT use head.etag — multipart ETags are not MD5/SHA-256 of the full object.
        data = storage.get_bytes(row.storage_key)
        if len(data) != size:
            raise AppError("size_mismatch", "Downloaded size mismatch", status_code=422)
        digest = "sha256:" + hashlib.sha256(data).hexdigest()

        prev_id = conn.execute(
            text(
                """
                SELECT supersedes_evidence_id
                FROM evidences
                WHERE id = :id AND organization_id = :org
                """
            ),
            {"id": evidence_id, "org": ctx.organization_id},
        ).scalar_one_or_none()

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
                RETURNING id, organization_id, assessment_id, improvement_case_id,
                          status, classification,
                          content_type, byte_size, content_hash, storage_key, version_no,
                          legal_hold, upload_expires_at, collected_phase, collected_at,
                          collected_by, created_at, updated_at
                """
            ),
            {
                "hash": digest,
                "ctype": detected_type,
                "size": size,
                "id": evidence_id,
                "org": ctx.organization_id,
            },
        ).one()

        if prev_id is not None:
            conn.execute(
                text(
                    """
                    UPDATE evidences
                    SET status = 'superseded', updated_at = now()
                    WHERE id = :prev AND organization_id = :org
                      AND status NOT IN ('disposed', 'pending_disposal', 'superseded')
                    """
                ),
                {"prev": prev_id, "org": ctx.organization_id},
            )

        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="system",
            action="evidence.receive",
            resource_type="evidence",
            resource_id=evidence_id,
            from_status="upload_pending",
            to_status="quarantined",
            metadata={
                "triggered_by_membership_id": str(ctx.membership_id),
                "byte_size": size,
                "content_type": detected_type,
                "content_hash": digest,
                "superseded_evidence_id": str(prev_id) if prev_id else None,
            },
        )
        conn.commit()
    return EvidenceTransitionResult(
        evidence=_row_to_out(updated),
        from_status="upload_pending",
        to_status="quarantined",
        event="receive",
    )


def security_pass(ctx: OrgContext, evidence_id: UUID) -> EvidenceTransitionResult:
    """Administrative/simulated until quarantine worker exists — blocked in prod by settings."""
    settings = get_settings()
    if not settings.allow_simulated_security_pass:
        raise AppError(
            "simulated_security_pass_disabled",
            "Simulated security_pass is disabled; use quarantine worker",
            status_code=503,
        )
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
                RETURNING id, organization_id, assessment_id, improvement_case_id,
                          status, classification,
                          content_type, byte_size, content_hash, storage_key, version_no,
                          legal_hold, upload_expires_at, collected_phase, collected_at,
                          collected_by, created_at, updated_at
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
            metadata={"simulated": True, "note": "pending quarantine worker"},
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
    settings = get_settings()
    storage = get_storage(settings)
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
                RETURNING id, organization_id, assessment_id, improvement_case_id,
                          status, classification,
                          content_type, byte_size, content_hash, storage_key, version_no,
                          legal_hold, upload_expires_at, collected_phase, collected_at,
                          collected_by, created_at, updated_at
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
    # Best-effort isolate object (keep key for audit trail; optional delete later)
    _ = storage
    return EvidenceTransitionResult(
        evidence=_row_to_out(updated),
        from_status="quarantined",
        to_status="rejected",
        event="security_fail",
    )


def get_evidence(ctx: OrgContext, evidence_id: UUID) -> EvidenceOut:
    require_role(ctx, *_READ_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        row = _fetch_evidence(conn, ctx.organization_id, evidence_id)
    return _row_to_out(row)


def get_bytes_local(ctx: OrgContext, evidence_id: UUID) -> tuple[bytes, str]:
    """Local/memory download — browser cannot fetch memory:// URLs."""
    require_role(ctx, *_READ_ROLES)
    settings = get_settings()
    if settings.environment == "prod" or settings.storage_backend != "memory":
        raise AppError(
            "local_download_disabled",
            "Direct byte download is only available with STORAGE_BACKEND=memory outside prod",
            status_code=503,
        )
    storage = get_storage(settings)
    with tenant_connection(ctx.organization_id) as conn:
        row = _fetch_evidence(conn, ctx.organization_id, evidence_id)
        if not row.storage_key:
            raise AppError("object_missing", "No storage object for evidence", status_code=422)
        is_operator = bool(set(ctx.roles).intersection(_OPERATOR_ROLES))
        if row.status == "approved":
            pass
        elif row.status == "quarantined" and is_operator:
            pass
        else:
            raise AppError(
                "download_not_allowed",
                f"Download not allowed in status {row.status}",
                status_code=409,
            )
        try:
            data = storage.get_bytes(row.storage_key)
        except FileNotFoundError as exc:
            raise AppError("object_missing", "Object not found in storage", status_code=422) from exc
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="evidence.local_download",
            resource_type="evidence",
            resource_id=evidence_id,
            metadata={"byte_size": len(data)},
        )
        conn.commit()
    return data, (row.content_type or "application/octet-stream")


def download_url(ctx: OrgContext, evidence_id: UUID) -> DownloadUrlOut:
    require_role(ctx, *_READ_ROLES)
    settings = get_settings()
    storage = get_storage(settings)
    with tenant_connection(ctx.organization_id) as conn:
        row = _fetch_evidence(conn, ctx.organization_id, evidence_id)
        if not row.storage_key:
            raise AppError("object_missing", "No storage object for evidence", status_code=422)
        is_operator = bool(set(ctx.roles).intersection(_OPERATOR_ROLES))
        if row.status == "approved":
            pass
        elif row.status == "quarantined" and is_operator:
            pass
        else:
            raise AppError(
                "download_not_allowed",
                f"Download not allowed in status {row.status}",
                status_code=409,
            )
        url = storage.presign_download(
            row.storage_key, expires_in=settings.evidence_download_expires_seconds
        )
        # Audit MUST NOT include signed URL
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="evidence.download_url",
            resource_type="evidence",
            resource_id=evidence_id,
            metadata={"expires_in": settings.evidence_download_expires_seconds},
        )
        conn.commit()
    return DownloadUrlOut(url=url, expires_in_seconds=settings.evidence_download_expires_seconds)


def abandon_upload(ctx: OrgContext, evidence_id: UUID) -> EvidenceTransitionResult:
    require_role(ctx, *_OPERATOR_ROLES)
    settings = get_settings()
    storage = get_storage(settings)
    with tenant_connection(ctx.organization_id) as conn:
        row = _lock_evidence(conn, ctx.organization_id, evidence_id)
        if row.status != "upload_pending":
            raise AppError(
                "invalid_transition",
                f"abandon requires upload_pending (current={row.status})",
                status_code=409,
            )
        if row.legal_hold:
            raise AppError("legal_hold", "Cannot dispose under legal hold", status_code=409)
        storage.delete(row.storage_key)
        updated = conn.execute(
            text(
                """
                UPDATE evidences
                SET status = 'disposed', disposed_at = now(), updated_at = now(),
                    storage_key = NULL
                WHERE id = :id AND organization_id = :org
                RETURNING id, organization_id, assessment_id, improvement_case_id,
                          status, classification,
                          content_type, byte_size, content_hash, storage_key, version_no,
                          legal_hold, upload_expires_at, collected_phase, collected_at,
                          collected_by, created_at, updated_at
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
            action="evidence.abandon",
            resource_type="evidence",
            resource_id=evidence_id,
            from_status="upload_pending",
            to_status="disposed",
        )
        conn.commit()
    return EvidenceTransitionResult(
        evidence=_row_to_out(updated),
        from_status="upload_pending",
        to_status="disposed",
        event="abandon",
    )


def cleanup_expired_uploads() -> CleanupResult:
    """Expire pending uploads past upload_expires_at (system job)."""
    settings = get_settings()
    storage = get_storage(settings)
    disposed = 0
    with admin_connection() as conn:
        rows = conn.execute(
            text(
                """
                SELECT id, organization_id, storage_key
                FROM evidences
                WHERE status = 'upload_pending'
                  AND upload_expires_at IS NOT NULL
                  AND upload_expires_at < now()
                  AND legal_hold = false
                FOR UPDATE SKIP LOCKED
                """
            )
        ).all()
        for r in rows:
            if r.storage_key:
                try:
                    storage.delete(r.storage_key)
                except Exception:
                    pass
            conn.execute(
                text(
                    """
                    UPDATE evidences
                    SET status = 'disposed', disposed_at = now(), updated_at = now(),
                        storage_key = NULL
                    WHERE id = :id
                    """
                ),
                {"id": r.id},
            )
            write_audit(
                conn,
                organization_id=r.organization_id,
                actor_type="system",
                action="evidence.expire",
                resource_type="evidence",
                resource_id=r.id,
                from_status="upload_pending",
                to_status="disposed",
            )
            disposed += 1
        conn.commit()
    return CleanupResult(disposed_count=disposed)


_LINK_COLS = """
    id, organization_id, evidence_id, target_type, target_id, created_at,
    removed_at, removed_by, removal_reason
"""


def _link_out(row) -> EvidenceLinkOut:
    return EvidenceLinkOut(
        id=row.id,
        organization_id=row.organization_id,
        evidence_id=row.evidence_id,
        target_type=row.target_type,
        target_id=row.target_id,
        created_at=row.created_at,
        removed_at=getattr(row, "removed_at", None),
        removed_by=getattr(row, "removed_by", None),
        removal_reason=getattr(row, "removal_reason", None),
    )


def _action_item_context(
    conn: Connection, org_id: UUID, action_item_id: UUID
) -> tuple[UUID | None, UUID | None, UUID]:
    """Assessment XOR improvement case that an action item ultimately belongs to."""
    row = conn.execute(
        text(
            """
            SELECT ap.assessment_id, ap.improvement_case_id, ai.owner_membership_id
            FROM action_items ai
            JOIN action_plans ap
              ON ap.id = ai.action_plan_id AND ap.organization_id = ai.organization_id
            WHERE ai.id = :id AND ai.organization_id = :org
            """
        ),
        {"id": action_item_id, "org": org_id},
    ).first()
    if row is None:
        raise AppError("not_found", "Action item not found", status_code=404)
    return row.assessment_id, row.improvement_case_id, row.owner_membership_id


def _assert_same_context(
    *,
    evidence_assessment_id: UUID | None,
    evidence_case_id: UUID | None,
    target_assessment_id: UUID | None,
    target_case_id: UUID | None,
    label: str,
) -> None:
    """A link may never cross the assessment/case boundary of its evidence."""
    if evidence_assessment_id is not None:
        if target_assessment_id != evidence_assessment_id:
            raise AppError(
                "link_context_mismatch",
                f"{label} belongs to a different assessment",
                status_code=422,
            )
        return
    if evidence_case_id is not None:
        if target_case_id != evidence_case_id:
            raise AppError(
                "link_context_mismatch",
                f"{label} belongs to a different improvement case",
                status_code=422,
            )


def _assert_link_target(
    conn: Connection,
    org_id: UUID,
    evidence_assessment_id: UUID | None,
    target_type: str,
    target_id: UUID,
    evidence_case_id: UUID | None = None,
) -> None:
    if target_type == "requirement":
        row = conn.execute(
            text("SELECT id FROM requirements WHERE id = :id"),
            {"id": target_id},
        ).first()
        if row is None:
            raise AppError("not_found", "Requirement not found", status_code=404)
        return

    if target_type == "question":
        row = conn.execute(
            text("SELECT id FROM questions WHERE id = :id"),
            {"id": target_id},
        ).first()
        if row is None:
            raise AppError("not_found", "Question not found", status_code=404)
        return

    if target_type == "interview":
        row = conn.execute(
            text(
                """
                SELECT id, assessment_id FROM interviews
                WHERE id = :id AND organization_id = :org
                """
            ),
            {"id": target_id, "org": org_id},
        ).first()
        if row is None:
            raise AppError("not_found", "Interview not found", status_code=404)
        if evidence_assessment_id and row.assessment_id != evidence_assessment_id:
            raise AppError(
                "link_assessment_mismatch",
                "Interview belongs to a different assessment",
                status_code=422,
            )
        return

    if target_type == "answer":
        row = conn.execute(
            text(
                """
                SELECT a.id, i.assessment_id
                FROM answers a
                JOIN interviews i
                  ON i.id = a.interview_id AND i.organization_id = a.organization_id
                WHERE a.id = :id AND a.organization_id = :org
                """
            ),
            {"id": target_id, "org": org_id},
        ).first()
        if row is None:
            raise AppError("not_found", "Answer not found", status_code=404)
        if evidence_assessment_id and row.assessment_id != evidence_assessment_id:
            raise AppError(
                "link_assessment_mismatch",
                "Answer belongs to a different assessment",
                status_code=422,
            )
        return

    if target_type == "finding":
        row = conn.execute(
            text(
                """
                SELECT id, assessment_id FROM findings
                WHERE id = :id AND organization_id = :org
                """
            ),
            {"id": target_id, "org": org_id},
        ).first()
        if row is None:
            raise AppError("not_found", "Finding not found", status_code=404)
        if evidence_assessment_id and row.assessment_id != evidence_assessment_id:
            raise AppError(
                "link_assessment_mismatch",
                "Finding belongs to a different assessment",
                status_code=422,
            )
        return

    if target_type == "action_item":
        target_assessment, target_case, _owner = _action_item_context(
            conn, org_id, target_id
        )
        _assert_same_context(
            evidence_assessment_id=evidence_assessment_id,
            evidence_case_id=evidence_case_id,
            target_assessment_id=target_assessment,
            target_case_id=target_case,
            label="Action item",
        )
        return

    # Execution artefacts inherit their context from the action item they hang off.
    _VIA_ACTION_ITEM = {
        "action_check_in": ("action_execution_check_ins", "Check-in"),
        "action_impediment": ("action_impediments", "Impediment"),
    }
    if target_type in _VIA_ACTION_ITEM:
        table, label = _VIA_ACTION_ITEM[target_type]
        row = conn.execute(
            text(
                f"""
                SELECT action_item_id FROM {table}
                WHERE id = :id AND organization_id = :org
                """
            ),
            {"id": target_id, "org": org_id},
        ).first()
        if row is None:
            raise AppError("not_found", f"{label} not found", status_code=404)
        target_assessment, target_case, _owner = _action_item_context(
            conn, org_id, row.action_item_id
        )
        _assert_same_context(
            evidence_assessment_id=evidence_assessment_id,
            evidence_case_id=evidence_case_id,
            target_assessment_id=target_assessment,
            target_case_id=target_case,
            label=label,
        )
        return

    if target_type == "measurement_record":
        row = conn.execute(
            text(
                """
                SELECT amp.assessment_id, amp.improvement_case_id
                FROM measurement_records mr
                JOIN action_measurement_plans amp
                  ON amp.id = mr.measurement_plan_id
                  AND amp.organization_id = mr.organization_id
                WHERE mr.id = :id AND mr.organization_id = :org
                """
            ),
            {"id": target_id, "org": org_id},
        ).first()
        if row is None:
            raise AppError("not_found", "Measurement record not found", status_code=404)
        _assert_same_context(
            evidence_assessment_id=evidence_assessment_id,
            evidence_case_id=evidence_case_id,
            target_assessment_id=row.assessment_id,
            target_case_id=row.improvement_case_id,
            label="Measurement record",
        )
        return

    if target_type == "outcome_observation":
        row = conn.execute(
            text(
                """
                SELECT improvement_case_id
                FROM improvement_case_outcome_observations
                WHERE id = :id AND organization_id = :org
                """
            ),
            {"id": target_id, "org": org_id},
        ).first()
        if row is None:
            raise AppError("not_found", "Outcome observation not found", status_code=404)
        _assert_same_context(
            evidence_assessment_id=evidence_assessment_id,
            evidence_case_id=evidence_case_id,
            target_assessment_id=None,
            target_case_id=row.improvement_case_id,
            label="Outcome observation",
        )
        return

    if target_type == "improvement_case":
        row = conn.execute(
            text(
                """
                SELECT id FROM improvement_cases
                WHERE id = :id AND organization_id = :org
                """
            ),
            {"id": target_id, "org": org_id},
        ).first()
        if row is None:
            raise AppError("not_found", "Improvement case not found", status_code=404)
        _assert_same_context(
            evidence_assessment_id=evidence_assessment_id,
            evidence_case_id=evidence_case_id,
            target_assessment_id=None,
            target_case_id=row.id,
            label="Improvement case",
        )
        return

    raise AppError("invalid_target_type", f"Unsupported target_type={target_type}", status_code=422)


def list_assessment_evidences(ctx: OrgContext, assessment_id: UUID) -> list[EvidenceOut]:
    require_role(ctx, *_READ_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        assess = conn.execute(
            text(
                "SELECT id FROM assessments WHERE id = :id AND organization_id = :org"
            ),
            {"id": assessment_id, "org": ctx.organization_id},
        ).first()
        if assess is None:
            raise AppError("not_found", "Assessment not found", status_code=404)
        rows = conn.execute(
            text(
                f"""
                SELECT {_EVIDENCE_COLS}
                FROM evidences
                WHERE assessment_id = :aid AND organization_id = :org
                ORDER BY created_at DESC
                """
            ),
            {"aid": assessment_id, "org": ctx.organization_id},
        ).all()
    return [_row_to_out(r) for r in rows]


def _find_idempotent_authorize(
    conn: Connection,
    org_id: UUID,
    scope: str,
    key_digest: str,
    fingerprint: str,
) -> AuthorizeUploadOut | None:
    """Replay of a previous authorize with the same key — never a second Evidence.

    The key is only ever compared inside its own scope, so `"run-1"` used for an
    action and for a case are two independent keys. A key reused for a
    *different* request is refused instead of being answered with the wrong
    evidence.
    """
    row = conn.execute(
        text(
            f"""
            SELECT {_EVIDENCE_COLS}, request_fingerprint
            FROM evidences
            WHERE organization_id = :org
              AND idempotency_scope = :scope
              AND idempotency_key_hash = :hash
            """
        ),
        {"org": org_id, "scope": scope, "hash": key_digest},
    ).first()
    if row is None:
        return None
    assert_same_request(row.request_fingerprint, fingerprint)
    link = conn.execute(
        text(
            f"""
            SELECT {_LINK_COLS}
            FROM evidence_links
            WHERE organization_id = :org AND evidence_id = :eid
              AND removed_at IS NULL
            ORDER BY created_at
            LIMIT 1
            """
        ),
        {"org": org_id, "eid": row.id},
    ).first()
    settings = get_settings()
    storage = get_storage(settings)
    upload = storage.presign_upload(
        row.storage_key,
        content_type=row.content_type or "application/octet-stream",
        max_bytes=settings.evidence_max_bytes,
        expires_in=settings.evidence_upload_expires_seconds,
    )
    return AuthorizeUploadOut(
        evidence=_row_to_out(row),
        upload=PresignedUploadOut(
            url=upload.url,
            method=upload.method,
            headers=upload.headers,
            expires_in_seconds=upload.expires_in_seconds,
        ),
        link=_link_out(link) if link is not None else None,
    )


def _upsert_link(
    conn: Connection,
    ctx: OrgContext,
    *,
    evidence_id: UUID,
    target_type: str,
    target_id: UUID,
):
    existing = conn.execute(
        text(
            f"""
            SELECT {_LINK_COLS}
            FROM evidence_links
            WHERE organization_id = :org
              AND evidence_id = :eid
              AND target_type = :tt
              AND target_id = :tid
              AND removed_at IS NULL
            """
        ),
        {
            "org": ctx.organization_id,
            "eid": evidence_id,
            "tt": target_type,
            "tid": target_id,
        },
    ).first()
    if existing is not None:
        return existing

    row = conn.execute(
        text(
            f"""
            INSERT INTO evidence_links (
              organization_id, evidence_id, target_type, target_id
            ) VALUES (
              :org, :eid, :tt, :tid
            )
            RETURNING {_LINK_COLS}
            """
        ),
        {
            "org": ctx.organization_id,
            "eid": evidence_id,
            "tt": target_type,
            "tid": target_id,
        },
    ).one()
    write_audit(
        conn,
        organization_id=ctx.organization_id,
        actor_type="user",
        actor_user_id=ctx.principal.user_id,
        actor_membership_id=ctx.membership_id,
        action="evidence.link",
        resource_type="evidence",
        resource_id=evidence_id,
        metadata={
            "link_id": str(row.id),
            "target_type": target_type,
            "target_id": str(target_id),
        },
    )
    return row


def attach_evidences(
    conn: Connection,
    ctx: OrgContext,
    *,
    target_type: str,
    target_id: UUID,
    evidence_ids: list[UUID],
) -> list[UUID]:
    """Link already-authorized evidences inside the caller's transaction.

    Used when a write both creates a domain object and says what proves it —
    recording a measurement, for instance — so the object and its proof commit
    together or not at all.
    """
    linked: list[UUID] = []
    for evidence_id in dict.fromkeys(evidence_ids):
        evidence = _fetch_evidence(conn, ctx.organization_id, evidence_id)
        if evidence.status in ("disposed", "pending_disposal"):
            raise AppError(
                "evidence_not_linkable",
                f"Cannot link Evidence in status {evidence.status}",
                status_code=409,
            )
        _assert_link_target(
            conn,
            ctx.organization_id,
            evidence.assessment_id,
            target_type,
            target_id,
            evidence.improvement_case_id,
        )
        row = _upsert_link(
            conn,
            ctx,
            evidence_id=evidence_id,
            target_type=target_type,
            target_id=target_id,
        )
        linked.append(row.id)
    return linked


def create_evidence_link(
    ctx: OrgContext, evidence_id: UUID, payload: EvidenceLinkCreate
) -> EvidenceLinkOut:
    require_role(ctx, *_OPERATOR_ROLES)
    target_type = (
        payload.target_type.value
        if hasattr(payload.target_type, "value")
        else str(payload.target_type)
    )
    with tenant_connection(ctx.organization_id) as conn:
        evidence = _fetch_evidence(conn, ctx.organization_id, evidence_id)
        if evidence.status in ("disposed", "pending_disposal"):
            raise AppError(
                "evidence_not_linkable",
                f"Cannot link Evidence in status {evidence.status}",
                status_code=409,
            )
        _assert_link_target(
            conn,
            ctx.organization_id,
            evidence.assessment_id,
            target_type,
            payload.target_id,
            evidence.improvement_case_id,
        )
        row = _upsert_link(
            conn,
            ctx,
            evidence_id=evidence_id,
            target_type=target_type,
            target_id=payload.target_id,
        )
        conn.commit()
    return _link_out(row)


def list_evidence_links(
    ctx: OrgContext, evidence_id: UUID, *, include_removed: bool = False
) -> list[EvidenceLinkOut]:
    require_role(ctx, *_READ_ROLES)
    if include_removed:
        require_role(ctx, *_OPERATOR_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        _fetch_evidence(conn, ctx.organization_id, evidence_id)
        rows = conn.execute(
            text(
                f"""
                SELECT {_LINK_COLS}
                FROM evidence_links
                WHERE evidence_id = :eid AND organization_id = :org
                  AND (:all OR removed_at IS NULL)
                ORDER BY created_at
                """
            ),
            {"eid": evidence_id, "org": ctx.organization_id, "all": include_removed},
        ).all()
    return [_link_out(r) for r in rows]


def list_links_for_target(
    ctx: OrgContext,
    *,
    target_type: str,
    target_id: UUID,
    include_removed: bool = False,
) -> list[EvidenceAttachmentOut]:
    """Every evidence attached to one domain object, already readable.

    The join is done here on purpose: a card detail screen would otherwise
    issue one request per attachment just to learn the file's type and status.
    """
    require_role(ctx, *_READ_ROLES)
    if include_removed:
        require_role(ctx, *_OPERATOR_ROLES)
    link_cols = ", ".join(f"el.{c.strip()}" for c in _LINK_COLS.split(","))
    evidence_cols = ", ".join(
        f"e.{c.strip()} AS ev_{c.strip()}" for c in _EVIDENCE_COLS.split(",")
    )
    with tenant_connection(ctx.organization_id) as conn:
        rows = conn.execute(
            text(
                f"""
                SELECT {link_cols}, {evidence_cols}
                FROM evidence_links el
                LEFT JOIN evidences e
                  ON e.id = el.evidence_id
                 AND e.organization_id = el.organization_id
                WHERE el.organization_id = :org
                  AND el.target_type = :tt
                  AND el.target_id = :tid
                  AND (:all OR el.removed_at IS NULL)
                ORDER BY el.created_at
                """
            ),
            {
                "org": ctx.organization_id,
                "tt": target_type,
                "tid": target_id,
                "all": include_removed,
            },
        ).all()
    return [
        EvidenceAttachmentOut(
            link=_link_out(r),
            evidence=_row_to_out(_EvidenceProjection(r)) if r.ev_id else None,
        )
        for r in rows
    ]


class _EvidenceProjection:
    """Reads the `ev_`-prefixed half of a joined row as if it were an evidence."""

    __slots__ = ("_row",)

    def __init__(self, row) -> None:
        self._row = row

    def __getattr__(self, name: str):
        return getattr(self._row, f"ev_{name}")


def delete_evidence_link(
    ctx: OrgContext,
    evidence_id: UUID,
    link_id: UUID,
    *,
    removal_reason: str = "",
) -> None:
    """Soft delete — the trail keeps the fact that this evidence was once linked."""
    require_role(ctx, *_OPERATOR_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        _fetch_evidence(conn, ctx.organization_id, evidence_id)
        removed = conn.execute(
            text(
                """
                UPDATE evidence_links
                SET removed_at = now(),
                    removed_by = :uid,
                    removal_reason = :reason
                WHERE id = :lid
                  AND evidence_id = :eid
                  AND organization_id = :org
                  AND removed_at IS NULL
                RETURNING id, target_type, target_id
                """
            ),
            {
                "lid": link_id,
                "eid": evidence_id,
                "org": ctx.organization_id,
                "uid": ctx.principal.user_id,
                "reason": (removal_reason or "").strip() or None,
            },
        ).first()
        if removed is None:
            raise AppError("not_found", "Evidence link not found", status_code=404)
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="evidence.unlink",
            resource_type="evidence",
            resource_id=evidence_id,
            metadata={
                "link_id": str(link_id),
                "target_type": removed.target_type,
                "target_id": str(removed.target_id),
                "removal_reason": (removal_reason or "").strip() or None,
            },
        )
        conn.commit()
