"""Guided Assessment Wizard — persist session/answers under tenant RLS."""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from sqlalchemy import text

from app.auth.context import OrgContext
from app.db import tenant_connection
from app.errors import AppError
from app.modules.guided import catalog as catalog_mod
from app.modules.guided.catalog import UnknownCatalogVersion
from app.modules.guided.show_when import visible_questions
from app.modules.guided.schemas import (
    GuidedAnswerOut,
    GuidedAnswerUpsert,
    GuidedContextPatch,
    GuidedPositionPatch,
    GuidedSessionOut,
    GuidedStep,
)
from app.modules.orgs.service import require_role

_MUTATE_ROLES = ("org_admin", "consultant_auditor", "quality_manager")
_READ_ROLES = _MUTATE_ROLES + ("process_owner", "reader")
_EDITABLE_ASSESSMENT = frozenset({"draft", "planned", "in_progress"})
_LEGACY_CATALOG = "iso9001-2015-c4c5-v1"


def _empty_context() -> dict[str, Any]:
    return {
        "organization_profile": {"trade_name": "", "summary": "", "size_band": ""},
        "qms_scope": {"description": "", "exclusions": "", "exclusion_justification": ""},
        "products_services": [],
        "sites": [],
        "processes": [],
        "stakeholders": [],
    }


def _assessment_row(conn, org_id: UUID, assessment_id: UUID):
    row = conn.execute(
        text(
            """
            SELECT id, organization_id, status
            FROM assessments
            WHERE id = :id AND organization_id = :org
            FOR UPDATE
            """
        ),
        {"id": assessment_id, "org": org_id},
    ).first()
    if row is None:
        raise AppError("not_found", "Avaliação não encontrada", status_code=404)
    return row


def _answers(conn, org_id: UUID, session_id: UUID) -> list[GuidedAnswerOut]:
    rows = conn.execute(
        text(
            """
            SELECT question_id, question_version, answer_value, description,
                   na_justification, evidence_mode, evidence_ids, evidence_note,
                   provide_later, updated_at
            FROM guided_answers
            WHERE session_id = :sid AND organization_id = :org
            ORDER BY question_id
            """
        ),
        {"sid": session_id, "org": org_id},
    ).all()
    out: list[GuidedAnswerOut] = []
    for r in rows:
        out.append(
            GuidedAnswerOut(
                question_id=r.question_id,
                question_version=r.question_version,
                answer_value=r.answer_value,
                description=r.description or "",
                na_justification=r.na_justification or "",
                evidence_mode=r.evidence_mode or "none",
                evidence_ids=list(r.evidence_ids or []),
                evidence_note=r.evidence_note or "",
                provide_later=bool(r.provide_later),
                updated_at=r.updated_at,
            )
        )
    return out


def _questions_for_session(catalog_version: str) -> list[dict[str, Any]]:
    try:
        return catalog_mod.list_questions(catalog_version)
    except UnknownCatalogVersion as exc:
        raise AppError(
            "conflict",
            f"Catálogo da sessão não está disponível: {catalog_version}",
            status_code=409,
        ) from exc


def _session_out(conn, org_id: UUID, session_row) -> GuidedSessionOut:
    answers = _answers(conn, org_id, session_row.id)
    ctx = session_row.context
    if isinstance(ctx, str):
        ctx = json.loads(ctx)
    ctx = ctx or _empty_context()
    visible = visible_questions(
        _questions_for_session(session_row.catalog_version),
        answers,
        ctx,
    )
    visible_ids = {q["id"] for q in visible}
    qcount = len(visible)
    answered = sum(
        1
        for a in answers
        if a.answer_value is not None and a.question_id in visible_ids
    )
    return GuidedSessionOut(
        id=session_row.id,
        assessment_id=session_row.assessment_id,
        organization_id=session_row.organization_id,
        catalog_version=session_row.catalog_version,
        status=session_row.status,
        current_step=session_row.current_step,
        current_question_id=session_row.current_question_id,
        context=ctx,
        answers=answers,
        answered_count=answered,
        question_count=qcount,
        updated_at=session_row.updated_at,
    )


