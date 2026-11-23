"""Authenticated Phase 5 Learning Tracks, Lessons, Diagnostics & Skill Graph API."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel

from app.api.v1.deps import (
    get_assignment_service,
    get_classroom_course_service,
    get_current_user,
    get_daily_plan_service,
    get_diagnostic_assessment_service,
    get_learning_dna_service,
    get_learning_journey_service,
    get_lessons_and_tracks_service,
    get_recommendation_service,
    get_retention_service,
    get_skill_graph_service,
)
from app.repositories.identity import UserRecord
from app.schemas.classroom import StudentAssignmentListItemView, StudentEnrolledCourseView
from app.schemas.growth import (
    DailyPlanWorkspaceView,
    LearningDnaProfileView,
    RetentionOverviewView,
)
from app.schemas.learning import (
    DiagnosticAnswerSubmitRequest,
    DiagnosticSessionCreateRequest,
    DiagnosticSessionView,
    LanguageProgressOverview,
    LanguageSlug,
    LearningDashboardView,
    LearningJourneyView,
    LessonDetailView,
    LessonExerciseRunRequest,
    LessonExerciseRunResponse,
    LessonReadingCompleteRequest,
    LessonSummaryView,
    RecommendationItemView,
    SelectActiveLanguageRequest,
    SelectTrackRequest,
    SkillGraphView,
    StudentTrackStatus,
)
from app.services.classroom.assignment_service import AssignmentService
from app.services.classroom.course_service import ClassroomCourseService
from app.services.growth.daily_plan_service import DailyPlanService
from app.services.growth.dna_service import LearningDnaService
from app.services.growth.retention_service import RetentionVerificationService
from app.services.learning.diagnostics_service import DiagnosticAssessmentService
from app.services.learning.journey_engine import LearningJourneyService
from app.services.learning.lessons_service import LessonsAndTracksService, resolve_user_language
from app.services.learning.recommendations_service import AdaptiveRecommendationService
from app.services.learning.skill_graph import SkillGraphService


class StudentDashboardBundleResponse(BaseModel):
    """Unified single-request payload for the Student Dashboard."""

    language_overview: LanguageProgressOverview
    dashboard: LearningDashboardView
    dna_profile: LearningDnaProfileView
    daily_plan_workspace: DailyPlanWorkspaceView
    retention_overview: RetentionOverviewView
    enrolled_classes: list[StudentEnrolledCourseView]
    student_assignments: list[StudentAssignmentListItemView]


phase5_learning_router = APIRouter(prefix="/learning", tags=["Phase 5 Adaptive Learning"])


@phase5_learning_router.get(
    "/languages",
    response_model=LanguageProgressOverview,
    summary="List all enabled programming languages with independent per-language progress",
)
async def get_learning_languages(
    current_user: UserRecord = Depends(get_current_user),
    service: LessonsAndTracksService = Depends(get_lessons_and_tracks_service),
) -> LanguageProgressOverview:
    return await service.get_language_progress_overview(current_user)


@phase5_learning_router.post(
    "/languages/select",
    response_model=LanguageProgressOverview,
    summary="Switch the student's active learning language while isolating per-language progress",
)
async def select_active_learning_language(
    payload: SelectActiveLanguageRequest,
    current_user: UserRecord = Depends(get_current_user),
    service: LessonsAndTracksService = Depends(get_lessons_and_tracks_service),
) -> LanguageProgressOverview:
    return await service.select_active_language(
        user=current_user, language_slug=payload.language_slug
    )


@phase5_learning_router.get(
    "/journey",
    response_model=LearningJourneyView,
    summary="Compute the student's authoritative Continue Learning journey state and next action",
)
async def get_learning_journey(
    language: LanguageSlug | None = Query(default=None),
    current_user: UserRecord = Depends(get_current_user),
    service: LearningJourneyService = Depends(get_learning_journey_service),
) -> LearningJourneyView:
    return await service.evaluate(current_user, language_slug=language)


@phase5_learning_router.get(
    "/dashboard",
    response_model=LearningDashboardView,
    summary="Unified evidence-based Student Learning Dashboard",
)
async def get_learning_dashboard(
    language: LanguageSlug | None = Query(default=None),
    current_user: UserRecord = Depends(get_current_user),
    service: AdaptiveRecommendationService = Depends(get_recommendation_service),
) -> LearningDashboardView:
    return await service.get_dashboard(current_user, language_slug=language)


@phase5_learning_router.get(
    "/dashboard-bundle",
    response_model=StudentDashboardBundleResponse,
    summary="Consolidated Student Dashboard payload sharing skill-graph and track state",
)
async def get_student_dashboard_bundle(
    language: LanguageSlug | None = Query(default=None),
    current_user: UserRecord = Depends(get_current_user),
    lessons_service: LessonsAndTracksService = Depends(get_lessons_and_tracks_service),
    rec_service: AdaptiveRecommendationService = Depends(get_recommendation_service),
    dna_service: LearningDnaService = Depends(get_learning_dna_service),
    daily_plan_service: DailyPlanService = Depends(get_daily_plan_service),
    retention_service: RetentionVerificationService = Depends(get_retention_service),
    course_service: ClassroomCourseService = Depends(get_classroom_course_service),
    assignment_service: AssignmentService = Depends(get_assignment_service),
) -> StudentDashboardBundleResponse:
    language_overview = await lessons_service.get_language_progress_overview(
        current_user, active_override=language
    )
    dashboard = await rec_service.get_dashboard(current_user, language_slug=language)
    retention_overview = await retention_service.get_retention_overview(
        current_user,
        language_slug=dashboard.language_slug,
        already_synced_evidence=True,
        preloaded_skill_graph=dashboard.skill_graph,
    )
    dna_profile = await dna_service.compute_and_persist_profile(
        current_user,
        language_slug=dashboard.language_slug,
        track_status=dashboard.track_status,
        skill_graph=dashboard.skill_graph,
    )
    daily_plan_workspace = await daily_plan_service.get_today_workspace(
        current_user,
        language_slug=dashboard.language_slug,
        track_status=dashboard.track_status,
        skill_graph=dashboard.skill_graph,
        retention_overview=retention_overview,
    )
    enrolled_classes = await course_service.list_student_courses(current_user)
    student_assignments = await assignment_service.list_student_assignments(
        student=current_user, status_filter="all"
    )
    return StudentDashboardBundleResponse(
        language_overview=language_overview,
        dashboard=dashboard,
        dna_profile=dna_profile,
        daily_plan_workspace=daily_plan_workspace,
        retention_overview=retention_overview,
        enrolled_classes=enrolled_classes,
        student_assignments=student_assignments,
    )


@phase5_learning_router.get(
    "/tracks",
    response_model=StudentTrackStatus,
    summary="List the 4 learner tracks and the student's active & evidence-recommended track",
)
async def get_learning_tracks(
    language: LanguageSlug | None = Query(default=None),
    current_user: UserRecord = Depends(get_current_user),
    service: LessonsAndTracksService = Depends(get_lessons_and_tracks_service),
) -> StudentTrackStatus:
    return await service.get_track_status(current_user, language_slug=language)


@phase5_learning_router.post(
    "/tracks/select",
    response_model=StudentTrackStatus,
    summary="Select an active learning track",
)
async def select_learning_track(
    payload: SelectTrackRequest,
    current_user: UserRecord = Depends(get_current_user),
    service: LessonsAndTracksService = Depends(get_lessons_and_tracks_service),
) -> StudentTrackStatus:
    return await service.select_track(
        user=current_user,
        track_slug=payload.track_slug,
        language_slug=payload.language_slug,
    )


@phase5_learning_router.get(
    "/lessons",
    response_model=list[LessonSummaryView],
    summary="List published bilingual beginner lessons with per-student progress",
)
async def list_published_lessons(
    track: str | None = Query(default=None),
    language: LanguageSlug | None = Query(default=None),
    current_user: UserRecord = Depends(get_current_user),
    service: LessonsAndTracksService = Depends(get_lessons_and_tracks_service),
) -> list[LessonSummaryView]:
    return await service.list_lessons(user=current_user, track_slug=track, language_slug=language)


@phase5_learning_router.get(
    "/lessons/{slug}",
    response_model=LessonDetailView,
    summary="Fetch full bilingual lesson content, interactive examples, and Judge0 guided exercise",
)
async def get_lesson_detail(
    slug: str,
    current_user: UserRecord = Depends(get_current_user),
    service: LessonsAndTracksService = Depends(get_lessons_and_tracks_service),
) -> LessonDetailView:
    return await service.get_lesson_detail(user=current_user, slug=slug)


@phase5_learning_router.post(
    "/lessons/{lesson_id}/reading",
    response_model=LessonDetailView,
    summary="Record lesson reading completion (advances skill to Introduced, not mastery)",
)
async def mark_lesson_reading_complete(
    lesson_id: UUID,
    _payload: LessonReadingCompleteRequest,
    current_user: UserRecord = Depends(get_current_user),
    service: LessonsAndTracksService = Depends(get_lessons_and_tracks_service),
) -> LessonDetailView:
    return await service.mark_reading_complete(user=current_user, lesson_id=lesson_id)


@phase5_learning_router.post(
    "/lessons/{lesson_id}/exercise/run",
    response_model=LessonExerciseRunResponse,
    summary="Execute guided lesson practice code on real Judge0 CE and save real progress",
)
async def run_lesson_guided_exercise(
    lesson_id: UUID,
    payload: LessonExerciseRunRequest,
    current_user: UserRecord = Depends(get_current_user),
    service: LessonsAndTracksService = Depends(get_lessons_and_tracks_service),
) -> LessonExerciseRunResponse:
    return await service.run_guided_exercise(
        user=current_user,
        lesson_id=lesson_id,
        source_code=payload.source_code,
    )


@phase5_learning_router.post(
    "/diagnostics/sessions",
    response_model=DiagnosticSessionView,
    status_code=status.HTTP_201_CREATED,
    summary="Start or resume an adaptive 8-domain diagnostic assessment session",
)
async def create_diagnostic_session(
    payload: DiagnosticSessionCreateRequest,
    current_user: UserRecord = Depends(get_current_user),
    service: DiagnosticAssessmentService = Depends(get_diagnostic_assessment_service),
) -> DiagnosticSessionView:
    return await service.start_or_resume_session(
        user=current_user,
        explanation_language=payload.explanation_language,
        language_slug=payload.language_slug,
        assessment_mode=payload.assessment_mode,
    )


@phase5_learning_router.get(
    "/diagnostics/sessions",
    response_model=list[DiagnosticSessionView],
    summary="List the authenticated student's diagnostic assessment history",
)
async def list_my_diagnostic_sessions(
    language: LanguageSlug | None = Query(default=None),
    current_user: UserRecord = Depends(get_current_user),
    service: DiagnosticAssessmentService = Depends(get_diagnostic_assessment_service),
) -> list[DiagnosticSessionView]:
    return await service.list_my_sessions(user=current_user, language_slug=language)


@phase5_learning_router.get(
    "/diagnostics/sessions/{session_id}",
    response_model=DiagnosticSessionView,
    summary="Fetch a student's own diagnostic session state and domain evidence",
)
async def get_diagnostic_session(
    session_id: UUID,
    current_user: UserRecord = Depends(get_current_user),
    service: DiagnosticAssessmentService = Depends(get_diagnostic_assessment_service),
) -> DiagnosticSessionView:
    return await service.get_session(user=current_user, session_id=session_id)


@phase5_learning_router.post(
    "/diagnostics/sessions/{session_id}/answers",
    response_model=DiagnosticSessionView,
    summary="Submit an MCQ or real sandbox code answer to advance the adaptive diagnostic",
)
async def submit_diagnostic_answer(
    session_id: UUID,
    payload: DiagnosticAnswerSubmitRequest,
    current_user: UserRecord = Depends(get_current_user),
    service: DiagnosticAssessmentService = Depends(get_diagnostic_assessment_service),
) -> DiagnosticSessionView:
    return await service.submit_answer(
        user=current_user,
        session_id=session_id,
        payload=payload,
    )


@phase5_learning_router.get(
    "/skill-graph",
    response_model=SkillGraphView,
    summary="Get the student's prerequisite-aware Skill Graph with honest evidence states",
)
async def get_student_skill_graph(
    language: LanguageSlug | None = Query(default=None),
    current_user: UserRecord = Depends(get_current_user),
    service: SkillGraphService = Depends(get_skill_graph_service),
) -> SkillGraphView:
    lang = resolve_user_language(current_user, language)
    return await service.get_student_skill_graph(current_user.id, language_slug=lang)


@phase5_learning_router.get(
    "/recommendations",
    response_model=list[RecommendationItemView],
    summary="Get explainable prerequisite-based next lesson and practice recommendations",
)
async def get_student_recommendations(
    language: LanguageSlug | None = Query(default=None),
    current_user: UserRecord = Depends(get_current_user),
    service: AdaptiveRecommendationService = Depends(get_recommendation_service),
) -> list[RecommendationItemView]:
    return await service.compute_recommendations(current_user, language_slug=language)
