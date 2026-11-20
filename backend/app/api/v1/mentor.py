"""Authenticated Socratic AI Mentor & ML Error Diagnosis API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.v1.deps import (
    get_current_user,
    get_problem_repository,
    get_socratic_mentor_service,
)
from app.core.errors import AppError
from app.repositories.identity import UserRecord
from app.repositories.problems import ProblemRepository
from app.schemas.mentor import (
    MentorSessionCreateRequest,
    MentorSessionDetail,
    MentorTurnCreateRequest,
    MLDiagnosisResponse,
)
from app.services.mentor.socratic_agent import SocraticMentorService

mentor_router = APIRouter(prefix="/mentor", tags=["AI Mentor"])


@mentor_router.post(
    "/sessions",
    response_model=MentorSessionDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Start or resume a Socratic AI Mentor session for a problem",
)
async def create_or_resume_mentor_session(
    payload: MentorSessionCreateRequest,
    current_user: UserRecord = Depends(get_current_user),
    service: SocraticMentorService = Depends(get_socratic_mentor_service),
) -> MentorSessionDetail:
    return await service.start_or_get_session(user=current_user, payload=payload)


@mentor_router.get(
    "/sessions/{session_id}",
    response_model=MentorSessionDetail,
    summary="Fetch a student's own Socratic AI Mentor session with diagnosis and citations",
)
async def get_mentor_session(
    session_id: UUID,
    current_user: UserRecord = Depends(get_current_user),
    service: SocraticMentorService = Depends(get_socratic_mentor_service),
) -> MentorSessionDetail:
    return await service.get_session(user=current_user, session_id=session_id)


@mentor_router.post(
    "/sessions/{session_id}/turns",
    response_model=MentorSessionDetail,
    summary="Submit a diagnose, respond, or progressive hint request turn to the AI Mentor",
)
async def create_mentor_turn(
    session_id: UUID,
    payload: MentorTurnCreateRequest,
    current_user: UserRecord = Depends(get_current_user),
    service: SocraticMentorService = Depends(get_socratic_mentor_service),
) -> MentorSessionDetail:
    return await service.process_turn(
        user=current_user,
        session_id=session_id,
        payload=payload,
    )


@mentor_router.post(
    "/diagnose/{submission_id}",
    response_model=MLDiagnosisResponse,
    summary="Run our trained ML error classifier on a student's real Judge0 submission",
)
async def diagnose_submission_endpoint(
    submission_id: UUID,
    current_user: UserRecord = Depends(get_current_user),
    problem_repo: ProblemRepository = Depends(get_problem_repository),
    service: SocraticMentorService = Depends(get_socratic_mentor_service),
) -> MLDiagnosisResponse:
    submission = await problem_repo.get_submission_by_id(submission_id)
    if submission is None:
        raise AppError(
            code="SUBMISSION_NOT_FOUND",
            message="Submission not found.",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    if submission.student_id != current_user.id and "admin" not in current_user.roles:
        raise AppError(
            code="FORBIDDEN",
            message="You cannot diagnose another student's submission.",
            status_code=status.HTTP_403_FORBIDDEN,
        )
    _, diagnosis = await service.diagnose_submission(user=current_user, submission=submission)
    return diagnosis
