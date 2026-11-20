"""Teacher Assignment Creation & Server-Enforced Student Assignment Submission Service."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import status

from app.core.errors import AppError
from app.models.classroom import (
    Assignment,
    AssignmentAttempt,
    AssignmentSubmission,
)
from app.repositories.classroom import ClassroomRepository
from app.repositories.identity import UserRecord
from app.repositories.problems import ProblemRepository
from app.schemas.classroom import (
    AssignmentAttemptView,
    AssignmentCreateRequest,
    AssignmentGradeView,
    AssignmentProblemInput,
    AssignmentProblemLinkView,
    AssignmentSummaryView,
    AssignmentUpdateRequest,
    StudentAssignmentAttemptResponse,
    StudentAssignmentDetailView,
    StudentAssignmentFilter,
    StudentAssignmentListItemView,
    StudentAssignmentSubmitRequest,
    TeacherFeedbackView,
)
from app.schemas.problems import SubmissionCreateRequest
from app.services.execution.service import ExecutionService


def _attempt_to_view(att: AssignmentAttempt) -> AssignmentAttemptView:
    return AssignmentAttemptView(
        id=att.id,
        problem_id=att.problem_id,
        problem_version_id=att.problem_version_id,
        execution_submission_id=att.execution_submission_id,
        attempt_number=att.attempt_number,
        language_slug=att.language_slug,
        source_code=att.source_code,
        student_notes=att.student_notes,
        verdict=att.verdict,
        passed_tests=att.passed_tests,
        total_tests=att.total_tests,
        hints_used=att.hints_used,
        is_late=att.is_late,
        submitted_at=att.submitted_at,
    )


def evaluate_submission_eligibility(
    *,
    assignment: Assignment,
    submission: AssignmentSubmission | None,
    now: datetime,
) -> tuple[bool, str | None, bool]:
    """Server-side eligibility evaluator for deadlines, attempts, and revision resubmissions.

    Returns `(can_submit, block_reason, is_late)`.
    """
    if assignment.status != "published":
        return (False, "This assignment is not published.", False)
    if assignment.opens_at is not None and now < assignment.opens_at:
        return (False, "This assignment is not open for submissions yet.", False)

    is_late = bool(assignment.due_at is not None and now > assignment.due_at)
    in_revision = bool(
        submission is not None
        and submission.status == "revision_requested"
        and assignment.allow_resubmission_on_revision
    )

    if is_late and not assignment.allow_late_submissions and not in_revision:
        return (
            False,
            "The assignment deadline has passed and late submissions are not permitted.",
            True,
        )

    attempts_used = submission.attempts_used if submission is not None else 0
    if attempts_used >= assignment.max_attempts and not in_revision:
        return (
            False,
            f"Maximum allowed attempts ({assignment.max_attempts}) have been used.",
            is_late,
        )
    return (True, None, is_late)


class AssignmentService:
    """Handles Teacher assignment authoring and Student Judge0-backed assignment submissions."""

    def __init__(
        self,
        *,
        repo: ClassroomRepository,
        problem_repo: ProblemRepository,
        execution_service: ExecutionService,
    ) -> None:
        self._repo = repo
        self._problem_repo = problem_repo
        self._execution = execution_service

    async def _validate_approved_problems(
        self, items: list[AssignmentProblemInput]
    ) -> list[tuple[UUID, UUID, Decimal]]:
        seen: set[UUID] = set()
        resolved: list[tuple[UUID, UUID, Decimal]] = []
        for item in items:
            if item.problem_id in seen:
                raise AppError(
                    code="DUPLICATE_ASSIGNMENT_PROBLEM",
                    message="Each problem can only be linked once per assignment.",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
            seen.add(item.problem_id)
            loaded = await self._problem_repo.get_published_problem(item.problem_id)
            if loaded is None:
                raise AppError(
                    code="UNAPPROVED_PROBLEM",
                    message="Only Admin-approved published problems can be assigned to a class.",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
            prob, ver = loaded
            if ver.status != "published":
                raise AppError(
                    code="UNAPPROVED_PROBLEM",
                    message="Only published problem versions can be assigned.",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
            resolved.append((prob.id, ver.id, Decimal(str(round(item.points, 2)))))
        return resolved

    def _validate_dates_and_policy(
        self,
        *,
        opens_at: datetime | None,
        due_at: datetime | None,
        allow_ai_hints: bool,
        hint_limit: int,
    ) -> None:
        if opens_at is not None and due_at is not None and due_at <= opens_at:
            raise AppError(
                code="INVALID_ASSIGNMENT_DATES",
                message="Assignment due date must be strictly after the opening date.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        if not allow_ai_hints and hint_limit > 0:
            # Automatically coerced to 0 on save, still ensure valid range
            return

    async def build_assignment_summary(self, asg: Assignment) -> AssignmentSummaryView:
        member_counts = await self._repo.count_course_memberships([asg.course_id])
        enrolled = member_counts.get(asg.course_id, (0, 0))[0]
        sub_counts = await self._repo.get_assignment_submission_counts([asg.id])
        submitted, graded, pending_grading = sub_counts.get(asg.id, (0, 0, 0))
        return AssignmentSummaryView(
            id=asg.id,
            course_id=asg.course_id,
            course_code=asg.course.code,
            course_title=asg.course.title,
            title=asg.title,
            status=asg.status,
            opens_at=asg.opens_at,
            due_at=asg.due_at,
            max_marks=float(asg.max_marks),
            max_attempts=asg.max_attempts,
            allow_ai_hints=asg.allow_ai_hints,
            hint_limit=asg.hint_limit,
            allow_late_submissions=asg.allow_late_submissions,
            allow_resubmission_on_revision=asg.allow_resubmission_on_revision,
            problem_count=len(asg.problem_links),
            enrolled_students_count=enrolled,
            submitted_count=submitted,
            graded_count=graded,
            pending_grading_count=pending_grading,
            created_at=asg.created_at,
        )

    async def build_problem_links_view(self, asg: Assignment) -> list[AssignmentProblemLinkView]:
        ver_ids = [lnk.problem_version_id for lnk in asg.problem_links]
        meta = await self._repo.get_problem_versions_meta(ver_ids)
        views: list[AssignmentProblemLinkView] = []
        for lnk in sorted(asg.problem_links, key=lambda x: x.ordinal):
            pair = meta.get(lnk.problem_version_id)
            if pair is None:
                continue
            prob, ver = pair
            views.append(
                AssignmentProblemLinkView(
                    link_id=lnk.id,
                    problem_id=lnk.problem_id,
                    problem_version_id=lnk.problem_version_id,
                    ordinal=lnk.ordinal,
                    points=float(lnk.points),
                    slug=prob.slug,
                    title=ver.title,
                    difficulty=ver.difficulty,
                    mode=ver.mode,
                    version_number=ver.version_number,
                )
            )
        return views

    # ------------------------------------------------------------------
    # Teacher Assignment Management
    # ------------------------------------------------------------------

    async def create_assignment(
        self, *, teacher: UserRecord, payload: AssignmentCreateRequest
    ) -> AssignmentSummaryView:
        course = await self._repo.get_course_by_id(payload.course_id)
        if course is None:
            raise AppError(
                code="COURSE_NOT_FOUND",
                message="Target class was not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        if course.teacher_id != teacher.id and "admin" not in teacher.roles:
            raise AppError(
                code="FORBIDDEN",
                message="You can only create assignments for classes you teach.",
                status_code=status.HTTP_403_FORBIDDEN,
            )
        if course.status != "active":
            raise AppError(
                code="COURSE_ARCHIVED",
                message="Cannot create assignments inside an archived class.",
                status_code=status.HTTP_409_CONFLICT,
            )

        self._validate_dates_and_policy(
            opens_at=payload.opens_at,
            due_at=payload.due_at,
            allow_ai_hints=payload.allow_ai_hints,
            hint_limit=payload.hint_limit,
        )
        resolved_problems = await self._validate_approved_problems(payload.problems)
        asg = await self._repo.create_assignment(
            course_id=course.id,
            teacher_id=teacher.id,
            title=payload.title,
            instructions_md=payload.instructions_md,
            opens_at=payload.opens_at,
            due_at=payload.due_at,
            max_marks=Decimal(str(round(payload.max_marks, 2))),
            grading_policy=payload.grading_policy,
            max_attempts=payload.max_attempts,
            allow_ai_hints=payload.allow_ai_hints,
            hint_limit=payload.hint_limit if payload.allow_ai_hints else 0,
            allow_late_submissions=payload.allow_late_submissions,
            allow_resubmission_on_revision=payload.allow_resubmission_on_revision,
            status="published" if payload.publish_now else "draft",
            problem_links=resolved_problems,
        )
        return await self.build_assignment_summary(asg)

    async def list_teacher_assignments(
        self, *, teacher: UserRecord, course_id: UUID | None = None
    ) -> list[AssignmentSummaryView]:
        courses = await self._repo.list_teacher_courses(teacher.id)
        authorized_ids = [c.id for c in courses]
        if course_id is not None:
            if course_id not in authorized_ids and "admin" not in teacher.roles:
                raise AppError(
                    code="FORBIDDEN",
                    message="You are not authorized to view assignments for this class.",
                    status_code=status.HTTP_403_FORBIDDEN,
                )
            target_ids = [course_id]
        else:
            target_ids = authorized_ids

        asgs = await self._repo.list_assignments_for_courses(target_ids)
        return [await self.build_assignment_summary(a) for a in asgs]

    async def update_assignment(
        self, *, teacher: UserRecord, assignment_id: UUID, payload: AssignmentUpdateRequest
    ) -> AssignmentSummaryView:
        asg = await self._repo.get_assignment_by_id(assignment_id)
        if asg is None:
            raise AppError(
                code="ASSIGNMENT_NOT_FOUND",
                message="Assignment was not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        if asg.teacher_id != teacher.id and "admin" not in teacher.roles:
            raise AppError(
                code="FORBIDDEN",
                message="You cannot modify another teacher's assignment.",
                status_code=status.HTTP_403_FORBIDDEN,
            )
        if asg.status != "draft":
            raise AppError(
                code="ASSIGNMENT_LOCKED",
                message="Only unpublished draft assignments can be edited. Archive instead if needed.",
                status_code=status.HTTP_409_CONFLICT,
            )

        opens_at = payload.opens_at if payload.opens_at is not None else asg.opens_at
        due_at = payload.due_at if payload.due_at is not None else asg.due_at
        allow_hints = (
            payload.allow_ai_hints if payload.allow_ai_hints is not None else asg.allow_ai_hints
        )
        hint_lim = payload.hint_limit if payload.hint_limit is not None else asg.hint_limit
        self._validate_dates_and_policy(
            opens_at=opens_at,
            due_at=due_at,
            allow_ai_hints=allow_hints,
            hint_limit=hint_lim,
        )

        if payload.title is not None:
            asg.title = payload.title.strip()
        if payload.instructions_md is not None:
            asg.instructions_md = payload.instructions_md
        asg.opens_at = opens_at
        asg.due_at = due_at
        if payload.max_marks is not None:
            asg.max_marks = Decimal(str(round(payload.max_marks, 2)))
        if payload.grading_policy is not None:
            asg.grading_policy = payload.grading_policy
        if payload.max_attempts is not None:
            asg.max_attempts = payload.max_attempts
        asg.allow_ai_hints = allow_hints
        asg.hint_limit = hint_lim if allow_hints else 0
        if payload.allow_late_submissions is not None:
            asg.allow_late_submissions = payload.allow_late_submissions
        if payload.allow_resubmission_on_revision is not None:
            asg.allow_resubmission_on_revision = payload.allow_resubmission_on_revision
        if payload.problems is not None:
            resolved = await self._validate_approved_problems(payload.problems)
            await self._repo.replace_assignment_problems(assignment=asg, problem_links=resolved)

        saved = await self._repo.save_assignment(asg)
        return await self.build_assignment_summary(saved)

    async def set_assignment_status(
        self, *, teacher: UserRecord, assignment_id: UUID, target_status: str
    ) -> AssignmentSummaryView:
        asg = await self._repo.get_assignment_by_id(assignment_id)
        if asg is None:
            raise AppError(
                code="ASSIGNMENT_NOT_FOUND",
                message="Assignment was not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        if asg.teacher_id != teacher.id and "admin" not in teacher.roles:
            raise AppError(
                code="FORBIDDEN",
                message="You cannot change status on another teacher's assignment.",
                status_code=status.HTTP_403_FORBIDDEN,
            )
        if target_status == "published" and len(asg.problem_links) == 0:
            raise AppError(
                code="ASSIGNMENT_EMPTY",
                message="At least one approved problem must be linked before publishing.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        now = datetime.now(UTC)
        asg.status = target_status
        if target_status == "published" and asg.published_at is None:
            asg.published_at = now
        if target_status == "archived":
            asg.archived_at = now
        saved = await self._repo.save_assignment(asg)
        return await self.build_assignment_summary(saved)

    # ------------------------------------------------------------------
    # Student Assignments & Server-Enforced Submissions
    # ------------------------------------------------------------------

    def _to_student_list_item(
        self,
        *,
        asg: Assignment,
        sub: AssignmentSubmission | None,
        now: datetime,
    ) -> StudentAssignmentListItemView:
        wf_status = sub.status if sub is not None else "not_started"
        attempts_used = sub.attempts_used if sub is not None else 0
        is_overdue = bool(
            asg.due_at is not None
            and now > asg.due_at
            and wf_status in ("not_started", "in_progress")
        )
        released_marks: float | None = None
        released_grade_status = None
        if (
            sub is not None
            and sub.grade is not None
            and sub.grade.status
            in (
                "published",
                "revision_requested",
            )
        ):
            released_marks = float(sub.grade.marks_awarded)
            released_grade_status = sub.grade.status

        return StudentAssignmentListItemView(
            assignment_id=asg.id,
            course_id=asg.course_id,
            course_code=asg.course.code,
            course_title=asg.course.title,
            title=asg.title,
            opens_at=asg.opens_at,
            due_at=asg.due_at,
            max_marks=float(asg.max_marks),
            max_attempts=asg.max_attempts,
            allow_ai_hints=asg.allow_ai_hints,
            hint_limit=asg.hint_limit,
            allow_late_submissions=asg.allow_late_submissions,
            allow_resubmission_on_revision=asg.allow_resubmission_on_revision,
            problem_count=len(asg.problem_links),
            workflow_status=wf_status,
            attempts_used=attempts_used,
            is_overdue=is_overdue,
            is_late=sub.is_late if sub is not None else False,
            released_marks=released_marks,
            released_grade_status=released_grade_status,
            submitted_at=sub.submitted_at if sub is not None else None,
        )

    async def list_student_assignments(
        self,
        *,
        student: UserRecord,
        status_filter: StudentAssignmentFilter = "all",
    ) -> list[StudentAssignmentListItemView]:
        memberships = await self._repo.list_student_memberships(student.id)
        active_course_ids = [c.id for m, c in memberships if m.status == "active"]
        if not active_course_ids:
            return []
        asgs = await self._repo.list_assignments_for_courses(active_course_ids, published_only=True)
        subs_map = await self._repo.list_submissions_for_student(
            student_id=student.id, assignment_ids=[a.id for a in asgs]
        )
        now = datetime.now(UTC)
        items = [self._to_student_list_item(asg=a, sub=subs_map.get(a.id), now=now) for a in asgs]

        if status_filter == "pending":
            return [
                i
                for i in items
                if i.workflow_status in ("not_started", "in_progress") and not i.is_overdue
            ]
        if status_filter == "submitted":
            return [i for i in items if i.workflow_status in ("submitted", "resubmitted")]
        if status_filter == "revision_requested":
            return [i for i in items if i.workflow_status == "revision_requested"]
        if status_filter == "graded":
            return [i for i in items if i.workflow_status == "graded"]
        if status_filter == "overdue":
            return [i for i in items if i.is_overdue]
        return items

    async def _require_enrolled_student_assignment(
        self, *, student: UserRecord, assignment_id: UUID
    ) -> Assignment:
        asg = await self._repo.get_assignment_by_id(assignment_id)
        if asg is None or asg.status != "published":
            raise AppError(
                code="ASSIGNMENT_NOT_FOUND",
                message="Published assignment was not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        membership = await self._repo.get_membership(course_id=asg.course_id, student_id=student.id)
        if membership is None or membership.status != "active":
            raise AppError(
                code="NOT_ENROLLED",
                message="You must be actively enrolled in this class to access its assignments.",
                status_code=status.HTTP_403_FORBIDDEN,
            )
        return asg

    async def get_student_assignment_detail(
        self, *, student: UserRecord, assignment_id: UUID
    ) -> StudentAssignmentDetailView:
        asg = await self._require_enrolled_student_assignment(
            student=student, assignment_id=assignment_id
        )
        sub = await self._repo.get_assignment_submission(
            assignment_id=asg.id, student_id=student.id
        )
        now = datetime.now(UTC)
        can_submit, block_reason, _ = evaluate_submission_eligibility(
            assignment=asg, submission=sub, now=now
        )
        problem_views = await self.build_problem_links_view(asg)
        item = self._to_student_list_item(asg=asg, sub=sub, now=now)

        attempts_views = [_attempt_to_view(a) for a in sub.attempts] if sub is not None else []
        grade_view: AssignmentGradeView | None = None
        feedback_views: list[TeacherFeedbackView] = []

        if sub is not None:
            actor_ids: list[UUID] = []
            if sub.grade is not None and sub.grade.status in ("published", "revision_requested"):
                actor_ids.append(sub.grade.graded_by)
            visible_fb = [f for f in sub.feedback_entries if f.is_visible_to_student]
            actor_ids.extend([f.teacher_id for f in visible_fb])
            profiles = await self._repo.get_profiles_map(actor_ids)

            if sub.grade is not None and sub.grade.status in ("published", "revision_requested"):
                gp = profiles.get(sub.grade.graded_by)
                grade_view = AssignmentGradeView(
                    id=sub.grade.id,
                    marks_awarded=float(sub.grade.marks_awarded),
                    max_marks=float(sub.grade.max_marks),
                    status=sub.grade.status,
                    graded_by_name=gp.full_name if gp else "Instructor",
                    published_at=sub.grade.published_at,
                    updated_at=sub.grade.updated_at,
                )
            for fb in visible_fb:
                tp = profiles.get(fb.teacher_id)
                feedback_views.append(
                    TeacherFeedbackView(
                        id=fb.id,
                        feedback_type=fb.feedback_type,
                        body_md=fb.body_md,
                        teacher_name=tp.full_name if tp else "Instructor",
                        is_visible_to_student=fb.is_visible_to_student,
                        created_at=fb.created_at,
                    )
                )

        return StudentAssignmentDetailView(
            assignment=item,
            instructions_md=asg.instructions_md,
            grading_policy=asg.grading_policy,
            problems=problem_views,
            attempts=attempts_views,
            can_submit=can_submit,
            submit_block_reason=block_reason,
            grade=grade_view,
            feedback=feedback_views,
        )

    async def submit_student_assignment(
        self,
        *,
        student: UserRecord,
        assignment_id: UUID,
        payload: StudentAssignmentSubmitRequest,
    ) -> StudentAssignmentAttemptResponse:
        asg = await self._require_enrolled_student_assignment(
            student=student, assignment_id=assignment_id
        )
        linked = next(
            (lnk for lnk in asg.problem_links if lnk.problem_id == payload.problem_id), None
        )
        if linked is None:
            raise AppError(
                code="PROBLEM_NOT_IN_ASSIGNMENT",
                message="Submitted problem is not part of this assignment.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # Enforce hint policy server-side
        if not asg.allow_ai_hints and payload.hints_used > 0:
            raise AppError(
                code="HINTS_NOT_ALLOWED",
                message="AI Mentor hints are disabled for this assignment.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        if asg.allow_ai_hints and payload.hints_used > asg.hint_limit:
            raise AppError(
                code="HINT_LIMIT_EXCEEDED",
                message=f"This assignment allows at most {asg.hint_limit} AI hint(s).",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        sub = await self._repo.get_or_create_assignment_submission(
            assignment=asg, student_id=student.id
        )
        now = datetime.now(UTC)
        can_submit, block_reason, is_late = evaluate_submission_eligibility(
            assignment=asg, submission=sub, now=now
        )
        if not can_submit:
            raise AppError(
                code="ASSIGNMENT_SUBMISSION_BLOCKED",
                message=block_reason or "Submission is not permitted at this time.",
                status_code=status.HTTP_409_CONFLICT,
            )

        # Evaluate on real isolated Judge0 CE against public + hidden tests (hidden inputs masked!)
        exec_resp = await self._execution.execute_submission(
            user=student,
            payload=SubmissionCreateRequest(
                problem_id=linked.problem_id,
                language_slug=payload.language_slug,
                submission_kind="submit",
                source_code=payload.source_code,
                explanation_text=payload.student_notes or None,
            ),
        )

        attempt, updated_sub = await self._repo.record_assignment_attempt(
            submission=sub,
            problem_id=linked.problem_id,
            problem_version_id=linked.problem_version_id,
            execution_submission_id=exec_resp.id,
            language_slug=payload.language_slug,
            source_code=payload.source_code,
            student_notes=payload.student_notes,
            verdict=exec_resp.verdict,
            passed_tests=exec_resp.passed_tests,
            total_tests=exec_resp.total_tests,
            hints_used=payload.hints_used,
            is_late=is_late,
        )

        return StudentAssignmentAttemptResponse(
            attempt=_attempt_to_view(attempt),
            workflow_status=updated_sub.status,
            attempts_used=updated_sub.attempts_used,
            attempts_remaining=max(0, asg.max_attempts - updated_sub.attempts_used),
        )
