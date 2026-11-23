"""Async SQLAlchemy repository for Phase 8 Admin Overview, Curriculum & Audit inspection."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.classroom import Assignment, Course, CourseMembership
from app.models.identity import AuditLog, Profile, UserRole
from app.models.learning import (
    CurriculumValidation,
    DiagnosticQuestion,
    DiagnosticQuestionAnswer,
    LearningTrack,
    Lesson,
    LessonVersion,
    SkillNode,
)
from app.models.mentor import KnowledgeDocument
from app.models.problems import Problem, ProblemVersion


class AdminRepository:
    """Queries and updates for Admin Studio overview, audit logs, tracks, lessons & diagnostics."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_latest_problem_status_rows(self) -> list[tuple[Problem, ProblemVersion]]:
        latest_subq = (
            select(
                ProblemVersion.problem_id,
                func.max(ProblemVersion.version_number).label("max_ver"),
            )
            .group_by(ProblemVersion.problem_id)
            .subquery()
        )
        stmt = (
            select(Problem, ProblemVersion)
            .join(latest_subq, Problem.id == latest_subq.c.problem_id)
            .join(
                ProblemVersion,
                (ProblemVersion.problem_id == latest_subq.c.problem_id)
                & (ProblemVersion.version_number == latest_subq.c.max_ver),
            )
            .order_by(ProblemVersion.updated_at.desc())
        )
        rows = (await self._session.execute(stmt)).all()
        return [(r[0], r[1]) for r in rows]

    async def list_all_lessons_with_latest(self) -> list[tuple[Lesson, LessonVersion]]:
        latest_subq = (
            select(
                LessonVersion.lesson_id,
                func.max(LessonVersion.version_number).label("max_ver"),
            )
            .group_by(LessonVersion.lesson_id)
            .subquery()
        )
        stmt = (
            select(Lesson, LessonVersion)
            .join(latest_subq, Lesson.id == latest_subq.c.lesson_id)
            .join(
                LessonVersion,
                (LessonVersion.lesson_id == latest_subq.c.lesson_id)
                & (LessonVersion.version_number == latest_subq.c.max_ver),
            )
            .order_by(Lesson.display_order.asc())
        )
        rows = (await self._session.execute(stmt)).all()
        return [(r[0], r[1]) for r in rows]

    async def list_lesson_overview_rows(self) -> list[tuple[UUID | None, list[str]]]:
        """Lightweight projection for Admin Overview (skips large markdown/exercise columns)."""
        latest_subq = (
            select(
                LessonVersion.lesson_id,
                func.max(LessonVersion.version_number).label("max_ver"),
            )
            .group_by(LessonVersion.lesson_id)
            .subquery()
        )
        stmt = (
            select(Lesson.current_published_version_id, LessonVersion.track_slugs)
            .join(latest_subq, Lesson.id == latest_subq.c.lesson_id)
            .join(
                LessonVersion,
                (LessonVersion.lesson_id == latest_subq.c.lesson_id)
                & (LessonVersion.version_number == latest_subq.c.max_ver),
            )
        )
        rows = (await self._session.execute(stmt)).all()
        return [(r[0], list(r[1] or [])) for r in rows]

    async def get_diagnostic_question_counts(self) -> tuple[int, int]:
        """Aggregate published and stretch diagnostic counts in one SQL query."""
        stmt = select(
            func.count().filter(DiagnosticQuestion.status == "published"),
            func.count().filter(
                (DiagnosticQuestion.status == "published")
                & (DiagnosticQuestion.difficulty == "stretch")
            ),
        ).select_from(DiagnosticQuestion)
        row = (await self._session.execute(stmt)).one()
        return int(row[0] or 0), int(row[1] or 0)

    async def get_lesson_latest(self, lesson_id: UUID) -> tuple[Lesson, LessonVersion] | None:
        stmt = (
            select(Lesson, LessonVersion)
            .join(LessonVersion, LessonVersion.lesson_id == Lesson.id)
            .where(Lesson.id == lesson_id)
            .order_by(LessonVersion.version_number.desc())
            .limit(1)
            .execution_options(populate_existing=True)
        )
        row = (await self._session.execute(stmt)).one_or_none()
        return (row[0], row[1]) if row else None

    async def set_lesson_status(
        self, *, lesson: Lesson, version: LessonVersion, status_value: str, actor_id: UUID
    ) -> LessonVersion:
        version.status = status_value
        if status_value == "published":
            version.published_by = actor_id
            version.published_at = datetime.now(UTC)
            lesson.current_published_version_id = version.id
        elif status_value == "archived" and lesson.current_published_version_id == version.id:
            lesson.current_published_version_id = None
        await self._session.commit()
        await self._session.refresh(version)
        await self._session.refresh(lesson)
        return version

    async def list_all_diagnostic_questions(self) -> list[DiagnosticQuestion]:
        stmt = (
            select(DiagnosticQuestion)
            .options(selectinload(DiagnosticQuestion.answer_key))
            .order_by(
                DiagnosticQuestion.domain_slug.asc(),
                DiagnosticQuestion.difficulty.asc(),
                DiagnosticQuestion.slug.asc(),
            )
            .execution_options(populate_existing=True)
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def get_diagnostic_question(self, question_id: UUID) -> DiagnosticQuestion | None:
        stmt = (
            select(DiagnosticQuestion)
            .where(DiagnosticQuestion.id == question_id)
            .options(selectinload(DiagnosticQuestion.answer_key))
            .execution_options(populate_existing=True)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def get_diagnostic_question_by_slug(self, slug: str) -> DiagnosticQuestion | None:
        stmt = (
            select(DiagnosticQuestion)
            .where(DiagnosticQuestion.slug == slug)
            .options(selectinload(DiagnosticQuestion.answer_key))
            .execution_options(populate_existing=True)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def update_diagnostic_question(
        self,
        *,
        question: DiagnosticQuestion,
        question_data: dict[str, Any],
        answer_data: dict[str, Any],
    ) -> DiagnosticQuestion:
        for k, v in question_data.items():
            setattr(question, k, v)
        if question.answer_key is None:
            self._session.add(DiagnosticQuestionAnswer(question_id=question.id, **answer_data))
        else:
            for k, v in answer_data.items():
                setattr(question.answer_key, k, v)
        await self._session.commit()
        reloaded = await self.get_diagnostic_question(question.id)
        assert reloaded is not None
        return reloaded

    async def set_diagnostic_status(
        self, *, question: DiagnosticQuestion, status_value: str, actor_id: UUID
    ) -> DiagnosticQuestion:
        question.status = status_value
        if status_value in ("approved", "published"):
            question.reviewed_by = actor_id
        if status_value == "published":
            question.published_at = datetime.now(UTC)
        await self._session.commit()
        reloaded = await self.get_diagnostic_question(question.id)
        assert reloaded is not None
        return reloaded

    async def update_track(
        self,
        *,
        track_slug: str,
        title_en: str,
        title_bn: str,
        summary_en: str,
        summary_bn: str,
        recommended_focus_skills: list[str],
    ) -> LearningTrack | None:
        track = (
            await self._session.execute(
                select(LearningTrack).where(LearningTrack.slug == track_slug)
            )
        ).scalar_one_or_none()
        if track is None:
            return None
        track.title_en = title_en
        track.title_bn = title_bn
        track.summary_en = summary_en
        track.summary_bn = summary_bn
        track.recommended_focus_skills = recommended_focus_skills
        await self._session.commit()
        await self._session.refresh(track)
        return track

    async def list_knowledge_status_counts(self) -> tuple[int, int]:
        stmt = select(
            func.count().filter(KnowledgeDocument.status == "approved"),
            func.count(),
        ).select_from(KnowledgeDocument)
        row = (await self._session.execute(stmt)).one()
        return int(row[0] or 0), int(row[1] or 0)

    async def count_skill_nodes(self) -> int:
        return int(
            (await self._session.execute(select(func.count()).select_from(SkillNode))).scalar_one()
        )

    async def get_role_and_classroom_counts(self) -> dict[str, int]:
        role_rows = (
            await self._session.execute(
                select(UserRole.role, func.count(func.distinct(UserRole.user_id))).group_by(
                    UserRole.role
                )
            )
        ).all()
        role_map = {str(role): int(cnt) for role, cnt in role_rows}

        classroom_stmt = select(
            select(func.count()).select_from(Course).scalar_subquery(),
            select(func.count())
            .select_from(Course)
            .where(Course.status == "active")
            .scalar_subquery(),
            select(func.count())
            .select_from(CourseMembership)
            .where(CourseMembership.status == "active")
            .scalar_subquery(),
            select(func.count())
            .select_from(Assignment)
            .where(Assignment.status == "published")
            .scalar_subquery(),
        )
        c_row = (await self._session.execute(classroom_stmt)).one()
        return {
            "students_count": role_map.get("student", 0),
            "teachers_count": role_map.get("teacher", 0),
            "admins_count": role_map.get("admin", 0),
            "courses_total": int(c_row[0] or 0),
            "courses_active": int(c_row[1] or 0),
            "enrollments_active": int(c_row[2] or 0),
            "assignments_published": int(c_row[3] or 0),
        }

    async def list_tracks(self) -> list[LearningTrack]:
        stmt = select(LearningTrack).order_by(LearningTrack.display_order.asc())
        return list((await self._session.execute(stmt)).scalars().all())

    async def list_audit_logs(
        self,
        *,
        action_prefix: str | None = None,
        target_type: str | None = None,
        limit: int = 40,
        offset: int = 0,
    ) -> tuple[list[tuple[AuditLog, Profile | None]], int]:
        base = select(AuditLog, Profile).outerjoin(Profile, AuditLog.actor_user_id == Profile.id)
        if action_prefix:
            base = base.where(AuditLog.action.ilike(f"{action_prefix.strip()}%"))
        if target_type:
            base = base.where(AuditLog.target_type == target_type.strip())
        total = int(
            (
                await self._session.execute(select(func.count()).select_from(base.subquery()))
            ).scalar_one()
        )
        rows = (
            await self._session.execute(
                base.order_by(AuditLog.created_at.desc()).limit(limit).offset(offset)
            )
        ).all()
        return [(r[0], r[1]) for r in rows], total

    async def record_validation(
        self,
        *,
        target_type: str,
        target_id: UUID,
        validator_id: UUID,
        passed: bool,
        summary: dict[str, Any],
    ) -> None:
        self._session.add(
            CurriculumValidation(
                target_type=target_type,
                target_id=target_id,
                validator_id=validator_id,
                passed=passed,
                summary=summary,
            )
        )
        await self._session.commit()
