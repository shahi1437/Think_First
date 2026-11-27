from collections.abc import Callable, Coroutine
from functools import lru_cache
from typing import Any

from fastapi import Depends, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import get_db_session
from app.core.errors import AppError
from app.core.security import AuthenticatedPrincipal, SupabaseJWTVerifier
from app.integrations.execution.router import ResilientExecutionClient
from app.integrations.judge0.client import HttpJudge0Client, Judge0Client
from app.integrations.judge0.worker_client import WorkerQueueJudge0Client
from app.integrations.llm.client import SocraticLLMClient
from app.integrations.piston.client import HttpPistonClient, is_piston_configured
from app.repositories.admin import AdminRepository
from app.repositories.classroom import ClassroomRepository
from app.repositories.execution_queue import ExecutionQueueRepository
from app.repositories.growth import GrowthRepository
from app.repositories.identity import IdentityRepository, SQLAlchemyIdentityRepository, UserRecord
from app.repositories.learning import LearningRepository
from app.repositories.mentor import MentorRepository
from app.repositories.notifications import NotificationRepository, SQLAlchemyNotificationRepository
from app.repositories.problems import ProblemRepository
from app.schemas.identity import RoleName
from app.services.admin.curriculum_service import AdminCurriculumService
from app.services.admin.overview_service import AdminOverviewService
from app.services.classroom.analytics_service import TeacherAnalyticsService
from app.services.classroom.assignment_service import AssignmentService
from app.services.classroom.course_service import ClassroomCourseService
from app.services.classroom.grading_service import GradingService
from app.services.execution.service import ExecutionService
from app.services.execution.worker_service import ExecutionWorkerService, is_worker_queue_mode
from app.services.growth.daily_plan_service import DailyPlanService
from app.services.growth.debugging_timeline_service import DebuggingTimelineService
from app.services.growth.dna_service import LearningDnaService
from app.services.growth.history_service import LearningHistoryService
from app.services.growth.retention_service import RetentionVerificationService
from app.services.growth.verified_progress_service import VerifiedProgressService
from app.services.identity.service import IdentityService
from app.services.learning.diagnostics_service import DiagnosticAssessmentService
from app.services.learning.journey_engine import LearningJourneyService
from app.services.learning.lessons_service import LessonsAndTracksService
from app.services.learning.recommendations_service import AdaptiveRecommendationService
from app.services.learning.skill_graph import SkillGraphService
from app.services.mentor.ml_inference import MLErrorClassifierService
from app.services.mentor.rag_service import RagKnowledgeService
from app.services.mentor.socratic_agent import SocraticMentorService
from app.services.notifications.service import NotificationService
from app.services.problems.service import ProblemService
from app.services.verification.service import VerificationService

_bearer_scheme = HTTPBearer(auto_error=False)


@lru_cache(maxsize=8)
def _cached_verifier(
    supabase_url: str | None,
    supabase_jwt_audience: str,
    jwks_cache_ttl_seconds: int,
    jwks_fetch_timeout_seconds: float,
) -> SupabaseJWTVerifier:
    settings = Settings(
        supabase_url=supabase_url,
        supabase_jwt_audience=supabase_jwt_audience,
        jwks_cache_ttl_seconds=jwks_cache_ttl_seconds,
        jwks_fetch_timeout_seconds=jwks_fetch_timeout_seconds,
    )
    return SupabaseJWTVerifier(settings)


def get_jwt_verifier(
    settings: Settings = Depends(get_settings),
) -> SupabaseJWTVerifier:
    """Return cached Supabase asymmetric JWKS verifier for the active settings."""
    return _cached_verifier(
        settings.supabase_url,
        settings.supabase_jwt_audience,
        settings.jwks_cache_ttl_seconds,
        settings.jwks_fetch_timeout_seconds,
    )


def get_judge0_client(
    settings: Settings = Depends(get_settings),
) -> Judge0Client:
    """Return resilient execution client: outbound worker queue OR direct Judge0 + Piston."""
    if is_worker_queue_mode(settings):
        return WorkerQueueJudge0Client(settings)
    primary = HttpJudge0Client(settings)
    fallback = HttpPistonClient(settings) if is_piston_configured(settings) else None
    return ResilientExecutionClient(primary=primary, fallback=fallback, settings=settings)


def get_execution_queue_repository(
    session: AsyncSession = Depends(get_db_session),
) -> ExecutionQueueRepository:
    return ExecutionQueueRepository(session)


def get_execution_worker_service(
    repo: ExecutionQueueRepository = Depends(get_execution_queue_repository),
    settings: Settings = Depends(get_settings),
) -> ExecutionWorkerService:
    return ExecutionWorkerService(repo=repo, settings=settings)


