"""Role-scoped In-App Notification Center service backed by persisted PostgreSQL data."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import status

from app.core.errors import AppError
from app.repositories.classroom import ClassroomRepository
from app.repositories.growth import GrowthRepository
from app.repositories.identity import UserRecord
from app.repositories.notifications import NotificationRepository
from app.schemas.identity import RoleName
from app.schemas.notifications import (
    NotificationCategory,
    NotificationItemView,
    NotificationListResponse,
    NotificationReadAllResponse,
    TeacherAnnouncementCreateRequest,
    TeacherAnnouncementResponse,
)


def _to_item_view(row: Any) -> NotificationItemView:
    role_val = str(row.recipient_role)
    resolved_role: RoleName = (
        role_val if role_val in ("student", "teacher", "admin") else "student"  # type: ignore[assignment]
    )
    cat_val = str(row.category)
    resolved_cat: NotificationCategory = (
        cat_val  # type: ignore[assignment]
        if cat_val
        in (
            "assignment",
            "submission_feedback",
            "grading",
            "announcement",
            "classroom",
            "ai_reminder",
            "system",
        )
        else "system"
    )
    return NotificationItemView(
        id=row.id,
        recipient_role=resolved_role,
        category=resolved_cat,
        title=row.title,
        body=row.body,
        href=row.href,
        metadata=dict(row.metadata_json or {}),
        is_read=bool(row.is_read),
        read_at=row.read_at,
        created_at=row.created_at,
    )


class NotificationService:
    """Derives real idempotent notifications and delivers explicit classroom announcements."""

    def __init__(
        self,
        *,
        notification_repo: NotificationRepository,
        classroom_repo: ClassroomRepository | None = None,
        growth_repo: GrowthRepository | None = None,
    ) -> None:
        self._repo = notification_repo
        self._classroom_repo = classroom_repo
        self._growth_repo = growth_repo

    async def _sync_student_notifications(self, user: UserRecord) -> None:
        if self._classroom_repo is not None:
            memberships = await self._classroom_repo.list_student_memberships(student_id=user.id)
            active_course_ids: list[UUID] = []
            for mem, course in memberships:
                if mem.status == "active":
                    active_course_ids.append(course.id)
                    await self._repo.upsert_notification_by_source_key(
                        recipient_user_id=user.id,
                        actor_user_id=course.teacher_id,
                        recipient_role="student",
                        category="classroom",
                        title=f"Enrolled in {course.code}: {course.title}",
                        body=(
                            f"You are actively enrolled in {course.title}. "
                            "Check published assignments and deadlines in your classroom workspace."
                        ),
                        href="/student/classes",
                        source_key=f"student:enrolled:{mem.id}",
                        metadata={"course_id": str(course.id), "course_code": course.code},
                    )
            if active_course_ids:
                assignments = await self._classroom_repo.list_assignments_for_courses(
                    course_ids=active_course_ids, published_only=True
                )
                subs_by_asn = await self._classroom_repo.list_submissions_for_student(
                    student_id=user.id, assignment_ids=[a.id for a in assignments]
                )
                for asn in assignments:
                    due_note = (
                        f" Due {asn.due_at.strftime('%b %d, %Y %H:%M UTC')}."
                        if asn.due_at is not None
                        else ""
                    )
                    await self._repo.upsert_notification_by_source_key(
                        recipient_user_id=user.id,
                        actor_user_id=asn.teacher_id,
                        recipient_role="student",
                        category="assignment",
                        title=f"Assignment published: {asn.title}",
                        body=f"New classroom coding assignment available.{due_note}",
                        href=f"/student/assignments/{asn.id}",
                        source_key=f"student:assignment:{asn.id}",
                        metadata={"assignment_id": str(asn.id)},
                    )
                    sub = subs_by_asn.get(asn.id)
                    if sub is None:
                        continue
                    if sub.status == "revision_requested":
                        await self._repo.upsert_notification_by_source_key(
                            recipient_user_id=user.id,
                            actor_user_id=asn.teacher_id,
                            recipient_role="student",
                            category="submission_feedback",
                            title=f"Revision requested: {asn.title}",
                            body=(
                                "Your instructor requested a revision on your assignment "
                                "submission. Review the feedback and resubmit."
                            ),
                            href=f"/student/assignments/{asn.id}",
                            source_key=f"student:revision:{sub.id}:{sub.attempts_used}",
                            metadata={"assignment_id": str(asn.id)},
                        )
                    grade = sub.grade
                    if grade is not None and grade.status == "published":
                        await self._repo.upsert_notification_by_source_key(
                            recipient_user_id=user.id,
                            actor_user_id=grade.graded_by,
                            recipient_role="student",
                            category="grading",
                            title=f"Grade published: {asn.title}",
                            body=(
                                f"Awarded {grade.marks_awarded} / {grade.max_marks}. "
                                "Open the assignment to review instructor feedback."
                            ),
                            href=f"/student/assignments/{asn.id}",
                            source_key=f"student:grade:{grade.id}",
                            metadata={
                                "assignment_id": str(asn.id),
                                "marks_awarded": float(grade.marks_awarded),
                                "max_marks": float(grade.max_marks),
                            },
                        )

        if self._growth_repo is not None:
            schedules = await self._growth_repo.list_retention_schedules(student_id=user.id)
            now = datetime.now(UTC)
            for sched in schedules:
                if sched.status in ("due", "needs_review") or (
                    sched.status == "scheduled" and sched.due_at <= now
                ):
                    await self._repo.upsert_notification_by_source_key(
                        recipient_user_id=user.id,
                        actor_user_id=None,
                        recipient_role="student",
                        category="ai_reminder",
                        title=f"Spaced retention check due: {sched.skill_slug}",
                        body=(
                            f"24-hour spaced verification is ready for skill '{sched.skill_slug}' "
                            f"({sched.language_slug}). Pass without hints to verify retention."
                        ),
                        href="/student/retention",
                        source_key=f"student:retention:{sched.id}:{sched.due_at.date().isoformat()}",
                        metadata={
                            "skill_slug": sched.skill_slug,
                            "language_slug": sched.language_slug,
                        },
                    )

    async def _sync_teacher_notifications(self, user: UserRecord) -> None:
        if self._classroom_repo is None or "teacher" not in user.roles:
            return
        courses = await self._classroom_repo.list_teacher_courses(teacher_id=user.id)
        if not courses:
            return
        course_ids = [c.id for c in courses]
        assignments = await self._classroom_repo.list_assignments_for_courses(
            course_ids=course_ids, published_only=False
        )
        for asn in assignments:
            subs = await self._classroom_repo.list_submissions_for_assignment(assignment_id=asn.id)
            for sub in subs:
                if sub.status in ("submitted", "resubmitted"):
                    latest_verdict = sub.attempts[0].verdict if sub.attempts else "pending"
                    await self._repo.upsert_notification_by_source_key(
                        recipient_user_id=user.id,
                        actor_user_id=sub.student_id,
                        recipient_role="teacher",
                        category="submission_feedback",
                        title=f"Submission ready to grade: {asn.title}",
                        body=(
                            f"A student {sub.status} attempt #{sub.attempts_used} "
                            f"(latest verdict: {latest_verdict})."
                        ),
                        href=f"/teacher/assignments/{asn.id}",
                        source_key=f"teacher:sub:{sub.id}:{sub.attempts_used}",
                        metadata={"assignment_id": str(asn.id)},
                    )

    async def list_notifications(
        self,
        *,
        user: UserRecord,
        role: RoleName | None = None,
        category: NotificationCategory | None = None,
        unread_only: bool = False,
        limit: int = 30,
        offset: int = 0,
    ) -> NotificationListResponse:
        # Enforce strict RBAC on role filter: users may only query roles they actually hold
        effective_role: RoleName | None = role
        if effective_role is not None and effective_role not in user.roles:
            raise AppError(
                code="FORBIDDEN",
                message="You cannot inspect notifications for an unauthorized role.",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        if effective_role in (None, "student") and "student" in user.roles:
            await self._sync_student_notifications(user)
        if effective_role in (None, "teacher") and "teacher" in user.roles:
            await self._sync_teacher_notifications(user)

        rows, total, unread_count = await self._repo.list_notifications(
            recipient_user_id=user.id,
            role=effective_role,
            category=category,
            unread_only=unread_only,
            limit=limit,
            offset=offset,
        )
        return NotificationListResponse(
            items=[_to_item_view(r) for r in rows],
            total=total,
            unread_count=unread_count,
            limit=limit,
            offset=offset,
        )

    async def mark_read(
        self,
        *,
        user: UserRecord,
        notification_id: UUID,
    ) -> NotificationItemView:
        updated = await self._repo.mark_read(
            recipient_user_id=user.id,
            notification_id=notification_id,
        )
        if updated is None:
            raise AppError(
                code="NOTIFICATION_NOT_FOUND",
                message="Notification not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        return _to_item_view(updated)

    async def mark_all_read(
        self,
        *,
        user: UserRecord,
        role: RoleName | None = None,
    ) -> NotificationReadAllResponse:
        if role is not None and role not in user.roles:
            raise AppError(
                code="FORBIDDEN",
                message="You cannot modify notifications for an unauthorized role.",
                status_code=status.HTTP_403_FORBIDDEN,
            )
        marked = await self._repo.mark_all_read(recipient_user_id=user.id, role=role)
        _, _, remaining_unread = await self._repo.list_notifications(
            recipient_user_id=user.id,
            role=role,
            limit=1,
            offset=0,
        )
        return NotificationReadAllResponse(
            marked_count=marked,
            unread_count=remaining_unread,
        )

    async def publish_course_announcement(
        self,
        *,
        teacher: UserRecord,
        course_id: UUID,
        payload: TeacherAnnouncementCreateRequest,
    ) -> TeacherAnnouncementResponse:
        if self._classroom_repo is None:
            raise AppError(
                code="SERVICE_UNAVAILABLE",
                message="Classroom repository unavailable.",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        course = await self._classroom_repo.get_course_by_id(course_id)
        if course is None:
            raise AppError(
                code="COURSE_NOT_FOUND",
                message="Course not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        if course.teacher_id != teacher.id and "admin" not in teacher.roles:
            raise AppError(
                code="FORBIDDEN",
                message="Only the assigned teacher or an admin can post class announcements.",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        roster = await self._classroom_repo.list_course_memberships(course_id=course.id)
        notified = 0
        now = datetime.now(UTC)
        clean_title = payload.title.strip()
        clean_body = payload.body.strip()
        for mem in roster:
            if mem.status != "active":
                continue
            await self._repo.create_notification(
                recipient_user_id=mem.student_id,
                actor_user_id=teacher.id,
                recipient_role="student",
                category="announcement",
                title=f"[{course.code}] {clean_title}",
                body=clean_body,
                href="/student/classes",
                metadata={
                    "course_id": str(course.id),
                    "course_code": course.code,
                    "teacher_name": teacher.full_name or teacher.email,
                },
            )
            notified += 1

        return TeacherAnnouncementResponse(
            course_id=course.id,
            course_code=course.code,
            recipients_notified=notified,
            title=clean_title,
            created_at=now,
        )
