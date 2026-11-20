from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status

from app.api.v1.deps import get_problem_service, require_roles
from app.repositories.identity import UserRecord
from app.schemas.common import PaginatedResponse
from app.schemas.problems import (
    AdminLanguageSyncResponse,
    AdminProblemArchiveResponse,
    AdminProblemCreateRequest,
    AdminProblemDetail,
    AdminProblemListItem,
    AdminProblemRejectRequest,
    AdminProblemUpdateRequest,
    AdminProblemVersionsResponse,
    AdminReviewActionRequest,
    AdminValidationReport,
    ProblemMode,
    ProblemStatus,
)
from app.services.problems.service import ProblemService

admin_problems_router = APIRouter(prefix="/admin/problems", tags=["Admin Problem Studio"])
admin_languages_router = APIRouter(prefix="/admin/languages", tags=["Admin Language Registry"])


@admin_languages_router.post("/sync", response_model=AdminLanguageSyncResponse)
async def sync_judge0_languages(
    request: Request,
    admin_user: UserRecord = Depends(require_roles("admin")),
    service: ProblemService = Depends(get_problem_service),
) -> AdminLanguageSyncResponse:
    """Fetch live Judge0 language IDs and sync the platform language registry (Admin only)."""
    request_id = getattr(request.state, "request_id", None)
    return await service.sync_languages_from_judge0(actor=admin_user, request_id=request_id)


@admin_problems_router.get("", response_model=PaginatedResponse[AdminProblemListItem])
async def list_admin_problems(
    status_filter: ProblemStatus | None = Query(default=None, alias="status"),
    mode: ProblemMode | None = Query(default=None),
    search: str | None = Query(default=None, max_length=120),
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _admin_user: UserRecord = Depends(require_roles("admin")),
    service: ProblemService = Depends(get_problem_service),
) -> PaginatedResponse[AdminProblemListItem]:
    """List all problems across draft, validated, approved, and published states."""
    return await service.list_admin_problems(
        status_filter=status_filter,
        mode=mode,
        search=search,
        limit=limit,
        offset=offset,
    )


@admin_problems_router.post(
    "", response_model=AdminProblemDetail, status_code=status.HTTP_201_CREATED
)
async def create_admin_problem(
    payload: AdminProblemCreateRequest,
    request: Request,
    admin_user: UserRecord = Depends(require_roles("admin")),
    service: ProblemService = Depends(get_problem_service),
) -> AdminProblemDetail:
    """Author a new draft problem with variants, private reference solution, and tests."""
    request_id = getattr(request.state, "request_id", None)
    return await service.create_problem(actor=admin_user, payload=payload, request_id=request_id)


@admin_problems_router.get("/{problem_id}", response_model=AdminProblemDetail)
async def get_admin_problem(
    problem_id: UUID,
    _admin_user: UserRecord = Depends(require_roles("admin")),
    service: ProblemService = Depends(get_problem_service),
) -> AdminProblemDetail:
    """Inspect latest version of a problem including hidden tests & private solutions."""
    return await service.get_admin_problem(problem_id)


@admin_problems_router.patch("/{problem_id}", response_model=AdminProblemDetail)
async def update_admin_problem(
    problem_id: UUID,
    payload: AdminProblemUpdateRequest,
    request: Request,
    admin_user: UserRecord = Depends(require_roles("admin")),
    service: ProblemService = Depends(get_problem_service),
) -> AdminProblemDetail:
    """Update draft or branch a new draft version if latest version is already published."""
    request_id = getattr(request.state, "request_id", None)
    return await service.update_problem(
        actor=admin_user,
        problem_id=problem_id,
        payload=payload,
        request_id=request_id,
    )