def get_identity_repository(
    session: AsyncSession = Depends(get_db_session),
) -> IdentityRepository:
    return SQLAlchemyIdentityRepository(session)


def get_identity_service(
    repository: IdentityRepository = Depends(get_identity_repository),
) -> IdentityService:
    return IdentityService(repository)


def get_problem_repository(
    session: AsyncSession = Depends(get_db_session),
) -> ProblemRepository:
    return ProblemRepository(session)


def get_problem_service(
    repository: ProblemRepository = Depends(get_problem_repository),
    judge0: Judge0Client = Depends(get_judge0_client),
) -> ProblemService:
    return ProblemService(repository=repository, judge0=judge0)


def get_execution_service(
    repository: ProblemRepository = Depends(get_problem_repository),
    queue_repository: ExecutionQueueRepository = Depends(get_execution_queue_repository),
    judge0: Judge0Client = Depends(get_judge0_client),
    settings: Settings = Depends(get_settings),
) -> ExecutionService:
    return ExecutionService(
        repository=repository,
        judge0=judge0,
        settings=settings,
        queue_repository=queue_repository,
    )


@lru_cache(maxsize=4)
def _cached_ml_classifier(
    artifact_path: str,
    low_confidence_threshold: float,
) -> MLErrorClassifierService:
    settings = Settings(
        ml_model_artifact_path=artifact_path,
        ml_low_confidence_threshold=low_confidence_threshold,
    )
    return MLErrorClassifierService(settings)


def get_ml_classifier_service(
    settings: Settings = Depends(get_settings),
) -> MLErrorClassifierService:
    return _cached_ml_classifier(
        settings.ml_model_artifact_path,
        settings.ml_low_confidence_threshold,
    )


def get_mentor_repository(
    session: AsyncSession = Depends(get_db_session),
) -> MentorRepository:
    return MentorRepository(session)


def get_rag_knowledge_service(
    repository: MentorRepository = Depends(get_mentor_repository),
    settings: Settings = Depends(get_settings),
) -> RagKnowledgeService:
    return RagKnowledgeService(repository=repository, settings=settings)


def get_llm_client(
    settings: Settings = Depends(get_settings),
) -> SocraticLLMClient:
    return SocraticLLMClient(settings)


def get_socratic_mentor_service(
    mentor_repo: MentorRepository = Depends(get_mentor_repository),
    problem_repo: ProblemRepository = Depends(get_problem_repository),
    ml_service: MLErrorClassifierService = Depends(get_ml_classifier_service),
    rag_service: RagKnowledgeService = Depends(get_rag_knowledge_service),
    llm_client: SocraticLLMClient = Depends(get_llm_client),
    settings: Settings = Depends(get_settings),
) -> SocraticMentorService:
    return SocraticMentorService(
        mentor_repo=mentor_repo,
        problem_repo=problem_repo,
        ml_service=ml_service,
        rag_service=rag_service,
        llm_client=llm_client,
        settings=settings,
    )


def get_verification_service(
    mentor_repo: MentorRepository = Depends(get_mentor_repository),
    execution_service: ExecutionService = Depends(get_execution_service),
) -> VerificationService:
    return VerificationService(
        mentor_repo=mentor_repo,
        execution_service=execution_service,
    )


def get_learning_repository(
    session: AsyncSession = Depends(get_db_session),
) -> LearningRepository:
    return LearningRepository(session)


def get_skill_graph_service(
    learning_repo: LearningRepository = Depends(get_learning_repository),
    mentor_repo: MentorRepository = Depends(get_mentor_repository),
    problem_repo: ProblemRepository = Depends(get_problem_repository),
) -> SkillGraphService:
    return SkillGraphService(
        learning_repo=learning_repo,
        mentor_repo=mentor_repo,
        problem_repo=problem_repo,
    )


def get_lessons_and_tracks_service(
    learning_repo: LearningRepository = Depends(get_learning_repository),
    problem_repo: ProblemRepository = Depends(get_problem_repository),
    mentor_repo: MentorRepository = Depends(get_mentor_repository),
    judge0: Judge0Client = Depends(get_judge0_client),
    skill_graph: SkillGraphService = Depends(get_skill_graph_service),
    identity_repo: IdentityRepository = Depends(get_identity_repository),
) -> LessonsAndTracksService:
    return LessonsAndTracksService(
        learning_repo=learning_repo,
        problem_repo=problem_repo,
        mentor_repo=mentor_repo,
        judge0=judge0,
        skill_graph=skill_graph,
        identity_repo=identity_repo,
    )


