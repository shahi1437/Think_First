from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.v1.deps import get_current_user, get_problem_service
from app.repositories.identity import UserRecord
from app.schemas.common import PaginatedResponse
from app.schemas.problems import (
    Difficulty,
    LanguageItem,
    ProblemMode,
    StudentProblemDetail,
    StudentProblemListItem,
)
from app.services.problems.service import ProblemService

languages_router = APIRouter(prefix="/languages", tags=["Languages"])
problems_router = APIRouter(prefix="/problems", tags=["Problem Bank"])


@languages_router.get("", response_model=list[LanguageItem])
async def list_enabled_languages(
    _user: UserRecord = Depends(get_current_user),
    service: ProblemService = Depends(get_problem_service),
) -> list[LanguageItem]:
    """Return enabled execution languages from the platform language registry."""
    return await service.list_languages(enabled_only=True)


@problems_router.get("", response_model=PaginatedResponse[StudentProblemListItem])
async def list_problems(
    search: str | None = Query(default=None, max_length=120),
    difficulty: Difficulty | None = Query(default=None),
    mode: ProblemMode | None = Query(default=None),
    topic: str | None = Query(default=None, max_length=64),
    language: str | None = Query(default=None, max_length=32),
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    _user: UserRecord = Depends(get_current_user),
    service: ProblemService = Depends(get_problem_service),
) -> PaginatedResponse[StudentProblemListItem]:
    """Search and filter published programming & debugging problems."""
    return await service.list_published_problems(
        search=search,
        difficulty=difficulty,
        mode=mode,
        topic=topic,
        language=language,
        limit=limit,
        offset=offset,
    )


@problems_router.get("/{problem_id}", response_model=StudentProblemDetail)
async def get_problem_detail(
    problem_id: UUID,
    _user: UserRecord = Depends(get_current_user),
    service: ProblemService = Depends(get_problem_service),
) -> StudentProblemDetail:
    """Return a published problem's statement, starter code, and public test cases only."""
    return await service.get_published_problem(problem_id)
