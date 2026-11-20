"""Phase 6 student API endpoints: Learning DNA, Daily Plan, Learning History & Retention."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.v1.deps import (
    get_daily_plan_service,
    get_learning_dna_service,
    get_learning_history_service,
    get_retention_service,
    require_roles,
)
from app.repositories.identity import UserRecord
from app.schemas.growth import (
    DailyLearningPlanView,
    DailyPlanWorkspaceView,
    HistoryCategory,
    LearningDnaProfileView,
    LearningHistoryResponseView,
    RegenerateDailyPlanRequest,
    RetentionAttemptView,
    RetentionOverviewView,
    SubmitRetentionAttemptRequest,
    UpdateDailyTaskStatusRequest,
)
from app.services.growth.daily_plan_service import DailyPlanService
from app.services.growth.dna_service import LearningDnaService
from app.services.growth.history_service import LearningHistoryService
from app.services.growth.retention_service import RetentionVerificationService

growth_router = APIRouter(prefix="/growth", tags=["growth-phase6"])

_STUDENT_ROLES = require_roles("student", "teacher", "admin")


@growth_router.get("/learning-dna", response_model=LearningDnaProfileView)
async def get_learning_dna(
    user: UserRecord = Depends(_STUDENT_ROLES),
    service: LearningDnaService = Depends(get_learning_dna_service),
) -> LearningDnaProfileView:
    """Compute and return the student's evidence-based Learning DNA profile."""
    return await service.compute_and_persist_profile(user)


@growth_router.get("/daily-plan", response_model=DailyPlanWorkspaceView)
async def get_daily_plan(
    user: UserRecord = Depends(_STUDENT_ROLES),
    service: DailyPlanService = Depends(get_daily_plan_service),
) -> DailyPlanWorkspaceView:
    """Return today's active Adaptive Daily Learning Plan plus recent plan history."""
    return await service.get_today_workspace(user)


@growth_router.post(
    "/daily-plan/regenerate",
    response_model=DailyPlanWorkspaceView,
    status_code=status.HTTP_201_CREATED,
)
async def regenerate_daily_plan(
    payload: RegenerateDailyPlanRequest,
    user: UserRecord = Depends(_STUDENT_ROLES),
    service: DailyPlanService = Depends(get_daily_plan_service),
) -> DailyPlanWorkspaceView:
    """Regenerate today's Adaptive Daily Learning Plan, preserving previous versions in history."""
    return await service.regenerate_today_plan(
        user=user, available_minutes=payload.available_minutes
    )


@growth_router.patch(
    "/daily-plan/tasks/{task_id}",
    response_model=DailyLearningPlanView,
)
async def update_daily_plan_task(
    task_id: UUID,
    payload: UpdateDailyTaskStatusRequest,
    user: UserRecord = Depends(_STUDENT_ROLES),
    service: DailyPlanService = Depends(get_daily_plan_service),
) -> DailyLearningPlanView:
    """Update a daily plan task's completion status."""
    return await service.update_task_status(user=user, task_id=task_id, payload=payload)


@growth_router.get("/history", response_model=LearningHistoryResponseView)
async def get_learning_history(
    q: str | None = Query(default=None, max_length=120),
    category: HistoryCategory | None = Query(default=None),
    limit: int = Query(default=40, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: UserRecord = Depends(_STUDENT_ROLES),
    service: LearningHistoryService = Depends(get_learning_history_service),
) -> LearningHistoryResponseView:
    """Return the searchable, persistent longitudinal timeline for the authenticated student."""
    return await service.get_timeline(user=user, q=q, category=category, limit=limit, offset=offset)


@growth_router.get("/retention", response_model=RetentionOverviewView)
async def get_retention_overview(
    user: UserRecord = Depends(_STUDENT_ROLES),
    service: RetentionVerificationService = Depends(get_retention_service),
) -> RetentionOverviewView:
    """Sync eligible retention schedules and return upcoming/due checks + recent Judge0 attempts."""
    return await service.get_retention_overview(user)


@growth_router.post(
    "/retention/{schedule_id}/attempts",
    response_model=RetentionAttemptView,
    status_code=status.HTTP_201_CREATED,
)
async def submit_retention_attempt(
    schedule_id: UUID,
    payload: SubmitRetentionAttemptRequest,
    user: UserRecord = Depends(_STUDENT_ROLES),
    service: RetentionVerificationService = Depends(get_retention_service),
) -> RetentionAttemptView:
    """Execute a real Judge0 retention check and enforce the >=24h retention invariant."""
    return await service.submit_retention_attempt(
        user=user, schedule_id=schedule_id, payload=payload
    )
