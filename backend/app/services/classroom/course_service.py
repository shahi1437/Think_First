"""Classroom & Course Management service with secure join codes and RBAC."""

from __future__ import annotations

import hashlib
import secrets
import time
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import status

from app.core.errors import AppError
from app.models.classroom import ClassInvitation, Course
from app.repositories.classroom import ClassroomRepository
from app.repositories.identity import UserRecord
from app.schemas.classroom import (
    ClassInvitationView,
    CourseCreateRequest,
    CourseSummaryView,
    CourseUpdateRequest,
    InvitationCreateRequest,
    JoinClassRequest,
    MembershipActionRequest,
    RosterMemberView,
    StudentEnrolledCourseView,
)

# Unambiguous high-entropy alphabet (32 chars => 10 chars = 50 bits entropy)
_INVITE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
_JOIN_RATE_WINDOW_SEC = 60.0
_JOIN_RATE_MAX_ATTEMPTS = 10
_join_attempts_by_user: dict[UUID, list[float]] = defaultdict(list)


def hash_invite_code(raw_code: str) -> str:
    normalized = raw_code.strip().upper().replace(" ", "")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def generate_invite_code() -> str:
    part_a = "".join(secrets.choice(_INVITE_ALPHABET) for _ in range(5))
    part_b = "".join(secrets.choice(_INVITE_ALPHABET) for _ in range(5))
    return f"CM-{part_a}-{part_b}"


def _check_join_rate_limit(student_id: UUID) -> None:
    now = time.monotonic()
    recent = [t for t in _join_attempts_by_user[student_id] if now - t <= _JOIN_RATE_WINDOW_SEC]
    if len(recent) >= _JOIN_RATE_MAX_ATTEMPTS:
        raise AppError(
            code="INVITE_RATE_LIMITED",
            message="Too many class join attempts. Please wait a minute and try again.",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )
    recent.append(now)
    _join_attempts_by_user[student_id] = recent


def _invitation_to_view(inv: ClassInvitation) -> ClassInvitationView:
    return ClassInvitationView(
        id=inv.id,
        course_id=inv.course_id,
        code_preview=inv.code_preview,
        max_uses=inv.max_uses,
        uses_count=inv.uses_count,
        expires_at=inv.expires_at,
        is_active=inv.is_active,
        created_at=inv.created_at,
    )