def get_diagnostic_assessment_service(
    learning_repo: LearningRepository = Depends(get_learning_repository),
    problem_repo: ProblemRepository = Depends(get_problem_repository),
    mentor_repo: MentorRepository = Depends(get_mentor_repository),
    judge0: Judge0Client = Depends(get_judge0_client),
    skill_graph: SkillGraphService = Depends(get_skill_graph_service),
) -> DiagnosticAssessmentService:
    return DiagnosticAssessmentService(
        learning_repo=learning_repo,
        problem_repo=problem_repo,
        mentor_repo=mentor_repo,
        judge0=judge0,
        skill_graph=skill_graph,
    )


def get_growth_repository(
    session: AsyncSession = Depends(get_db_session),
) -> GrowthRepository:
    return GrowthRepository(session)


def get_classroom_repository(
    session: AsyncSession = Depends(get_db_session),
) -> ClassroomRepository:
    return ClassroomRepository(session)


def get_learning_journey_service(
    learning_repo: LearningRepository = Depends(get_learning_repository),
    problem_repo: ProblemRepository = Depends(get_problem_repository),
    mentor_repo: MentorRepository = Depends(get_mentor_repository),
    growth_repo: GrowthRepository = Depends(get_growth_repository),
    classroom_repo: ClassroomRepository = Depends(get_classroom_repository),
    lessons_service: LessonsAndTracksService = Depends(get_lessons_and_tracks_service),
    diagnostics_service: DiagnosticAssessmentService = Depends(get_diagnostic_assessment_service),
    skill_graph_service: SkillGraphService = Depends(get_skill_graph_service),
) -> LearningJourneyService:
    return LearningJourneyService(
        learning_repo=learning_repo,
        problem_repo=problem_repo,
        mentor_repo=mentor_repo,
        growth_repo=growth_repo,
        classroom_repo=classroom_repo,
        lessons_service=lessons_service,
        diagnostics_service=diagnostics_service,
        skill_graph_service=skill_graph_service,
    )


def get_recommendation_service(
    learning_repo: LearningRepository = Depends(get_learning_repository),
    problem_repo: ProblemRepository = Depends(get_problem_repository),
    mentor_repo: MentorRepository = Depends(get_mentor_repository),
    lessons_service: LessonsAndTracksService = Depends(get_lessons_and_tracks_service),
    diagnostics_service: DiagnosticAssessmentService = Depends(get_diagnostic_assessment_service),
    skill_graph_service: SkillGraphService = Depends(get_skill_graph_service),
    journey_service: LearningJourneyService = Depends(get_learning_journey_service),
) -> AdaptiveRecommendationService:
    return AdaptiveRecommendationService(
        learning_repo=learning_repo,
        problem_repo=problem_repo,
        mentor_repo=mentor_repo,
        lessons_service=lessons_service,
        diagnostics_service=diagnostics_service,
        skill_graph_service=skill_graph_service,
        journey_service=journey_service,
    )


def get_retention_service(
    growth_repo: GrowthRepository = Depends(get_growth_repository),
    learning_repo: LearningRepository = Depends(get_learning_repository),
    problem_repo: ProblemRepository = Depends(get_problem_repository),
    mentor_repo: MentorRepository = Depends(get_mentor_repository),
    skill_graph_service: SkillGraphService = Depends(get_skill_graph_service),
    execution_service: ExecutionService = Depends(get_execution_service),
) -> RetentionVerificationService:
    return RetentionVerificationService(
        growth_repo=growth_repo,
        learning_repo=learning_repo,
        problem_repo=problem_repo,
        mentor_repo=mentor_repo,
        skill_graph_service=skill_graph_service,
        execution_service=execution_service,
    )


def get_learning_dna_service(
    growth_repo: GrowthRepository = Depends(get_growth_repository),
    lessons_service: LessonsAndTracksService = Depends(get_lessons_and_tracks_service),
    skill_graph_service: SkillGraphService = Depends(get_skill_graph_service),
) -> LearningDnaService:
    return LearningDnaService(
        growth_repo=growth_repo,
        lessons_service=lessons_service,
        skill_graph_service=skill_graph_service,
    )


def get_daily_plan_service(
    growth_repo: GrowthRepository = Depends(get_growth_repository),
    problem_repo: ProblemRepository = Depends(get_problem_repository),
    mentor_repo: MentorRepository = Depends(get_mentor_repository),
    lessons_service: LessonsAndTracksService = Depends(get_lessons_and_tracks_service),
    diagnostics_service: DiagnosticAssessmentService = Depends(get_diagnostic_assessment_service),
    skill_graph_service: SkillGraphService = Depends(get_skill_graph_service),
    retention_service: RetentionVerificationService = Depends(get_retention_service),
) -> DailyPlanService:
    return DailyPlanService(
        growth_repo=growth_repo,
        problem_repo=problem_repo,
        mentor_repo=mentor_repo,
        lessons_service=lessons_service,
        diagnostics_service=diagnostics_service,
        skill_graph_service=skill_graph_service,
        retention_service=retention_service,
    )


