"""Spaced Retention Verification service backed by real Judge0 execution.

Core pedagogical invariants:
- Retention schedules are automatically created for verified skills (independent/transferred)
  and eligible Judge0 passes using real published Python problems.
- Retention is NEVER marked `retained` immediately: a student must pass a real Judge0
  submission across all public + hidden tests at least `interval_hours` (>= 24h) after
  `source_verified_at`.
- If a student runs a retention check early (< 24h) and passes on Judge0, we honestly record
  `passed_too_early` and keep the schedule active until >= 24h has elapsed.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import status

from app.core.errors import AppError
from app.models.growth import RetentionSchedule
from app.repositories.growth import GrowthRepository
from app.repositories.identity import UserRecord
from app.repositories.learning import LearningRepository
from app.repositories.mentor import MentorRepository
from app.repositories.problems import ProblemRepository
from app.schemas.growth import (
    RetentionAttemptView,
    RetentionOverviewView,
    RetentionScheduleView,
    SubmitRetentionAttemptRequest,
)
from app.schemas.problems import SubmissionCreateRequest
from app.services.execution.service import ExecutionService
from app.services.learning.lessons_service import resolve_user_language
from app.services.learning.skill_graph import SKILL_FOCUS_TO_NODE, STATE_RANK, SkillGraphService

MIN_RETENTION_HOURS = 24.0


class RetentionVerificationService:
    """Schedules spaced retention checks and verifies delayed Judge0 outcomes."""

    def __init__(
        self,
        *,
        growth_repo: GrowthRepository,
        learning_repo: LearningRepository,
        problem_repo: ProblemRepository,
        mentor_repo: MentorRepository,
        skill_graph_service: SkillGraphService,
        execution_service: ExecutionService,
    ) -> None:
        self._growth_repo = growth_repo
        self._learning_repo = learning_repo
        self._problem_repo = problem_repo
        self._mentor_repo = mentor_repo
        self._skill_graph = skill_graph_service
        self._execution = execution_service

    async def _pick_problem_for_skill(
        self, skill_slug: str, *, language_slug: str = "python"
    ) -> UUID | None:
        problems, _ = await self._problem_repo.list_published_problems(
            language=language_slug, limit=40, offset=0
        )
        if not problems:
            problems, _ = await self._problem_repo.list_published_problems(limit=40, offset=0)
        if not problems:
            return None
        # Prefer a problem matching the skill topic/slug
        for prob, ver in problems:
            topics_and_skills = [t.lower() for t in (ver.topics or []) + (ver.skills or [])]
            mapped = {SKILL_FOCUS_TO_NODE.get(tok, tok) for tok in topics_and_skills}
            if skill_slug in mapped:
                return prob.id
        # Fallback to any non-transfer published problem, then first published problem
        for prob, _ in problems:
            if not prob.slug.startswith("transfer-"):
                return prob.id
        return problems[0][0].id

    async def sync_schedules_for_student(
        self, user: UserRecord, *, language_slug: str | None = None
    ) -> list[RetentionSchedule]:
        """Auto-schedule delayed retention checks for independently verified/transferred skills."""
        lang = resolve_user_language(user, language_slug)
        await self._skill_graph.sync_phase3_and_phase4_evidence(user.id, language_slug=lang)
        skill_states = await self._learning_repo.list_student_skill_states(
            user.id, language_slug=lang
        )
        existing = await self._growth_repo.list_retention_schedules(user.id, language_slug=lang)
        existing_by_skill = {s.skill_slug: s for s in existing}
        now = datetime.now(UTC)

        # Refresh `scheduled` -> `due` when due_at has arrived
        for sched in existing:
            if sched.status == "scheduled" and sched.due_at <= now:
                await self._growth_repo.update_retention_schedule(schedule=sched, status="due")

        # Create a 24h retention schedule for each skill that reached guided/independent/transferred
        for st in skill_states:
            if st.skill_slug in existing_by_skill:
                continue
            if STATE_RANK.get(st.state, 0) < STATE_RANK["guided"]:
                continue
            prob_id = await self._pick_problem_for_skill(st.skill_slug, language_slug=lang)
            if prob_id is None:
                continue
            verified_at = st.first_verified_at or st.last_evidence_at or now
            due_at = verified_at + timedelta(hours=24)
            src_type = (
                "phase4_transfer"
                if st.state == "transferred"
                else "zero_hint_submit"
                if st.state == "independent"
                else "lesson_guided_pass"
            )
            await self._growth_repo.create_retention_schedule(
                student_id=user.id,
                language_slug=lang,
                skill_slug=st.skill_slug,
                problem_id=prob_id,
                source_evidence_type=src_type,
                source_evidence_ref_id=st.last_evidence_type,
                source_verified_at=verified_at,
                due_at=due_at,
                interval_hours=24,
            )

        return await self._growth_repo.list_retention_schedules(user.id, language_slug=lang)

    async def get_retention_overview(
        self, user: UserRecord, *, language_slug: str | None = None
    ) -> RetentionOverviewView:
        lang = resolve_user_language(user, language_slug)
        schedules = await self.sync_schedules_for_student(user, language_slug=lang)
        attempts = await self._growth_repo.list_retention_attempts(
            student_id=user.id, limit=25, language_slug=lang
        )
        skill_nodes = {n.slug: n for n in await self._learning_repo.list_skill_nodes()}
        skill_states = await self._learning_repo.list_student_skill_states(
            user.id, language_slug=lang
        )
        retained_skills_count = sum(1 for s in skill_states if s.state == "retained")

        now = datetime.now(UTC)
        schedule_views: list[RetentionScheduleView] = []
        due_count = 0

        for sched in schedules:
            loaded = await self._problem_repo.get_published_problem(sched.problem_id)
            if loaded is None:
                continue
            prob, ver = loaded
            starter_code = ""
            sched_lang = sched.language_slug or lang
            for variant in ver.variants:
                if variant.language_slug == sched_lang:
                    starter_code = variant.buggy_starter_code or variant.starter_code or ""
                    break
            if not starter_code and ver.variants:
                fallback_var = ver.variants[0]
                starter_code = fallback_var.buggy_starter_code or fallback_var.starter_code or ""

            node = skill_nodes.get(sched.skill_slug)
            remaining_hours = max(0.0, (sched.due_at - now).total_seconds() / 3600.0)
            is_due = sched.due_at <= now and sched.status != "passed_retained"
            if is_due:
                due_count += 1

            schedule_views.append(
                RetentionScheduleView(
                    id=sched.id,
                    language_slug=sched_lang,
                    skill_slug=sched.skill_slug,
                    skill_title_en=node.title_en if node else sched.skill_slug,
                    skill_title_bn=node.title_bn if node else sched.skill_slug,
                    problem_id=prob.id,
                    problem_slug=prob.slug,
                    problem_title=ver.title,
                    starter_code=starter_code,
                    source_evidence_type=sched.source_evidence_type,
                    source_verified_at=sched.source_verified_at,
                    due_at=sched.due_at,
                    interval_hours=sched.interval_hours,
                    status=sched.status,
                    is_due_now=is_due,
                    hours_until_eligible=round(remaining_hours, 2),
                    last_attempt_at=sched.last_attempt_at,
                    created_at=sched.created_at,
                )
            )

        attempt_views = [
            RetentionAttemptView(
                id=a.id,
                schedule_id=a.schedule_id,
                skill_slug=a.skill_slug,
                problem_id=a.problem_id,
                submission_id=a.submission_id,
                language_slug=a.language_slug,
                verdict=a.verdict,
                passed_tests=a.passed_tests,
                total_tests=a.total_tests,
                elapsed_hours_since_initial=round(float(a.elapsed_hours_since_initial), 2),
                outcome=a.outcome,
                summary_message=a.summary_message,
                created_at=a.created_at,
            )
            for a in attempts
        ]

        return RetentionOverviewView(
            schedules=schedule_views,
            recent_attempts=attempt_views,
            due_count=due_count,
            retained_skills_count=retained_skills_count,
            policy_note_en=(
                "A skill reaches 'Retained' ONLY after passing a real Judge0 full test suite at least "
                "24 hours after initial verification. Earlier passes are logged as practice without inflating retention."
            ),
            policy_note_bn=(
                "প্রাথমিক যাচাইয়ের কমপক্ষে ২৪ ঘণ্টা পর আসল Judge0-তে সব টেস্ট পাস করলেই কেবল দক্ষতা "
                "'Retained' হিসেবে চিহ্নিত হয়। এর আগে পাস করলে তা অনুশীলন হিসেবে সংরক্ষিত হয়।"
            ),
        )

    async def submit_retention_attempt(
        self,
        *,
        user: UserRecord,
        schedule_id: UUID,
        payload: SubmitRetentionAttemptRequest,
    ) -> RetentionAttemptView:
        sched = await self._growth_repo.get_retention_schedule_by_id(schedule_id)
        if sched is None:
            raise AppError(
                code="RETENTION_SCHEDULE_NOT_FOUND",
                message="Retention schedule was not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        if sched.student_id != user.id and "admin" not in user.roles:
            raise AppError(
                code="FORBIDDEN",
                message="You cannot submit an attempt for another student's retention schedule.",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        # Execute ALL public & hidden test cases on real Judge0 via ExecutionService
        submission_resp = await self._execution.execute_submission(
            user=user,
            payload=SubmissionCreateRequest(
                problem_id=sched.problem_id,
                language_slug=payload.language_slug,
                submission_kind="submit",
                source_code=payload.source_code,
                explanation_text=payload.student_explanation,
            ),
        )

        now = datetime.now(UTC)
        elapsed_hours = max(0.0, (now - sched.source_verified_at).total_seconds() / 3600.0)
        passed_all = (
            submission_resp.verdict == "accepted"
            and submission_resp.total_tests > 0
            and submission_resp.passed_tests == submission_resp.total_tests
        )

        if passed_all and elapsed_hours >= MIN_RETENTION_HOURS:
            outcome = "retained_verified"
            summary = (
                f"Retention verified! Passed {submission_resp.passed_tests}/{submission_resp.total_tests} "
                f"Judge0 tests {elapsed_hours:.1f}h after initial verification."
            )
            await self._growth_repo.update_retention_schedule(
                schedule=sched,
                status="passed_retained",
                last_attempt_at=now,
            )
            await self._skill_graph.record_evidence(
                student_id=user.id,
                language_slug=sched.language_slug or payload.language_slug,
                skill_slug=sched.skill_slug,
                target_state="retained",
                evidence_source="phase6_retention_verification",
                evidence_ref_id=str(submission_resp.id),
                reason=summary,
                uncertainty_note=(
                    f"Re-verified independently on Judge0 {elapsed_hours:.1f}h after initial mastery."
                ),
            )
        elif passed_all:
            outcome = "passed_too_early"
            remaining = max(0.0, MIN_RETENTION_HOURS - elapsed_hours)
            summary = (
                f"Passed {submission_resp.passed_tests}/{submission_resp.total_tests} Judge0 tests, "
                f"but only {elapsed_hours:.1f}h elapsed since initial verification. Wait {remaining:.1f}h "
                "more to prove long-term retention (Skill Graph NOT prematurely marked Retained)."
            )
            await self._growth_repo.update_retention_schedule(
                schedule=sched,
                status="scheduled",
                last_attempt_at=now,
            )
        else:
            outcome = "needs_review"
            summary = (
                f"Judge0 verdict: {submission_resp.verdict} "
                f"({submission_resp.passed_tests}/{submission_resp.total_tests} tests passed). "
                "Review the concept and retry this retention check."
            )
            await self._growth_repo.update_retention_schedule(
                schedule=sched,
                status="needs_review",
                last_attempt_at=now,
            )

        attempt = await self._growth_repo.record_retention_attempt(
            schedule_id=sched.id,
            student_id=user.id,
            skill_slug=sched.skill_slug,
            problem_id=sched.problem_id,
            submission_id=submission_resp.id,
            language_slug=payload.language_slug,
            source_code=payload.source_code,
            student_explanation=payload.student_explanation,
            verdict=submission_resp.verdict,
            passed_tests=submission_resp.passed_tests,
            total_tests=submission_resp.total_tests,
            elapsed_hours_since_initial=elapsed_hours,
            outcome=outcome,
            summary_message=summary,
        )

        # Also record a unified Phase 4 learning_event for longitudinal analytics
        loaded = await self._problem_repo.get_published_problem(sched.problem_id)
        if loaded is not None:
            _, ver = loaded
            await self._mentor_repo.record_learning_event(
                student_id=user.id,
                problem_id=sched.problem_id,
                problem_version_id=ver.id,
                language_slug=payload.language_slug,
                submission_id=submission_resp.id,
                diagnosis_id=None,
                event_type=f"retention.{outcome}",
                hints_used=0,
                verdict=submission_resp.verdict,
                verification_outcome=outcome,
                metadata={
                    "schedule_id": str(sched.id),
                    "skill_slug": sched.skill_slug,
                    "elapsed_hours": round(elapsed_hours, 2),
                },
            )

        return RetentionAttemptView(
            id=attempt.id,
            schedule_id=attempt.schedule_id,
            skill_slug=attempt.skill_slug,
            problem_id=attempt.problem_id,
            submission_id=attempt.submission_id,
            language_slug=attempt.language_slug,
            verdict=attempt.verdict,
            passed_tests=attempt.passed_tests,
            total_tests=attempt.total_tests,
            elapsed_hours_since_initial=round(float(attempt.elapsed_hours_since_initial), 2),
            outcome=attempt.outcome,
            summary_message=attempt.summary_message,
            created_at=attempt.created_at,
        )
