"""Persistent, searchable Student Learning History timeline service.

Aggregates real persisted database events across Phases 3-6:
- Beginner lessons & Judge0 guided exercises
- 8-Domain adaptive diagnostic assessments
- Judge0 coding/debugging submissions & verdicts
- Code revisions (with output predictions & bug explanations)
- Socratic AI Mentor turns (including live_llm vs deterministic_fallback)
- Progressive AI hint events
- Phase 4 independent transfer verification attempts
- Skill Graph state transitions
- Completed Adaptive Daily Plan tasks
- Phase 6 spaced retention verification attempts
"""

from __future__ import annotations

from app.repositories.growth import GrowthRepository
from app.repositories.identity import UserRecord
from app.schemas.growth import (
    HistoryCategory,
    LearningHistoryItemView,
    LearningHistoryResponseView,
)


class LearningHistoryService:
    """Builds a searchable, category-filterable longitudinal timeline from real DB tables."""

    def __init__(self, *, growth_repo: GrowthRepository) -> None:
        self._growth_repo = growth_repo

    async def get_timeline(
        self,
        *,
        user: UserRecord,
        q: str | None = None,
        category: HistoryCategory | None = None,
        language_slug: str | None = None,
        limit: int = 40,
        offset: int = 0,
    ) -> LearningHistoryResponseView:
        events: list[LearningHistoryItemView] = []

        # 1. Lessons
        lesson_rows = await self._growth_repo.list_student_lesson_progress_with_meta(
            student_id=user.id, language_slug=language_slug
        )
        for prog, lsn, ver in lesson_rows:
            ts = prog.completed_at or prog.updated_at
            events.append(
                LearningHistoryItemView(
                    id=f"lesson:{prog.id}",
                    category="lesson",
                    title_en=f"Lesson: {ver.title_en}",
                    title_bn=f"লেসন: {ver.title_bn}",
                    summary_en=(
                        f"Status: {prog.status} · Reading: {'done' if prog.reading_completed else 'pending'} "
                        f"· Judge0 Exercise: {'passed' if prog.exercise_passed else 'not passed'} "
                        f"({prog.exercise_attempts} run(s))"
                    ),
                    summary_bn=(
                        f"অবস্থা: {prog.status} · পড়া: {'সম্পন্ন' if prog.reading_completed else 'বাকি'} "
                        f"· Judge0 অনুশীলন: {'পাস' if prog.exercise_passed else 'বাকি'} "
                        f"({prog.exercise_attempts} বার চেষ্টা)"
                    ),
                    verdict_or_status=prog.status,
                    skill_slug=lsn.skill_slug,
                    href=f"/student/lessons/{lsn.slug}",
                    metadata={
                        "lesson_slug": lsn.slug,
                        "exercise_passed": prog.exercise_passed,
                        "attempts": prog.exercise_attempts,
                    },
                    occurred_at=ts,
                )
            )

        # 2. Diagnostic Assessments
        diag_sessions = await self._growth_repo.list_student_diagnostic_sessions(
            student_id=user.id, limit=25, language_slug=language_slug
        )
        for ds in diag_sessions:
            ts = ds.completed_at or ds.started_at
            rec_track = (ds.recommended_track_slug or "pending").replace("_", " ")
            events.append(
                LearningHistoryItemView(
                    id=f"diagnostic:{ds.id}",
                    category="diagnostic",
                    title_en="8-Domain Adaptive Diagnostic Assessment",
                    title_bn="৮-ডোমেইন অ্যাডাপ্টিভ ডায়াগনস্টিক অ্যাসেসমেন্ট",
                    summary_en=(
                        f"Status: {ds.status} · Recommended Track: {rec_track} "
                        f"· Adaptive follow-ups: {ds.adaptive_followups_added}"
                    ),
                    summary_bn=(
                        f"অবস্থা: {ds.status} · প্রস্তাবিত ট্র্যাক: {rec_track} "
                        f"· অ্যাডাপ্টিভ ফলো-আপ: {ds.adaptive_followups_added}টি"
                    ),
                    verdict_or_status=ds.status,
                    skill_slug=None,
                    href="/student/diagnostic",
                    metadata={
                        "recommended_track_slug": ds.recommended_track_slug,
                        "adaptive_followups_added": ds.adaptive_followups_added,
                    },
                    occurred_at=ts,
                )
            )

        # 3. Sandbox Submissions (Judge0 / Piston)
        subs = await self._growth_repo.list_student_submissions_all(
            student_id=user.id, limit=80, language_slug=language_slug
        )
        for sub, prob, prob_ver in subs:
            events.append(
                LearningHistoryItemView(
                    id=f"submission:{sub.id}",
                    category="submission",
                    title_en=f"Judge0 {sub.submission_kind.title()}: {prob_ver.title}",
                    title_bn=f"Judge0 {sub.submission_kind}: {prob_ver.title}",
                    summary_en=(
                        f"Verdict: {sub.verdict} ({sub.passed_tests}/{sub.total_tests} tests passed) "
                        f"· Language: {sub.language_slug}"
                    ),
                    summary_bn=(
                        f"ফলাফল: {sub.verdict} ({sub.passed_tests}/{sub.total_tests} টেস্ট পাস) "
                        f"· ভাষা: {sub.language_slug}"
                    ),
                    verdict_or_status=sub.verdict,
                    skill_slug=prob_ver.skills[0] if prob_ver.skills else None,
                    href=f"/student/problems/{prob.id}",
                    metadata={
                        "problem_slug": prob.slug,
                        "submission_kind": sub.submission_kind,
                        "passed_tests": sub.passed_tests,
                        "total_tests": sub.total_tests,
                    },
                    occurred_at=sub.created_at,
                )
            )

        # 4. Code Revisions
        revs = await self._growth_repo.list_student_revisions(
            student_id=user.id, limit=50, language_slug=language_slug
        )
        for rev, rev_ver in revs:
            notes_parts: list[str] = []
            if (rev.prediction_text or "").strip():
                notes_parts.append("prediction saved")
            if (rev.explanation_text or "").strip():
                notes_parts.append("bug explanation saved")
            notes_str = ", ".join(notes_parts) if notes_parts else "code snapshot"
            events.append(
                LearningHistoryItemView(
                    id=f"revision:{rev.id}",
                    category="revision",
                    title_en=f"Code Revision ({rev.revision_type}): {rev_ver.title}",
                    title_bn=f"কোড রিভিশন ({rev.revision_type}): {rev_ver.title}",
                    summary_en=f"Saved {len(rev.source_code)} chars in {rev.language_slug} ({notes_str}).",
                    summary_bn=f"{rev.language_slug}-এ {len(rev.source_code)} অক্ষরের কোড সংরক্ষিত ({notes_str})।",
                    verdict_or_status=rev.revision_type,
                    skill_slug=rev_ver.skills[0] if rev_ver.skills else None,
                    href=f"/student/problems/{rev_ver.problem_id}",
                    metadata={"revision_type": rev.revision_type},
                    occurred_at=rev.created_at,
                )
            )

        # 5. Socratic AI Mentor Turns
        turns = await self._growth_repo.list_student_mentor_turns(student_id=user.id, limit=60)
        for turn, sess in turns:
            preview = turn.message_text.replace("\n", " ")[:150]
            mode_label = (
                "Live Gemini LLM" if turn.provider_mode == "live_llm" else "Socratic Fallback"
            )
            events.append(
                LearningHistoryItemView(
                    id=f"mentor:{turn.id}",
                    category="mentor",
                    title_en=f"Socratic AI Mentor ({mode_label})",
                    title_bn=f"Socratic AI Mentor ({mode_label})",
                    summary_en=f"[{turn.state_after}] {preview}",
                    summary_bn=f"[{turn.state_after}] {preview}",
                    verdict_or_status=turn.provider_mode,
                    skill_slug=None,
                    href=f"/student/problems/{sess.problem_id}",
                    metadata={
                        "provider_mode": turn.provider_mode,
                        "state_after": turn.state_after,
                        "language": sess.explanation_language,
                    },
                    occurred_at=turn.created_at,
                )
            )

        # 6. Progressive Hints
        hints = await self._growth_repo.list_student_hint_events(student_id=user.id, limit=60)
        for h in hints:
            events.append(
                LearningHistoryItemView(
                    id=f"hint:{h.id}",
                    category="hint",
                    title_en=f"Progressive AI Hint (Level {h.hint_level})",
                    title_bn=f"ধাপে ধাপে AI হিন্ট (লেভেল {h.hint_level})",
                    summary_en=h.hint_text[:160],
                    summary_bn=h.hint_text[:160],
                    verdict_or_status=f"level_{h.hint_level}",
                    skill_slug=None,
                    href=None,
                    metadata={"hint_level": h.hint_level},
                    occurred_at=h.created_at,
                )
            )

        # 7. Independent Transfer Verification
        verifs = await self._growth_repo.list_student_verification_attempts_all(
            student_id=user.id, limit=40
        )
        for att in verifs:
            events.append(
                LearningHistoryItemView(
                    id=f"transfer:{att.id}",
                    category="transfer",
                    title_en="Independent Transfer Verification",
                    title_bn="স্বাধীন ট্রান্সফার যাচাই",
                    summary_en=(
                        f"Outcome: {att.outcome} · Judge0: {att.verdict} "
                        f"({att.passed_tests}/{att.total_tests}) · Hints used: {att.hints_used}"
                    ),
                    summary_bn=(
                        f"ফলাফল: {att.outcome} · Judge0: {att.verdict} "
                        f"({att.passed_tests}/{att.total_tests}) · হিন্ট: {att.hints_used}"
                    ),
                    verdict_or_status=att.outcome,
                    skill_slug=None,
                    href=f"/student/problems/{att.transfer_problem_id}",
                    metadata={
                        "outcome": att.outcome,
                        "hints_used": att.hints_used,
                        "passed_tests": att.passed_tests,
                        "total_tests": att.total_tests,
                    },
                    occurred_at=att.created_at,
                )
            )

        # 8. Skill Graph Transitions
        transitions = await self._growth_repo.list_student_skill_transitions_all(
            student_id=user.id, limit=60, language_slug=language_slug
        )
        for tr in transitions:
            events.append(
                LearningHistoryItemView(
                    id=f"skill:{tr.id}",
                    category="skill",
                    title_en=f"Skill Graph: {tr.skill_slug} ({tr.from_state} -> {tr.to_state})",
                    title_bn=f"Skill Graph: {tr.skill_slug} ({tr.from_state} -> {tr.to_state})",
                    summary_en=tr.reason,
                    summary_bn=tr.reason,
                    verdict_or_status=tr.to_state,
                    skill_slug=tr.skill_slug,
                    href="/student",
                    metadata={
                        "from_state": tr.from_state,
                        "to_state": tr.to_state,
                        "evidence_source": tr.evidence_source,
                    },
                    occurred_at=tr.created_at,
                )
            )

        # 9. Completed Daily Plan Tasks
        completed_tasks = await self._growth_repo.list_student_completed_daily_tasks(
            student_id=user.id, limit=50
        )
        for t in completed_tasks:
            events.append(
                LearningHistoryItemView(
                    id=f"daily_plan:{t.id}",
                    category="daily_plan",
                    title_en=f"Daily Plan Completed: {t.title_en}",
                    title_bn=f"দৈনিক পরিকল্পনা সম্পন্ন: {t.title_bn}",
                    summary_en=t.reason_en,
                    summary_bn=t.reason_bn,
                    verdict_or_status="completed",
                    skill_slug=t.skill_slug,
                    href=t.href,
                    metadata={"task_type": t.task_type, "estimated_minutes": t.estimated_minutes},
                    occurred_at=t.completed_at or t.updated_at,
                )
            )

        # 10. Retention Attempts
        ret_attempts = await self._growth_repo.list_retention_attempts(
            student_id=user.id, limit=40, language_slug=language_slug
        )
        for ra in ret_attempts:
            events.append(
                LearningHistoryItemView(
                    id=f"retention:{ra.id}",
                    category="retention",
                    title_en=f"Retention Check ({ra.skill_slug}): {ra.outcome}",
                    title_bn=f"রিটেনশন যাচাই ({ra.skill_slug}): {ra.outcome}",
                    summary_en=ra.summary_message,
                    summary_bn=ra.summary_message,
                    verdict_or_status=ra.outcome,
                    skill_slug=ra.skill_slug,
                    href="/student/retention",
                    metadata={
                        "verdict": ra.verdict,
                        "elapsed_hours": ra.elapsed_hours_since_initial,
                        "passed_tests": ra.passed_tests,
                        "total_tests": ra.total_tests,
                    },
                    occurred_at=ra.created_at,
                )
            )

        # Compute category counts before filtering by category
        category_counts: dict[str, int] = {}
        for ev in events:
            category_counts[ev.category] = category_counts.get(ev.category, 0) + 1

        # Apply search & category filters
        filtered = events
        if category is not None:
            filtered = [ev for ev in filtered if ev.category == category]
        if q and q.strip():
            needle = q.strip().lower()
            filtered = [
                ev
                for ev in filtered
                if needle in ev.title_en.lower()
                or needle in ev.title_bn.lower()
                or needle in ev.summary_en.lower()
                or needle in ev.summary_bn.lower()
                or (ev.skill_slug and needle in ev.skill_slug.lower())
                or (ev.verdict_or_status and needle in ev.verdict_or_status.lower())
            ]

        filtered.sort(key=lambda item: item.occurred_at, reverse=True)
        total = len(filtered)
        page = filtered[offset : offset + limit]

        return LearningHistoryResponseView(
            items=page,
            total=total,
            limit=limit,
            offset=offset,
            category_counts=category_counts,
        )
