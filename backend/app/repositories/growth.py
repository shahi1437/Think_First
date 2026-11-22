"""Async SQLAlchemy repository for Phase 6 Learning DNA, Daily Plans, History & Retention."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import desc, func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.growth import (
    DailyLearningPlan,
    DailyPlanTask,
    LearningDnaSnapshot,
    RetentionAttempt,
    RetentionSchedule,
)
from app.models.learning import (
    DiagnosticResponse,
    DiagnosticSession,
    Lesson,
    LessonProgress,
    LessonVersion,
    SkillStateTransition,
)
from app.models.mentor import (
    ErrorDiagnosis,
    HintEvent,
    MentorSession,
    MentorTurn,
    VerificationAttempt,
)
from app.models.problems import CodeRevision, Problem, ProblemVersion, Submission


class GrowthRepository:
    """Data access layer for Phase 6 adaptive growth features."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # Learning DNA Snapshots
    # ------------------------------------------------------------------

    async def create_dna_snapshot(
        self,
        *,
        student_id: UUID,
        selected_track_slug: str,
        dimensions_json: list[dict[str, Any]],
        skill_state_summary: dict[str, int],
        strengths: list[str],
        growth_areas: list[str],
        source_counts: dict[str, int],
        language_slug: str = "python",
    ) -> LearningDnaSnapshot:
        snap = LearningDnaSnapshot(
            student_id=student_id,
            language_slug=language_slug,
            selected_track_slug=selected_track_slug,
            dimensions_json=dimensions_json,
            skill_state_summary=skill_state_summary,
            strengths=strengths,
            growth_areas=growth_areas,
            source_counts=source_counts,
        )
        self._session.add(snap)
        await self._session.commit()
        await self._session.refresh(snap)
        return snap

    async def list_dna_snapshots(
        self, *, student_id: UUID, limit: int = 10, language_slug: str | None = None
    ) -> list[LearningDnaSnapshot]:
        stmt = select(LearningDnaSnapshot).where(LearningDnaSnapshot.student_id == student_id)
        if language_slug is not None:
            stmt = stmt.where(LearningDnaSnapshot.language_slug == language_slug)
        res = await self._session.execute(
            stmt.order_by(desc(LearningDnaSnapshot.computed_at)).limit(limit)
        )
        return list(res.scalars().all())

    # ------------------------------------------------------------------
    # Daily Learning Plans & Tasks
    # ------------------------------------------------------------------

    async def get_active_daily_plan(
        self, *, student_id: UUID, plan_date: date, language_slug: str = "python"
    ) -> DailyLearningPlan | None:
        res = await self._session.execute(
            select(DailyLearningPlan)
            .options(selectinload(DailyLearningPlan.tasks))
            .where(
                DailyLearningPlan.student_id == student_id,
                DailyLearningPlan.language_slug == language_slug,
                DailyLearningPlan.plan_date == plan_date,
                DailyLearningPlan.is_active.is_(True),
            )
        )
        return res.scalar_one_or_none()

    async def list_daily_plan_history(
        self, *, student_id: UUID, limit: int = 14, language_slug: str | None = None
    ) -> list[DailyLearningPlan]:
        stmt = (
            select(DailyLearningPlan)
            .options(selectinload(DailyLearningPlan.tasks))
            .where(DailyLearningPlan.student_id == student_id)
        )
        if language_slug is not None:
            stmt = stmt.where(DailyLearningPlan.language_slug == language_slug)
        res = await self._session.execute(
            stmt.order_by(
                desc(DailyLearningPlan.plan_date), desc(DailyLearningPlan.version_number)
            ).limit(limit)
        )
        return list(res.scalars().all())

    async def create_daily_plan(
        self,
        *,
        student_id: UUID,
        plan_date: date,
        selected_track_slug: str,
        available_minutes: int,
        generation_reason_en: str,
        generation_reason_bn: str,
        evidence_snapshot: dict[str, Any],
        tasks_payload: list[dict[str, Any]],
        reuse_if_active_exists: bool = False,
        language_slug: str = "python",
    ) -> DailyLearningPlan:
        # Serialize concurrent plan creations per student+language (e.g. parallel Next.js RSC loads)
        await self._session.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:lock_key))"),
            {"lock_key": f"daily_plan:{student_id}:{language_slug}:{plan_date.isoformat()}"},
        )
        if reuse_if_active_exists:
            existing = await self.get_active_daily_plan(
                student_id=student_id, plan_date=plan_date, language_slug=language_slug
            )
            if existing is not None:
                return existing

        # Deactivate any currently active plan for this student, language & date
        await self._session.execute(
            update(DailyLearningPlan)
            .where(
                DailyLearningPlan.student_id == student_id,
                DailyLearningPlan.language_slug == language_slug,
                DailyLearningPlan.plan_date == plan_date,
                DailyLearningPlan.is_active.is_(True),
            )
            .values(is_active=False)
        )
        max_ver_res = await self._session.execute(
            select(func.coalesce(func.max(DailyLearningPlan.version_number), 0)).where(
                DailyLearningPlan.student_id == student_id,
                DailyLearningPlan.language_slug == language_slug,
                DailyLearningPlan.plan_date == plan_date,
            )
        )
        next_version = int(max_ver_res.scalar_one()) + 1
        total_minutes = sum(int(t["estimated_minutes"]) for t in tasks_payload)

        plan = DailyLearningPlan(
            student_id=student_id,
            language_slug=language_slug,
            plan_date=plan_date,
            version_number=next_version,
            is_active=True,
            selected_track_slug=selected_track_slug,
            available_minutes=available_minutes,
            total_estimated_minutes=total_minutes,
            generation_reason_en=generation_reason_en,
            generation_reason_bn=generation_reason_bn,
            evidence_snapshot=evidence_snapshot,
        )
        self._session.add(plan)
        await self._session.flush()

        for idx, t in enumerate(tasks_payload, start=1):
            task = DailyPlanTask(
                plan_id=plan.id,
                student_id=student_id,
                task_order=idx,
                task_type=t["task_type"],
                skill_slug=t.get("skill_slug"),
                target_id=t["target_id"],
                target_slug=t["target_slug"],
                title_en=t["title_en"],
                title_bn=t["title_bn"],
                reason_en=t["reason_en"],
                reason_bn=t["reason_bn"],
                href=t["href"],
                estimated_minutes=int(t["estimated_minutes"]),
                status="pending",
            )
            self._session.add(task)

        await self._session.commit()
        reloaded = await self.get_active_daily_plan(
            student_id=student_id, plan_date=plan_date, language_slug=language_slug
        )
        assert reloaded is not None
        return reloaded

    async def get_daily_task_by_id(self, task_id: UUID) -> DailyPlanTask | None:
        res = await self._session.execute(select(DailyPlanTask).where(DailyPlanTask.id == task_id))
        return res.scalar_one_or_none()

    async def update_daily_task_status(
        self,
        *,
        task: DailyPlanTask,
        status: str,
        completion_evidence_ref: str | None = None,
    ) -> DailyPlanTask:
        task.status = status
        if status == "completed":
            task.completed_at = datetime.now(UTC)
            if completion_evidence_ref:
                task.completion_evidence_ref = completion_evidence_ref
        else:
            task.completed_at = None
        await self._session.commit()
        await self._session.refresh(task)
        return task

    async def get_daily_plan_by_id(self, plan_id: UUID) -> DailyLearningPlan | None:
        res = await self._session.execute(
            select(DailyLearningPlan)
            .options(selectinload(DailyLearningPlan.tasks))
            .where(DailyLearningPlan.id == plan_id)
        )
        return res.scalar_one_or_none()

    # ------------------------------------------------------------------
    # Retention Verification Schedules & Attempts
    # ------------------------------------------------------------------

    async def list_retention_schedules(
        self, student_id: UUID, *, language_slug: str | None = None
    ) -> list[RetentionSchedule]:
        stmt = select(RetentionSchedule).where(RetentionSchedule.student_id == student_id)
        if language_slug is not None:
            stmt = stmt.where(RetentionSchedule.language_slug == language_slug)
        res = await self._session.execute(stmt.order_by(RetentionSchedule.due_at.asc()))
        return list(res.scalars().all())

    async def get_retention_schedule_by_id(self, schedule_id: UUID) -> RetentionSchedule | None:
        res = await self._session.execute(
            select(RetentionSchedule).where(RetentionSchedule.id == schedule_id)
        )
        return res.scalar_one_or_none()

    async def create_retention_schedule(
        self,
        *,
        student_id: UUID,
        skill_slug: str,
        problem_id: UUID,
        source_evidence_type: str,
        source_evidence_ref_id: str | None,
        source_verified_at: datetime,
        due_at: datetime,
        interval_hours: int = 24,
        language_slug: str = "python",
    ) -> RetentionSchedule:
        now = datetime.now(UTC)
        initial_status = "due" if due_at <= now else "scheduled"
        sched = RetentionSchedule(
            student_id=student_id,
            language_slug=language_slug,
            skill_slug=skill_slug,
            problem_id=problem_id,
            source_evidence_type=source_evidence_type,
            source_evidence_ref_id=source_evidence_ref_id,
            source_verified_at=source_verified_at,
            due_at=due_at,
            interval_hours=max(interval_hours, 24),
            status=initial_status,
        )
        self._session.add(sched)
        await self._session.commit()
        await self._session.refresh(sched)
        return sched

    async def update_retention_schedule(
        self,
        *,
        schedule: RetentionSchedule,
        status: str,
        due_at: datetime | None = None,
        interval_hours: int | None = None,
        last_attempt_at: datetime | None = None,
    ) -> RetentionSchedule:
        schedule.status = status
        if due_at is not None:
            schedule.due_at = due_at
        if interval_hours is not None:
            schedule.interval_hours = max(interval_hours, 24)
        if last_attempt_at is not None:
            schedule.last_attempt_at = last_attempt_at
        await self._session.commit()
        await self._session.refresh(schedule)
        return schedule

    async def record_retention_attempt(
        self,
        *,
        schedule_id: UUID,
        student_id: UUID,
        skill_slug: str,
        problem_id: UUID,
        submission_id: UUID | None,
        language_slug: str,
        source_code: str,
        student_explanation: str,
        verdict: str,
        passed_tests: int,
        total_tests: int,
        elapsed_hours_since_initial: float,
        outcome: str,
        summary_message: str,
    ) -> RetentionAttempt:
        attempt = RetentionAttempt(
            schedule_id=schedule_id,
            student_id=student_id,
            skill_slug=skill_slug,
            problem_id=problem_id,
            submission_id=submission_id,
            language_slug=language_slug,
            source_code=source_code,
            student_explanation=student_explanation,
            verdict=verdict,
            passed_tests=passed_tests,
            total_tests=total_tests,
            elapsed_hours_since_initial=round(elapsed_hours_since_initial, 2),
            outcome=outcome,
            summary_message=summary_message,
        )
        self._session.add(attempt)
        await self._session.commit()
        await self._session.refresh(attempt)
        return attempt

    async def list_retention_attempts(
        self, *, student_id: UUID, limit: int = 30, language_slug: str | None = None
    ) -> list[RetentionAttempt]:
        stmt = select(RetentionAttempt).where(RetentionAttempt.student_id == student_id)
        if language_slug is not None:
            stmt = stmt.where(RetentionAttempt.language_slug == language_slug)
        res = await self._session.execute(
            stmt.order_by(desc(RetentionAttempt.created_at)).limit(limit)
        )
        return list(res.scalars().all())

    # ------------------------------------------------------------------
    # Cross-Phase Evidence Queries for Learning DNA & Persistent History
    # ------------------------------------------------------------------

    async def list_student_submissions_all(
        self, *, student_id: UUID, limit: int = 120, language_slug: str | None = None
    ) -> list[tuple[Submission, Problem, ProblemVersion]]:
        stmt = (
            select(Submission, Problem, ProblemVersion)
            .join(Problem, Problem.id == Submission.problem_id)
            .join(ProblemVersion, ProblemVersion.id == Submission.problem_version_id)
            .where(Submission.student_id == student_id)
        )
        if language_slug is not None:
            stmt = stmt.where(Submission.language_slug == language_slug)
        res = await self._session.execute(stmt.order_by(desc(Submission.created_at)).limit(limit))
        return [(row[0], row[1], row[2]) for row in res.all()]

    async def list_student_revisions(
        self, *, student_id: UUID, limit: int = 80, language_slug: str | None = None
    ) -> list[tuple[CodeRevision, ProblemVersion]]:
        stmt = (
            select(CodeRevision, ProblemVersion)
            .join(ProblemVersion, ProblemVersion.id == CodeRevision.problem_version_id)
            .where(CodeRevision.student_id == student_id)
        )
        if language_slug is not None:
            stmt = stmt.where(CodeRevision.language_slug == language_slug)
        res = await self._session.execute(stmt.order_by(desc(CodeRevision.created_at)).limit(limit))
        return [(row[0], row[1]) for row in res.all()]

    async def list_student_diagnoses(
        self, *, student_id: UUID, limit: int = 80
    ) -> list[ErrorDiagnosis]:
        res = await self._session.execute(
            select(ErrorDiagnosis)
            .where(ErrorDiagnosis.student_id == student_id)
            .order_by(desc(ErrorDiagnosis.created_at))
            .limit(limit)
        )
        return list(res.scalars().all())

    async def list_student_mentor_turns(
        self, *, student_id: UUID, limit: int = 80
    ) -> list[tuple[MentorTurn, MentorSession]]:
        res = await self._session.execute(
            select(MentorTurn, MentorSession)
            .join(MentorSession, MentorSession.id == MentorTurn.session_id)
            .where(MentorSession.student_id == student_id, MentorTurn.role == "mentor")
            .order_by(desc(MentorTurn.created_at))
            .limit(limit)
        )
        return [(row[0], row[1]) for row in res.all()]

    async def list_student_hint_events(
        self, *, student_id: UUID, limit: int = 80
    ) -> list[HintEvent]:
        res = await self._session.execute(
            select(HintEvent)
            .where(HintEvent.student_id == student_id)
            .order_by(desc(HintEvent.created_at))
            .limit(limit)
        )
        return list(res.scalars().all())

    async def list_student_diagnostic_responses(
        self, *, student_id: UUID, limit: int = 120, language_slug: str | None = None
    ) -> list[DiagnosticResponse]:
        stmt = select(DiagnosticResponse).where(DiagnosticResponse.student_id == student_id)
        if language_slug is not None:
            stmt = stmt.join(
                DiagnosticSession, DiagnosticSession.id == DiagnosticResponse.session_id
            ).where(DiagnosticSession.language_slug == language_slug)
        res = await self._session.execute(
            stmt.order_by(desc(DiagnosticResponse.created_at)).limit(limit)
        )
        return list(res.scalars().all())

    async def list_student_diagnostic_sessions(
        self, *, student_id: UUID, limit: int = 30, language_slug: str | None = None
    ) -> list[DiagnosticSession]:
        stmt = select(DiagnosticSession).where(DiagnosticSession.student_id == student_id)
        if language_slug is not None:
            stmt = stmt.where(DiagnosticSession.language_slug == language_slug)
        res = await self._session.execute(
            stmt.order_by(desc(DiagnosticSession.started_at)).limit(limit)
        )
        return list(res.scalars().all())

    async def list_student_lesson_progress_with_meta(
        self, *, student_id: UUID, language_slug: str | None = None
    ) -> list[tuple[LessonProgress, Lesson, LessonVersion]]:
        stmt = (
            select(LessonProgress, Lesson, LessonVersion)
            .join(Lesson, Lesson.id == LessonProgress.lesson_id)
            .join(LessonVersion, LessonVersion.id == LessonProgress.lesson_version_id)
            .where(LessonProgress.student_id == student_id)
        )
        if language_slug is not None:
            stmt = stmt.where(Lesson.language_slug == language_slug)
        res = await self._session.execute(stmt.order_by(desc(LessonProgress.updated_at)))
        return [(row[0], row[1], row[2]) for row in res.all()]

    async def list_student_verification_attempts_all(
        self, *, student_id: UUID, limit: int = 50
    ) -> list[VerificationAttempt]:
        res = await self._session.execute(
            select(VerificationAttempt)
            .where(VerificationAttempt.student_id == student_id)
            .order_by(desc(VerificationAttempt.created_at))
            .limit(limit)
        )
        return list(res.scalars().all())

    async def list_student_skill_transitions_all(
        self, *, student_id: UUID, limit: int = 80, language_slug: str | None = None
    ) -> list[SkillStateTransition]:
        stmt = select(SkillStateTransition).where(SkillStateTransition.student_id == student_id)
        if language_slug is not None:
            stmt = stmt.where(SkillStateTransition.language_slug == language_slug)
        res = await self._session.execute(
            stmt.order_by(desc(SkillStateTransition.created_at)).limit(limit)
        )
        return list(res.scalars().all())

    async def list_student_completed_daily_tasks(
        self, *, student_id: UUID, limit: int = 60
    ) -> list[DailyPlanTask]:
        res = await self._session.execute(
            select(DailyPlanTask)
            .where(
                DailyPlanTask.student_id == student_id,
                DailyPlanTask.status == "completed",
            )
            .order_by(desc(DailyPlanTask.completed_at))
            .limit(limit)
        )
        return list(res.scalars().all())
