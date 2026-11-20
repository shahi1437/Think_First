"""Teacher Submission Review, Auditable Grading & Written Feedback Service."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from fastapi import status

from app.core.errors import AppError
from app.models.classroom import AssignmentSubmission
from app.repositories.classroom import ClassroomRepository
from app.repositories.identity import UserRecord
from app.schemas.classroom import (
    AssignmentAttemptView,
    AssignmentGradeView,
    GradeSubmissionRequest,
    GradingAuditEventView,
    TeacherAssignmentDetailView,
    TeacherFeedbackView,
    TeacherSubmissionReviewItem,
)
from app.services.classroom.assignment_service import AssignmentService


class GradingService:
    """Handles Teacher review, marks validation, feedback, revision requests, and audit logs."""

    def __init__(
        self,
        *,
        repo: ClassroomRepository,
        assignment_service: AssignmentService,
    ) -> None:
        self._repo = repo
        self._assignments = assignment_service

    async def _build_review_items(
        self, submissions: list[AssignmentSubmission]
    ) -> list[TeacherSubmissionReviewItem]:
        if not submissions:
            return []
        sub_ids = [s.id for s in submissions]
        audit_map = await self._repo.list_audit_events_for_submissions(sub_ids)

        user_ids: list[UUID] = []
        for s in submissions:
            user_ids.append(s.student_id)
            if s.grade is not None:
                user_ids.append(s.grade.graded_by)
            for fb in s.feedback_entries:
                user_ids.append(fb.teacher_id)
            for ev in audit_map.get(s.id, []):
                user_ids.append(ev.actor_user_id)
        profiles = await self._repo.get_profiles_map(user_ids)

        items: list[TeacherSubmissionReviewItem] = []
        for s in submissions:
            sp = profiles.get(s.student_id)
            att_views = [
                AssignmentAttemptView(
                    id=a.id,
                    problem_id=a.problem_id,
                    problem_version_id=a.problem_version_id,
                    execution_submission_id=a.execution_submission_id,
                    attempt_number=a.attempt_number,
                    language_slug=a.language_slug,
                    source_code=a.source_code,
                    student_notes=a.student_notes,
                    verdict=a.verdict,
                    passed_tests=a.passed_tests,
                    total_tests=a.total_tests,
                    hints_used=a.hints_used,
                    is_late=a.is_late,
                    submitted_at=a.submitted_at,
                )
                for a in sorted(s.attempts, key=lambda x: x.submitted_at, reverse=True)
            ]
            grade_view: AssignmentGradeView | None = None
            if s.grade is not None:
                gp = profiles.get(s.grade.graded_by)
                grade_view = AssignmentGradeView(
                    id=s.grade.id,
                    marks_awarded=float(s.grade.marks_awarded),
                    max_marks=float(s.grade.max_marks),
                    status=s.grade.status,
                    graded_by_name=gp.full_name if gp else "Instructor",
                    published_at=s.grade.published_at,
                    updated_at=s.grade.updated_at,
                )
            fb_views = [
                TeacherFeedbackView(
                    id=f.id,
                    feedback_type=f.feedback_type,
                    body_md=f.body_md,
                    teacher_name=(
                        profiles[f.teacher_id].full_name
                        if f.teacher_id in profiles
                        else "Instructor"
                    ),
                    is_visible_to_student=f.is_visible_to_student,
                    created_at=f.created_at,
                )
                for f in s.feedback_entries
            ]
            audit_views = [
                GradingAuditEventView(
                    id=ev.id,
                    actor_name=(
                        profiles[ev.actor_user_id].full_name
                        if ev.actor_user_id in profiles
                        else "Instructor"
                    ),
                    action=ev.action,
                    previous_marks=float(ev.previous_marks)
                    if ev.previous_marks is not None
                    else None,
                    new_marks=float(ev.new_marks) if ev.new_marks is not None else None,
                    previous_status=ev.previous_status,
                    new_status=ev.new_status,
                    notes=ev.notes,
                    created_at=ev.created_at,
                )
                for ev in audit_map.get(s.id, [])
            ]
            items.append(
                TeacherSubmissionReviewItem(
                    assignment_submission_id=s.id,
                    student_id=s.student_id,
                    student_name=sp.full_name if sp else "Student",
                    student_email=sp.email if sp else "",
                    status=s.status,
                    attempts_used=s.attempts_used,
                    is_late=s.is_late,
                    submitted_at=s.submitted_at,
                    resubmitted_at=s.resubmitted_at,
                    latest_attempt=att_views[0] if att_views else None,
                    attempts=att_views,
                    grade=grade_view,
                    feedback=fb_views,
                    audit_events=audit_views,
                )
            )
        return items

    async def get_teacher_assignment_detail(
        self, *, teacher: UserRecord, assignment_id: UUID
    ) -> TeacherAssignmentDetailView:
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
                message="You are not authorized to review submissions for this assignment.",
                status_code=status.HTTP_403_FORBIDDEN,
            )
        summary = await self._assignments.build_assignment_summary(asg)
        problems = await self._assignments.build_problem_links_view(asg)
        subs = await self._repo.list_submissions_for_assignment(asg.id)
        review_items = await self._build_review_items(subs)
        return TeacherAssignmentDetailView(
            assignment=summary,
            instructions_md=asg.instructions_md,
            grading_policy=asg.grading_policy,
            problems=problems,
            submissions=review_items,
        )

    async def grade_submission(
        self,
        *,
        teacher: UserRecord,
        submission_id: UUID,
        payload: GradeSubmissionRequest,
    ) -> TeacherSubmissionReviewItem:
        sub = await self._repo.get_assignment_submission_by_id(submission_id)
        if sub is None:
            raise AppError(
                code="SUBMISSION_NOT_FOUND",
                message="Assignment submission was not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        asg = await self._repo.get_assignment_by_id(sub.assignment_id)
        if asg is None:
            raise AppError(
                code="ASSIGNMENT_NOT_FOUND",
                message="Parent assignment was not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        if asg.teacher_id != teacher.id and "admin" not in teacher.roles:
            raise AppError(
                code="FORBIDDEN",
                message="Only the authorized class teacher can grade this submission.",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        marks_dec = Decimal(str(round(payload.marks_awarded, 2)))
        if marks_dec < Decimal("0.00") or marks_dec > asg.max_marks:
            raise AppError(
                code="MARKS_OUT_OF_RANGE",
                message=f"Awarded marks must be between 0 and {float(asg.max_marks)}.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        if payload.action == "request_revision" and not payload.feedback_md.strip():
            raise AppError(
                code="REVISION_FEEDBACK_REQUIRED",
                message="Please provide written guidance when requesting a revision.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        updated = await self._repo.save_grade_with_audit(
            submission=sub,
            actor_user_id=teacher.id,
            marks_awarded=marks_dec,
            max_marks=asg.max_marks,
            action=payload.action,
            feedback_md=payload.feedback_md,
        )
        items = await self._build_review_items([updated])
        return items[0]
