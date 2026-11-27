"""Verified Learning Progress service — separates execution-proven achievements from estimates."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from typing import Literal
from uuid import UUID

from app.repositories.classroom import ClassroomRepository
from app.repositories.growth import GrowthRepository
from app.repositories.identity import UserRecord
from app.repositories.learning import LearningRepository
from app.schemas.growth import (
    DailyActivityPointView,
    VerifiedLanguageBreakdownView,
    VerifiedLearningProgressView,
)

_VERIFIED_SKILL_STATES = frozenset({"independent", "transferred", "retained"})
_IN_PROGRESS_SKILL_STATES = frozenset({"introduced", "guided", "emerging"})


class VerifiedProgressService:
    """Computes strictly evidence-based learning progress without fabricating metrics."""

    def __init__(
        self,
        *,
        growth_repo: GrowthRepository,
        learning_repo: LearningRepository,
        classroom_repo: ClassroomRepository | None = None,
    ) -> None:
        self._growth_repo = growth_repo
        self._learning_repo = learning_repo
        self._classroom_repo = classroom_repo

    async def get_verified_progress(
        self,
        *,
        user: UserRecord,
        language_slug: str | None = None,
    ) -> VerifiedLearningProgressView:
        subs = await self._growth_repo.list_student_submissions_all(
            student_id=user.id, limit=250, language_slug=language_slug
        )
        lessons = await self._growth_repo.list_student_lesson_progress_with_meta(
            student_id=user.id, language_slug=language_slug
        )
        skill_states = await self._learning_repo.list_student_skill_states(
            student_id=user.id, language_slug=language_slug
        )
        verifs = await self._growth_repo.list_student_verification_attempts_all(
            student_id=user.id, limit=100
        )
        retentions = await self._growth_repo.list_retention_attempts(
            student_id=user.id, limit=100, language_slug=language_slug
        )
        diag_sessions = await self._growth_repo.list_student_diagnostic_sessions(
            student_id=user.id, limit=50, language_slug=language_slug
        )

        # 1. Execution-verified problem solves & per-language breakdown
        attempted_problems: set[UUID] = set()
        solved_problems: set[UUID] = set()
        accepted_submissions = 0

        lang_attempted: dict[str, set[UUID]] = defaultdict(set)
        lang_solved: dict[str, set[UUID]] = defaultdict(set)
        lang_total_subs: dict[str, int] = defaultdict(int)
        lang_lessons_done: dict[str, int] = defaultdict(int)

        today = datetime.now(UTC).date()
        window_days = [today - timedelta(days=i) for i in range(13, -1, -1)]
        day_subs: dict[date, int] = {d: 0 for d in window_days}
        day_acc: dict[date, int] = {d: 0 for d in window_days}
        day_lessons: dict[date, int] = {d: 0 for d in window_days}

        ordered_subs = sorted(subs, key=lambda row: row[0].created_at)
        for sub, prob, _ in ordered_subs:
            attempted_problems.add(prob.id)
            lang = str(sub.language_slug)
            lang_attempted[lang].add(prob.id)
            lang_total_subs[lang] += 1
            if str(sub.verdict) == "accepted":
                accepted_submissions += 1
                solved_problems.add(prob.id)
                lang_solved[lang].add(prob.id)
            ev_day = sub.created_at.date()
            if ev_day in day_subs:
                day_subs[ev_day] += 1
                if str(sub.verdict) == "accepted":
                    day_acc[ev_day] += 1

        lessons_completed = 0
        for prog, lsn, _ in lessons:
            if prog.status == "completed" or prog.exercise_passed:
                lessons_completed += 1
                lang_lessons_done[str(lsn.language_slug)] += 1
                ts = prog.completed_at or prog.updated_at
                ev_day = ts.date()
                if ev_day in day_lessons:
                    day_lessons[ev_day] += 1

        all_langs = sorted(set(lang_total_subs.keys()) | set(lang_lessons_done.keys()))
        languages_used = [
            VerifiedLanguageBreakdownView(
                language_slug=lg,
                problems_attempted=len(lang_attempted[lg]),
                problems_solved_verified=len(lang_solved[lg]),
                lessons_completed=lang_lessons_done[lg],
                total_submissions=lang_total_subs[lg],
            )
            for lg in all_langs
        ]

        # 2. Concepts mastered (verified) vs in-progress (guided/estimated)
        mastered = sorted(
            {st.skill_slug for st in skill_states if st.state in _VERIFIED_SKILL_STATES}
        )
        in_progress = sorted(
            {st.skill_slug for st in skill_states if st.state in _IN_PROGRESS_SKILL_STATES}
        )

        # 3. Classroom assignments completion & published grades
        assignments_total = 0
        assignments_completed = 0
        published_grade_pcts: list[float] = []
        if self._classroom_repo is not None:
            memberships = await self._classroom_repo.list_student_memberships(student_id=user.id)
            active_course_ids = [c.id for m, c in memberships if m.status == "active"]
            if active_course_ids:
                asns = await self._classroom_repo.list_assignments_for_courses(
                    course_ids=active_course_ids, published_only=True
                )
                assignments_total = len(asns)
                subs_map = await self._classroom_repo.list_submissions_for_student(
                    student_id=user.id, assignment_ids=[a.id for a in asns]
                )
                for asn in asns:
                    asub = subs_map.get(asn.id)
                    if asub is None:
                        continue
                    if asub.status in ("submitted", "resubmitted", "graded"):
                        assignments_completed += 1
                    if (
                        asub.grade is not None
                        and asub.grade.status == "published"
                        and float(asub.grade.max_marks) > 0
                    ):
                        pct = (float(asub.grade.marks_awarded) / float(asub.grade.max_marks)) * 100
                        published_grade_pcts.append(round(pct, 1))

        avg_grade = (
            round(sum(published_grade_pcts) / len(published_grade_pcts), 1)
            if published_grade_pcts
            else None
        )

        # 4. Transfer & spaced retention verified checks
        transfer_passed = sum(1 for v in verifs if str(v.outcome) == "verified_independent")
        retention_passed = sum(1 for r in retentions if str(r.outcome) == "retained_verified")

        # 5. 14-day factual consistency & honest improvement trend (requires >=4 submissions)
        daily_points = [
            DailyActivityPointView(
                day=d,
                submissions_count=day_subs[d],
                accepted_count=day_acc[d],
                lessons_completed=day_lessons[d],
            )
            for d in window_days
        ]
        active_days = sum(
            1 for p in daily_points if p.submissions_count > 0 or p.lessons_completed > 0
        )

        trend: Literal["improving", "steady", "needs_focus", "insufficient_data"]
        early_rate: float | None = None
        recent_rate: float | None = None
        if len(ordered_subs) >= 4:
            mid = len(ordered_subs) // 2
            early_slice = ordered_subs[:mid]
            recent_slice = ordered_subs[mid:]
            early_rate = round(
                (sum(1 for s, _, _ in early_slice if s.verdict == "accepted") / len(early_slice))
                * 100.0,
                1,
            )
            recent_rate = round(
                (sum(1 for s, _, _ in recent_slice if s.verdict == "accepted") / len(recent_slice))
                * 100.0,
                1,
            )
            delta = recent_rate - early_rate
            if delta >= 8.0:
                trend = "improving"
            elif delta <= -8.0:
                trend = "needs_focus"
            else:
                trend = "steady"
        else:
            trend = "insufficient_data"

        completed_diagnostics = sum(1 for ds in diag_sessions if ds.status == "completed")

        return VerifiedLearningProgressView(
            problems_attempted=len(attempted_problems),
            problems_solved_verified=len(solved_problems),
            total_submissions=len(ordered_subs),
            accepted_submissions=accepted_submissions,
            languages_used=languages_used,
            concepts_mastered_verified=mastered,
            concepts_in_progress=in_progress,
            assignments_completed_verified=assignments_completed,
            assignments_total=assignments_total,
            average_published_grade_pct=avg_grade,
            transfer_verifications_passed=transfer_passed,
            retention_checks_passed=retention_passed,
            consistency_active_days_14d=active_days,
            daily_activity_14d=daily_points,
            improvement_trend=trend,
            early_acceptance_rate_pct=early_rate,
            recent_acceptance_rate_pct=recent_rate,
            estimated_lessons_completed=lessons_completed,
            estimated_diagnostic_sessions=completed_diagnostics,
            estimated_guided_skills_count=len(in_progress),
            methodology_note=(
                "Verified achievements count only Judge0/Piston accepted executions, "
                "zero-hint independent transfer checks, >=24h spaced retention checks, "
                "and published instructor grades. Lesson readings, diagnostics, and guided "
                "skills are tracked separately as in-progress estimates."
            ),
        )
