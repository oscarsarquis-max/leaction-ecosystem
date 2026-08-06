"""Typed guided_answer ↔ evidence links (Wizard provenance).

Does not create Findings. Future findings may consume these links after
human review + approved evidence + existing segregation rules.
"""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.auth.context import OrgContext
from app.db import tenant_connection
from app.errors import AppError
from app.modules.evidence.schemas import AuthorizeUploadIn, AuthorizeUploadOut
from app.modules.evidence import service as evidence_service
from app.modules.guided import catalog as catalog_mod
from app.modules.evidence.collection import assert_assessment_allows_collection
from app.modules.guided.evidence_status import (
    public_origin_label,
    public_situation,
    situation_bucket,
)
from app.modules.guided.schemas import (
    GuidedEvidenceLinkCreate,
    GuidedEvidenceLinkOut,
    GuidedEvidenceStatusOut,
    GuidedSessionOut,
)
from app.modules.orgs.service import require_role

logger = logging.getLogger(__name__)

_MUTATE_ROLES = ("org_admin", "consultant_auditor", "quality_manager")
_READ_ROLES = _MUTATE_ROLES + ("process_owner", "reader")


def _session_for_assessment(
    conn: Connection, org_id: UUID, assessment_id: UUID, *, for_update: bool = False
):
    sql = """
        SELECT id, organization_id, assessment_id, catalog_version, status,
               current_step, current_question_id, context, updated_at
        FROM guided_sessions
        WHERE assessment_id = :aid AND organization_id = :org
    """
    if for_update:
        sql += " FOR UPDATE"
    row = conn.execute(text(sql), {"aid": assessment_id, "org": org_id}).first()
    if row is None:
        raise AppError("not_found", "Sessão do roteiro não encontrada", status_code=404)
    return row


def _answer_row(
    conn: Connection,
    org_id: UUID,
    session_id: UUID,
    question_id: str,
    *,
    for_update: bool = False,
):
    sql = """
        SELECT id, organization_id, session_id, question_id, question_version,
               evidence_ids, evidence_mode, provide_later
        FROM guided_answers
        WHERE session_id = :sid AND organization_id = :org AND question_id = :qid
    """
    if for_update:
        sql += " FOR UPDATE"
    row = conn.execute(
        text(sql), {"sid": session_id, "org": org_id, "qid": question_id}
    ).first()
    if row is None:
        raise AppError(
            "not_found",
            "Resposta não encontrada — responda a pergunta antes de vincular evidência",
            status_code=404,
        )
    return row


def _link_row_to_out(row) -> GuidedEvidenceLinkOut:
    phase = getattr(row, "collected_phase", None)
    return GuidedEvidenceLinkOut(
        id=row.id,
        organization_id=row.organization_id,
        guided_session_id=row.guided_session_id,
        guided_answer_id=row.guided_answer_id,
        assessment_id=row.assessment_id,
        question_id=row.question_id,
        question_version=row.question_version,
        evidence_id=row.evidence_id,
        link_type=row.link_type,
        created_by=row.created_by_user_id,
        created_at=row.created_at,
        evidence_status=row.evidence_status,
        situation=public_situation(row.evidence_status),
        collected_phase=phase,
        collection_origin=public_origin_label(phase),
        content_type=row.content_type,
        byte_size=row.byte_size,
        file_name=row.file_name,
        evidence_updated_at=row.evidence_updated_at,
    )


_LINK_SELECT = """
    SELECT gae.id, gae.organization_id, gae.guided_session_id, gae.guided_answer_id,
           gae.assessment_id, gae.question_id, gae.question_version, gae.evidence_id,
           gae.link_type, gae.created_by_user_id, gae.created_at,
           ev.status AS evidence_status, ev.content_type, ev.byte_size,
           ev.collected_phase, ev.updated_at AS evidence_updated_at,
           COALESCE(
             NULLIF(regexp_replace(ev.storage_key, '^.*/', ''), ''),
             ev.content_type
           ) AS file_name
    FROM guided_answer_evidences gae
    JOIN evidences ev
      ON ev.id = gae.evidence_id
     AND ev.organization_id = gae.organization_id
"""


