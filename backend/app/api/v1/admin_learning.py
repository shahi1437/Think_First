"""Admin-only Phase 5 & Phase 8 Curriculum, Lesson, Diagnostic & Bundle Import routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, Request, status

from app.api.v1.deps import (
    get_admin_curriculum_service,
    get_diagnostic_assessment_service,
    get_lessons_and_tracks_service,
    get_problem_service,
    require_roles,
)
from app.repositories.identity import UserRecord
from app.schemas.admin import (
    AdminCurriculumImportReport,
    AdminCurriculumImportRequest,
    AdminCurriculumValidateResponse,
    AdminDiagnosticQuestionDetail,
    AdminDiagnosticQuestionUpdateRequest,
    AdminDiagnosticStatusUpdateRequest,
    AdminDiagnosticValidateRequest,
    AdminLessonDetailView,
    AdminLessonExerciseValidateRequest,
    AdminLessonStatusUpdateRequest,
    AdminTrackUpdateRequest,
)
from app.schemas.learning import (
    AdminDiagnosticQuestionCreateRequest,
    AdminLessonCreateRequest,
    DiagnosticQuestionPublicView,
    LearningTrackView,
    LessonSummaryView,
)
from app.services.admin.curriculum_service import AdminCurriculumService
from app.services.learning.diagnostics_service import DiagnosticAssessmentService
from app.services.learning.lessons_service import LessonsAndTracksService
from app.services.problems.service import ProblemService

admin_learning_router = APIRouter(prefix="/admin/learning", tags=["Admin Curriculum & Learning"])


@admin_learning_router.get("/tracks", response_model=list[LearningTrackView])
async def list_admin_tracks(
    _admin: UserRecord = Depends(require_roles("admin")),
    service: AdminCurriculumService = Depends(get_admin_curriculum_service),
) -> list[LearningTrackView]:
    return await service.list_tracks()


@admin_learning_router.patch("/tracks/{track_slug}", response_model=LearningTrackView)
async def update_admin_track(
    track_slug: str,
    payload: AdminTrackUpdateRequest,
    request: Request,
    admin: UserRecord = Depends(require_roles("admin")),
    service: AdminCurriculumService = Depends(get_admin_curriculum_service),
) -> LearningTrackView:
    request_id = getattr(request.state, "request_id", None)
    return await service.update_track(
        actor=admin,
        track_slug=track_slug,
        payload=payload,
        request_id=request_id,
    )


@admin_learning_router.get("/lessons", response_model=list[AdminLessonDetailView])
async def list_admin_lessons(
    _admin: UserRecord = Depends(require_roles("admin")),
    service: AdminCurriculumService = Depends(get_admin_curriculum_service),
) -> list[AdminLessonDetailView]:
    return await service.list_admin_lessons()


@admin_learning_router.get("/lessons/{lesson_id}", response_model=AdminLessonDetailView)
async def get_admin_lesson(
    lesson_id: UUID,
    _admin: UserRecord = Depends(require_roles("admin")),
    service: AdminCurriculumService = Depends(get_admin_curriculum_service),
) -> AdminLessonDetailView:
    return await service.get_admin_lesson(lesson_id)


@admin_learning_router.post(
    "/lessons",
    response_model=LessonSummaryView,
    status_code=status.HTTP_201_CREATED,
    summary="Admin-only creation/versioning/publishing of bilingual lessons",
)
async def create_admin_lesson(
    payload: AdminLessonCreateRequest,
    admin: UserRecord = Depends(require_roles("admin")),
    service: LessonsAndTracksService = Depends(get_lessons_and_tracks_service),
) -> LessonSummaryView:
    return await service.create_admin_lesson(admin=admin, payload=payload)


@admin_learning_router.patch(
    "/lessons/{lesson_id}/status",
    response_model=AdminLessonDetailView,
)
async def update_admin_lesson_status(
    lesson_id: UUID,
    payload: AdminLessonStatusUpdateRequest,
    request: Request,
    admin: UserRecord = Depends(require_roles("admin")),
    service: AdminCurriculumService = Depends(get_admin_curriculum_service),
) -> AdminLessonDetailView:
    request_id = getattr(request.state, "request_id", None)
    return await service.update_lesson_status(
        actor=admin,
        lesson_id=lesson_id,
        new_status=payload.status,
        request_id=request_id,
    )


@admin_learning_router.post(
    "/lessons/{lesson_id}/validate-exercise",
    response_model=AdminCurriculumValidateResponse,
)
async def validate_admin_lesson_exercise(
    lesson_id: UUID,
    payload: AdminLessonExerciseValidateRequest,
    request: Request,
    admin: UserRecord = Depends(require_roles("admin")),
    service: AdminCurriculumService = Depends(get_admin_curriculum_service),
) -> AdminCurriculumValidateResponse:
    request_id = getattr(request.state, "request_id", None)
    return await service.validate_lesson_exercise(
        actor=admin,
        lesson_id=lesson_id,
        reference_solution=payload.reference_solution,
        request_id=request_id,
    )


@admin_learning_router.get(
    "/diagnostic-questions",
    response_model=list[AdminDiagnosticQuestionDetail],
)
async def list_admin_diagnostic_questions(
    _admin: UserRecord = Depends(require_roles("admin")),
    service: AdminCurriculumService = Depends(get_admin_curriculum_service),
) -> list[AdminDiagnosticQuestionDetail]:
    return await service.list_admin_diagnostics()


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


@admin_learning_router.patch(
    "/diagnostic-questions/{question_id}",
    response_model=AdminDiagnosticQuestionDetail,
)
async def update_admin_diagnostic_question(
    question_id: UUID,
    payload: AdminDiagnosticQuestionUpdateRequest,
    request: Request,
    admin: UserRecord = Depends(require_roles("admin")),
    service: AdminCurriculumService = Depends(get_admin_curriculum_service),
) -> AdminDiagnosticQuestionDetail:
    request_id = getattr(request.state, "request_id", None)
    return await service.update_admin_diagnostic(
        actor=admin,
        question_id=question_id,
        payload=payload,
        request_id=request_id,
    )


@admin_learning_router.patch(
    "/diagnostic-questions/{question_id}/status",
    response_model=AdminDiagnosticQuestionDetail,
)
async def update_admin_diagnostic_status(
    question_id: UUID,
    payload: AdminDiagnosticStatusUpdateRequest,
    request: Request,
    admin: UserRecord = Depends(require_roles("admin")),
    service: AdminCurriculumService = Depends(get_admin_curriculum_service),
) -> AdminDiagnosticQuestionDetail:
    request_id = getattr(request.state, "request_id", None)
    return await service.update_diagnostic_status(
        actor=admin,
        question_id=question_id,
        new_status=payload.status,
        request_id=request_id,
    )


@admin_learning_router.post(
    "/diagnostic-questions/{question_id}/validate",
    response_model=AdminCurriculumValidateResponse,
)
async def validate_admin_diagnostic_question(
    question_id: UUID,
    payload: AdminDiagnosticValidateRequest,
    request: Request,
    admin: UserRecord = Depends(require_roles("admin")),
    service: AdminCurriculumService = Depends(get_admin_curriculum_service),
) -> AdminCurriculumValidateResponse:
    request_id = getattr(request.state, "request_id", None)
    return await service.validate_diagnostic_question(
        actor=admin,
        question_id=question_id,
        reference_solution=payload.reference_solution,
        request_id=request_id,
    )


@admin_learning_router.post(
    "/import-bundle",
    response_model=AdminCurriculumImportReport,
    summary="Admin-only protected curriculum import with Judge0 validation before publishing",
)
async def import_admin_curriculum_bundle(
    payload: AdminCurriculumImportRequest,
    request: Request,
    admin: UserRecord = Depends(require_roles("admin")),
    service: AdminCurriculumService = Depends(get_admin_curriculum_service),
    problem_service: ProblemService = Depends(get_problem_service),
) -> AdminCurriculumImportReport:
    request_id = getattr(request.state, "request_id", None)
    return await service.import_curriculum_bundle(
        actor=admin,
        payload=payload,
        problem_service=problem_service,
        request_id=request_id,
    )
