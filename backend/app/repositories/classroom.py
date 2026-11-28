"""Async SQLAlchemy repository for Phase 7 Classrooms, Assignments, Grading & Analytics."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import desc, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.classroom import (
    Assignment,
    AssignmentAttempt,
    AssignmentGrade,
    AssignmentProblemLink,
    AssignmentSubmission,
    ClassInvitation,
    Course,
    CourseMembership,
    GradingAuditEvent,
    TeacherFeedback,
)
from app.models.identity import Profile
from app.models.learning import StudentSkillState
from app.models.mentor import ErrorDiagnosis, HintEvent, VerificationAttempt
from app.models.problems import Problem, ProblemVersion


class ClassroomRepository:
    """Data access layer for Phase 7 courses, memberships, assignments, grading, and analytics."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # Profiles helper
    # ------------------------------------------------------------------

    async def get_profiles_map(self, user_ids: list[UUID]) -> dict[UUID, Profile]:
        if not user_ids:
            return {}
        res = await self._session.execute(
            select(Profile).where(Profile.id.in_(list(set(user_ids))))
        )
        return {p.id: p for p in res.scalars().all()}

    # ------------------------------------------------------------------
    # Courses & Invitations
    # ------------------------------------------------------------------

    async def create_course(
        self,
        *,
        teacher_id: UUID,
        code: str,
        title: str,
        description: str,
        term: str,
        enrollment_policy: str,
        allow_student_leave: bool,
    ) -> Course:
        course = Course(
            teacher_id=teacher_id,
            code=code.strip().upper(),
            title=title.strip(),
            description=description.strip(),
            term=term.strip(),
            enrollment_policy=enrollment_policy,
            allow_student_leave=allow_student_leave,
            status="active",
        )
        self._session.add(course)
        await self._session.commit()
        await self._session.refresh(course)
        return course

    async def get_course_by_id(self, course_id: UUID) -> Course | None:
        res = await self._session.execute(select(Course).where(Course.id == course_id))
        return res.scalar_one_or_none()

    async def list_teacher_courses(self, teacher_id: UUID) -> list[Course]:
        res = await self._session.execute(
            select(Course)
            .where(Course.teacher_id == teacher_id)
            .order_by(Course.status.asc(), desc(Course.created_at))
        )
        return list(res.scalars().all())

    async def update_course(self, course: Course) -> Course:
        await self._session.commit()
        await self._session.refresh(course)
        return course

    async def create_invitation(
        self,
        *,
        course_id: UUID,
        created_by: UUID,
        code_hash: str,
        code_preview: str,
        max_uses: int | None,
        expires_at: datetime | None,
    ) -> ClassInvitation:
        inv = ClassInvitation(
            course_id=course_id,
            created_by=created_by,
            code_hash=code_hash,
            code_preview=code_preview,
            max_uses=max_uses,
            expires_at=expires_at,
            is_active=True,
        )
        self._session.add(inv)
        await self._session.commit()
        await self._session.refresh(inv)
        return inv

    async def list_course_invitations(self, course_id: UUID) -> list[ClassInvitation]:
        res = await self._session.execute(
            select(ClassInvitation)
            .where(ClassInvitation.course_id == course_id)
            .order_by(desc(ClassInvitation.created_at))
        )
        return list(res.scalars().all())

    async def get_invitation_by_hash(self, code_hash: str) -> ClassInvitation | None:
        res = await self._session.execute(
            select(ClassInvitation).where(ClassInvitation.code_hash == code_hash)
        )
        return res.scalar_one_or_none()

    async def get_invitation_by_id(self, invitation_id: UUID) -> ClassInvitation | None:
        res = await self._session.execute(
            select(ClassInvitation).where(ClassInvitation.id == invitation_id)
        )
        return res.scalar_one_or_none()

    async def save_invitation(self, invitation: ClassInvitation) -> ClassInvitation:
        await self._session.commit()
        await self._session.refresh(invitation)
        return invitation

    # ------------------------------------------------------------------
    # Course Memberships
    # ------------------------------------------------------------------

    async def get_membership(self, *, course_id: UUID, student_id: UUID) -> CourseMembership | None:
        res = await self._session.execute(
            select(CourseMembership).where(
                CourseMembership.course_id == course_id,
                CourseMembership.student_id == student_id,
            )
        )
        return res.scalar_one_or_none()

    async def get_membership_by_id(self, membership_id: UUID) -> CourseMembership | None:
        res = await self._session.execute(
            select(CourseMembership).where(CourseMembership.id == membership_id)
        )
        return res.scalar_one_or_none()

    async def upsert_membership_from_invite(
        self,
        *,
        course_id: UUID,
        student_id: UUID,
        invitation: ClassInvitation,
        initial_status: str,
    ) -> CourseMembership:
        await self._session.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:lock_key))"),
            {"lock_key": f"course_join:{course_id}:{student_id}"},
        )
        existing = await self.get_membership(course_id=course_id, student_id=student_id)
        now = datetime.now(UTC)
        if existing is not None:
            existing.status = initial_status
            existing.joined_via_invitation_id = invitation.id
            existing.joined_at = now
            existing.removed_at = None
            if initial_status == "active":
                existing.approved_at = now
            membership = existing
        else:
            membership = CourseMembership(
                course_id=course_id,
                student_id=student_id,
                status=initial_status,
                joined_via_invitation_id=invitation.id,
                joined_at=now,
                approved_at=now if initial_status == "active" else None,
            )
            self._session.add(membership)
        invitation.uses_count += 1
        await self._session.commit()
        await self._session.refresh(membership)
        return membership

    async def save_membership(self, membership: CourseMembership) -> CourseMembership:
        await self._session.commit()
        await self._session.refresh(membership)
        return membership

    async def list_course_memberships(self, course_id: UUID) -> list[CourseMembership]:
        res = await self._session.execute(
            select(CourseMembership)
            .where(CourseMembership.course_id == course_id)
            .order_by(CourseMembership.status.asc(), desc(CourseMembership.joined_at))
        )
        return list(res.scalars().all())

    async def list_student_memberships(
        self, student_id: UUID
    ) -> list[tuple[CourseMembership, Course]]:
        res = await self._session.execute(
            select(CourseMembership, Course)
            .join(Course, Course.id == CourseMembership.course_id)
            .where(
                CourseMembership.student_id == student_id,
                CourseMembership.status.in_(["active", "pending"]),
            )
            .order_by(desc(CourseMembership.joined_at))
        )
        return [(row[0], row[1]) for row in res.all()]

    async def count_course_memberships(self, course_ids: list[UUID]) -> dict[UUID, tuple[int, int]]:
        if not course_ids:
            return {}
        res = await self._session.execute(
            select(CourseMembership.course_id, CourseMembership.status, func.count())
            .where(CourseMembership.course_id.in_(course_ids))
            .group_by(CourseMembership.course_id, CourseMembership.status)
        )
        out: dict[UUID, list[int]] = {cid: [0, 0] for cid in course_ids}
        for cid, st, cnt in res.all():
            if st == "active":
                out[cid][0] = int(cnt)
            elif st == "pending":
                out[cid][1] = int(cnt)
        return {k: (v[0], v[1]) for k, v in out.items()}

    # ------------------------------------------------------------------
    # Assignments & Problem Links
    # ------------------------------------------------------------------

    async def create_assignment(
        self,
        *,
        course_id: UUID,
        teacher_id: UUID,
        title: str,
        instructions_md: str,
        opens_at: datetime | None,
        due_at: datetime | None,
        max_marks: Decimal,
        grading_policy: str,
        max_attempts: int,
        allow_ai_hints: bool,
        hint_limit: int,
        allow_late_submissions: bool,
        allow_resubmission_on_revision: bool,
        status: str,
        problem_links: list[tuple[UUID, UUID, Decimal]],
    ) -> Assignment:
        now = datetime.now(UTC)
        asg = Assignment(
            course_id=course_id,
            teacher_id=teacher_id,
            title=title.strip(),
            instructions_md=instructions_md,
            opens_at=opens_at,
            due_at=due_at,
            max_marks=max_marks,
            grading_policy=grading_policy,
            max_attempts=max_attempts,
            allow_ai_hints=allow_ai_hints,
            hint_limit=hint_limit if allow_ai_hints else 0,
            allow_late_submissions=allow_late_submissions,
            allow_resubmission_on_revision=allow_resubmission_on_revision,
            status=status,
            published_at=now if status == "published" else None,
        )
        self._session.add(asg)
        await self._session.flush()
        for idx, (pid, pvid, pts) in enumerate(problem_links, start=1):
            self._session.add(
                AssignmentProblemLink(
                    assignment_id=asg.id,
                    problem_id=pid,
                    problem_version_id=pvid,
                    ordinal=idx,
                    points=pts,
                )
            )
        await self._session.commit()
        reloaded = await self.get_assignment_by_id(asg.id)
        assert reloaded is not None
        return reloaded

    async def get_assignment_by_id(self, assignment_id: UUID) -> Assignment | None:
        res = await self._session.execute(
            select(Assignment)
            .options(selectinload(Assignment.problem_links), selectinload(Assignment.course))
            .where(Assignment.id == assignment_id)
        )
        return res.scalar_one_or_none()

    async def replace_assignment_problems(
        self,
        *,
        assignment: Assignment,
        problem_links: list[tuple[UUID, UUID, Decimal]],
    ) -> None:
        assignment.problem_links.clear()
        await self._session.flush()
        for idx, (pid, pvid, pts) in enumerate(problem_links, start=1):
            assignment.problem_links.append(
                AssignmentProblemLink(
                    assignment_id=assignment.id,
                    problem_id=pid,
                    problem_version_id=pvid,
                    ordinal=idx,
                    points=pts,
                )
            )

    async def save_assignment(self, assignment: Assignment) -> Assignment:
        await self._session.commit()
        reloaded = await self.get_assignment_by_id(assignment.id)
        assert reloaded is not None
        return reloaded

    async def list_assignments_for_courses(
        self, course_ids: list[UUID], *, published_only: bool = False
    ) -> list[Assignment]:
        if not course_ids:
            return []
        stmt = (
            select(Assignment)
            .options(selectinload(Assignment.problem_links), selectinload(Assignment.course))
            .where(Assignment.course_id.in_(course_ids))
        )
        if published_only:
            stmt = stmt.where(Assignment.status == "published")
        stmt = stmt.order_by(Assignment.due_at.asc().nullslast(), desc(Assignment.created_at))
        res = await self._session.execute(stmt)
        return list(res.scalars().all())

    async def get_problem_versions_meta(
        self, version_ids: list[UUID]
    ) -> dict[UUID, tuple[Problem, ProblemVersion]]:
        if not version_ids:
            return {}
        res = await self._session.execute(
            select(Problem, ProblemVersion)
            .join(ProblemVersion, ProblemVersion.problem_id == Problem.id)
            .where(ProblemVersion.id.in_(list(set(version_ids))))
        )
        return {row[1].id: (row[0], row[1]) for row in res.all()}

    # ------------------------------------------------------------------
    # Assignment Submissions, Attempts, Grades, Feedback & Audit
    # ------------------------------------------------------------------

    async def get_or_create_assignment_submission(
        self, *, assignment: Assignment, student_id: UUID
    ) -> AssignmentSubmission:
        await self._session.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:lock_key))"),
            {"lock_key": f"asg_sub:{assignment.id}:{student_id}"},
        )
        res = await self._session.execute(
            select(AssignmentSubmission)
            .options(
                selectinload(AssignmentSubmission.attempts),
                selectinload(AssignmentSubmission.grade),
                selectinload(AssignmentSubmission.feedback_entries),
            )
            .where(
                AssignmentSubmission.assignment_id == assignment.id,
                AssignmentSubmission.student_id == student_id,
            )
        )
        existing = res.scalar_one_or_none()
        if existing is not None:
            return existing
        sub = AssignmentSubmission(
            assignment_id=assignment.id,
            course_id=assignment.course_id,
            student_id=student_id,
            status="in_progress",
            attempts_used=0,
        )
        self._session.add(sub)
        await self._session.commit()
        reloaded = await self.get_assignment_submission_by_id(sub.id)
        assert reloaded is not None
        return reloaded

    async def get_assignment_submission(
        self, *, assignment_id: UUID, student_id: UUID
    ) -> AssignmentSubmission | None:
        res = await self._session.execute(
            select(AssignmentSubmission)
            .options(
                selectinload(AssignmentSubmission.attempts),
                selectinload(AssignmentSubmission.grade),
                selectinload(AssignmentSubmission.feedback_entries),
            )
            .where(
                AssignmentSubmission.assignment_id == assignment_id,
                AssignmentSubmission.student_id == student_id,
            )
        )
        return res.scalar_one_or_none()

    async def get_assignment_submission_by_id(
        self, submission_id: UUID
    ) -> AssignmentSubmission | None:
        res = await self._session.execute(
            select(AssignmentSubmission)
            .options(
                selectinload(AssignmentSubmission.attempts),
                selectinload(AssignmentSubmission.grade),
                selectinload(AssignmentSubmission.feedback_entries),
            )
            .where(AssignmentSubmission.id == submission_id)
        )
        return res.scalar_one_or_none()

    async def list_submissions_for_assignment(
        self, assignment_id: UUID
    ) -> list[AssignmentSubmission]:
        res = await self._session.execute(
            select(AssignmentSubmission)
            .options(
                selectinload(AssignmentSubmission.attempts),
                selectinload(AssignmentSubmission.grade),
                selectinload(AssignmentSubmission.feedback_entries),
            )
            .where(AssignmentSubmission.assignment_id == assignment_id)
            .order_by(desc(AssignmentSubmission.updated_at))
        )
        return list(res.scalars().all())

    async def list_submissions_for_student(
        self, *, student_id: UUID, assignment_ids: list[UUID]
    ) -> dict[UUID, AssignmentSubmission]:
        if not assignment_ids:
            return {}
        res = await self._session.execute(
            select(AssignmentSubmission)
            .options(
                selectinload(AssignmentSubmission.attempts),
                selectinload(AssignmentSubmission.grade),
                selectinload(AssignmentSubmission.feedback_entries),
            )
            .where(
                AssignmentSubmission.student_id == student_id,
                AssignmentSubmission.assignment_id.in_(assignment_ids),
            )
        )
        return {s.assignment_id: s for s in res.scalars().all()}

    async def record_assignment_attempt(
        self,
        *,
        submission: AssignmentSubmission,
        problem_id: UUID,
        problem_version_id: UUID,
        execution_submission_id: UUID | None,
        language_slug: str,
        source_code: str,
        student_notes: str,
        verdict: str,
        passed_tests: int,
        total_tests: int,
        hints_used: int,
        is_late: bool,
    ) -> tuple[AssignmentAttempt, AssignmentSubmission]:
        max_num_res = await self._session.execute(
            select(func.coalesce(func.max(AssignmentAttempt.attempt_number), 0)).where(
                AssignmentAttempt.assignment_submission_id == submission.id,
                AssignmentAttempt.problem_id == problem_id,
            )
        )
        next_num = int(max_num_res.scalar_one()) + 1
        now = datetime.now(UTC)

        attempt = AssignmentAttempt(
            assignment_submission_id=submission.id,
            assignment_id=submission.assignment_id,
            course_id=submission.course_id,
            student_id=submission.student_id,
            problem_id=problem_id,
            problem_version_id=problem_version_id,
            execution_submission_id=execution_submission_id,
            attempt_number=next_num,
            language_slug=language_slug,
            source_code=source_code,
            student_notes=student_notes,
            verdict=verdict,
            passed_tests=passed_tests,
            total_tests=total_tests,
            hints_used=hints_used,
            is_late=is_late,
            submitted_at=now,
        )
        self._session.add(attempt)
        await self._session.flush()

        was_revision = submission.status == "revision_requested"
        submission.attempts_used += 1
        submission.latest_attempt_id = attempt.id
        submission.is_late = submission.is_late or is_late
        if was_revision:
            submission.status = "resubmitted"
            submission.resubmitted_at = now
        else:
            submission.status = "submitted"
            submission.submitted_at = submission.submitted_at or now

        await self._session.commit()
        await self._session.refresh(attempt)
        reloaded_sub = await self.get_assignment_submission_by_id(submission.id)
        assert reloaded_sub is not None
        return attempt, reloaded_sub

    async def save_grade_with_audit(
        self,
        *,
        submission: AssignmentSubmission,
        actor_user_id: UUID,
        marks_awarded: Decimal,
        max_marks: Decimal,
        action: str,
        feedback_md: str,
    ) -> AssignmentSubmission:
        now = datetime.now(UTC)
        existing_grade = submission.grade
        prev_marks = existing_grade.marks_awarded if existing_grade else None
        prev_status = existing_grade.status if existing_grade else submission.status

        if action == "save_draft":
            new_grade_status = "draft"
            audit_action = "grade_draft_saved"
        elif action == "request_revision":
            new_grade_status = "revision_requested"
            audit_action = "revision_requested"
            submission.status = "revision_requested"
        else:
            new_grade_status = "published"
            audit_action = (
                "grade_updated"
                if existing_grade and existing_grade.status == "published"
                else "grade_published"
            )
            submission.status = "graded"

        if existing_grade is None:
            existing_grade = AssignmentGrade(
                assignment_submission_id=submission.id,
                assignment_id=submission.assignment_id,
                course_id=submission.course_id,
                student_id=submission.student_id,
                graded_by=actor_user_id,
                marks_awarded=marks_awarded,
                max_marks=max_marks,
                status=new_grade_status,
                published_at=now if new_grade_status == "published" else None,
            )
            self._session.add(existing_grade)
        else:
            existing_grade.graded_by = actor_user_id
            existing_grade.marks_awarded = marks_awarded
            existing_grade.max_marks = max_marks
            existing_grade.status = new_grade_status
            if new_grade_status == "published":
                existing_grade.published_at = now

        cleaned_fb = feedback_md.strip()
        if cleaned_fb:
            fb_type = (
                "revision_request"
                if action == "request_revision"
                else "grade_release"
                if action == "publish"
                else "comment"
            )
            self._session.add(
                TeacherFeedback(
                    assignment_submission_id=submission.id,
                    assignment_id=submission.assignment_id,
                    course_id=submission.course_id,
                    student_id=submission.student_id,
                    teacher_id=actor_user_id,
                    feedback_type=fb_type,
                    body_md=cleaned_fb,
                    is_visible_to_student=(action != "save_draft"),
                )
            )

        self._session.add(
            GradingAuditEvent(
                assignment_submission_id=submission.id,
                assignment_id=submission.assignment_id,
                course_id=submission.course_id,
                actor_user_id=actor_user_id,
                action=audit_action,
                previous_marks=prev_marks,
                new_marks=marks_awarded,
                previous_status=prev_status,
                new_status=new_grade_status,
                notes=cleaned_fb[:500] if cleaned_fb else f"Action: {audit_action}",
            )
        )
        await self._session.commit()
        reloaded = await self.get_assignment_submission_by_id(submission.id)
        assert reloaded is not None
        return reloaded

    async def list_audit_events_for_submissions(
        self, submission_ids: list[UUID]
    ) -> dict[UUID, list[GradingAuditEvent]]:
        if not submission_ids:
            return {}
        res = await self._session.execute(
            select(GradingAuditEvent)
            .where(GradingAuditEvent.assignment_submission_id.in_(submission_ids))
            .order_by(desc(GradingAuditEvent.created_at))
        )
        grouped: dict[UUID, list[GradingAuditEvent]] = {}
        for ev in res.scalars().all():
            grouped.setdefault(ev.assignment_submission_id, []).append(ev)
        return grouped

    # ------------------------------------------------------------------
    # Real Aggregated Teacher Analytics Queries (Zero Fabricated Metrics)
    # ------------------------------------------------------------------

    async def get_assignment_submission_counts(
        self, assignment_ids: list[UUID]
    ) -> dict[UUID, tuple[int, int, int]]:
        """Return {assignment_id: (submitted_total, graded_count, pending_grading_count)}."""
        if not assignment_ids:
            return {}
        res = await self._session.execute(
            select(
                AssignmentSubmission.assignment_id,
                AssignmentSubmission.status,
                func.count(),
            )
            .where(AssignmentSubmission.assignment_id.in_(assignment_ids))
            .group_by(AssignmentSubmission.assignment_id, AssignmentSubmission.status)
        )
        counts: dict[UUID, list[int]] = {aid: [0, 0, 0] for aid in assignment_ids}
        for aid, st, cnt in res.all():
            c = int(cnt)
            if st in ("submitted", "resubmitted", "graded", "revision_requested"):
                counts[aid][0] += c
            if st == "graded":
                counts[aid][1] += c
            if st in ("submitted", "resubmitted"):
                counts[aid][2] += c
        return {k: (v[0], v[1], v[2]) for k, v in counts.items()}

    async def list_active_student_ids_for_courses(self, course_ids: list[UUID]) -> list[UUID]:
        if not course_ids:
            return []
        res = await self._session.execute(
            select(CourseMembership.student_id)
            .where(
                CourseMembership.course_id.in_(course_ids),
                CourseMembership.status == "active",
            )
            .distinct()
        )
        return list(res.scalars().all())

    async def list_attempts_for_courses(self, course_ids: list[UUID]) -> list[AssignmentAttempt]:
        if not course_ids:
            return []
        res = await self._session.execute(
            select(AssignmentAttempt)
            .where(AssignmentAttempt.course_id.in_(course_ids))
            .order_by(desc(AssignmentAttempt.submitted_at))
        )
        return list(res.scalars().all())

    async def count_misconceptions_for_students(
        self, student_ids: list[UUID]
    ) -> list[tuple[str, int]]:
        if not student_ids:
            return []
        res = await self._session.execute(
            select(ErrorDiagnosis.predicted_error_code, func.count())
            .where(ErrorDiagnosis.student_id.in_(student_ids))
            .group_by(ErrorDiagnosis.predicted_error_code)
            .order_by(desc(func.count()))
            .limit(8)
        )
        return [(str(row[0]), int(row[1])) for row in res.all()]

    async def aggregate_skill_gaps_for_students(
        self, student_ids: list[UUID], *, limit: int | None = 8
    ) -> list[tuple[str, int, int]]:
        if not student_ids:
            return []
        res = await self._session.execute(
            select(StudentSkillState.skill_slug, StudentSkillState.state, func.count())
            .where(StudentSkillState.student_id.in_(student_ids))
            .group_by(StudentSkillState.skill_slug, StudentSkillState.state)
        )
        buckets: dict[str, list[int]] = {}
        for slug, st, cnt in res.all():
            b = buckets.setdefault(str(slug), [0, 0])
            if st in ("independent", "transferred", "retained"):
                b[1] += int(cnt)
            else:
                b[0] += int(cnt)
        ranked = sorted(buckets.items(), key=lambda kv: (-kv[1][0], kv[0]))
        sliced = ranked if limit is None else ranked[:limit]
        return [(slug, vals[0], vals[1]) for slug, vals in sliced]

    async def count_hints_and_transfers_for_students(
        self, student_ids: list[UUID]
    ) -> tuple[int, int]:
        if not student_ids:
            return (0, 0)
        hints_res = await self._session.execute(
            select(func.count()).where(HintEvent.student_id.in_(student_ids))
        )
        transfers_res = await self._session.execute(
            select(func.count()).where(
                VerificationAttempt.student_id.in_(student_ids),
                VerificationAttempt.outcome == "verified_independent",
            )
        )
        return (int(hints_res.scalar_one()), int(transfers_res.scalar_one()))