def list_links_for_answer(
    conn: Connection, org_id: UUID, answer_id: UUID
) -> list[GuidedEvidenceLinkOut]:
    rows = conn.execute(
        text(
            _LINK_SELECT
            + """
            WHERE gae.guided_answer_id = :aid AND gae.organization_id = :org
            ORDER BY gae.created_at ASC
            """
        ),
        {"aid": answer_id, "org": org_id},
    ).all()
    return [_link_row_to_out(r) for r in rows]


def list_links_for_session(
    conn: Connection, org_id: UUID, session_id: UUID
) -> dict[UUID, list[GuidedEvidenceLinkOut]]:
    rows = conn.execute(
        text(
            _LINK_SELECT
            + """
            WHERE gae.guided_session_id = :sid AND gae.organization_id = :org
            ORDER BY gae.created_at ASC
            """
        ),
        {"sid": session_id, "org": org_id},
    ).all()
    by_answer: dict[UUID, list[GuidedEvidenceLinkOut]] = {}
    for r in rows:
        by_answer.setdefault(r.guided_answer_id, []).append(_link_row_to_out(r))
    return by_answer


def _sync_evidence_ids_array(
    conn: Connection, org_id: UUID, answer_id: UUID
) -> list[UUID]:
    ids = [
        r.evidence_id
        for r in conn.execute(
            text(
                """
                SELECT evidence_id FROM guided_answer_evidences
                WHERE guided_answer_id = :aid AND organization_id = :org
                ORDER BY created_at ASC
                """
            ),
            {"aid": answer_id, "org": org_id},
        ).all()
    ]
    conn.execute(
        text(
            """
            UPDATE guided_answers
            SET evidence_ids = CAST(:eids AS uuid[]), updated_at = now()
            WHERE id = :aid AND organization_id = :org
            """
        ),
        {
            "aid": answer_id,
            "org": org_id,
            "eids": "{" + ",".join(str(x) for x in ids) + "}",
        },
    )
    return ids


def _insert_link(
    conn: Connection,
    *,
    org_id: UUID,
    session_id: UUID,
    answer_id: UUID,
    assessment_id: UUID,
    question_id: str,
    question_version: str,
    evidence_id: UUID,
    link_type: str,
    created_by: UUID | None,
) -> GuidedEvidenceLinkOut:
    ev = conn.execute(
        text(
            """
            SELECT id, assessment_id, status, content_type, byte_size, storage_key,
                   collected_phase, updated_at
            FROM evidences
            WHERE id = :eid AND organization_id = :org
            """
        ),
        {"eid": evidence_id, "org": org_id},
    ).first()
    if ev is None:
        raise AppError("not_found", "Evidência não encontrada", status_code=404)
    if ev.assessment_id != assessment_id:
        raise AppError("not_found", "Evidência não encontrada", status_code=404)

    dup = conn.execute(
        text(
            """
            SELECT 1 FROM guided_answer_evidences
            WHERE guided_answer_id = :aid AND evidence_id = :eid
            """
        ),
        {"aid": answer_id, "eid": evidence_id},
    ).first()
    if dup is not None:
        raise AppError(
            "conflict",
            "Evidência já vinculada a esta resposta",
            status_code=409,
        )

    row = conn.execute(
        text(
            """
            INSERT INTO guided_answer_evidences (
              organization_id, guided_session_id, guided_answer_id,
              assessment_id, question_id, question_version,
              evidence_id, link_type, created_by_user_id
            )
            VALUES (
              :org, :sid, :aid, :assess, :qid, :qver, :eid, :ltype, :uid
            )
            RETURNING id, organization_id, guided_session_id, guided_answer_id,
                      assessment_id, question_id, question_version, evidence_id,
                      link_type, created_by_user_id, created_at
            """
        ),
        {
            "org": org_id,
            "sid": session_id,
            "aid": answer_id,
            "assess": assessment_id,
            "qid": question_id,
            "qver": question_version,
            "eid": evidence_id,
            "ltype": link_type,
            "uid": created_by,
        },
    ).one()

    return GuidedEvidenceLinkOut(
        id=row.id,
        organization_id=row.organization_id,
        guided_session_id=row.guided_session_id,
        guided_answer_id=row.guided_answer_id,
        assessment_id=row.assessment_id,
        question_id=row.question_id,
        question_version=row.question_version,
        evidence_id=row.evidence_id,
        link_type=row.link_type,
        created_by=row.created_by_user_id,
        created_at=row.created_at,
        evidence_status=ev.status,
        situation=public_situation(ev.status),
        collected_phase=ev.collected_phase,
        collection_origin=public_origin_label(ev.collected_phase),
        content_type=ev.content_type,
        byte_size=ev.byte_size,
        file_name=(
            (ev.storage_key or "").rsplit("/", 1)[-1]
            if ev.storage_key
            else (ev.content_type or "evidência")
        ),
        evidence_updated_at=ev.updated_at,
    )


