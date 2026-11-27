"""API endpoints for the In-App Notification Center and Teacher Classroom Announcements."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.v1.deps import get_notification_service, require_roles
from app.repositories.identity import UserRecord
from app.schemas.identity import RoleName
from app.schemas.notifications import (
    NotificationCategory,
    NotificationItemView,
    NotificationListResponse,
    NotificationReadAllRequest,
    NotificationReadAllResponse,
    TeacherAnnouncementCreateRequest,
    TeacherAnnouncementResponse,
)
from app.services.notifications.service import NotificationService

notifications_router = APIRouter(prefix="/notifications", tags=["Notifications"])
teacher_announcements_router = APIRouter(prefix="/teacher/classes", tags=["Teacher Announcements"])

_ANY_ROLE = require_roles("student", "teacher", "admin")
_TEACHER_ROLES = require_roles("teacher", "admin")


@notifications_router.get("", response_model=NotificationListResponse)
async def list_notifications(
    role: RoleName | None = Query(default=None),
    category: NotificationCategory | None = Query(default=None),
    unread_only: bool = Query(default=False),
    limit: int = Query(default=30, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: UserRecord = Depends(_ANY_ROLE),
    service: NotificationService = Depends(get_notification_service),
) -> NotificationListResponse:
    """List role-scoped in-app notifications with unread badge count."""
    return await service.list_notifications(
        user=user,
        role=role,
        category=category,
        unread_only=unread_only,
        limit=limit,
        offset=offset,
    )


@notifications_router.patch(
    "/{notification_id}/read",
    response_model=NotificationItemView,
)
async def mark_notification_read(
    notification_id: UUID,
    user: UserRecord = Depends(_ANY_ROLE),
    service: NotificationService = Depends(get_notification_service),
) -> NotificationItemView:
    """Mark a single notification owned by the authenticated user as read."""
    return await service.mark_read(user=user, notification_id=notification_id)


@notifications_router.post(
    "/read-all",
    response_model=NotificationReadAllResponse,
)
async def mark_all_notifications_read(
    payload: NotificationReadAllRequest | None = None,
    user: UserRecord = Depends(_ANY_ROLE),
    service: NotificationService = Depends(get_notification_service),
) -> NotificationReadAllResponse:
    """Mark all unread notifications for the authenticated user as read."""
    role_filter = payload.role if payload is not None else None
    return await service.mark_all_read(user=user, role=role_filter)


@teacher_announcements_router.post(
    "/{course_id}/announcements",
    response_model=TeacherAnnouncementResponse,
    status_code=status.HTTP_201_CREATED,
)
async def post_teacher_class_announcement(
    course_id: UUID,
    payload: TeacherAnnouncementCreateRequest,
    teacher: UserRecord = Depends(_TEACHER_ROLES),
    service: NotificationService = Depends(get_notification_service),
) -> TeacherAnnouncementResponse:
    """Broadcast a real teacher announcement to active students enrolled in the course."""
    return await service.publish_course_announcement(
        teacher=teacher,
        course_id=course_id,
        payload=payload,
    )