@admin_problems_router.post("/{problem_id}/validate", response_model=AdminValidationReport)
async def validate_admin_problem(
    problem_id: UUID,
    request: Request,
    admin_user: UserRecord = Depends(require_roles("admin")),
    service: ProblemService = Depends(get_problem_service),
) -> AdminValidationReport:
    """Validate reference solutions (and buggy starter code) via real Judge0 execution."""
    request_id = getattr(request.state, "request_id", None)
    return await service.validate_problem(
        actor=admin_user, problem_id=problem_id, request_id=request_id
    )


@admin_problems_router.post("/{problem_id}/approve", response_model=AdminProblemDetail)
async def approve_admin_problem(
    problem_id: UUID,
    payload: AdminReviewActionRequest,
    request: Request,
    admin_user: UserRecord = Depends(require_roles("admin")),
    service: ProblemService = Depends(get_problem_service),
) -> AdminProblemDetail:
    """Record human review approval on a validated problem version."""
    request_id = getattr(request.state, "request_id", None)
    return await service.approve_problem(
        actor=admin_user,
        problem_id=problem_id,
        notes=payload.notes,
        request_id=request_id,
    )


@admin_problems_router.post("/{problem_id}/publish", response_model=AdminProblemDetail)
async def publish_admin_problem(
    problem_id: UUID,
    payload: AdminReviewActionRequest,
    request: Request,
    admin_user: UserRecord = Depends(require_roles("admin")),
    service: ProblemService = Depends(get_problem_service),
) -> AdminProblemDetail:
    """Publish a validated/approved problem version to the Student Problem Bank."""
    request_id = getattr(request.state, "request_id", None)
    return await service.publish_problem(
        actor=admin_user,
        problem_id=problem_id,
        notes=payload.notes,
        request_id=request_id,
    )


@admin_problems_router.post("/{problem_id}/submit-review", response_model=AdminProblemDetail)
async def submit_problem_for_review(
    problem_id: UUID,
    payload: AdminReviewActionRequest,
    request: Request,
    admin_user: UserRecord = Depends(require_roles("admin")),
    service: ProblemService = Depends(get_problem_service),
) -> AdminProblemDetail:
    """Move a validated problem version into human review queue."""
    request_id = getattr(request.state, "request_id", None)
    return await service.submit_for_review(
        actor=admin_user,
        problem_id=problem_id,
        notes=payload.notes,
        request_id=request_id,
    )


@admin_problems_router.post("/{problem_id}/reject", response_model=AdminProblemDetail)
async def reject_admin_problem(
    problem_id: UUID,
    payload: AdminProblemRejectRequest,
    request: Request,
    admin_user: UserRecord = Depends(require_roles("admin")),
    service: ProblemService = Depends(get_problem_service),
) -> AdminProblemDetail:
    """Reject content back to draft with mandatory reviewer feedback notes."""
    request_id = getattr(request.state, "request_id", None)
    return await service.reject_problem(
        actor=admin_user,
        problem_id=problem_id,
        notes=payload.notes,
        request_id=request_id,
    )


@admin_problems_router.post("/{problem_id}/archive", response_model=AdminProblemArchiveResponse)
async def archive_admin_problem(
    problem_id: UUID,
    payload: AdminReviewActionRequest,
    request: Request,
    admin_user: UserRecord = Depends(require_roles("admin")),
    service: ProblemService = Depends(get_problem_service),
) -> AdminProblemArchiveResponse:
    """Archive problem from new discovery while preserving published versions for assignments."""
    request_id = getattr(request.state, "request_id", None)
    return await service.archive_problem(
        actor=admin_user,
        problem_id=problem_id,
        notes=payload.notes,
        request_id=request_id,
    )


@admin_problems_router.get("/{problem_id}/versions", response_model=AdminProblemVersionsResponse)
async def list_admin_problem_versions(
    problem_id: UUID,
    _admin_user: UserRecord = Depends(require_roles("admin")),
    service: ProblemService = Depends(get_problem_service),
) -> AdminProblemVersionsResponse:
    """Return full immutable version history & reviews for side-by-side comparison."""
    return await service.list_problem_versions(problem_id)