def sync_links_from_evidence_ids(
    conn: Connection,
    *,
    org_id: UUID,
    session_id: UUID,
    assessment_id: UUID,
    answer_id: UUID,
    question_id: str,
    question_version: str,
    evidence_ids: list[UUID],
    created_by: UUID | None,
    link_type: str = "link_existing",
) -> None:
    """Align typed links with a declared evidence_ids list (legacy upsert path)."""
    desired = list(dict.fromkeys(evidence_ids or []))
    existing = {
        r.evidence_id: r.id
        for r in conn.execute(
            text(
                """
                SELECT id, evidence_id FROM guided_answer_evidences
                WHERE guided_answer_id = :aid AND organization_id = :org
                """
            ),
            {"aid": answer_id, "org": org_id},
        ).all()
    }
    for eid in desired:
        if eid in existing:
            continue
        try:
            _insert_link(
                conn,
                org_id=org_id,
                session_id=session_id,
                answer_id=answer_id,
                assessment_id=assessment_id,
                question_id=question_id,
                question_version=question_version,
                evidence_id=eid,
                link_type=link_type if link_type in ("attach", "link_existing") else "link_existing",
                created_by=created_by,
            )
        except AppError as exc:
            if exc.status_code == 404:
                logger.warning(
                    "guided_evidence_sync_skip reason=invalid_evidence org=%s",
                    org_id,
                )
                continue
            raise
    for eid, link_id in existing.items():
        if eid not in desired:
            conn.execute(
                text(
                    """
                    DELETE FROM guided_answer_evidences
                    WHERE id = :id AND organization_id = :org
                    """
                ),
                {"id": link_id, "org": org_id},
            )
    _sync_evidence_ids_array(conn, org_id, answer_id)


def log_legacy_inconsistencies(
    conn: Connection, org_id: UUID, session_id: UUID
) -> None:
    """Count-only log when legacy evidence_ids diverge from typed links (no PII)."""
    row = conn.execute(
        text(
            """
            WITH legacy AS (
              SELECT ga.id AS answer_id, unnest(ga.evidence_ids) AS evidence_id
              FROM guided_answers ga
              WHERE ga.session_id = :sid AND ga.organization_id = :org
                AND cardinality(ga.evidence_ids) > 0
            ),
            linked AS (
              SELECT guided_answer_id AS answer_id, evidence_id
              FROM guided_answer_evidences
              WHERE guided_session_id = :sid AND organization_id = :org
            )
            SELECT
              (SELECT count(*) FROM legacy) AS legacy_n,
              (SELECT count(*) FROM linked) AS linked_n,
              (SELECT count(*) FROM legacy l
                 WHERE NOT EXISTS (
                   SELECT 1 FROM linked k
                   WHERE k.answer_id = l.answer_id AND k.evidence_id = l.evidence_id
                 )) AS orphan_legacy
            """
        ),
        {"sid": session_id, "org": org_id},
    ).one()
    if row.orphan_legacy and row.orphan_legacy > 0:
        logger.warning(
            "guided_evidence_legacy_inconsistency org=%s session=%s "
            "legacy=%s linked=%s orphan_legacy=%s",
            org_id,
            session_id,
            row.legacy_n,
            row.linked_n,
            row.orphan_legacy,
        )


