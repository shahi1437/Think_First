"""Admin-only Phase 5 Lesson and Diagnostic Question publishing routes."""

from fastapi import APIRouter, Depends, status

from app.api.v1.deps import (
    get_diagnostic_assessment_service,
    get_lessons_and_tracks_service,
    require_roles,
)
from app.repositories.identity import UserRecord
from app.schemas.learning import (
    AdminDiagnosticQuestionCreateRequest,
    AdminLessonCreateRequest,
    DiagnosticQuestionPublicView,
    LessonSummaryView,
)
from app.services.learning.diagnostics_service import DiagnosticAssessmentService
from app.services.learning.lessons_service import LessonsAndTracksService

admin_learning_router = APIRouter(prefix="/admin/learning", tags=["Admin Phase 5 Content"])


@admin_learning_router.post(
    "/lessons",
    response_model=LessonSummaryView,
    status_code=status.HTTP_201_CREATED,
    summary="Admin-only creation/versioning/publishing of bilingual beginner lessons",
)
async def create_admin_lesson(
    payload: AdminLessonCreateRequest,
    admin: UserRecord = Depends(require_roles("admin")),
    service: LessonsAndTracksService = Depends(get_lessons_and_tracks_service),
) -> LessonSummaryView:
    return await service.create_admin_lesson(admin=admin, payload=payload)


@admin_learning_router.post(
    "/diagnostic-questions",
    response_model=DiagnosticQuestionPublicView,
    status_code=status.HTTP_201_CREATED,
    summary="Admin-only creation/publishing of diagnostic items with isolated private answer keys",
)
async def create_admin_diagnostic_question(
    payload: AdminDiagnosticQuestionCreateRequest,
    admin: UserRecord = Depends(require_roles("admin")),
    service: DiagnosticAssessmentService = Depends(get_diagnostic_assessment_service),
) -> DiagnosticQuestionPublicView:
    return await service.create_admin_question(admin=admin, payload=payload)