def get_learning_history_service(
    growth_repo: GrowthRepository = Depends(get_growth_repository),
) -> LearningHistoryService:
    return LearningHistoryService(growth_repo=growth_repo)


def get_debugging_timeline_service(
    growth_repo: GrowthRepository = Depends(get_growth_repository),
) -> DebuggingTimelineService:
    return DebuggingTimelineService(growth_repo=growth_repo)


def get_verified_progress_service(
    growth_repo: GrowthRepository = Depends(get_growth_repository),
    learning_repo: LearningRepository = Depends(get_learning_repository),
    classroom_repo: ClassroomRepository = Depends(get_classroom_repository),
) -> VerifiedProgressService:
    return VerifiedProgressService(
        growth_repo=growth_repo,
        learning_repo=learning_repo,
        classroom_repo=classroom_repo,
    )


def get_notification_repository(
    session: AsyncSession = Depends(get_db_session),
) -> NotificationRepository:
    return SQLAlchemyNotificationRepository(session)


def get_notification_service(
    notification_repo: NotificationRepository = Depends(get_notification_repository),
    classroom_repo: ClassroomRepository = Depends(get_classroom_repository),
    growth_repo: GrowthRepository = Depends(get_growth_repository),
) -> NotificationService:
    return NotificationService(
        notification_repo=notification_repo,
        classroom_repo=classroom_repo,
        growth_repo=growth_repo,
    )


def get_classroom_course_service(
    repo: ClassroomRepository = Depends(get_classroom_repository),
) -> ClassroomCourseService:
    return ClassroomCourseService(repo=repo)


def get_assignment_service(
    repo: ClassroomRepository = Depends(get_classroom_repository),
    problem_repo: ProblemRepository = Depends(get_problem_repository),
    execution_service: ExecutionService = Depends(get_execution_service),
) -> AssignmentService:
    return AssignmentService(
        repo=repo,
        problem_repo=problem_repo,
        execution_service=execution_service,
    )


def get_grading_service(
    repo: ClassroomRepository = Depends(get_classroom_repository),
    assignment_service: AssignmentService = Depends(get_assignment_service),
) -> GradingService:
    return GradingService(repo=repo, assignment_service=assignment_service)


def get_teacher_analytics_service(
    repo: ClassroomRepository = Depends(get_classroom_repository),
    course_service: ClassroomCourseService = Depends(get_classroom_course_service),
    assignment_service: AssignmentService = Depends(get_assignment_service),
) -> TeacherAnalyticsService:
    return TeacherAnalyticsService(
        repo=repo,
        course_service=course_service,
        assignment_service=assignment_service,
    )


def get_admin_repository(
    session: AsyncSession = Depends(get_db_session),
) -> AdminRepository:
    return AdminRepository(session)


def get_admin_overview_service(
    repo: AdminRepository = Depends(get_admin_repository),
) -> AdminOverviewService:
    return AdminOverviewService(repo=repo)


def get_admin_curriculum_service(
    admin_repo: AdminRepository = Depends(get_admin_repository),
    learning_repo: LearningRepository = Depends(get_learning_repository),
    problem_repo: ProblemRepository = Depends(get_problem_repository),
    judge0: Judge0Client = Depends(get_judge0_client),
    rag_service: RagKnowledgeService = Depends(get_rag_knowledge_service),
) -> AdminCurriculumService:
    return AdminCurriculumService(
        admin_repo=admin_repo,
        learning_repo=learning_repo,
        problem_repo=problem_repo,
        judge0=judge0,
        rag_service=rag_service,
    )


async def get_current_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    verifier: SupabaseJWTVerifier = Depends(get_jwt_verifier),
) -> AuthenticatedPrincipal:
    """Verify Bearer JWT on every protected route."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AppError(
            code="UNAUTHORIZED",
            message="Missing or invalid Authorization header.",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
    return await verifier.verify_token(credentials.credentials)


async def get_current_user(
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    service: IdentityService = Depends(get_identity_service),
) -> UserRecord:
    """Resolve authenticated user along with authoritative DB-backed roles."""
    return await service.resolve_authenticated_user(principal)


def require_roles(
    *allowed_roles: RoleName,
) -> Callable[[UserRecord], Coroutine[Any, Any, UserRecord]]:
    """Dependency enforcing DB-backed role membership."""
    allowed_set = frozenset(allowed_roles)

    async def _role_guard(
        current_user: UserRecord = Depends(get_current_user),
    ) -> UserRecord:
        if not any(role in allowed_set for role in current_user.roles):
            raise AppError(
                code="FORBIDDEN",
                message="You do not have permission to perform this action.",
                status_code=status.HTTP_403_FORBIDDEN,
            )
        return current_user

    return _role_guard
