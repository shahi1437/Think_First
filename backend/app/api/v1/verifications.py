"""Authenticated Independent Understanding Verification & Learning Events API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.v1.deps import get_current_user, get_verification_service
from app.repositories.identity import UserRecord
from app.schemas.mentor import (
    LearningEventView,
    TransferChallengeSummary,
    VerificationAttemptSubmitRequest,
    VerificationAttemptView,
)
from app.services.verification.service import VerificationService

verifications_router = APIRouter(prefix="/verifications", tags=["Independent Verification"])
learning_router = APIRouter(prefix="/learning", tags=["Learning Evidence"])


@verifications_router.get(
    "/problem/{source_problem_id}",
    response_model=TransferChallengeSummary | None,
    summary="Get linked unseen transfer challenge and unlock status for a debugging problem",
)
async def get_transfer_challenge_for_problem(
    source_problem_id: UUID,
    current_user: UserRecord = Depends(get_current_user),
    service: VerificationService = Depends(get_verification_service),
) -> TransferChallengeSummary | None:
    return await service.get_transfer_for_source_problem(
        user=current_user,
        source_problem_id=source_problem_id,
    )


@verifications_router.post(
    "/{verification_link_id}/attempts",
    response_model=VerificationAttemptView,
    status_code=status.HTTP_201_CREATED,
    summary="Submit an independent unseen transfer challenge attempt evaluated via real Judge0",
)
async def submit_transfer_verification_attempt(
    verification_link_id: UUID,
    payload: VerificationAttemptSubmitRequest,
    current_user: UserRecord = Depends(get_current_user),
    service: VerificationService = Depends(get_verification_service),
) -> VerificationAttemptView:
    return await service.submit_transfer_attempt(
        user=current_user,
        verification_link_id=verification_link_id,
        payload=payload,
    )


@verifications_router.get(
    "/attempts",
    response_model=list[VerificationAttemptView],
    summary="List the authenticated student's persisted transfer verification attempts",
)
async def list_my_verification_attempts(
    verification_link_id: UUID | None = Query(default=None),
    current_user: UserRecord = Depends(get_current_user),
    service: VerificationService = Depends(get_verification_service),
) -> list[VerificationAttemptView]:
    return await service.list_my_attempts(
        user=current_user,
        verification_link_id=verification_link_id,
    )


@learning_router.get(
    "/events",
    response_model=list[LearningEventView],
    summary="List the authenticated student's traceable Phase 4 learning events",
)
async def list_my_learning_events(
    limit: int = Query(default=30, ge=1, le=100),
    current_user: UserRecord = Depends(get_current_user),
    service: VerificationService = Depends(get_verification_service),
) -> list[LearningEventView]:
    return await service.list_my_learning_events(user=current_user, limit=limit)
