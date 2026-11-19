from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.v1.deps import get_current_user, get_execution_service
from app.repositories.identity import UserRecord
from app.schemas.common import PaginatedResponse
from app.schemas.problems import (
    RevisionResponse,
    RevisionSaveRequest,
    SubmissionCreateRequest,
    SubmissionResponse,
    SubmissionSummaryItem,
)
from app.services.execution.service import ExecutionService

submissions_router = APIRouter(prefix="/submissions", tags=["Execution & Submissions"])
workspace_router = APIRouter(prefix="/workspace", tags=["Workspace Revisions"])


@submissions_router.post("", response_model=SubmissionResponse)
async def create_submission(
    payload: SubmissionCreateRequest,
    current_user: UserRecord = Depends(get_current_user),
    service: ExecutionService = Depends(get_execution_service),
) -> SubmissionResponse:
    """Run public tests (`run`) or evaluate public + hidden tests (`submit`) via Judge0."""
    return await service.execute_submission(user=current_user, payload=payload)


@submissions_router.get("", response_model=PaginatedResponse[SubmissionSummaryItem])
async def list_my_submissions(
    problem_id: UUID | None = Query(default=None),
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: UserRecord = Depends(get_current_user),
    service: ExecutionService = Depends(get_execution_service),
) -> PaginatedResponse[SubmissionSummaryItem]:
    """List the authenticated student's own submission history."""
    return await service.list_my_submissions(
        user=current_user,
        problem_id=problem_id,
        limit=limit,
        offset=offset,
    )


@submissions_router.get("/{submission_id}", response_model=SubmissionResponse)
async def get_submission(
    submission_id: UUID,
    current_user: UserRecord = Depends(get_current_user),
    service: ExecutionService = Depends(get_execution_service),
) -> SubmissionResponse:
    """Fetch a single submission's sanitized execution results (owner or Admin only)."""
    return await service.get_submission(user=current_user, submission_id=submission_id)


@workspace_router.put("/revisions", response_model=RevisionResponse)
async def save_workspace_revision(
    payload: RevisionSaveRequest,
    current_user: UserRecord = Depends(get_current_user),
    service: ExecutionService = Depends(get_execution_service),
) -> RevisionResponse:
    """Autosave or manually checkpoint a student's code & debugging notes."""
    return await service.save_revision(user=current_user, payload=payload)


@workspace_router.get("/revisions", response_model=list[RevisionResponse])
async def list_workspace_revisions(
    problem_version_id: UUID = Query(...),
    limit: int = Query(default=20, ge=1, le=50),
    current_user: UserRecord = Depends(get_current_user),
    service: ExecutionService = Depends(get_execution_service),
) -> list[RevisionResponse]:
    """List recent code revisions for the authenticated student on a problem version."""
    return await service.list_revisions(
        user=current_user,
        problem_version_id=problem_version_id,
        limit=limit,
    )