def _maybe_migrate_draft_session(conn, assessment, session_row):
    """
    Upgrade legacy c4c5 → latest only when safe:
    assessment still draft AND session has zero answers.
    """
    if assessment.status != "draft":
        return session_row
    if session_row.catalog_version != _LEGACY_CATALOG:
        return session_row
    latest = catalog_mod.catalog_version()
    if session_row.catalog_version == latest:
        return session_row

    n_answers = conn.execute(
        text(
            """
            SELECT count(*)::int AS n
            FROM guided_answers
            WHERE session_id = :sid AND organization_id = :org
            """
        ),
        {"sid": session_row.id, "org": session_row.organization_id},
    ).one().n
    if n_answers > 0:
        return session_row

    return conn.execute(
        text(
            """
            UPDATE guided_sessions
            SET catalog_version = :cat, updated_at = now()
            WHERE id = :id AND organization_id = :org
            RETURNING id, organization_id, assessment_id, catalog_version, status,
                      current_step, current_question_id, context, updated_at
            """
        ),
        {
            "cat": latest,
            "id": session_row.id,
            "org": session_row.organization_id,
        },
    ).one()


def get_or_create_session(ctx: OrgContext, assessment_id: UUID) -> GuidedSessionOut:
    require_role(ctx, *_READ_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        assessment = _assessment_row(conn, ctx.organization_id, assessment_id)
        if assessment.status not in _EDITABLE_ASSESSMENT | {"analysis", "actions", "report", "closed"}:
            raise AppError("conflict", "Avaliação não disponível para o roteiro guiado", status_code=409)

        row = conn.execute(
            text(
                """
                SELECT id, organization_id, assessment_id, catalog_version, status,
                       current_step, current_question_id, context, updated_at
                FROM guided_sessions
                WHERE assessment_id = :aid AND organization_id = :org
                """
            ),
            {"aid": assessment_id, "org": ctx.organization_id},
        ).first()

        if row is None:
            if assessment.status not in _EDITABLE_ASSESSMENT:
                # Sem sessão: leitura vazia (dashboard/mapa) — não cria fora de draft/planned/in_progress.
                raise AppError(
                    "not_found",
                    "Roteiro guiado ainda não iniciado nesta avaliação",
                    status_code=404,
                )
            require_role(ctx, *_MUTATE_ROLES)
            row = conn.execute(
                text(
                    """
                    INSERT INTO guided_sessions (
                      organization_id, assessment_id, catalog_version, status,
                      current_step, context, created_by_user_id
                    )
                    VALUES (
                      :org, :aid, :cat, 'in_progress', 'organization',
                      CAST(:ctx AS jsonb), :uid
                    )
                    RETURNING id, organization_id, assessment_id, catalog_version, status,
                              current_step, current_question_id, context, updated_at
                    """
                ),
                {
                    "org": ctx.organization_id,
                    "aid": assessment_id,
                    "cat": catalog_mod.catalog_version(),
                    "ctx": json.dumps(_empty_context()),
                    "uid": ctx.principal.user_id,
                },
            ).one()
        else:
            row = _maybe_migrate_draft_session(conn, assessment, row)

        out = _session_out(conn, ctx.organization_id, row)
        conn.commit()
        return out


def patch_context(ctx: OrgContext, assessment_id: UUID, payload: GuidedContextPatch) -> GuidedSessionOut:
    require_role(ctx, *_MUTATE_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        _assessment_row(conn, ctx.organization_id, assessment_id)
        session = conn.execute(
            text(
                """
                SELECT id, organization_id, assessment_id, catalog_version, status,
                       current_step, current_question_id, context, updated_at
                FROM guided_sessions
                WHERE assessment_id = :aid AND organization_id = :org
                FOR UPDATE
                """
            ),
            {"aid": assessment_id, "org": ctx.organization_id},
        ).first()
        if session is None:
            raise AppError("not_found", "Sessão do roteiro não encontrada", status_code=404)

        ctx_data = session.context
        if isinstance(ctx_data, str):
            ctx_data = json.loads(ctx_data)
        if payload.context is not None:
            merged = {**(ctx_data or {}), **payload.context}
            ctx_data = merged

        step = payload.current_step or session.current_step
        qid = (
            payload.current_question_id
            if payload.current_question_id is not None
            else session.current_question_id
        )
        status = session.status
        if step == "review":
            status = "review"

        row = conn.execute(
            text(
                """
                UPDATE guided_sessions
                SET context = CAST(:ctx AS jsonb),
                    current_step = :step,
                    current_question_id = :qid,
                    status = :status,
                    updated_at = now()
                WHERE id = :id AND organization_id = :org
                RETURNING id, organization_id, assessment_id, catalog_version, status,
                          current_step, current_question_id, context, updated_at
                """
            ),
            {
                "ctx": json.dumps(ctx_data or _empty_context()),
                "step": step,
                "qid": qid,
                "status": status,
                "id": session.id,
                "org": ctx.organization_id,
            },
        ).one()
        out = _session_out(conn, ctx.organization_id, row)
        conn.commit()
        return out


def patch_position(
    ctx: OrgContext, assessment_id: UUID, payload: GuidedPositionPatch
) -> GuidedSessionOut:
    return patch_context(
        ctx,
        assessment_id,
        GuidedContextPatch(
            current_step=payload.current_step,
            current_question_id=payload.current_question_id,
        ),
    )


def upsert_answer(
    ctx: OrgContext, assessment_id: UUID, question_id: str, payload: GuidedAnswerUpsert
) -> GuidedSessionOut:
    require_role(ctx, *_MUTATE_ROLES)

    with tenant_connection(ctx.organization_id) as conn:
        _assessment_row(conn, ctx.organization_id, assessment_id)
        session = conn.execute(
            text(
                """
                SELECT id, catalog_version FROM guided_sessions
                WHERE assessment_id = :aid AND organization_id = :org
                FOR UPDATE
                """
            ),
            {"aid": assessment_id, "org": ctx.organization_id},
        ).first()
        if session is None:
            raise AppError("not_found", "Sessão do roteiro não encontrada", status_code=404)

        q = catalog_mod.get_question(question_id, session.catalog_version)
        if q is None:
            raise AppError(
                "not_found",
                "Pergunta não encontrada no catálogo desta sessão",
                status_code=404,
            )
        if payload.answer_value == "not_applicable" and not (
            payload.na_justification or ""
        ).strip():
            raise AppError(
                "validation_error",
                "Justificativa obrigatória quando a resposta é não aplicável",
                status_code=422,
            )

        conn.execute(
            text(
                """
                INSERT INTO guided_answers (
                  organization_id, session_id, question_id, question_version,
                  answer_value, description, na_justification, evidence_mode,
                  evidence_ids, evidence_note, provide_later
                )
                VALUES (
                  :org, :sid, :qid, :qver, :aval, :desc, :naj, :emode,
                  CAST(:eids AS uuid[]), :enote, :later
                )
                ON CONFLICT (session_id, question_id) DO UPDATE SET
                  question_version = EXCLUDED.question_version,
                  answer_value = EXCLUDED.answer_value,
                  description = EXCLUDED.description,
                  na_justification = EXCLUDED.na_justification,
                  evidence_mode = EXCLUDED.evidence_mode,
                  evidence_ids = EXCLUDED.evidence_ids,
                  evidence_note = EXCLUDED.evidence_note,
                  provide_later = EXCLUDED.provide_later,
                  updated_at = now()
                """
            ),
            {
                "org": ctx.organization_id,
                "sid": session.id,
                "qid": question_id,
                "qver": payload.question_version or q["version"],
                "aval": payload.answer_value,
                "desc": payload.description or "",
                "naj": payload.na_justification or "",
                "emode": payload.evidence_mode or "none",
                "eids": "{"
                + ",".join(str(x) for x in (payload.evidence_ids or []))
                + "}",
                "enote": payload.evidence_note or "",
                "later": bool(payload.provide_later),
            },
        )
        # Advance position to this question when answering in route
        row = conn.execute(
            text(
                """
                UPDATE guided_sessions
                SET current_step = 'route',
                    current_question_id = :qid,
                    updated_at = now()
                WHERE id = :sid AND organization_id = :org
                RETURNING id, organization_id, assessment_id, catalog_version, status,
                          current_step, current_question_id, context, updated_at
                """
            ),
            {"qid": question_id, "sid": session.id, "org": ctx.organization_id},
        ).one()
        out = _session_out(conn, ctx.organization_id, row)
        conn.commit()
        return out


def get_catalog(version: str | None = None) -> dict[str, Any]:
    try:
        return catalog_mod.load_catalog(version)
    except UnknownCatalogVersion as exc:
        raise AppError(
            "not_found",
            f"Catálogo não encontrado: {exc.args[0]}",
            status_code=404,
        ) from exc
