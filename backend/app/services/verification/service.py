"""Independent transfer challenge verification backed by real Judge0 execution.

Never fabricates mastery percentages: reports factual verification outcomes
(`verified_independent`, `attempted_not_verified`) linked to real execution evidence.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import status

from app.core.errors import AppError
from app.models.mentor import VerificationAttempt
from app.repositories.identity import UserRecord
from app.repositories.mentor import MentorRepository
from app.schemas.mentor import (
    LearningEventView,
    TransferChallengeSummary,
    VerificationAttemptSubmitRequest,
    VerificationAttemptView,
)
from app.schemas.problems import SubmissionCreateRequest
from app.services.execution.service import ExecutionService


def _attempt_to_view(attempt: VerificationAttempt) -> VerificationAttemptView:
    if attempt.outcome == "verified_independent":
        summary = (
            f"Independent transfer verified: passed {attempt.passed_tests}/{attempt.total_tests} "
            f"Judge0 tests with {attempt.hints_used} hints."
        )
    else:
        summary = (
            f"Not yet verified: Judge0 verdict '{attempt.verdict}' "
            f"({attempt.passed_tests}/{attempt.total_tests} tests passed). "
            "Review your logic and try another independent attempt."
        )
    return VerificationAttemptView(
        id=attempt.id,
        verification_link_id=attempt.verification_link_id,
        transfer_problem_id=attempt.transfer_problem_id,
        transfer_submission_id=attempt.transfer_submission_id,
        hints_used=attempt.hints_used,
        student_explanation=attempt.student_explanation,
        outcome=attempt.outcome,
        verdict=attempt.verdict,
        passed_tests=attempt.passed_tests,
        total_tests=attempt.total_tests,
        summary_message=summary,
        created_at=attempt.created_at,
    )


class VerificationService:
    """Manages independent unseen transfer challenges and traceable learning evidence."""

    def __init__(
        self,
        *,
        mentor_repo: MentorRepository,
        execution_service: ExecutionService,
    ) -> None:
        self._mentor_repo = mentor_repo
        self._execution = execution_service

    async def get_transfer_for_source_problem(
        self, *, user: UserRecord, source_problem_id: UUID
    ) -> TransferChallengeSummary | None:
        link_tuple = await self._mentor_repo.get_verification_link_for_source_problem(
            source_problem_id
        )
        if link_tuple is None:
            return None

        link, transfer_problem, transfer_version = link_tuple
        accepted = await self._mentor_repo.has_accepted_submit(
            student_id=user.id, problem_id=source_problem_id
        )
        latest_attempt = await self._mentor_repo.get_latest_verification_attempt(
            student_id=user.id, verification_link_id=link.id
        )
        unlocked = accepted is not None
        reason = (
            "Unlocked: your debugging fix passed all Judge0 tests. Complete this unseen "
            "transfer challenge without AI hints to prove independent understanding."
            if unlocked
            else "Locked until your fix for this problem passes Submit Code (all public + hidden Judge0 tests)."
        )

        return TransferChallengeSummary(
            verification_link_id=link.id,
            source_problem_id=link.source_problem_id,
            transfer_problem_id=transfer_problem.id,
            transfer_problem_title=transfer_version.title,
            transfer_problem_slug=transfer_problem.slug,
            skill_focus=link.skill_focus,
            max_hints_allowed=link.max_hints_allowed,
            instructions_md=link.instructions_md,
            unlocked=unlocked,
            unlock_reason=reason,
            latest_attempt=_attempt_to_view(latest_attempt) if latest_attempt else None,
        )

    async def submit_transfer_attempt(
        self,
        *,
        user: UserRecord,
        verification_link_id: UUID,
        payload: VerificationAttemptSubmitRequest,
    ) -> VerificationAttemptView:
        link_tuple = await self._mentor_repo.get_verification_link_by_id(verification_link_id)
        if link_tuple is None:
            raise AppError(
                code="VERIFICATION_LINK_NOT_FOUND",
                message="Transfer verification challenge not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        link, transfer_problem, transfer_version = link_tuple

        # Require verified Accepted submission on the source debugging problem first
        source_accepted = await self._mentor_repo.has_accepted_submit(
            student_id=user.id, problem_id=link.source_problem_id
        )
        if source_accepted is None:
            raise AppError(
                code="TRANSFER_LOCKED",
                message="Complete and pass the debugging problem on Judge0 before submitting its transfer challenge.",
                status_code=status.HTTP_409_CONFLICT,
            )

        # Execute transfer submission on real Judge0 (all public + hidden tests)
        submission = await self._execution.execute_submission(
            user=user,
            payload=SubmissionCreateRequest(
                problem_id=transfer_problem.id,
                language_slug=payload.language_slug,
                submission_kind="submit",
                source_code=payload.source_code,
                explanation_text=payload.student_explanation,
            ),
        )

        # Hint restriction enforced from persisted mentor sessions on this transfer problem
        hints_used = await self._mentor_repo.count_hints_used_for_problem(
            student_id=user.id, problem_id=transfer_problem.id
        )
        outcome = (
            "verified_independent"
            if submission.verdict == "accepted" and hints_used <= link.max_hints_allowed
            else "attempted_not_verified"
        )

        attempt = await self._mentor_repo.save_verification_attempt(
            student_id=user.id,
            verification_link_id=link.id,
            source_submission_id=payload.source_submission_id or source_accepted.id,
            transfer_submission_id=submission.id,
            transfer_problem_id=transfer_problem.id,
            hints_used=hints_used,
            student_explanation=payload.student_explanation.strip(),
            outcome=outcome,
            verdict=submission.verdict,
            passed_tests=submission.passed_tests,
            total_tests=submission.total_tests,
        )

        await self._mentor_repo.record_learning_event(
            student_id=user.id,
            problem_id=transfer_problem.id,
            problem_version_id=transfer_version.id,
            language_slug=payload.language_slug,
            submission_id=submission.id,
            diagnosis_id=None,
            event_type="verification.transfer_attempt",
            hints_used=hints_used,
            verdict=submission.verdict,
            verification_outcome=outcome,
            metadata={
                "verification_link_id": str(link.id),
                "source_problem_id": str(link.source_problem_id),
                "skill_focus": link.skill_focus,
                "passed_tests": submission.passed_tests,
                "total_tests": submission.total_tests,
            },
        )
        return _attempt_to_view(attempt)

    async def list_my_attempts(
        self, *, user: UserRecord, verification_link_id: UUID | None = None
    ) -> list[VerificationAttemptView]:
        rows = await self._mentor_repo.list_verification_attempts(
            student_id=user.id, verification_link_id=verification_link_id
        )
        return [_attempt_to_view(r) for r in rows]

    async def list_my_learning_events(
        self, *, user: UserRecord, limit: int = 30
    ) -> list[LearningEventView]:
        rows = await self._mentor_repo.list_learning_events(student_id=user.id, limit=limit)
        return [
            LearningEventView(
                id=ev.id,
                problem_id=ev.problem_id,
                submission_id=ev.submission_id,
                diagnosis_id=ev.diagnosis_id,
                event_type=ev.event_type,
                hints_used=ev.hints_used,
                verdict=ev.verdict,
                verification_outcome=ev.verification_outcome,
                metadata=dict(ev.metadata_json or {}),
                created_at=ev.created_at,
            )
            for ev in rows
        ]
