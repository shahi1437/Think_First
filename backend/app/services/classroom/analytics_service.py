"""Evidence-based Teacher Dashboard & Class Analytics Service.

Strictly aggregates real database evidence from authorized classes:
- Course enrollments & assignment submission counts
- Real Judge0 assignment attempt verdicts
- Own ML `error_diagnoses` misconception frequencies for enrolled students
- Skill Graph (`student_skill_states`) gap distributions
- Real AI Mentor hint usage & Phase 4 independent transfer counts
- Students needing support (explicit factual criteria: >= 2 non-accepted attempts
  or high hint reliance without accepted solve)

Never fabricates percentages, completion estimates, or AI-generated insights.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import UTC, datetime
from uuid import UUID

from fastapi import status

from app.core.errors import AppError
from app.repositories.classroom import ClassroomRepository
from app.repositories.identity import UserRecord
from app.schemas.classroom import (
    ClassAnalyticsView,
    ClassComparisonItem,
    GradeStatus,
    MembershipStatus,
    MisconceptionCountItem,
    SkillGapItem,
    SubmissionWorkflowStatus,
    SupportStudentItem,
    TeacherCourseDetailView,
    TeacherDashboardView,
    TeacherStudentAssignmentRecord,
    TeacherStudentPerformanceView,
    VerdictCountItem,
)
from app.services.classroom.assignment_service import AssignmentService
from app.services.classroom.course_service import ClassroomCourseService, _invitation_to_view


class TeacherAnalyticsService:
    """Computes evidence-backed analytics for a teacher's authorized classes."""

    def __init__(
        self,
        *,
        repo: ClassroomRepository,
        course_service: ClassroomCourseService,
        assignment_service: AssignmentService,
    ) -> None:
        self._repo = repo
        self._courses = course_service
        self._assignments = assignment_service

    async def compute_class_analytics(
        self, *, course_ids: list[UUID], course_titles: dict[UUID, str]
    ) -> ClassAnalyticsView:
        student_ids = await self._repo.list_active_student_ids_for_courses(course_ids)
        attempts = await self._repo.list_attempts_for_courses(course_ids)

        verdict_counter: Counter[str] = Counter()
        accepted_attempts = 0
        failed_by_student: dict[UUID, int] = defaultdict(int)
        accepted_by_student: dict[UUID, int] = defaultdict(int)
        hints_by_student: dict[UUID, int] = defaultdict(int)
        course_by_student: dict[UUID, UUID] = {}

        for att in attempts:
            verdict_counter[att.verdict] += 1
            course_by_student.setdefault(att.student_id, att.course_id)
            hints_by_student[att.student_id] += att.hints_used
            if att.verdict == "accepted":
                accepted_attempts += 1
                accepted_by_student[att.student_id] += 1
            else:
                failed_by_student[att.student_id] += 1

        verdict_breakdown = [
            VerdictCountItem(verdict=v, count=c) for v, c in verdict_counter.most_common()
        ]
        misconceptions = [
            MisconceptionCountItem(error_code=code, occurrences=cnt)
            for code, cnt in await self._repo.count_misconceptions_for_students(student_ids)
        ]
        skill_gaps = [
            SkillGapItem(
                skill_slug=slug,
                unobserved_or_guided_count=unobs,
                verified_count=verif,
            )
            for slug, unobs, verif in await self._repo.aggregate_skill_gaps_for_students(
                student_ids
            )
        ]
        (
            mentor_hints_total,
            verified_transfers,
        ) = await self._repo.count_hints_and_transfers_for_students(student_ids)
        total_hints = mentor_hints_total + sum(hints_by_student.values())

        support_ids = [
            sid
            for sid in student_ids
            if (failed_by_student[sid] >= 2 and accepted_by_student[sid] == 0)
            or (failed_by_student[sid] >= 1 and hints_by_student[sid] >= 2)
        ]
        profiles = await self._repo.get_profiles_map(support_ids)
        support_items: list[SupportStudentItem] = []
        for sid in support_ids[:10]:
            prof = profiles.get(sid)
            cid = course_by_student.get(sid)
            reason = (
                f"{failed_by_student[sid]} non-accepted Judge0 assignment attempt(s) "
                f"with {accepted_by_student[sid]} accepted and {hints_by_student[sid]} hint(s)."
            )
            support_items.append(
                SupportStudentItem(
                    student_id=sid,
                    full_name=prof.full_name if prof else "Student",
                    email=prof.email if prof else "",
                    course_title=course_titles.get(cid, "Class") if cid else "Class",
                    reason=reason,
                    failed_attempts=failed_by_student[sid],
                    hints_used=hints_by_student[sid],
                )
            )

        return ClassAnalyticsView(
            active_students=len(student_ids),
            total_attempts=len(attempts),
            accepted_attempts=accepted_attempts,
            verdict_breakdown=verdict_breakdown,
            common_misconceptions=misconceptions,
            skill_gaps=skill_gaps,
            total_hints_used=total_hints,
            verified_independent_transfers=verified_transfers,
            students_needing_support=support_items,
        )

    async def get_teacher_course_detail(
        self, *, teacher: UserRecord, course_id: UUID
    ) -> TeacherCourseDetailView:
        course = await self._repo.get_course_by_id(course_id)
        if course is None:
            raise AppError(
                code="COURSE_NOT_FOUND",
                message="Class was not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        if course.teacher_id != teacher.id and "admin" not in teacher.roles:
            raise AppError(
                code="FORBIDDEN",
                message="You are not authorized to inspect this class.",
                status_code=status.HTTP_403_FORBIDDEN,
            )
        summary = await self._courses._course_to_summary(course)
        invs = await self._repo.list_course_invitations(course.id)
        roster = await self._courses.list_course_roster(teacher=teacher, course_id=course.id)
        asgs = await self._assignments.list_teacher_assignments(
            teacher=teacher, course_id=course.id
        )
        analytics = await self.compute_class_analytics(
            course_ids=[course.id], course_titles={course.id: course.title}
        )
        return TeacherCourseDetailView(
            course=summary,
            invitations=[_invitation_to_view(i) for i in invs],
            roster=roster,
            assignments=asgs,
            analytics=analytics,
        )

    async def get_teacher_dashboard(self, teacher: UserRecord) -> TeacherDashboardView:
        courses = await self._courses.list_teacher_courses(teacher)
        course_ids = [c.id for c in courses]
        course_titles = {c.id: c.title for c in courses}
        all_assignments = await self._assignments.list_teacher_assignments(teacher=teacher)

        now = datetime.now(UTC)
        active_assignments = [a for a in all_assignments if a.status == "published"]
        upcoming = [a for a in active_assignments if a.due_at is not None and a.due_at >= now][:6]

        pending_grading = sum(a.pending_grading_count for a in all_assignments)
        graded_count = sum(a.graded_count for a in all_assignments)
        analytics = await self.compute_class_analytics(
            course_ids=course_ids, course_titles=course_titles
        )

        # Build factual per-class comparison from real assignments & Judge0 attempts
        all_attempts = await self._repo.list_attempts_for_courses(course_ids)
        attempts_by_course: dict[UUID, list[int]] = {cid: [0, 0] for cid in course_ids}
        for att in all_attempts:
            bucket = attempts_by_course.get(att.course_id)
            if bucket is not None:
                bucket[0] += 1
                if att.verdict == "accepted":
                    bucket[1] += 1

        comparison: list[ClassComparisonItem] = []
        for c in courses:
            c_asgs = [a for a in all_assignments if a.course_id == c.id and a.status == "published"]
            tot_att, acc_att = attempts_by_course.get(c.id, [0, 0])
            acc_pct = round((acc_att / tot_att) * 100.0, 1) if tot_att > 0 else None
            comparison.append(
                ClassComparisonItem(
                    course_id=c.id,
                    course_code=c.code,
                    course_title=c.title,
                    active_students=c.active_students_count,
                    published_assignments=len(c_asgs),
                    submitted_count=sum(a.submitted_count for a in c_asgs),
                    graded_count=sum(a.graded_count for a in c_asgs),
                    pending_grading_count=sum(a.pending_grading_count for a in c_asgs),
                    total_attempts=tot_att,
                    accepted_attempts=acc_att,
                    acceptance_rate_pct=acc_pct,
                )
            )

        return TeacherDashboardView(
            courses_count=len(courses),
            active_courses_count=sum(1 for c in courses if c.status == "active"),
            total_enrolled_students=analytics.active_students,
            active_assignments_count=len(active_assignments),
            pending_grading_count=pending_grading,
            graded_submissions_count=graded_count,
            courses=courses,
            upcoming_deadlines=upcoming,
            analytics=analytics,
            class_comparison=comparison,
            methodology_note=(
                "All dashboard counts, Judge0 verdict distributions, ML misconceptions, Skill Graph gaps, "
                "hint usage, class comparisons, and support flags are computed strictly from real database "
                "records scoped to your authorized classes."
            ),
        )

    async def get_student_performance_in_course(
        self, *, teacher: UserRecord, course_id: UUID, student_id: UUID
    ) -> TeacherStudentPerformanceView:
        """Drill-down from class analytics to a single enrolled student's real DB record."""
        course = await self._repo.get_course_by_id(course_id)
        if course is None:
            raise AppError(
                code="COURSE_NOT_FOUND",
                message="Class was not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        if course.teacher_id != teacher.id and "admin" not in teacher.roles:
            raise AppError(
                code="FORBIDDEN",
                message="You are not authorized to inspect students in this class.",
                status_code=status.HTTP_403_FORBIDDEN,
            )
        membership = await self._repo.get_membership(course_id=course_id, student_id=student_id)
        if membership is None:
            raise AppError(
                code="STUDENT_NOT_IN_CLASS",
                message="Student is not enrolled in this class.",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        profiles = await self._repo.get_profiles_map([student_id])
        prof = profiles.get(student_id)

        asns = await self._repo.list_assignments_for_courses(
            course_ids=[course_id], published_only=False
        )
        subs_map = await self._repo.list_submissions_for_student(
            student_id=student_id, assignment_ids=[a.id for a in asns]
        )
        course_attempts = [
            att
            for att in await self._repo.list_attempts_for_courses([course_id])
            if att.student_id == student_id
        ]
        total_att = len(course_attempts)
        accepted_att = sum(1 for att in course_attempts if att.verdict == "accepted")
        attempt_hints = sum(int(att.hints_used) for att in course_attempts)

        misconceptions = [
            MisconceptionCountItem(error_code=code, occurrences=cnt)
            for code, cnt in await self._repo.count_misconceptions_for_students([student_id])
        ]
        skill_rows = await self._repo.aggregate_skill_gaps_for_students([student_id])
        verified_skills = sorted(slug for slug, _unobs, verif in skill_rows if verif > 0)
        developing_skills = sorted(
            slug for slug, unobs, verif in skill_rows if unobs > 0 and verif == 0
        )
        mentor_hints, verified_transfers = await self._repo.count_hints_and_transfers_for_students(
            [student_id]
        )

        asn_records: list[TeacherStudentAssignmentRecord] = []
        for asn in asns:
            sub = subs_map.get(asn.id)
            wf_raw = sub.status if sub is not None else "not_started"
            wf: SubmissionWorkflowStatus = (
                wf_raw  # type: ignore[assignment]
                if wf_raw
                in (
                    "not_started",
                    "in_progress",
                    "submitted",
                    "revision_requested",
                    "resubmitted",
                    "graded",
                )
                else "not_started"
            )
            latest_verdict = sub.attempts[0].verdict if (sub is not None and sub.attempts) else None
            grade = sub.grade if sub is not None else None
            g_status: GradeStatus | None = None
            if grade is not None and grade.status in ("draft", "published", "revision_requested"):
                g_status = grade.status  # type: ignore[assignment]
            asn_records.append(
                TeacherStudentAssignmentRecord(
                    assignment_id=asn.id,
                    title=asn.title,
                    due_at=asn.due_at,
                    workflow_status=wf,
                    attempts_used=sub.attempts_used if sub is not None else 0,
                    latest_verdict=latest_verdict,
                    marks_awarded=float(grade.marks_awarded) if grade is not None else None,
                    max_marks=float(asn.max_marks),
                    grade_status=g_status,
                    submitted_at=sub.submitted_at if sub is not None else None,
                )
            )

        mem_status: MembershipStatus = (
            membership.status  # type: ignore[assignment]
            if membership.status in ("pending", "active", "removed", "left")
            else "active"
        )
        return TeacherStudentPerformanceView(
            course_id=course.id,
            course_code=course.code,
            course_title=course.title,
            student_id=student_id,
            full_name=prof.full_name if prof else "Student",
            email=prof.email if prof else "",
            membership_status=mem_status,
            total_assignment_attempts=total_att,
            accepted_assignment_attempts=accepted_att,
            hints_used_total=mentor_hints + attempt_hints,
            verified_transfers_count=verified_transfers,
            verified_skills=verified_skills,
            developing_skills=developing_skills,
            common_misconceptions=misconceptions,
            assignments=asn_records,
        )
