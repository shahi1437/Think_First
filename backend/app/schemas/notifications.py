"""Pydantic schemas for the In-App Notification Center and Teacher Announcements."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.identity import RoleName

NotificationCategory = Literal[
    "assignment",
    "submission_feedback",
    "grading",
    "announcement",
    "classroom",
    "ai_reminder",
    "system",
]


class NotificationItemView(BaseModel):
    """Single role-scoped in-app notification returned to its recipient."""

    id: UUID
    recipient_role: RoleName
    category: NotificationCategory
    title: str
    body: str
    href: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    is_read: bool
    read_at: datetime | None = None
    created_at: datetime


class NotificationListResponse(BaseModel):
    """Paginated notification list with accurate unread badge count."""

    items: list[NotificationItemView]
    total: int
    unread_count: int
    limit: int
    offset: int


class NotificationReadAllRequest(BaseModel):
    """Optional role filter when marking all unread notifications as read."""

    model_config = ConfigDict(extra="forbid")

    role: RoleName | None = None


class NotificationReadAllResponse(BaseModel):
    """Result of marking all unread notifications as read."""

    marked_count: int
    unread_count: int


class TeacherAnnouncementCreateRequest(BaseModel):
    """Teacher request to broadcast an in-app announcement to active students in a class."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., min_length=3, max_length=140)
    body: str = Field(..., min_length=5, max_length=1200)


class TeacherAnnouncementResponse(BaseModel):
    """Confirmation of a delivered classroom announcement."""

    course_id: UUID
    course_code: str
    recipients_notified: int
    title: str
    created_at: datetime
