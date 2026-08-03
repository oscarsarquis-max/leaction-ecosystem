"""Interview + Answer collection — editable only while assessment is in_progress
and interview status is planned.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.audit import write_audit
from app.auth.context import OrgContext
from app.db import tenant_connection
from app.errors import AppError
from app.modules.interviews.schemas import (
    AnswerCreate,
    AnswerOut,
    AnswerUpdate,
    InterviewCreate,
    InterviewOut,
    InterviewTransitionResult,
    QuestionOut,
)
from app.modules.orgs.service import require_role

_MUTATE_ROLES = ("org_admin", "consultant_auditor", "quality_manager")
_READ_ROLES = _MUTATE_ROLES + ("process_owner", "reader")
_FIELD_EDITABLE_ASSESSMENT = frozenset({"in_progress"})


def _interview_out(row) -> InterviewOut:
    return InterviewOut(
        id=row.id,
        organization_id=row.organization_id,
        assessment_id=row.assessment_id,
        conducted_at=row.conducted_at,
        mode=row.mode,
        status=row.status,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _answer_out(row) -> AnswerOut:
    return AnswerOut(
        id=row.id,
        organization_id=row.organization_id,
        interview_id=row.interview_id,
        question_id=row.question_id,
        criterion_id=row.criterion_id,
        body=row.body,
        author_membership_id=row.author_membership_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _lock_assessment(conn: Connection, org_id: UUID, assessment_id: UUID):
    row = conn.execute(
        text(
            """
            SELECT id, status, assessment_model_id
            FROM assessments
            WHERE id = :id AND organization_id = :org
            FOR UPDATE
            """
        ),
        {"id": assessment_id, "org": org_id},
    ).first()
    if row is None:
        raise AppError("not_found", "Assessment not found", status_code=404)
    return row


def _lock_interview(conn: Connection, org_id: UUID, interview_id: UUID):
    row = conn.execute(
        text(
            """
            SELECT i.id, i.organization_id, i.assessment_id, i.conducted_at, i.mode,
                   i.status, i.created_at, i.updated_at, a.status AS assessment_status
            FROM interviews i
            JOIN assessments a
              ON a.id = i.assessment_id AND a.organization_id = i.organization_id
            WHERE i.id = :id AND i.organization_id = :org
            FOR UPDATE OF i
            """
        ),
        {"id": interview_id, "org": org_id},
    ).first()
    if row is None:
        raise AppError("not_found", "Interview not found", status_code=404)
    return row


def _assert_field_collecting(assessment_status: str) -> None:
    if assessment_status not in _FIELD_EDITABLE_ASSESSMENT:
        raise AppError(
            "interview_phase_closed",
            f"Interview edits require assessment in_progress (current={assessment_status})",
            status_code=409,
        )


def _assert_interview_editable(interview_status: str, assessment_status: str) -> None:
    _assert_field_collecting(assessment_status)
    if interview_status != "planned":
        raise AppError(
            "interview_locked",
            f"Interview is not editable (status={interview_status})",
            status_code=409,
        )


def list_assessment_questions(ctx: OrgContext, assessment_id: UUID) -> list[QuestionOut]:
    require_role(ctx, *_READ_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        assess = conn.execute(
            text(
                """
                SELECT assessment_model_id FROM assessments
                WHERE id = :id AND organization_id = :org
                """
            ),
            {"id": assessment_id, "org": ctx.organization_id},
        ).first()
        if assess is None:
            raise AppError("not_found", "Assessment not found", status_code=404)
        rows = conn.execute(
            text(
                """
                SELECT id, assessment_model_id, criterion_id, code, prompt_text, sort_order
                FROM questions
                WHERE assessment_model_id = :mid
                ORDER BY sort_order, code
                """
            ),
            {"mid": assess.assessment_model_id},
        ).all()
    return [
        QuestionOut(
            id=r.id,
            assessment_model_id=r.assessment_model_id,
            criterion_id=r.criterion_id,
            code=r.code,
            prompt_text=r.prompt_text,
            sort_order=r.sort_order,
        )
        for r in rows
    ]


def create_interview(
    ctx: OrgContext, assessment_id: UUID, payload: InterviewCreate
) -> InterviewOut:
    require_role(ctx, *_MUTATE_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        assess = _lock_assessment(conn, ctx.organization_id, assessment_id)
        _assert_field_collecting(assess.status)
        row = conn.execute(
            text(
                """
                INSERT INTO interviews (
                  organization_id, assessment_id, conducted_at, mode, status
                ) VALUES (
                  :org, :assess, :conducted, :mode, 'planned'
                )
                RETURNING id, organization_id, assessment_id, conducted_at, mode,
                          status, created_at, updated_at
                """
            ),
            {
                "org": ctx.organization_id,
                "assess": assessment_id,
                "conducted": payload.conducted_at,
                "mode": payload.mode.value if payload.mode else None,
            },
        ).one()
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="interview.create",
            resource_type="interview",
            resource_id=row.id,
            to_status="planned",
            metadata={"assessment_id": str(assessment_id)},
        )
        conn.commit()
    return _interview_out(row)


def list_interviews(ctx: OrgContext, assessment_id: UUID) -> list[InterviewOut]:
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
                """
                SELECT id, organization_id, assessment_id, conducted_at, mode,
                       status, created_at, updated_at
                FROM interviews
                WHERE assessment_id = :aid AND organization_id = :org
                ORDER BY created_at
                """
            ),
            {"aid": assessment_id, "org": ctx.organization_id},
        ).all()
    return [_interview_out(r) for r in rows]


def get_interview(ctx: OrgContext, interview_id: UUID) -> InterviewOut:
    require_role(ctx, *_READ_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        row = conn.execute(
            text(
                """
                SELECT id, organization_id, assessment_id, conducted_at, mode,
                       status, created_at, updated_at
                FROM interviews
                WHERE id = :id AND organization_id = :org
                """
            ),
            {"id": interview_id, "org": ctx.organization_id},
        ).first()
        if row is None:
            raise AppError("not_found", "Interview not found", status_code=404)
    return _interview_out(row)


def complete_interview(ctx: OrgContext, interview_id: UUID) -> InterviewTransitionResult:
    require_role(ctx, *_MUTATE_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        row = _lock_interview(conn, ctx.organization_id, interview_id)
        _assert_field_collecting(row.assessment_status)
        if row.status != "planned":
            raise AppError(
                "invalid_transition",
                f"complete requires planned (current={row.status})",
                status_code=409,
            )
        updated = conn.execute(
            text(
                """
                UPDATE interviews
                SET status = 'completed',
                    conducted_at = COALESCE(conducted_at, now()),
                    updated_at = now()
                WHERE id = :id AND organization_id = :org AND status = 'planned'
                RETURNING id, organization_id, assessment_id, conducted_at, mode,
                          status, created_at, updated_at
                """
            ),
            {"id": interview_id, "org": ctx.organization_id},
        ).first()
        if updated is None:
            raise AppError("invalid_transition", "Interview complete race", status_code=409)
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="interview.complete",
            resource_type="interview",
            resource_id=interview_id,
            from_status="planned",
            to_status="completed",
        )
        conn.commit()
    return InterviewTransitionResult(
        interview=_interview_out(updated),
        from_status="planned",
        to_status="completed",
        event="complete",
    )


def cancel_interview(ctx: OrgContext, interview_id: UUID) -> InterviewTransitionResult:
    require_role(ctx, *_MUTATE_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        row = _lock_interview(conn, ctx.organization_id, interview_id)
        _assert_field_collecting(row.assessment_status)
        if row.status != "planned":
            raise AppError(
                "invalid_transition",
                f"cancel requires planned (current={row.status})",
                status_code=409,
            )
        updated = conn.execute(
            text(
                """
                UPDATE interviews
                SET status = 'cancelled', updated_at = now()
                WHERE id = :id AND organization_id = :org AND status = 'planned'
                RETURNING id, organization_id, assessment_id, conducted_at, mode,
                          status, created_at, updated_at
                """
            ),
            {"id": interview_id, "org": ctx.organization_id},
        ).first()
        if updated is None:
            raise AppError("invalid_transition", "Interview cancel race", status_code=409)
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="interview.cancel",
            resource_type="interview",
            resource_id=interview_id,
            from_status="planned",
            to_status="cancelled",
        )
        conn.commit()
    return InterviewTransitionResult(
        interview=_interview_out(updated),
        from_status="planned",
        to_status="cancelled",
        event="cancel",
    )


def _validate_answer_refs(
    conn: Connection,
    org_id: UUID,
    assessment_id: UUID,
    question_id: UUID | None,
    criterion_id: UUID | None,
) -> None:
    if question_id is not None:
        q = conn.execute(
            text(
                """
                SELECT q.id
                FROM questions q
                JOIN assessments a ON a.assessment_model_id = q.assessment_model_id
                WHERE q.id = :qid
                  AND a.id = :aid
                  AND a.organization_id = :org
                """
            ),
            {"qid": question_id, "aid": assessment_id, "org": org_id},
        ).first()
        if q is None:
            raise AppError(
                "not_found",
                "Question not found for this assessment model",
                status_code=404,
            )
    if criterion_id is not None:
        c = conn.execute(
            text("SELECT id FROM criteria WHERE id = :id"),
            {"id": criterion_id},
        ).first()
        if c is None:
            raise AppError("not_found", "Criterion not found", status_code=404)


def create_answer(
    ctx: OrgContext, interview_id: UUID, payload: AnswerCreate
) -> AnswerOut:
    require_role(ctx, *_MUTATE_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        interview = _lock_interview(conn, ctx.organization_id, interview_id)
        _assert_interview_editable(interview.status, interview.assessment_status)
        _validate_answer_refs(
            conn,
            ctx.organization_id,
            interview.assessment_id,
            payload.question_id,
            payload.criterion_id,
        )
        row = conn.execute(
            text(
                """
                INSERT INTO answers (
                  organization_id, interview_id, question_id, criterion_id,
                  body, author_membership_id
                ) VALUES (
                  :org, :interview, :qid, :cid, :body, :author
                )
                RETURNING id, organization_id, interview_id, question_id, criterion_id,
                          body, author_membership_id, created_at, updated_at
                """
            ),
            {
                "org": ctx.organization_id,
                "interview": interview_id,
                "qid": payload.question_id,
                "cid": payload.criterion_id,
                "body": payload.body.strip(),
                "author": ctx.membership_id,
            },
        ).one()
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="answer.create",
            resource_type="answer",
            resource_id=row.id,
            metadata={"interview_id": str(interview_id)},
        )
        conn.commit()
    return _answer_out(row)


def list_answers(ctx: OrgContext, interview_id: UUID) -> list[AnswerOut]:
    require_role(ctx, *_READ_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        interview = conn.execute(
            text(
                "SELECT id FROM interviews WHERE id = :id AND organization_id = :org"
            ),
            {"id": interview_id, "org": ctx.organization_id},
        ).first()
        if interview is None:
            raise AppError("not_found", "Interview not found", status_code=404)
        rows = conn.execute(
            text(
                """
                SELECT id, organization_id, interview_id, question_id, criterion_id,
                       body, author_membership_id, created_at, updated_at
                FROM answers
                WHERE interview_id = :iid AND organization_id = :org
                ORDER BY created_at
                """
            ),
            {"iid": interview_id, "org": ctx.organization_id},
        ).all()
    return [_answer_out(r) for r in rows]


def update_answer(ctx: OrgContext, answer_id: UUID, payload: AnswerUpdate) -> AnswerOut:
    require_role(ctx, *_MUTATE_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        row = conn.execute(
            text(
                """
                SELECT a.id, a.interview_id, i.status AS interview_status,
                       ass.status AS assessment_status
                FROM answers a
                JOIN interviews i
                  ON i.id = a.interview_id AND i.organization_id = a.organization_id
                JOIN assessments ass
                  ON ass.id = i.assessment_id AND ass.organization_id = a.organization_id
                WHERE a.id = :id AND a.organization_id = :org
                FOR UPDATE OF a
                """
            ),
            {"id": answer_id, "org": ctx.organization_id},
        ).first()
        if row is None:
            raise AppError("not_found", "Answer not found", status_code=404)
        _assert_interview_editable(row.interview_status, row.assessment_status)
        updated = conn.execute(
            text(
                """
                UPDATE answers
                SET body = :body, updated_at = now()
                WHERE id = :id AND organization_id = :org
                RETURNING id, organization_id, interview_id, question_id, criterion_id,
                          body, author_membership_id, created_at, updated_at
                """
            ),
            {
                "id": answer_id,
                "org": ctx.organization_id,
                "body": payload.body.strip(),
            },
        ).one()
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="answer.update",
            resource_type="answer",
            resource_id=answer_id,
        )
        conn.commit()
    return _answer_out(updated)