def list_answer_evidences(
    ctx: OrgContext, assessment_id: UUID, question_id: str
) -> list[GuidedEvidenceLinkOut]:
    from app.modules.guided import service as guided_service

    require_role(ctx, *_READ_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        guided_service._assessment_row(conn, ctx.organization_id, assessment_id)
        session = _session_for_assessment(conn, ctx.organization_id, assessment_id)
        answer = _answer_row(conn, ctx.organization_id, session.id, question_id)
        out = list_links_for_answer(conn, ctx.organization_id, answer.id)
        conn.commit()
        return out


def link_existing(
    ctx: OrgContext,
    assessment_id: UUID,
    question_id: str,
    payload: GuidedEvidenceLinkCreate,
) -> GuidedSessionOut:
    from app.modules.guided import service as guided_service

    require_role(ctx, *_MUTATE_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        assess = guided_service._assessment_row(
            conn, ctx.organization_id, assessment_id
        )
        assert_assessment_allows_collection(assess.status)
        session = _session_for_assessment(
            conn, ctx.organization_id, assessment_id, for_update=True
        )
        answer = _answer_row(
            conn, ctx.organization_id, session.id, question_id, for_update=True
        )
        _insert_link(
            conn,
            org_id=ctx.organization_id,
            session_id=session.id,
            answer_id=answer.id,
            assessment_id=assessment_id,
            question_id=answer.question_id,
            question_version=answer.question_version,
            evidence_id=payload.evidence_id,
            link_type="link_existing",
            created_by=ctx.principal.user_id,
        )
        _sync_evidence_ids_array(conn, ctx.organization_id, answer.id)
        conn.execute(
            text(
                """
                UPDATE guided_answers
                SET evidence_mode = 'link_existing',
                    provide_later = false,
                    updated_at = now()
                WHERE id = :aid AND organization_id = :org
                """
            ),
            {"aid": answer.id, "org": ctx.organization_id},
        )
        # Reload unlocked session row for _session_out
        session = conn.execute(
            text(
                """
                SELECT id, organization_id, assessment_id, catalog_version, status,
                       current_step, current_question_id, context, updated_at
                FROM guided_sessions
                WHERE id = :id AND organization_id = :org
                """
            ),
            {"id": session.id, "org": ctx.organization_id},
        ).one()
        out = guided_service._session_out(conn, ctx.organization_id, session)
        conn.commit()
        return out


def unlink(
    ctx: OrgContext,
    assessment_id: UUID,
    question_id: str,
    evidence_id: UUID,
) -> GuidedSessionOut:
    from app.modules.guided import service as guided_service

    require_role(ctx, *_MUTATE_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        assess = guided_service._assessment_row(
            conn, ctx.organization_id, assessment_id
        )
        assert_assessment_allows_collection(assess.status)
        session = _session_for_assessment(
            conn, ctx.organization_id, assessment_id, for_update=True
        )
        answer = _answer_row(
            conn, ctx.organization_id, session.id, question_id, for_update=True
        )
        deleted = conn.execute(
            text(
                """
                DELETE FROM guided_answer_evidences
                WHERE guided_answer_id = :aid
                  AND evidence_id = :eid
                  AND organization_id = :org
                RETURNING id
                """
            ),
            {"aid": answer.id, "eid": evidence_id, "org": ctx.organization_id},
        ).first()
        if deleted is None:
            raise AppError("not_found", "Vínculo não encontrado", status_code=404)
        _sync_evidence_ids_array(conn, ctx.organization_id, answer.id)
        session = conn.execute(
            text(
                """
                SELECT id, organization_id, assessment_id, catalog_version, status,
                       current_step, current_question_id, context, updated_at
                FROM guided_sessions
                WHERE id = :id AND organization_id = :org
                """
            ),
            {"id": session.id, "org": ctx.organization_id},
        ).one()
        out = guided_service._session_out(conn, ctx.organization_id, session)
        conn.commit()
        return out


def authorize_for_question(
    ctx: OrgContext,
    assessment_id: UUID,
    question_id: str,
    payload: AuthorizeUploadIn,
) -> AuthorizeUploadOut:
    """Authorize upload via evidence vertical; assessment_id must match path."""
    from app.modules.guided import service as guided_service

    require_role(ctx, *_MUTATE_ROLES)
    if payload.assessment_id != assessment_id:
        raise AppError(
            "validation_error",
            "assessment_id do corpo deve coincidir com a avaliação da rota",
            status_code=422,
        )
    with tenant_connection(ctx.organization_id) as conn:
        assess = guided_service._assessment_row(
            conn, ctx.organization_id, assessment_id
        )
        assert_assessment_allows_collection(assess.status)
        session = _session_for_assessment(conn, ctx.organization_id, assessment_id)
        q = catalog_mod.get_question(question_id, session.catalog_version)
        if q is None:
            raise AppError(
                "not_found",
                "Pergunta não encontrada no catálogo desta sessão",
                status_code=404,
            )
        _answer_row(conn, ctx.organization_id, session.id, question_id)
        conn.commit()

    # Reuse existing S3/memory authorize → client PUT → receive.
    return evidence_service.authorize_upload(ctx, payload)


def complete_after_receive(
    ctx: OrgContext,
    assessment_id: UUID,
    question_id: str,
    evidence_id: UUID,
) -> GuidedSessionOut:
    """Create/confirm typed link after evidence receive (or later statuses)."""
    from app.modules.guided import service as guided_service

    require_role(ctx, *_MUTATE_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        assess = guided_service._assessment_row(
            conn, ctx.organization_id, assessment_id
        )
        assert_assessment_allows_collection(assess.status)
        session = _session_for_assessment(
            conn, ctx.organization_id, assessment_id, for_update=True
        )
        answer = _answer_row(
            conn, ctx.organization_id, session.id, question_id, for_update=True
        )
        ev = conn.execute(
            text(
                """
                SELECT id, assessment_id, status
                FROM evidences
                WHERE id = :eid AND organization_id = :org
                """
            ),
            {"eid": evidence_id, "org": ctx.organization_id},
        ).first()
        if ev is None or ev.assessment_id != assessment_id:
            raise AppError("not_found", "Evidência não encontrada", status_code=404)
        if ev.status == "upload_pending":
            raise AppError(
                "conflict",
                "Conclua o envio (receive) antes de confirmar o vínculo",
                status_code=409,
            )

        existing = conn.execute(
            text(
                """
                SELECT id FROM guided_answer_evidences
                WHERE guided_answer_id = :aid AND evidence_id = :eid
                  AND organization_id = :org
                """
            ),
            {"aid": answer.id, "eid": evidence_id, "org": ctx.organization_id},
        ).first()
        if existing is None:
            _insert_link(
                conn,
                org_id=ctx.organization_id,
                session_id=session.id,
                answer_id=answer.id,
                assessment_id=assessment_id,
                question_id=answer.question_id,
                question_version=answer.question_version,
                evidence_id=evidence_id,
                link_type="attach",
                created_by=ctx.principal.user_id,
            )
        _sync_evidence_ids_array(conn, ctx.organization_id, answer.id)
        conn.execute(
            text(
                """
                UPDATE guided_answers
                SET evidence_mode = 'attach',
                    provide_later = false,
                    updated_at = now()
                WHERE id = :aid AND organization_id = :org
                """
            ),
            {"aid": answer.id, "org": ctx.organization_id},
        )
        session = conn.execute(
            text(
                """
                SELECT id, organization_id, assessment_id, catalog_version, status,
                       current_step, current_question_id, context, updated_at
                FROM guided_sessions
                WHERE id = :id AND organization_id = :org
                """
            ),
            {"id": session.id, "org": ctx.organization_id},
        ).one()
        out = guided_service._session_out(conn, ctx.organization_id, session)
        conn.commit()
        return out


def answer_evidence_status(
    ctx: OrgContext, assessment_id: UUID, question_id: str
) -> GuidedEvidenceStatusOut:
    from app.modules.guided import service as guided_service

    require_role(ctx, *_READ_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        guided_service._assessment_row(conn, ctx.organization_id, assessment_id)
        session = _session_for_assessment(conn, ctx.organization_id, assessment_id)
        answer = _answer_row(conn, ctx.organization_id, session.id, question_id)
        links = list_links_for_answer(conn, ctx.organization_id, answer.id)
        buckets = {
            "related": len(links),
            "awaiting_upload": 0,
            "processing": 0,
            "approved": 0,
            "rejected": 0,
            "promised_later": 1 if answer.provide_later else 0,
        }
        for link in links:
            b = situation_bucket(link.evidence_status)
            if b in buckets:
                buckets[b] += 1
        conn.commit()
        return GuidedEvidenceStatusOut(
            question_id=question_id,
            provide_later=bool(answer.provide_later),
            related=buckets["related"],
            awaiting_upload=buckets["awaiting_upload"],
            processing=buckets["processing"],
            approved=buckets["approved"],
            rejected=buckets["rejected"],
            promised_later=buckets["promised_later"],
            links=links,
        )