class ClassroomCourseService:
    """Manages teacher classes, secure invitations, and authorized student enrollments."""

    def __init__(self, *, repo: ClassroomRepository) -> None:
        self._repo = repo

    def _assert_course_owner(self, *, user: UserRecord, course: Course) -> None:
        if course.teacher_id != user.id and "admin" not in user.roles:
            raise AppError(
                code="FORBIDDEN",
                message="You are not authorized to access or modify this class.",
                status_code=status.HTTP_403_FORBIDDEN,
            )

    async def _course_to_summary(self, course: Course) -> CourseSummaryView:
        profiles = await self._repo.get_profiles_map([course.teacher_id])
        teacher_profile = profiles.get(course.teacher_id)
        counts = await self._repo.count_course_memberships([course.id])
        active_cnt, pending_cnt = counts.get(course.id, (0, 0))
        assignments = await self._repo.list_assignments_for_courses([course.id])
        return CourseSummaryView(
            id=course.id,
            teacher_id=course.teacher_id,
            teacher_name=teacher_profile.full_name if teacher_profile else "Instructor",
            code=course.code,
            title=course.title,
            description=course.description,
            term=course.term,
            enrollment_policy=course.enrollment_policy,
            allow_student_leave=course.allow_student_leave,
            status=course.status,
            active_students_count=active_cnt,
            pending_students_count=pending_cnt,
            assignments_count=len(assignments),
            created_at=course.created_at,
            updated_at=course.updated_at,
        )

    async def create_course(
        self, *, teacher: UserRecord, payload: CourseCreateRequest
    ) -> CourseSummaryView:
        course = await self._repo.create_course(
            teacher_id=teacher.id,
            code=payload.code,
            title=payload.title,
            description=payload.description,
            term=payload.term,
            enrollment_policy=payload.enrollment_policy,
            allow_student_leave=payload.allow_student_leave,
        )
        # Auto-generate an initial active invite code so the teacher can onboard students immediately
        raw_code = generate_invite_code()
        await self._repo.create_invitation(
            course_id=course.id,
            created_by=teacher.id,
            code_hash=hash_invite_code(raw_code),
            code_preview=raw_code,
            max_uses=None,
            expires_at=datetime.now(UTC) + timedelta(days=30),
        )
        return await self._course_to_summary(course)

    async def list_teacher_courses(self, teacher: UserRecord) -> list[CourseSummaryView]:
        courses = await self._repo.list_teacher_courses(teacher.id)
        if not courses:
            return []
        course_ids = [c.id for c in courses]
        counts = await self._repo.count_course_memberships(course_ids)
        assignments = await self._repo.list_assignments_for_courses(course_ids)
        asg_count_by_course: dict[UUID, int] = defaultdict(int)
        for a in assignments:
            asg_count_by_course[a.course_id] += 1
        profiles = await self._repo.get_profiles_map([c.teacher_id for c in courses])

        views: list[CourseSummaryView] = []
        for c in courses:
            active_cnt, pending_cnt = counts.get(c.id, (0, 0))
            tp = profiles.get(c.teacher_id)
            views.append(
                CourseSummaryView(
                    id=c.id,
                    teacher_id=c.teacher_id,
                    teacher_name=tp.full_name if tp else teacher.full_name,
                    code=c.code,
                    title=c.title,
                    description=c.description,
                    term=c.term,
                    enrollment_policy=c.enrollment_policy,
                    allow_student_leave=c.allow_student_leave,
                    status=c.status,
                    active_students_count=active_cnt,
                    pending_students_count=pending_cnt,
                    assignments_count=asg_count_by_course.get(c.id, 0),
                    created_at=c.created_at,
                    updated_at=c.updated_at,
                )
            )
        return views

    async def update_course(
        self, *, teacher: UserRecord, course_id: UUID, payload: CourseUpdateRequest
    ) -> CourseSummaryView:
        course = await self._repo.get_course_by_id(course_id)
        if course is None:
            raise AppError(
                code="COURSE_NOT_FOUND",
                message="Class was not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        self._assert_course_owner(user=teacher, course=course)
        if payload.code is not None:
            course.code = payload.code.strip().upper()
        if payload.title is not None:
            course.title = payload.title.strip()
        if payload.description is not None:
            course.description = payload.description.strip()
        if payload.term is not None:
            course.term = payload.term.strip()
        if payload.enrollment_policy is not None:
            course.enrollment_policy = payload.enrollment_policy
        if payload.allow_student_leave is not None:
            course.allow_student_leave = payload.allow_student_leave
        saved = await self._repo.update_course(course)
        return await self._course_to_summary(saved)

    async def archive_course(
        self, *, teacher: UserRecord, course_id: UUID, archive: bool = True
    ) -> CourseSummaryView:
        course = await self._repo.get_course_by_id(course_id)
        if course is None:
            raise AppError(
                code="COURSE_NOT_FOUND",
                message="Class was not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        self._assert_course_owner(user=teacher, course=course)
        course.status = "archived" if archive else "active"
        course.archived_at = datetime.now(UTC) if archive else None
        saved = await self._repo.update_course(course)
        return await self._course_to_summary(saved)

    async def create_invitation(
        self, *, teacher: UserRecord, course_id: UUID, payload: InvitationCreateRequest
    ) -> ClassInvitationView:
        course = await self._repo.get_course_by_id(course_id)
        if course is None:
            raise AppError(
                code="COURSE_NOT_FOUND",
                message="Class was not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        self._assert_course_owner(user=teacher, course=course)
        if course.status != "active":
            raise AppError(
                code="COURSE_ARCHIVED",
                message="Cannot create invitation codes for an archived class.",
                status_code=status.HTTP_409_CONFLICT,
            )
        raw_code = generate_invite_code()
        expires_at = (
            datetime.now(UTC) + timedelta(hours=payload.expires_in_hours)
            if payload.expires_in_hours
            else None
        )
        inv = await self._repo.create_invitation(
            course_id=course.id,
            created_by=teacher.id,
            code_hash=hash_invite_code(raw_code),
            code_preview=raw_code,
            max_uses=payload.max_uses,
            expires_at=expires_at,
        )
        return _invitation_to_view(inv)

    async def revoke_invitation(
        self, *, teacher: UserRecord, course_id: UUID, invitation_id: UUID
    ) -> ClassInvitationView:
        course = await self._repo.get_course_by_id(course_id)
        if course is None:
            raise AppError(
                code="COURSE_NOT_FOUND",
                message="Class was not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        self._assert_course_owner(user=teacher, course=course)
        inv = await self._repo.get_invitation_by_id(invitation_id)
        if inv is None or inv.course_id != course.id:
            raise AppError(
                code="INVITATION_NOT_FOUND",
                message="Invitation code was not found for this class.",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        inv.is_active = False
        saved = await self._repo.save_invitation(inv)
        return _invitation_to_view(saved)

    async def list_course_roster(
        self, *, teacher: UserRecord, course_id: UUID
    ) -> list[RosterMemberView]:
        course = await self._repo.get_course_by_id(course_id)
        if course is None:
            raise AppError(
                code="COURSE_NOT_FOUND",
                message="Class was not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        self._assert_course_owner(user=teacher, course=course)
        members = await self._repo.list_course_memberships(course_id)
        profiles = await self._repo.get_profiles_map([m.student_id for m in members])
        attempts = await self._repo.list_attempts_for_courses([course_id])
        stats: dict[UUID, list[int]] = defaultdict(lambda: [0, 0, 0])
        for att in attempts:
            stats[att.student_id][0] += 1
            if att.verdict == "accepted":
                stats[att.student_id][1] += 1
            stats[att.student_id][2] += att.hints_used

        roster: list[RosterMemberView] = []
        for m in members:
            prof = profiles.get(m.student_id)
            st = stats[m.student_id]
            roster.append(
                RosterMemberView(
                    membership_id=m.id,
                    student_id=m.student_id,
                    full_name=prof.full_name if prof else "Student",
                    email=prof.email if prof else "",
                    status=m.status,
                    joined_at=m.joined_at,
                    approved_at=m.approved_at,
                    submissions_count=st[0],
                    accepted_attempts_count=st[1],
                    hints_used_total=st[2],
                )
            )
        return roster

    async def manage_membership(
        self,
        *,
        teacher: UserRecord,
        course_id: UUID,
        membership_id: UUID,
        payload: MembershipActionRequest,
    ) -> RosterMemberView:
        course = await self._repo.get_course_by_id(course_id)
        if course is None:
            raise AppError(
                code="COURSE_NOT_FOUND",
                message="Class was not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        self._assert_course_owner(user=teacher, course=course)
        m = await self._repo.get_membership_by_id(membership_id)
        if m is None or m.course_id != course.id:
            raise AppError(
                code="MEMBERSHIP_NOT_FOUND",
                message="Student membership not found in this class.",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        now = datetime.now(UTC)
        if payload.action == "approve":
            m.status = "active"
            m.approved_by = teacher.id
            m.approved_at = now
            m.removed_at = None
        else:
            m.status = "removed"
            m.removed_at = now
        saved = await self._repo.save_membership(m)
        profiles = await self._repo.get_profiles_map([saved.student_id])
        prof = profiles.get(saved.student_id)
        return RosterMemberView(
            membership_id=saved.id,
            student_id=saved.student_id,
            full_name=prof.full_name if prof else "Student",
            email=prof.email if prof else "",
            status=saved.status,
            joined_at=saved.joined_at,
            approved_at=saved.approved_at,
        )

    # ------------------------------------------------------------------
    # Student Enrollment Actions
    # ------------------------------------------------------------------

    async def join_class_with_code(
        self, *, student: UserRecord, payload: JoinClassRequest
    ) -> StudentEnrolledCourseView:
        _check_join_rate_limit(student.id)
        code_hash = hash_invite_code(payload.invite_code)
        inv = await self._repo.get_invitation_by_hash(code_hash)
        if inv is None or not inv.is_active:
            raise AppError(
                code="INVALID_INVITE_CODE",
                message="Class invitation code is invalid or has been revoked.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        now = datetime.now(UTC)
        if inv.expires_at is not None and inv.expires_at < now:
            raise AppError(
                code="INVITE_CODE_EXPIRED",
                message="This class invitation code has expired.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        if inv.max_uses is not None and inv.uses_count >= inv.max_uses:
            raise AppError(
                code="INVITE_CODE_EXHAUSTED",
                message="This class invitation code has reached its maximum number of uses.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        course = await self._repo.get_course_by_id(inv.course_id)
        if course is None or course.status != "active":
            raise AppError(
                code="COURSE_NOT_ACTIVE",
                message="This class is archived and no longer accepting enrollments.",
                status_code=status.HTTP_409_CONFLICT,
            )

        existing = await self._repo.get_membership(course_id=course.id, student_id=student.id)
        if existing is not None and existing.status == "active":
            raise AppError(
                code="ALREADY_ENROLLED",
                message="You are already enrolled in this class.",
                status_code=status.HTTP_409_CONFLICT,
            )
        if existing is not None and existing.status == "removed":
            raise AppError(
                code="MEMBERSHIP_REMOVED",
                message="Your membership was removed by the instructor. Contact your teacher for re-approval.",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        initial_status = "pending" if course.enrollment_policy == "approval_required" else "active"
        membership = await self._repo.upsert_membership_from_invite(
            course_id=course.id,
            student_id=student.id,
            invitation=inv,
            initial_status=initial_status,
        )
        profiles = await self._repo.get_profiles_map([course.teacher_id])
        tp = profiles.get(course.teacher_id)
        published_asgs = await self._repo.list_assignments_for_courses(
            [course.id], published_only=True
        )
        return StudentEnrolledCourseView(
            membership_id=membership.id,
            course_id=course.id,
            code=course.code,
            title=course.title,
            description=course.description,
            term=course.term,
            teacher_name=tp.full_name if tp else "Instructor",
            course_status=course.status,
            membership_status=membership.status,
            allow_student_leave=course.allow_student_leave,
            published_assignments_count=len(published_asgs),
            joined_at=membership.joined_at,
        )

    async def list_student_courses(self, student: UserRecord) -> list[StudentEnrolledCourseView]:
        rows = await self._repo.list_student_memberships(student.id)
        if not rows:
            return []
        teacher_ids = [c.teacher_id for _, c in rows]
        course_ids = [c.id for _, c in rows]
        profiles = await self._repo.get_profiles_map(teacher_ids)
        published = await self._repo.list_assignments_for_courses(course_ids, published_only=True)
        asg_count: dict[UUID, int] = defaultdict(int)
        for a in published:
            asg_count[a.course_id] += 1

        out: list[StudentEnrolledCourseView] = []
        for m, c in rows:
            tp = profiles.get(c.teacher_id)
            out.append(
                StudentEnrolledCourseView(
                    membership_id=m.id,
                    course_id=c.id,
                    code=c.code,
                    title=c.title,
                    description=c.description,
                    term=c.term,
                    teacher_name=tp.full_name if tp else "Instructor",
                    course_status=c.status,
                    membership_status=m.status,
                    allow_student_leave=c.allow_student_leave,
                    published_assignments_count=asg_count.get(c.id, 0),
                    joined_at=m.joined_at,
                )
            )
        return out

    async def leave_class(self, *, student: UserRecord, course_id: UUID) -> None:
        course = await self._repo.get_course_by_id(course_id)
        if course is None:
            raise AppError(
                code="COURSE_NOT_FOUND",
                message="Class was not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        if not course.allow_student_leave:
            raise AppError(
                code="LEAVE_DISABLED",
                message="Self-unenrollment is disabled by the instructor for this class.",
                status_code=status.HTTP_403_FORBIDDEN,
            )
        m = await self._repo.get_membership(course_id=course_id, student_id=student.id)
        if m is None or m.status not in ("active", "pending"):
            raise AppError(
                code="MEMBERSHIP_NOT_FOUND",
                message="You are not actively enrolled in this class.",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        m.status = "left"
        m.removed_at = datetime.now(UTC)
        await self._repo.save_membership(m)
