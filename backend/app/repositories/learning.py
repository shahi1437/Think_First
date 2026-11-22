"""Async SQLAlchemy repository for Phase 5 tracks, lessons, diagnostics, skill graph & recs."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import defer, selectinload

from app.models.learning import (
    DiagnosticQuestion,
    DiagnosticQuestionAnswer,
    DiagnosticResponse,
    DiagnosticSession,
    LearningTrack,
    Lesson,
    LessonProgress,
    LessonVersion,
    SkillNode,
    SkillPrerequisite,
    SkillStateTransition,
    StudentRecommendation,
    StudentSkillState,
    StudentTrackEnrollment,
)


class LearningRepository:
    """Persistence operations for Phase 5 adaptive learning models."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # --- Learning Tracks ---

    async def list_tracks(self) -> list[LearningTrack]:
        stmt = select(LearningTrack).order_by(LearningTrack.display_order.asc())
        return list((await self._session.execute(stmt)).scalars().all())

    async def get_track_enrollment(
        self, student_id: UUID, language_slug: str = "python"
    ) -> StudentTrackEnrollment | None:
        stmt = (
            select(StudentTrackEnrollment)
            .where(
                StudentTrackEnrollment.student_id == student_id,
                StudentTrackEnrollment.language_slug == language_slug,
            )
            .execution_options(populate_existing=True)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list_track_enrollments(self, student_id: UUID) -> list[StudentTrackEnrollment]:
        stmt = (
            select(StudentTrackEnrollment)
            .where(StudentTrackEnrollment.student_id == student_id)
            .execution_options(populate_existing=True)
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def upsert_track_enrollment(
        self,
        *,
        student_id: UUID,
        selected_track_slug: str,
        recommended_track_slug: str | None,
        recommendation_source: str,
        recommendation_reason: str,
        diagnostic_session_id: UUID | None = None,
        language_slug: str = "python",
    ) -> StudentTrackEnrollment:
        update_values: dict[str, Any] = {
            "selected_track_slug": selected_track_slug,
            "recommendation_source": recommendation_source,
            "recommendation_reason": recommendation_reason,
            "updated_at": datetime.now(UTC),
        }
        if recommended_track_slug is not None:
            update_values["recommended_track_slug"] = recommended_track_slug
        if diagnostic_session_id is not None:
            update_values["diagnostic_session_id"] = diagnostic_session_id

        stmt = (
            pg_insert(StudentTrackEnrollment)
            .values(
                student_id=student_id,
                language_slug=language_slug,
                selected_track_slug=selected_track_slug,
                recommended_track_slug=recommended_track_slug,
                recommendation_source=recommendation_source,
                recommendation_reason=recommendation_reason,
                diagnostic_session_id=diagnostic_session_id,
            )
            .on_conflict_do_update(
                index_elements=[
                    StudentTrackEnrollment.student_id,
                    StudentTrackEnrollment.language_slug,
                ],
                set_=update_values,
            )
        )
        await self._session.execute(stmt)
        await self._session.commit()
        row = await self.get_track_enrollment(student_id, language_slug=language_slug)
        assert row is not None
        return row

    # --- Skill Graph ---

    async def list_skill_nodes(self) -> list[SkillNode]:
        stmt = select(SkillNode).order_by(SkillNode.display_order.asc())
        return list((await self._session.execute(stmt)).scalars().all())

    async def list_skill_prerequisites(self) -> list[SkillPrerequisite]:
        stmt = select(SkillPrerequisite)
        return list((await self._session.execute(stmt)).scalars().all())

    async def list_student_skill_states(
        self, student_id: UUID, language_slug: str = "python"
    ) -> list[StudentSkillState]:
        stmt = (
            select(StudentSkillState)
            .where(
                StudentSkillState.student_id == student_id,
                StudentSkillState.language_slug == language_slug,
            )
            .execution_options(populate_existing=True)
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def get_student_skill_state(
        self, *, student_id: UUID, skill_slug: str, language_slug: str = "python"
    ) -> StudentSkillState | None:
        stmt = (
            select(StudentSkillState)
            .where(
                StudentSkillState.student_id == student_id,
                StudentSkillState.language_slug == language_slug,
                StudentSkillState.skill_slug == skill_slug,
            )
            .execution_options(populate_existing=True)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def upsert_skill_state(
        self,
        *,
        student_id: UUID,
        skill_slug: str,
        new_state: str,
        uncertainty_note: str,
        evidence_source: str,
        evidence_ref_id: str | None,
        reason: str,
        increment_evidence: bool = True,
        mark_verified: bool = False,
        language_slug: str = "python",
    ) -> StudentSkillState:
        now = datetime.now(UTC)
        existing = await self.get_student_skill_state(
            student_id=student_id, skill_slug=skill_slug, language_slug=language_slug
        )
        prev_state = existing.state if existing else "unobserved"

        if existing is None:
            row = StudentSkillState(
                student_id=student_id,
                language_slug=language_slug,
                skill_slug=skill_slug,
                state=new_state,
                evidence_count=1 if increment_evidence else 0,
                uncertainty_note=uncertainty_note,
                last_evidence_type=evidence_source,
                last_evidence_at=now,
                first_verified_at=now if mark_verified else None,
            )
            self._session.add(row)
        else:
            existing.state = new_state
            if increment_evidence:
                existing.evidence_count += 1
            existing.uncertainty_note = uncertainty_note
            existing.last_evidence_type = evidence_source
            existing.last_evidence_at = now
            if mark_verified and existing.first_verified_at is None:
                existing.first_verified_at = now
            row = existing

        if prev_state != new_state:
            self._session.add(
                SkillStateTransition(
                    student_id=student_id,
                    language_slug=language_slug,
                    skill_slug=skill_slug,
                    from_state=prev_state,
                    to_state=new_state,
                    evidence_source=evidence_source,
                    evidence_ref_id=evidence_ref_id,
                    reason=reason,
                )
            )

        await self._session.commit()
        await self._session.refresh(row)
        return row

    async def list_skill_transitions(
        self, *, student_id: UUID, limit: int = 20, language_slug: str | None = "python"
    ) -> list[SkillStateTransition]:
        stmt = select(SkillStateTransition).where(SkillStateTransition.student_id == student_id)
        if language_slug is not None:
            stmt = stmt.where(SkillStateTransition.language_slug == language_slug)
        stmt = stmt.order_by(SkillStateTransition.created_at.desc()).limit(limit)
        return list((await self._session.execute(stmt)).scalars().all())

    # --- Beginner Lessons ---

    async def list_published_lessons(
        self, *, language_slug: str | None = None, include_content: bool = True
    ) -> list[tuple[Lesson, LessonVersion]]:
        stmt = (
            select(Lesson, LessonVersion)
            .join(LessonVersion, Lesson.current_published_version_id == LessonVersion.id)
            .where(LessonVersion.status == "published")
            .order_by(Lesson.language_slug.asc(), Lesson.display_order.asc())
        )
        if not include_content:
            stmt = stmt.options(
                defer(LessonVersion.content_en_md),
                defer(LessonVersion.content_bn_md),
                defer(LessonVersion.interactive_examples),
                defer(LessonVersion.guided_exercise),
                defer(LessonVersion.learning_objectives),
            )
        if language_slug is not None:
            stmt = stmt.where(Lesson.language_slug == language_slug)
        rows = (await self._session.execute(stmt)).all()
        return [(row[0], row[1]) for row in rows]

    async def count_published_lessons_by_language(self) -> dict[str, int]:
        stmt = (
            select(Lesson.language_slug, func.count(Lesson.id))
            .join(LessonVersion, Lesson.current_published_version_id == LessonVersion.id)
            .where(LessonVersion.status == "published")
            .group_by(Lesson.language_slug)
        )
        return {str(row[0]): int(row[1]) for row in (await self._session.execute(stmt)).all()}

    async def count_completed_lessons_by_language(self, student_id: UUID) -> dict[str, int]:
        stmt = (
            select(Lesson.language_slug, func.count(LessonProgress.id))
            .join(Lesson, LessonProgress.lesson_id == Lesson.id)
            .join(LessonVersion, Lesson.current_published_version_id == LessonVersion.id)
            .where(
                LessonProgress.student_id == student_id,
                LessonProgress.status == "completed",
                LessonVersion.status == "published",
            )
            .group_by(Lesson.language_slug)
        )
        return {str(row[0]): int(row[1]) for row in (await self._session.execute(stmt)).all()}

    async def count_completed_diagnostics_by_language(self, student_id: UUID) -> dict[str, int]:
        stmt = (
            select(DiagnosticSession.language_slug, func.count(DiagnosticSession.id))
            .where(
                DiagnosticSession.student_id == student_id,
                DiagnosticSession.status == "completed",
            )
            .group_by(DiagnosticSession.language_slug)
        )
        return {str(row[0]): int(row[1]) for row in (await self._session.execute(stmt)).all()}

    async def list_completed_lesson_slugs(
        self, *, student_id: UUID, language_slug: str
    ) -> set[str]:
        stmt = (
            select(Lesson.slug)
            .join(LessonProgress, LessonProgress.lesson_id == Lesson.id)
            .where(
                LessonProgress.student_id == student_id,
                LessonProgress.status == "completed",
                Lesson.language_slug == language_slug,
            )
        )
        return {str(row[0]) for row in (await self._session.execute(stmt)).all()}

    async def get_published_lesson_by_slug(self, slug: str) -> tuple[Lesson, LessonVersion] | None:
        stmt = (
            select(Lesson, LessonVersion)
            .join(LessonVersion, Lesson.current_published_version_id == LessonVersion.id)
            .where(Lesson.slug == slug, LessonVersion.status == "published")
        )
        row = (await self._session.execute(stmt)).one_or_none()
        return (row[0], row[1]) if row else None

    async def get_published_lesson_by_id(
        self, lesson_id: UUID
    ) -> tuple[Lesson, LessonVersion] | None:
        stmt = (
            select(Lesson, LessonVersion)
            .join(LessonVersion, Lesson.current_published_version_id == LessonVersion.id)
            .where(Lesson.id == lesson_id, LessonVersion.status == "published")
        )
        row = (await self._session.execute(stmt)).one_or_none()
        return (row[0], row[1]) if row else None

    async def list_student_lesson_progress(self, student_id: UUID) -> dict[UUID, LessonProgress]:
        stmt = (
            select(LessonProgress)
            .where(LessonProgress.student_id == student_id)
            .execution_options(populate_existing=True)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return {r.lesson_id: r for r in rows}

    async def get_lesson_progress(
        self, *, student_id: UUID, lesson_id: UUID
    ) -> LessonProgress | None:
        stmt = (
            select(LessonProgress)
            .where(
                LessonProgress.student_id == student_id,
                LessonProgress.lesson_id == lesson_id,
            )
            .execution_options(populate_existing=True)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def upsert_lesson_progress(
        self,
        *,
        student_id: UUID,
        lesson_id: UUID,
        lesson_version_id: UUID,
        reading_completed: bool | None = None,
        exercise_passed: bool | None = None,
        increment_attempts: bool = False,
        last_code: str | None = None,
        last_verdict: str | None = None,
        last_stdout: str | None = None,
        last_stderr: str | None = None,
    ) -> LessonProgress:
        existing = await self.get_lesson_progress(student_id=student_id, lesson_id=lesson_id)
        now = datetime.now(UTC)
        if existing is None:
            passed = bool(exercise_passed)
            read_done = bool(reading_completed)
            row = LessonProgress(
                student_id=student_id,
                lesson_id=lesson_id,
                lesson_version_id=lesson_version_id,
                status="completed" if passed else "in_progress",
                reading_completed=read_done,
                exercise_passed=passed,
                exercise_attempts=1 if increment_attempts else 0,
                last_code=last_code,
                last_verdict=last_verdict,
                last_stdout=last_stdout,
                last_stderr=last_stderr,
                completed_at=now if passed else None,
            )
            self._session.add(row)
        else:
            existing.lesson_version_id = lesson_version_id
            if reading_completed is not None:
                existing.reading_completed = existing.reading_completed or reading_completed
            if increment_attempts:
                existing.exercise_attempts += 1
            if last_code is not None:
                existing.last_code = last_code
            if last_verdict is not None:
                existing.last_verdict = last_verdict
            if last_stdout is not None:
                existing.last_stdout = last_stdout
            if last_stderr is not None:
                existing.last_stderr = last_stderr
            if exercise_passed:
                existing.exercise_passed = True
                existing.status = "completed"
                if existing.completed_at is None:
                    existing.completed_at = now
            elif existing.status == "not_started":
                existing.status = "in_progress"
            row = existing

        await self._session.commit()
        await self._session.refresh(row)
        return row

    async def create_admin_lesson(
        self,
        *,
        actor_id: UUID,
        slug: str,
        skill_slug: str,
        display_order: int,
        version_data: dict[str, Any],
        publish: bool,
        language_slug: str = "python",
    ) -> tuple[Lesson, LessonVersion]:
        stmt = select(Lesson).where(Lesson.slug == slug)
        lesson = (await self._session.execute(stmt)).scalar_one_or_none()
        now = datetime.now(UTC)

        if lesson is None:
            lesson = Lesson(
                slug=slug,
                language_slug=language_slug,
                skill_slug=skill_slug,
                display_order=display_order,
                created_by=actor_id,
            )
            self._session.add(lesson)
            await self._session.flush()
            next_ver = 1
        else:
            lesson.language_slug = language_slug
            ver_stmt = select(LessonVersion.version_number).where(
                LessonVersion.lesson_id == lesson.id
            )
            existing_nums = list((await self._session.execute(ver_stmt)).scalars().all())
            next_ver = max(existing_nums, default=0) + 1

        lv = LessonVersion(
            lesson_id=lesson.id,
            version_number=next_ver,
            status="published" if publish else "draft",
            published_by=actor_id if publish else None,
            published_at=now if publish else None,
            **version_data,
        )
        self._session.add(lv)
        await self._session.flush()
        if publish:
            lesson.current_published_version_id = lv.id
        await self._session.commit()
        await self._session.refresh(lesson)
        await self._session.refresh(lv)
        return lesson, lv

    # --- Diagnostic Questions & Sessions ---

    async def list_published_diagnostic_questions(
        self, *, language_slug: str | None = None
    ) -> list[DiagnosticQuestion]:
        stmt = (
            select(DiagnosticQuestion)
            .where(DiagnosticQuestion.status == "published")
            .options(selectinload(DiagnosticQuestion.answer_key))
            .order_by(DiagnosticQuestion.domain_slug.asc(), DiagnosticQuestion.slug.asc())
        )
        if language_slug is not None:
            stmt = stmt.where(DiagnosticQuestion.language_slug == language_slug)
        return list((await self._session.execute(stmt)).scalars().all())

    async def get_diagnostic_question_with_answer(
        self, question_id: UUID
    ) -> DiagnosticQuestion | None:
        stmt = (
            select(DiagnosticQuestion)
            .where(DiagnosticQuestion.id == question_id)
            .options(selectinload(DiagnosticQuestion.answer_key))
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def create_admin_diagnostic_question(
        self,
        *,
        actor_id: UUID,
        question_data: dict[str, Any],
        answer_data: dict[str, Any],
        publish: bool,
    ) -> DiagnosticQuestion:
        now = datetime.now(UTC)
        q = DiagnosticQuestion(
            status="published" if publish else "draft",
            reviewed_by=actor_id if publish else None,
            published_at=now if publish else None,
            **question_data,
        )
        self._session.add(q)
        await self._session.flush()
        ans = DiagnosticQuestionAnswer(question_id=q.id, **answer_data)
        self._session.add(ans)
        await self._session.commit()
        reloaded = await self.get_diagnostic_question_with_answer(q.id)
        assert reloaded is not None
        return reloaded

    async def create_diagnostic_session(
        self,
        *,
        student_id: UUID,
        explanation_language: str,
        question_queue: list[str],
        language_slug: str = "python",
        domain_summary: dict[str, Any] | None = None,
    ) -> DiagnosticSession:
        sess = DiagnosticSession(
            student_id=student_id,
            language_slug=language_slug,
            status="in_progress",
            explanation_language=explanation_language,
            question_queue=question_queue,
            current_index=0,
            adaptive_followups_added=0,
            domain_summary=domain_summary or {},
        )
        self._session.add(sess)
        await self._session.commit()
        loaded = await self.get_diagnostic_session(sess.id)
        assert loaded is not None
        return loaded

    async def get_diagnostic_session(self, session_id: UUID) -> DiagnosticSession | None:
        stmt = (
            select(DiagnosticSession)
            .where(DiagnosticSession.id == session_id)
            .options(selectinload(DiagnosticSession.responses))
            .execution_options(populate_existing=True)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list_student_diagnostic_sessions(
        self, *, student_id: UUID, limit: int = 10, language_slug: str | None = None
    ) -> list[DiagnosticSession]:
        stmt = (
            select(DiagnosticSession)
            .where(DiagnosticSession.student_id == student_id)
            .options(selectinload(DiagnosticSession.responses))
            .order_by(DiagnosticSession.created_at.desc())
            .limit(limit)
            .execution_options(populate_existing=True)
        )
        if language_slug is not None:
            stmt = stmt.where(DiagnosticSession.language_slug == language_slug)
        return list((await self._session.execute(stmt)).scalars().all())

    async def save_diagnostic_response_and_advance(
        self,
        *,
        session: DiagnosticSession,
        response_data: dict[str, Any],
        updated_queue: list[str],
        next_index: int,
        followups_added: int,
        completed: bool,
        recommended_track_slug: str | None = None,
        domain_summary: dict[str, Any] | None = None,
        recommendation_rationale: str | None = None,
    ) -> DiagnosticSession:
        resp = DiagnosticResponse(
            session_id=session.id,
            student_id=session.student_id,
            **response_data,
        )
        self._session.add(resp)
        session.question_queue = updated_queue
        session.current_index = next_index
        session.adaptive_followups_added = followups_added
        if domain_summary is not None:
            session.domain_summary = domain_summary
        if completed:
            session.status = "completed"
            session.completed_at = datetime.now(UTC)
            session.recommended_track_slug = recommended_track_slug
            session.recommendation_rationale = recommendation_rationale
        await self._session.commit()
        reloaded = await self.get_diagnostic_session(session.id)
        assert reloaded is not None
        return reloaded

    async def finalize_diagnostic_session(
        self,
        *,
        session_id: UUID,
        recommended_track_slug: str,
        recommendation_rationale: str,
        domain_summary: dict[str, Any],
    ) -> DiagnosticSession:
        sess = await self.get_diagnostic_session(session_id)
        assert sess is not None
        sess.status = "completed"
        sess.completed_at = datetime.now(UTC)
        sess.recommended_track_slug = recommended_track_slug
        sess.recommendation_rationale = recommendation_rationale
        sess.domain_summary = domain_summary
        await self._session.commit()
        reloaded = await self.get_diagnostic_session(session_id)
        assert reloaded is not None
        return reloaded

    # --- Recommendations ---

    async def replace_student_recommendations(
        self,
        *,
        student_id: UUID,
        items: list[dict[str, Any]],
        language_slug: str = "python",
    ) -> list[StudentRecommendation]:
        existing = list(
            (
                await self._session.execute(
                    select(StudentRecommendation)
                    .where(
                        StudentRecommendation.student_id == student_id,
                        StudentRecommendation.language_slug == language_slug,
                    )
                    .order_by(StudentRecommendation.priority.asc())
                )
            )
            .scalars()
            .all()
        )
        existing_sig = [
            (r.recommendation_type, r.target_id, r.target_slug, r.priority, r.reason_en)
            for r in existing
        ]
        next_sig = [
            (
                item["recommendation_type"],
                item["target_id"],
                item["target_slug"],
                item["priority"],
                item["reason_en"],
            )
            for item in items
        ]
        if existing_sig == next_sig:
            return existing

        await self._session.execute(
            delete(StudentRecommendation).where(
                StudentRecommendation.student_id == student_id,
                StudentRecommendation.language_slug == language_slug,
            )
        )
        created: list[StudentRecommendation] = []
        for item in items:
            row = StudentRecommendation(
                student_id=student_id,
                language_slug=language_slug,
                **item,
            )
            self._session.add(row)
            created.append(row)
        await self._session.commit()
        return created
