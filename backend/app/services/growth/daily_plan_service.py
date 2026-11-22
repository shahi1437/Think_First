"""Deterministic Adaptive Daily Learning Plan service.

Builds personalized daily study tasks grounded in:
- Learner track (`selected_track_slug`)
- Prerequisite readiness & Skill Graph gaps
- Available daily study time (`available_minutes`, 15-240 min)
- Real diagnostic results, incomplete beginner lessons, debugging problems,
  unlocked transfer challenges, and due/scheduled retention checks.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID

from fastapi import status

from app.core.errors import AppError
from app.models.growth import DailyLearningPlan
from app.repositories.growth import GrowthRepository
from app.repositories.identity import UserRecord
from app.repositories.mentor import MentorRepository
from app.repositories.problems import ProblemRepository
from app.schemas.growth import (
    DailyLearningPlanView,
    DailyPlanHistoryItemView,
    DailyPlanTaskView,
    DailyPlanWorkspaceView,
    UpdateDailyTaskStatusRequest,
)
from app.services.growth.retention_service import RetentionVerificationService
from app.services.learning.diagnostics_service import DiagnosticAssessmentService
from app.services.learning.lessons_service import (
    LessonsAndTracksService,
    resolve_user_language,
)
from app.services.learning.skill_graph import SkillGraphService


def _plan_to_view(plan: DailyLearningPlan) -> DailyLearningPlanView:
    ordered_tasks = sorted(plan.tasks, key=lambda t: t.task_order)
    task_views = [
        DailyPlanTaskView(
            id=t.id,
            task_order=t.task_order,
            task_type=t.task_type,
            skill_slug=t.skill_slug,
            target_id=t.target_id,
            target_slug=t.target_slug,
            title_en=t.title_en,
            title_bn=t.title_bn,
            reason_en=t.reason_en,
            reason_bn=t.reason_bn,
            href=t.href,
            estimated_minutes=t.estimated_minutes,
            status=t.status,
            completed_at=t.completed_at,
            completion_evidence_ref=t.completion_evidence_ref,
        )
        for t in ordered_tasks
    ]
    completed_count = sum(1 for t in task_views if t.status == "completed")
    return DailyLearningPlanView(
        id=plan.id,
        language_slug=plan.language_slug,
        plan_date=plan.plan_date,
        version_number=plan.version_number,
        is_active=plan.is_active,
        selected_track_slug=plan.selected_track_slug,
        available_minutes=plan.available_minutes,
        total_estimated_minutes=plan.total_estimated_minutes,
        completed_tasks=completed_count,
        total_tasks=len(task_views),
        generation_reason_en=plan.generation_reason_en,
        generation_reason_bn=plan.generation_reason_bn,
        tasks=task_views,
        created_at=plan.created_at,
        updated_at=plan.updated_at,
    )


def _plan_to_history_item(plan: DailyLearningPlan) -> DailyPlanHistoryItemView:
    completed = sum(1 for t in plan.tasks if t.status == "completed")
    return DailyPlanHistoryItemView(
        id=plan.id,
        plan_date=plan.plan_date,
        version_number=plan.version_number,
        is_active=plan.is_active,
        available_minutes=plan.available_minutes,
        total_estimated_minutes=plan.total_estimated_minutes,
        completed_tasks=completed,
        total_tasks=len(plan.tasks),
        created_at=plan.created_at,
    )


class DailyPlanService:
    """Generates, persists, regenerates, and tracks personalized daily learning plans."""

    def __init__(
        self,
        *,
        growth_repo: GrowthRepository,
        problem_repo: ProblemRepository,
        mentor_repo: MentorRepository,
        lessons_service: LessonsAndTracksService,
        diagnostics_service: DiagnosticAssessmentService,
        skill_graph_service: SkillGraphService,
        retention_service: RetentionVerificationService,
    ) -> None:
        self._growth_repo = growth_repo
        self._problem_repo = problem_repo
        self._mentor_repo = mentor_repo
        self._lessons = lessons_service
        self._diagnostics = diagnostics_service
        self._skill_graph = skill_graph_service
        self._retention = retention_service

    async def _build_tasks(
        self, *, user: UserRecord, available_minutes: int, language_slug: str = "python"
    ) -> tuple[str, str, str, dict[str, Any], list[dict[str, Any]]]:
        track_status = await self._lessons.get_track_status(user, language_slug=language_slug)
        lessons = await self._lessons.list_lessons(user=user, language_slug=language_slug)
        skill_graph = await self._skill_graph.get_student_skill_graph(
            user.id, language_slug=language_slug
        )
        diag_sessions = await self._diagnostics.list_my_sessions(
            user=user, language_slug=language_slug
        )
        completed_diags = [s for s in diag_sessions if s.status == "completed"]
        latest_diag = completed_diags[0] if completed_diags else None
        retention_overview = await self._retention.get_retention_overview(
            user, language_slug=language_slug
        )

        skill_state_map = {n.slug: n.state for n in skill_graph.nodes}
        tasks: list[dict[str, Any]] = []
        used_minutes = 0

        def can_fit(est: int) -> bool:
            return len(tasks) == 0 or (used_minutes + est <= available_minutes)

        # Priority 1: Due retention checks first (spaced verification protects real retention)
        due_retentions = [s for s in retention_overview.schedules if s.is_due_now]
        for sched in due_retentions[:2]:
            est = 15
            if not can_fit(est):
                break
            tasks.append(
                {
                    "task_type": "retention",
                    "skill_slug": sched.skill_slug,
                    "target_id": str(sched.id),
                    "target_slug": sched.problem_slug,
                    "title_en": f"Retention Check: {sched.skill_title_en}",
                    "title_bn": f"রিটেনশন যাচাই: {sched.skill_title_bn}",
                    "reason_en": (
                        f"Your {sched.interval_hours}h spaced retention window for "
                        f"'{sched.skill_title_en}' is now due. Pass Judge0 to earn Retained."
                    ),
                    "reason_bn": (
                        f"'{sched.skill_title_bn}' দক্ষতার {sched.interval_hours} ঘণ্টার রিটেনশন যাচাই "
                        "এখন উন্মুক্ত। Judge0 পাস করে Retained অর্জন করো।"
                    ),
                    "href": "/student/retention",
                    "estimated_minutes": est,
                }
            )
            used_minutes += est

        # Priority 2: Adaptive Entry Diagnostic (for beginners, wait until >=2 foundation lessons done!)
        completed_lessons_count = sum(1 for lsn in lessons if lsn.progress_status == "completed")
        prefs = user.preferences
        is_beginner_entry = bool(
            (prefs.programming_experience if prefs else "none") in ("none", "beginner")
            and (prefs.starting_preference if prefs else "guided_beginner") == "guided_beginner"
        )
        lang_labels = {
            "python": "Python",
            "javascript": "JavaScript",
            "c": "C",
            "cpp": "C++",
            "java": "Java",
        }
        lang_name = lang_labels.get(language_slug, language_slug.capitalize())

        if latest_diag is None and can_fit(15):
            if not is_beginner_entry:
                tasks.append(
                    {
                        "task_type": "diagnostic",
                        "skill_slug": None,
                        "target_id": f"diagnostic-8-domain-{language_slug}",
                        "target_slug": "diagnostic-8-domain",
                        "title_en": f"Complete 8-Domain {lang_name} Adaptive Diagnostic",
                        "title_bn": f"৮-ডোমেইন {lang_name} অ্যাডাপ্টিভ ডায়াগনস্টিক সম্পন্ন করো",
                        "reason_en": (
                            f"Establishes evidence-backed track placement across 8 {lang_name} domains "
                            "instead of relying on self-reported experience."
                        ),
                        "reason_bn": (
                            f"নিজের অনুমানের বদলে ৮টি {lang_name} ডোমেইনে বাস্তব প্রমাণের ভিত্তিতে সঠিক ট্র্যাক নির্ধারণ করবে।"
                        ),
                        "href": "/student/diagnostic?mode=full",
                        "estimated_minutes": 15,
                    }
                )
                used_minutes += 15
            elif completed_lessons_count >= 2:
                tasks.append(
                    {
                        "task_type": "diagnostic",
                        "skill_slug": None,
                        "target_id": f"diagnostic-readiness-{language_slug}",
                        "target_slug": "diagnostic-readiness",
                        "title_en": f"Take Short {lang_name} Foundation Readiness Check",
                        "title_bn": f"{lang_name} সংক্ষিপ্ত প্রস্তুতি যাচাই সম্পন্ন করো",
                        "reason_en": (
                            f"You finished {completed_lessons_count} foundation lessons — confirm your "
                            f"{lang_name} track with a quick 4-question readiness check."
                        ),
                        "reason_bn": (
                            f"তুমি {completed_lessons_count}টি প্রাথমিক লেসন সম্পন্ন করেছ — চারটি প্রশ্নের "
                            f"সংক্ষিপ্ত যাচাই দিয়ে তোমার {lang_name} ট্র্যাক নিশ্চিত করো।"
                        ),
                        "href": "/student/diagnostic?mode=readiness",
                        "estimated_minutes": 10,
                    }
                )
                used_minutes += 10

        # Priority 3: Gap-targeted or prerequisite-ready lessons matching selected track
        gap_skills: set[str] = set()
        if latest_diag is not None:
            domain_to_skill = {
                "variables": "variables",
                "syntax_runtime_debugging": "debugging_basics",
                "conditions": "conditions",
                "loop_boundaries": "loops",
                "arrays_lists": "lists",
                "indexing": "indexing",
                "functions": "functions",
                "mixed_logic": "mixed_problem_solving",
            }
            for ev in latest_diag.domain_evidence:
                if ev.evidence_status in ("gap_detected", "guided_needed"):
                    gap_skills.add(domain_to_skill.get(ev.domain_slug, ev.domain_slug))

        incomplete_lessons = [lsn for lsn in lessons if lsn.progress_status != "completed"]
        ordered_lessons = (
            [
                lsn
                for lsn in incomplete_lessons
                if lsn.prerequisites_met and lsn.skill_slug in gap_skills
            ]
            + [
                lsn
                for lsn in incomplete_lessons
                if lsn.prerequisites_met
                and track_status.selected_track_slug in lsn.track_slugs
                and lsn.skill_slug not in gap_skills
            ]
            + [
                lsn
                for lsn in incomplete_lessons
                if lsn.prerequisites_met
                and lsn.skill_slug not in gap_skills
                and track_status.selected_track_slug not in lsn.track_slugs
            ]
        )

        added_lessons = 0
        for lsn in ordered_lessons:
            if added_lessons >= 2:
                break
            est = min(max(lsn.estimated_minutes, 10), 25)
            if not can_fit(est):
                continue
            cur_state = skill_state_map.get(lsn.skill_slug, "unobserved")
            is_gap = lsn.skill_slug in gap_skills
            tasks.append(
                {
                    "task_type": "lesson",
                    "skill_slug": lsn.skill_slug,
                    "target_id": str(lsn.lesson_id),
                    "target_slug": lsn.slug,
                    "title_en": f"Lesson: {lsn.title_en}",
                    "title_bn": f"লেসন: {lsn.title_bn}",
                    "reason_en": (
                        f"Targets a diagnostic gap in '{lsn.skill_slug}' (state: {cur_state}) "
                        "with a real Judge0 guided exercise."
                        if is_gap
                        else f"Prerequisite-ready lesson for your {track_status.selected_track_slug.replace('_', ' ')} "
                        f"track (state: {cur_state})."
                    ),
                    "reason_bn": (
                        f"ডায়াগনস্টিকে '{lsn.title_bn}' বিষয়ে ঘাটতি পাওয়া গেছে; Judge0 অনুশীলনসহ সম্পন্ন করো।"
                        if is_gap
                        else f"তোমার নির্বাচিত ট্র্যাকের পূর্বশর্ত-সম্পন্ন পরবর্তী লেসন: {lsn.title_bn}।"
                    ),
                    "href": f"/student/lessons/{lsn.slug}",
                    "estimated_minutes": est,
                }
            )
            used_minutes += est
            added_lessons += 1

        # Priority 4: Unlocked Transfer Challenges or Debugging/Coding Problems from Problem Bank
        problems, _ = await self._problem_repo.list_published_problems(limit=20, offset=0)
        for prob, ver in problems:
            if used_minutes >= available_minutes or len(tasks) >= 5:
                break
            if prob.slug.startswith("transfer-"):
                continue
            accepted = await self._mentor_repo.has_accepted_submit(
                student_id=user.id, problem_id=prob.id
            )
            link_tuple = await self._mentor_repo.get_verification_link_for_source_problem(prob.id)

            if accepted is not None and link_tuple is not None:
                link, _, transfer_ver = link_tuple
                latest_att = await self._mentor_repo.get_latest_verification_attempt(
                    student_id=user.id, verification_link_id=link.id
                )
                if latest_att is None or latest_att.outcome != "verified_independent":
                    est = 20
                    if can_fit(est):
                        tasks.append(
                            {
                                "task_type": "transfer",
                                "skill_slug": "loops"
                                if "loop" in link.skill_focus
                                else "variables",
                                "target_id": str(prob.id),
                                "target_slug": prob.slug,
                                "title_en": f"Transfer Check: {transfer_ver.title}",
                                "title_bn": f"স্বাধীন ট্রান্সফার যাচাই: {transfer_ver.title}",
                                "reason_en": (
                                    f"Unlocked after fixing '{ver.title}'. Solve with 0 AI hints "
                                    "to prove independent transfer on Judge0."
                                ),
                                "reason_bn": (
                                    f"'{ver.title}' সমাধানের পর আনলক হয়েছে। শূন্য হিন্টে Judge0-তে "
                                    "স্বাধীন প্রয়োগ প্রমাণ করো।"
                                ),
                                "href": f"/student/problems/{prob.id}",
                                "estimated_minutes": est,
                            }
                        )
                        used_minutes += est
                    continue

            if accepted is None:
                est = 20 if ver.mode == "debugging" else 15
                if not can_fit(est):
                    continue
                is_debug = ver.mode == "debugging"
                tasks.append(
                    {
                        "task_type": "debugging" if is_debug else "problem",
                        "skill_slug": "debugging_basics" if is_debug else "mixed_problem_solving",
                        "target_id": str(prob.id),
                        "target_slug": prob.slug,
                        "title_en": f"{'Debug' if is_debug else 'Solve'}: {ver.title}",
                        "title_bn": f"{'ডিবাগ অনুশীলন' if is_debug else 'সমস্যা সমাধান'}: {ver.title}",
                        "reason_en": (
                            f"Practice Judge0 debugging with ML diagnosis & Socratic AI Mentor on '{ver.title}'."
                            if is_debug
                            else f"Build independent Judge0 coding evidence on '{ver.title}'."
                        ),
                        "reason_bn": (
                            f"Judge0, ML ডায়াগনোসিস ও Socratic AI Mentor দিয়ে '{ver.title}' ডিবাগ করো।"
                            if is_debug
                            else f"Judge0-তে স্বাধীন কোডিং দক্ষতার প্রমাণ তৈরি করতে '{ver.title}' সমাধান করো।"
                        ),
                        "href": f"/student/problems/{prob.id}",
                        "estimated_minutes": est,
                    }
                )
                used_minutes += est

        # Priority 5: Upcoming retention preview if student still has budget & schedules exist
        upcoming_retentions = [
            s
            for s in retention_overview.schedules
            if not s.is_due_now and s.status != "passed_retained"
        ]
        if upcoming_retentions and can_fit(10) and len(tasks) < 5:
            sched = upcoming_retentions[0]
            tasks.append(
                {
                    "task_type": "retention",
                    "skill_slug": sched.skill_slug,
                    "target_id": str(sched.id),
                    "target_slug": sched.problem_slug,
                    "title_en": f"Upcoming Retention Prep: {sched.skill_title_en}",
                    "title_bn": f"আসন্ন রিটেনশন প্রস্তুতি: {sched.skill_title_bn}",
                    "reason_en": (
                        f"Scheduled for delayed verification in ~{sched.hours_until_eligible:.1f}h "
                        "(retention unlocks only after 24h elapsed)."
                    ),
                    "reason_bn": (
                        f"প্রায় {sched.hours_until_eligible:.1f} ঘণ্টা পর ২৪ ঘণ্টার রিটেনশন যাচাই উন্মুক্ত হবে।"
                    ),
                    "href": "/student/retention",
                    "estimated_minutes": 10,
                }
            )
            used_minutes += 10

        reason_en = (
            f"Tailored for your {track_status.selected_track_slug.replace('_', ' ')} track "
            f"({available_minutes} min budget): {len(due_retentions)} due retention check(s), "
            f"{len(gap_skills)} diagnostic gap skill(s), and prerequisite-ready next steps."
        )
        reason_bn = (
            f"তোমার {track_status.selected_track_slug.replace('_', ' ')} ট্র্যাক এবং {available_minutes} মিনিট "
            f"সময়ের ওপর ভিত্তি করে {len(tasks)}টি প্রমাণ-ভিত্তিক কাজ সাজানো হয়েছে।"
        )
        evidence_snapshot = {
            "selected_track": track_status.selected_track_slug,
            "available_minutes": available_minutes,
            "due_retention_count": len(due_retentions),
            "diagnostic_completed": latest_diag is not None,
            "gap_skills": sorted(gap_skills),
        }
        return (
            track_status.selected_track_slug,
            reason_en,
            reason_bn,
            evidence_snapshot,
            tasks,
        )

    async def get_today_workspace(
        self, user: UserRecord, *, language_slug: str | None = None
    ) -> DailyPlanWorkspaceView:
        lang = resolve_user_language(user, language_slug)
        today = datetime.now(UTC).date()
        active = await self._growth_repo.get_active_daily_plan(
            student_id=user.id, plan_date=today, language_slug=lang
        )
        if active is None:
            default_minutes = (
                user.preferences.daily_practice_minutes
                if user.preferences and user.preferences.daily_practice_minutes
                else 45
            )
            default_minutes = min(max(default_minutes, 15), 240)
            track_slug, reason_en, reason_bn, ev_snap, tasks = await self._build_tasks(
                user=user, available_minutes=default_minutes, language_slug=lang
            )
            active = await self._growth_repo.create_daily_plan(
                student_id=user.id,
                language_slug=lang,
                plan_date=today,
                selected_track_slug=track_slug,
                available_minutes=default_minutes,
                generation_reason_en=reason_en,
                generation_reason_bn=reason_bn,
                evidence_snapshot=ev_snap,
                tasks_payload=tasks,
                reuse_if_active_exists=True,
            )

        history = await self._growth_repo.list_daily_plan_history(
            student_id=user.id, limit=14, language_slug=lang
        )
        return DailyPlanWorkspaceView(
            active_plan=_plan_to_view(active),
            history=[_plan_to_history_item(p) for p in history],
        )

    async def regenerate_today_plan(
        self,
        *,
        user: UserRecord,
        available_minutes: int | None,
        language_slug: str | None = None,
    ) -> DailyPlanWorkspaceView:
        lang = resolve_user_language(user, language_slug)
        today: date = datetime.now(UTC).date()
        budget = available_minutes or (
            user.preferences.daily_practice_minutes
            if user.preferences and user.preferences.daily_practice_minutes
            else 45
        )
        budget = min(max(budget, 15), 240)
        track_slug, reason_en, reason_bn, ev_snap, tasks = await self._build_tasks(
            user=user, available_minutes=budget, language_slug=lang
        )
        active = await self._growth_repo.create_daily_plan(
            student_id=user.id,
            language_slug=lang,
            plan_date=today,
            selected_track_slug=track_slug,
            available_minutes=budget,
            generation_reason_en=reason_en,
            generation_reason_bn=reason_bn,
            evidence_snapshot=ev_snap,
            tasks_payload=tasks,
        )
        history = await self._growth_repo.list_daily_plan_history(
            student_id=user.id, limit=14, language_slug=lang
        )
        return DailyPlanWorkspaceView(
            active_plan=_plan_to_view(active),
            history=[_plan_to_history_item(p) for p in history],
        )

    async def update_task_status(
        self,
        *,
        user: UserRecord,
        task_id: UUID,
        payload: UpdateDailyTaskStatusRequest,
    ) -> DailyLearningPlanView:
        task = await self._growth_repo.get_daily_task_by_id(task_id)
        if task is None:
            raise AppError(
                code="DAILY_TASK_NOT_FOUND",
                message="Daily plan task was not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        if task.student_id != user.id and "admin" not in user.roles:
            raise AppError(
                code="FORBIDDEN",
                message="You cannot modify another student's daily plan task.",
                status_code=status.HTTP_403_FORBIDDEN,
            )
        await self._growth_repo.update_daily_task_status(
            task=task,
            status=payload.status,
            completion_evidence_ref=payload.completion_evidence_ref,
        )
        plan = await self._growth_repo.get_daily_plan_by_id(task.plan_id)
        assert plan is not None
        return _plan_to_view(plan)
