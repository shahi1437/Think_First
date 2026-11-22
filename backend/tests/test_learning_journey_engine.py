"""Unit tests for the Central Learning Journey Engine, Onboarding Entry Redirects,
and Short Readiness Check vs Full 8-Domain Adaptive Diagnostic placement.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest

from app.repositories.identity import PreferencesRecord, UserRecord
from app.schemas.learning import (
    DiagnosticDomainEvidence,
    DiagnosticSessionView,
    LessonSummaryView,
)
from app.services.identity.service import _format_preferences
from app.services.learning.journey_engine import (
    DueRetentionCandidate,
    JourneyDecisionInput,
    LearningJourneyService,
    PracticeProblemCandidate,
    TransferCandidate,
    UrgentAssignmentCandidate,
    build_post_lesson_next_action,
    decide_learning_journey,
)


def _make_lesson(
    slug: str,
    *,
    order: int = 1,
    skill: str = "variables",
    status: str = "not_started",
    reading: bool = False,
    prereqs_met: bool = True,
    lang: str = "python",
) -> LessonSummaryView:
    return LessonSummaryView(
        lesson_id=uuid4(),
        version_id=uuid4(),
        slug=slug,
        language_slug=lang,
        skill_slug=skill,
        display_order=order,
        title_en=f"Lesson {order}: {slug}",
        title_bn=f"লেসন {order}: {slug}",
        summary_en="Summary",
        summary_bn="সারাংশ",
        prerequisite_lesson_slugs=[],
        track_slugs=["absolute_beginner", "basic_university"],
        estimated_minutes=12,
        progress_status=status,  # type: ignore[arg-type]
        reading_completed=reading,
        exercise_passed=status == "completed",
        exercise_attempts=1 if status != "not_started" else 0,
        prerequisites_met=prereqs_met,
    )


def _make_diag(
    *,
    status: str = "completed",
    mode: str = "full",
    lang: str = "python",
    gap_domain: str | None = None,
) -> DiagnosticSessionView:
    ev: list[DiagnosticDomainEvidence] = []
    if gap_domain is not None:
        ev.append(
            DiagnosticDomainEvidence(
                domain_slug=gap_domain,  # type: ignore[arg-type]
                observed_attempts=1,
                observed_correct=0,
                execution_verified=False,
                evidence_status="gap_detected",
                note_en="Gap",
                note_bn="ঘাটতি",
            )
        )
    return DiagnosticSessionView(
        id=uuid4(),
        language_slug=lang,
        assessment_mode=mode,  # type: ignore[arg-type]
        status=status,  # type: ignore[arg-type]
        explanation_language="en",
        answered_count=2 if status == "in_progress" else 8,
        remaining_count=2 if status == "in_progress" else 0,
        adaptive_followups_added=0,
        domain_evidence=ev,
        started_at=datetime.now(UTC),
    )


def test_onboarding_incomplete_returns_priority_zero() -> None:
    result = decide_learning_journey(
        JourneyDecisionInput(
            language_slug="python",
            onboarding_completed=False,
            programming_experience="none",
            starting_preference="guided_beginner",
            active_track_slug="absolute_beginner",
        )
    )
    assert result.journey_stage == "onboarding"
    assert result.primary_action.action_type == "onboarding"
    assert result.primary_action.href == "/student/onboarding"
    assert result.primary_action.priority == 0


def test_absolute_beginner_starts_with_foundation_lessons_before_readiness_check() -> None:
    lessons = [
        _make_lesson("intro-to-programming", order=1, skill="programming_basics"),
        _make_lesson("variables-types", order=2, skill="variables"),
        _make_lesson("conditions-if", order=3, skill="conditions"),
    ]
    # 0 lessons completed -> Foundation Lesson 1 (NOT overwhelmed with 8-domain diagnostic!)
    step0 = decide_learning_journey(
        JourneyDecisionInput(
            language_slug="python",
            onboarding_completed=True,
            programming_experience="none",
            starting_preference="guided_beginner",
            active_track_slug="absolute_beginner",
            lessons=lessons,
        )
    )
    assert step0.journey_stage == "foundation_lessons"
    assert step0.readiness_check_unlocked is False
    assert step0.primary_action.action_type == "lesson"
    assert step0.primary_action.href == "/student/lessons/intro-to-programming"

    # 2 foundation lessons completed -> Short Readiness Check unlocked!
    lessons[0].progress_status = "completed"
    lessons[1].progress_status = "completed"
    step2 = decide_learning_journey(
        JourneyDecisionInput(
            language_slug="python",
            onboarding_completed=True,
            programming_experience="none",
            starting_preference="guided_beginner",
            active_track_slug="absolute_beginner",
            lessons=lessons,
        )
    )
    assert step2.journey_stage == "readiness_check"
    assert step2.readiness_check_unlocked is True
    assert step2.primary_action.action_type == "diagnostic_readiness"
    assert step2.primary_action.href == "/student/diagnostic?mode=readiness"


def test_experienced_student_prioritizes_full_adaptive_diagnostic() -> None:
    result = decide_learning_journey(
        JourneyDecisionInput(
            language_slug="javascript",
            onboarding_completed=True,
            programming_experience="intermediate",
            starting_preference="diagnostic_assessment",
            active_track_slug="intermediate",
            lessons=[_make_lesson("js-01-hello-output", order=1, lang="javascript")],
        )
    )
    assert result.journey_stage == "diagnostic_placement"
    assert result.primary_action.action_type == "diagnostic_full"
    assert result.primary_action.href == "/student/diagnostic?mode=full"


def test_urgent_teacher_assignment_takes_top_priority_over_self_paced_tasks() -> None:
    now = datetime.now(UTC)
    result = decide_learning_journey(
        JourneyDecisionInput(
            language_slug="python",
            onboarding_completed=True,
            programming_experience="none",
            starting_preference="guided_beginner",
            active_track_slug="absolute_beginner",
            lessons=[_make_lesson("intro", order=1, status="in_progress", reading=True)],
            urgent_assignments=[
                UrgentAssignmentCandidate(
                    assignment_id="asg-123",
                    course_code="CSE-101",
                    title="Loops Homework",
                    workflow_status="not_started",
                    due_at=now + timedelta(hours=18),
                    is_overdue=False,
                    allow_late=False,
                )
            ],
            due_retentions=[
                DueRetentionCandidate(
                    schedule_id="ret-1",
                    skill_slug="variables",
                    problem_slug="sum-of-even-numbers",
                    interval_hours=24,
                )
            ],
            now=now,
        )
    )
    assert result.primary_action.action_type == "assignment"
    assert result.primary_action.href == "/student/assignments/asg-123"
    assert result.primary_action.urgency == "urgent"
    assert result.resume_activity is not None
    assert result.resume_activity.action_type == "lesson_resume"


def test_unfinished_activity_and_due_retention_priority_order() -> None:
    # In-progress diagnostic -> Priority 2 beats due retention (Priority 3)
    res_diag = decide_learning_journey(
        JourneyDecisionInput(
            language_slug="c",
            onboarding_completed=True,
            programming_experience="basic",
            starting_preference="diagnostic_assessment",
            active_track_slug="basic_university",
            diag_sessions=[_make_diag(status="in_progress", mode="readiness", lang="c")],
            due_retentions=[
                DueRetentionCandidate(
                    schedule_id="ret-1",
                    skill_slug="loops",
                    problem_slug="sum",
                    interval_hours=24,
                )
            ],
        )
    )
    assert res_diag.primary_action.action_type == "diagnostic_resume"
    assert res_diag.primary_action.href == "/student/diagnostic?mode=readiness"

    # No unfinished activity -> Due retention wins (Priority 3)
    res_ret = decide_learning_journey(
        JourneyDecisionInput(
            language_slug="c",
            onboarding_completed=True,
            programming_experience="basic",
            starting_preference="diagnostic_assessment",
            active_track_slug="basic_university",
            diag_sessions=[_make_diag(status="completed", mode="full", lang="c")],
            due_retentions=[
                DueRetentionCandidate(
                    schedule_id="ret-1",
                    skill_slug="loops",
                    problem_slug="sum",
                    interval_hours=24,
                )
            ],
        )
    )
    assert res_ret.primary_action.action_type == "retention_check"
    assert res_ret.primary_action.href == "/student/retention"


def test_diagnostic_gap_remediation_transfer_and_zero_dead_end_fallback() -> None:
    # Gap remediation (Priority 5)
    lessons = [
        _make_lesson("intro", order=1, skill="programming_basics", status="completed"),
        _make_lesson("loops-basics", order=2, skill="loops", status="not_started"),
    ]
    res_gap = decide_learning_journey(
        JourneyDecisionInput(
            language_slug="python",
            onboarding_completed=True,
            programming_experience="basic",
            starting_preference="diagnostic_assessment",
            active_track_slug="basic_university",
            lessons=lessons,
            diag_sessions=[_make_diag(status="completed", gap_domain="loop_boundaries")],
        )
    )
    assert res_gap.primary_action.action_type == "lesson_remediation"
    assert res_gap.primary_action.href == "/student/lessons/loops-basics"

    # All lessons done + unlocked transfer -> Priority 7 beats generic practice (Priority 8)
    lessons[1].progress_status = "completed"
    res_tr = decide_learning_journey(
        JourneyDecisionInput(
            language_slug="python",
            onboarding_completed=True,
            programming_experience="basic",
            starting_preference="diagnostic_assessment",
            active_track_slug="intermediate",
            lessons=lessons,
            diag_sessions=[_make_diag(status="completed")],
            unlocked_transfers=[
                TransferCandidate(
                    source_problem_id="prob-1",
                    source_problem_slug="debug-range-sum",
                    source_problem_title="Debug Range Sum",
                    transfer_problem_title="Step Range Sum",
                    skill_focus="loops",
                )
            ],
            unsolved_problems=[
                PracticeProblemCandidate(
                    problem_id="prob-2",
                    slug="sum-evens",
                    title="Sum Evens",
                    mode="coding",
                    difficulty="easy",
                )
            ],
        )
    )
    assert res_tr.primary_action.action_type == "transfer_verification"
    assert res_tr.primary_action.href == "/student/problems/prob-1?tab=verify"

    # Everything complete -> never dead-end!
    res_done = decide_learning_journey(
        JourneyDecisionInput(
            language_slug="python",
            onboarding_completed=True,
            programming_experience="advanced",
            starting_preference="diagnostic_assessment",
            active_track_slug="advanced",
            lessons=lessons,
            diag_sessions=[_make_diag(status="completed", mode="full")],
        )
    )
    assert res_done.primary_action.action_type == "milestone_complete"
    assert res_done.primary_action.href.startswith("/student/")


def test_onboarding_entry_redirect_path_and_post_lesson_next_action() -> None:
    uid = uuid4()
    exp_pref = PreferencesRecord(
        user_id=uid,
        programming_experience="intermediate",
        preferred_language="cpp",
        active_language_slug="cpp",
        learning_goal="interview_prep",
        daily_practice_minutes=45,
        preferred_explanation_language="en",
        starting_preference="diagnostic_assessment",
        recommended_entry_track="diagnostic_assessment",
    )
    formatted_exp = _format_preferences(exp_pref)
    assert formatted_exp is not None
    assert formatted_exp.entry_redirect_path == "/student/diagnostic?mode=full&entry=onboarding"

    beg_pref = PreferencesRecord(
        user_id=uid,
        programming_experience="none",
        preferred_language="python",
        active_language_slug="python",
        learning_goal="school_fundamentals",
        daily_practice_minutes=30,
        preferred_explanation_language="bn",
        starting_preference="guided_beginner",
        recommended_entry_track="foundation_lessons",
    )
    formatted_beg = _format_preferences(beg_pref)
    assert formatted_beg is not None
    assert formatted_beg.entry_redirect_path == "/student"

    user_beg = UserRecord(
        id=uid,
        email="beg@thinkfirst.test",
        full_name="Beginner",
        avatar_url=None,
        roles=["student"],
        onboarding_completed=True,
        onboarding_completed_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
        preferences=beg_pref,
    )
    lsns = [
        _make_lesson("l1", order=1, status="completed"),
        _make_lesson("l2", order=2, status="not_started"),
    ]
    next_after_1 = build_post_lesson_next_action(
        lessons=lsns,
        current_lesson_slug="l1",
        language_slug="python",
        user=user_beg,
        has_completed_diagnostic=False,
    )
    assert next_after_1.action_type == "lesson"
    assert next_after_1.href == "/student/lessons/l2"

    lsns[1].progress_status = "completed"
    next_after_2 = build_post_lesson_next_action(
        lessons=lsns,
        current_lesson_slug="l2",
        language_slug="python",
        user=user_beg,
        has_completed_diagnostic=False,
    )
    assert next_after_2.action_type == "diagnostic_readiness"
    assert next_after_2.href == "/student/diagnostic?mode=readiness"


@pytest.mark.asyncio
async def test_load_due_retentions_excludes_passed_retained_schedules() -> None:
    """Regression test: schedules already marked `passed_retained` must never re-surface as due."""
    now = datetime.now(UTC)
    past_due = now - timedelta(hours=30)
    future_due = now + timedelta(hours=12)

    class _FakeGrowthRepo:
        async def list_retention_schedules(
            self, student_id: Any, *, language_slug: str
        ) -> list[Any]:
            return [
                SimpleNamespace(
                    id=uuid4(),
                    skill_slug="variables",
                    problem_id=uuid4(),
                    interval_hours=24,
                    status="passed_retained",
                    due_at=past_due,
                ),
                SimpleNamespace(
                    id=uuid4(),
                    skill_slug="loops",
                    problem_id=uuid4(),
                    interval_hours=24,
                    status="due",
                    due_at=past_due,
                ),
                SimpleNamespace(
                    id=uuid4(),
                    skill_slug="conditions",
                    problem_id=uuid4(),
                    interval_hours=24,
                    status="scheduled",
                    due_at=future_due,
                ),
            ]

    svc = LearningJourneyService(
        learning_repo=SimpleNamespace(),  # type: ignore[arg-type]
        problem_repo=SimpleNamespace(),  # type: ignore[arg-type]
        mentor_repo=SimpleNamespace(),  # type: ignore[arg-type]
        growth_repo=_FakeGrowthRepo(),  # type: ignore[arg-type]
        classroom_repo=SimpleNamespace(),  # type: ignore[arg-type]
        lessons_service=SimpleNamespace(),  # type: ignore[arg-type]
        diagnostics_service=SimpleNamespace(),  # type: ignore[arg-type]
        skill_graph_service=SimpleNamespace(),  # type: ignore[arg-type]
    )
    due = await svc._load_due_retentions(uuid4(), "python", now)
    assert len(due) == 1
    assert due[0].skill_slug == "loops"
