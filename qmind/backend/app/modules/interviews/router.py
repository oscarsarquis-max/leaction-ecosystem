"""Interview + Answer HTTP surface."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from app.auth.deps import OrgContextDep
from app.modules.interviews import service
from app.modules.interviews.schemas import (
    AnswerCreate,
    AnswerOut,
    AnswerUpdate,
    InterviewCreate,
    InterviewOut,
    InterviewTransitionResult,
    InterviewUpdate,
    QuestionOut,
)
from app.schemas.common import ERROR_RESPONSES, IdempotencyKeyHeader

router = APIRouter(tags=["Interviews"])


@router.get(
    "/assessments/{assessment_id}/questions",
    response_model=list[QuestionOut],
    operation_id="listAssessmentQuestions",
    responses={404: ERROR_RESPONSES[404]},
)
def list_assessment_questions(
    assessment_id: UUID,
    ctx: OrgContextDep,
) -> list[QuestionOut]:
    return service.list_assessment_questions(ctx, assessment_id)


@router.post(
    "/assessments/{assessment_id}/interviews",
    response_model=InterviewOut,
    status_code=201,
    operation_id="createInterview",
    responses={404: ERROR_RESPONSES[404], 409: ERROR_RESPONSES[409]},
)
def create_interview(
    assessment_id: UUID,
    payload: InterviewCreate,
    ctx: OrgContextDep,
    _idempotency_key: IdempotencyKeyHeader = None,
) -> InterviewOut:
    return service.create_interview(ctx, assessment_id, payload)


@router.get(
    "/assessments/{assessment_id}/interviews",
    response_model=list[InterviewOut],
    operation_id="listAssessmentInterviews",
    responses={404: ERROR_RESPONSES[404]},
)
def list_interviews(
    assessment_id: UUID,
    ctx: OrgContextDep,
) -> list[InterviewOut]:
    return service.list_interviews(ctx, assessment_id)


@router.get(
    "/interviews/{interview_id}",
    response_model=InterviewOut,
    operation_id="getInterview",
    responses={404: ERROR_RESPONSES[404]},
)
def get_interview(interview_id: UUID, ctx: OrgContextDep) -> InterviewOut:
    return service.get_interview(ctx, interview_id)


@router.patch(
    "/interviews/{interview_id}",
    response_model=InterviewOut,
    operation_id="updateInterview",
    responses={404: ERROR_RESPONSES[404], 409: ERROR_RESPONSES[409]},
)
def update_interview(
    interview_id: UUID,
    payload: InterviewUpdate,
    ctx: OrgContextDep,
    _idempotency_key: IdempotencyKeyHeader = None,
) -> InterviewOut:
    return service.update_interview(ctx, interview_id, payload)


@router.post(
    "/interviews/{interview_id}/confirm",
    response_model=InterviewTransitionResult,
    operation_id="confirmInterview",
    responses={404: ERROR_RESPONSES[404], 409: ERROR_RESPONSES[409]},
)
def confirm_interview(
    interview_id: UUID, ctx: OrgContextDep
) -> InterviewTransitionResult:
    return service.confirm_interview(ctx, interview_id)


@router.post(
    "/interviews/{interview_id}/start",
    response_model=InterviewTransitionResult,
    operation_id="startInterview",
    responses={404: ERROR_RESPONSES[404], 409: ERROR_RESPONSES[409]},
)
def start_interview(
    interview_id: UUID, ctx: OrgContextDep
) -> InterviewTransitionResult:
    return service.start_interview(ctx, interview_id)


@router.post(
    "/interviews/{interview_id}/complete",
    response_model=InterviewTransitionResult,
    operation_id="completeInterview",
    responses={404: ERROR_RESPONSES[404], 409: ERROR_RESPONSES[409]},
)
def complete_interview(
    interview_id: UUID, ctx: OrgContextDep
) -> InterviewTransitionResult:
    return service.complete_interview(ctx, interview_id)


@router.post(
    "/interviews/{interview_id}/cancel",
    response_model=InterviewTransitionResult,
    operation_id="cancelInterview",
    responses={404: ERROR_RESPONSES[404], 409: ERROR_RESPONSES[409]},
)
def cancel_interview(
    interview_id: UUID, ctx: OrgContextDep
) -> InterviewTransitionResult:
    return service.cancel_interview(ctx, interview_id)


@router.post(
    "/interviews/{interview_id}/answers",
    response_model=AnswerOut,
    status_code=201,
    operation_id="createAnswer",
    responses={404: ERROR_RESPONSES[404], 409: ERROR_RESPONSES[409]},
)
def create_answer(
    interview_id: UUID,
    payload: AnswerCreate,
    ctx: OrgContextDep,
) -> AnswerOut:
    return service.create_answer(ctx, interview_id, payload)


@router.get(
    "/interviews/{interview_id}/answers",
    response_model=list[AnswerOut],
    operation_id="listInterviewAnswers",
    responses={404: ERROR_RESPONSES[404]},
)
def list_answers(interview_id: UUID, ctx: OrgContextDep) -> list[AnswerOut]:
    return service.list_answers(ctx, interview_id)


@router.patch(
    "/answers/{answer_id}",
    response_model=AnswerOut,
    operation_id="updateAnswer",
    responses={404: ERROR_RESPONSES[404], 409: ERROR_RESPONSES[409]},
)
def update_answer(
    answer_id: UUID,
    payload: AnswerUpdate,
    ctx: OrgContextDep,
) -> AnswerOut:
    return service.update_answer(ctx, answer_id, payload)
