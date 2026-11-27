"""AI Debugging Timeline service — groups persisted debugging events chronologically per problem.

Strictly reads real persisted PostgreSQL records (submissions, ML error diagnoses,
progressive AI hints, Socratic mentor turns, code revisions, transfer verifications)
and never fabricates debugging steps or outcomes.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from app.repositories.growth import GrowthRepository
from app.repositories.identity import UserRecord
from app.schemas.growth import (
    DebuggingJourneyView,
    DebuggingTimelineResponseView,
    DebuggingTimelineStepView,
)


def _trim_code(source_code: str | None, max_chars: int = 240) -> str | None:
    if not source_code:
        return None
    cleaned = source_code.strip()
    if not cleaned:
        return None
    return cleaned if len(cleaned) <= max_chars else cleaned[:max_chars] + "\n..."


class DebuggingTimelineService:
    """Constructs chronological per-problem AI Debugging Timelines from real persisted records."""

    def __init__(self, *, growth_repo: GrowthRepository) -> None:
        self._growth_repo = growth_repo

    async def get_debugging_timeline(
        self,
        *,
        user: UserRecord,
        language_slug: str | None = None,
        problem_id: UUID | None = None,
        limit: int = 12,
        offset: int = 0,
    ) -> DebuggingTimelineResponseView:
        subs = await self._growth_repo.list_student_submissions_all(
            student_id=user.id, limit=150, language_slug=language_slug
        )
        diagnoses = await self._growth_repo.list_student_diagnoses(student_id=user.id, limit=150)
        revs = await self._growth_repo.list_student_revisions(
            student_id=user.id, limit=100, language_slug=language_slug
        )
        hints = await self._growth_repo.list_student_hint_events_with_sessions(
            student_id=user.id, limit=100
        )
        turns = await self._growth_repo.list_student_mentor_turns(student_id=user.id, limit=100)
        verifs = await self._growth_repo.list_student_verification_attempts_all(
            student_id=user.id, limit=60
        )

        # Group submissions per problem_id
        subs_by_problem: dict[UUID, list[tuple[Any, Any, Any]]] = defaultdict(list)
        sub_to_problem: dict[UUID, UUID] = {}
        problem_meta: dict[UUID, tuple[str, str, str]] = {}

        for sub, prob, prob_ver in subs:
            if problem_id is not None and prob.id != problem_id:
                continue
            subs_by_problem[prob.id].append((sub, prob, prob_ver))
            sub_to_problem[sub.id] = prob.id
            if prob.id not in problem_meta:
                problem_meta[prob.id] = (prob.slug, prob_ver.title, sub.language_slug)

        diagnoses_by_problem: dict[UUID, list[Any]] = defaultdict(list)
        for diag in diagnoses:
            pid = sub_to_problem.get(diag.submission_id)
            if pid is not None:
                diagnoses_by_problem[pid].append(diag)

        revs_by_problem: dict[UUID, list[Any]] = defaultdict(list)
        for rev, rev_ver in revs:
            if rev_ver.problem_id in subs_by_problem:
                revs_by_problem[rev_ver.problem_id].append(rev)

        hints_by_problem: dict[UUID, list[Any]] = defaultdict(list)
        for hint, sess in hints:
            if sess.problem_id in subs_by_problem:
                hints_by_problem[sess.problem_id].append(hint)

        turns_by_problem: dict[UUID, list[Any]] = defaultdict(list)
        for turn, sess in turns:
            if sess.problem_id in subs_by_problem:
                turns_by_problem[sess.problem_id].append(turn)

        verifs_by_problem: dict[UUID, list[Any]] = defaultdict(list)
        for att in verifs:
            verif_pid = (
                sub_to_problem.get(att.source_submission_id)
                if att.source_submission_id is not None
                else None
            )
            if verif_pid is None and att.transfer_problem_id in subs_by_problem:
                verif_pid = att.transfer_problem_id
            if verif_pid is not None and verif_pid in subs_by_problem:
                verifs_by_problem[verif_pid].append(att)

        journeys: list[DebuggingJourneyView] = []
        for pid, sub_rows in subs_by_problem.items():
            slug, title, lang_slug = problem_meta[pid]
            ordered_subs = sorted(sub_rows, key=lambda row: row[0].created_at)
            first_sub, _, first_ver = ordered_subs[0]
            steps: list[DebuggingTimelineStepView] = []

            # 1. Original coding problem anchor
            starter_code = getattr(first_ver, "starter_code", None)
            steps.append(
                DebuggingTimelineStepView(
                    id=f"start:{pid}",
                    step_kind="problem_started",
                    title=f"Problem started: {title}",
                    detail=(
                        f"Language: {lang_slug} · Tracked across {len(ordered_subs)} "
                        "sandbox execution attempt(s)."
                    ),
                    code_excerpt=_trim_code(starter_code, max_chars=180),
                    verdict_or_status="started",
                    metadata={"problem_slug": slug, "language_slug": lang_slug},
                    occurred_at=first_sub.created_at,
                )
            )

            # 2. Submissions: initial attempt, corrections, and first accepted execution
            first_accepted_seen = False
            for idx, (sub, _, _) in enumerate(ordered_subs):
                verdict = str(sub.verdict)
                passed = int(sub.passed_tests)
                total = int(sub.total_tests)
                ev = sub.execution_evidence if isinstance(sub.execution_evidence, dict) else {}
                err_excerpt = str(ev.get("compile_output") or ev.get("stderr") or "").strip()[:180]
                detail = (
                    f"{sub.submission_kind.title()} verdict: {verdict} "
                    f"({passed}/{total} tests passed)"
                )
                if err_excerpt:
                    detail += f" · Error: {err_excerpt}"

                if idx == 0:
                    kind: Literal[
                        "initial_attempt", "student_correction", "successful_execution"
                    ] = "successful_execution" if verdict == "accepted" else "initial_attempt"
                    step_title = (
                        "Initial attempt passed all tests"
                        if verdict == "accepted"
                        else f"Initial attempt ({verdict.replace('_', ' ')})"
                    )
                    if verdict == "accepted":
                        first_accepted_seen = True
                elif verdict == "accepted" and not first_accepted_seen:
                    kind = "successful_execution"
                    step_title = f"Successful execution on attempt #{idx + 1}"
                    first_accepted_seen = True
                else:
                    kind = "student_correction"
                    step_title = f"Code correction attempt #{idx + 1} ({verdict.replace('_', ' ')})"

                steps.append(
                    DebuggingTimelineStepView(
                        id=f"sub:{sub.id}",
                        step_kind=kind,
                        title=step_title,
                        detail=detail,
                        code_excerpt=_trim_code(sub.source_code),
                        verdict_or_status=verdict,
                        metadata={
                            "passed_tests": passed,
                            "total_tests": total,
                            "runtime_ms": sub.runtime_ms,
                            "provider": getattr(sub, "execution_provider", "judge0"),
                        },
                        occurred_at=sub.created_at,
                    )
                )

            # 3. ML / Rule-Based Error Diagnoses
            diag_list = diagnoses_by_problem.get(pid, [])
            for diag in diag_list:
                conf_pct = round(float(diag.confidence) * 100.0, 1)
                low_note = " (low confidence)" if diag.is_low_confidence else ""
                steps.append(
                    DebuggingTimelineStepView(
                        id=f"diag:{diag.id}",
                        step_kind="error_diagnosed",
                        title=f"Error diagnosed: {diag.predicted_error_code.replace('_', ' ')}",
                        detail=(
                            f"Model {diag.model_version_tag} predicted "
                            f"{diag.predicted_error_code} at {conf_pct}% confidence{low_note}."
                        ),
                        verdict_or_status=diag.predicted_error_code,
                        metadata={
                            "confidence": round(float(diag.confidence), 4),
                            "is_low_confidence": bool(diag.is_low_confidence),
                            "model_version": diag.model_version_tag,
                        },
                        occurred_at=diag.created_at,
                    )
                )

            # 4. Progressive AI Hints & Socratic Mentor guidance
            hint_list = hints_by_problem.get(pid, [])
            for hint in hint_list:
                steps.append(
                    DebuggingTimelineStepView(
                        id=f"hint:{hint.id}",
                        step_kind="ai_hint",
                        title=f"Progressive AI hint (Level {hint.hint_level})",
                        detail=str(hint.hint_text).strip()[:240],
                        verdict_or_status=f"level_{hint.hint_level}",
                        metadata={"hint_level": int(hint.hint_level)},
                        occurred_at=hint.created_at,
                    )
                )
            if not hint_list:
                for turn in turns_by_problem.get(pid, [])[:3]:
                    steps.append(
                        DebuggingTimelineStepView(
                            id=f"turn:{turn.id}",
                            step_kind="ai_hint",
                            title=f"Socratic mentor guidance ({turn.provider_mode})",
                            detail=str(turn.message_text).replace("\n", " ").strip()[:240],
                            verdict_or_status=str(turn.state_after),
                            metadata={"provider_mode": str(turn.provider_mode)},
                            occurred_at=turn.created_at,
                        )
                    )

            # 5. Saved Code Revisions with reasoning notes
            for rev in revs_by_problem.get(pid, []):
                if (rev.prediction_text or "").strip() or (rev.explanation_text or "").strip():
                    note = (rev.explanation_text or rev.prediction_text or "").strip()[:200]
                    steps.append(
                        DebuggingTimelineStepView(
                            id=f"rev:{rev.id}",
                            step_kind="student_correction",
                            title=f"Reasoning note saved ({rev.revision_type})",
                            detail=note,
                            code_excerpt=_trim_code(rev.source_code, max_chars=180),
                            verdict_or_status=str(rev.revision_type),
                            occurred_at=rev.created_at,
                        )
                    )

            # 6. Independent Transfer Verification & Outcome
            verif_list = verifs_by_problem.get(pid, [])
            transfer_passed = any(str(v.outcome) == "verified_independent" for v in verif_list)
            for att in verif_list:
                steps.append(
                    DebuggingTimelineStepView(
                        id=f"verif:{att.id}",
                        step_kind="learning_outcome",
                        title="Independent transfer verification",
                        detail=(
                            f"Outcome: {att.outcome} · Verdict: {att.verdict} "
                            f"({att.passed_tests}/{att.total_tests} tests, {att.hints_used} hints)."
                        ),
                        verdict_or_status=str(att.outcome),
                        metadata={"hints_used": int(att.hints_used)},
                        occurred_at=att.created_at,
                    )
                )

            outcome_status: Literal["verified_transfer", "solved", "in_progress"]
            if transfer_passed:
                outcome_status = "verified_transfer"
            elif first_accepted_seen:
                outcome_status = "solved"
            else:
                outcome_status = "in_progress"

            # Sort steps chronologically within each problem journey
            steps.sort(key=lambda s: s.occurred_at)
            started_at: datetime = steps[0].occurred_at
            latest_at: datetime = steps[-1].occurred_at

            journeys.append(
                DebuggingJourneyView(
                    problem_id=pid,
                    problem_slug=slug,
                    problem_title=title,
                    language_slug=lang_slug,
                    href=f"/student/problems/{pid}",
                    outcome_status=outcome_status,
                    attempts_count=len(ordered_subs),
                    hints_used=len(hint_list),
                    diagnoses_count=len(diag_list),
                    started_at=started_at,
                    latest_event_at=latest_at,
                    steps=steps,
                )
            )

        # Most recently active debugging journey first
        journeys.sort(key=lambda j: j.latest_event_at, reverse=True)
        solved_count = sum(
            1 for j in journeys if j.outcome_status in ("solved", "verified_transfer")
        )
        page = journeys[offset : offset + limit]
        return DebuggingTimelineResponseView(
            journeys=page,
            total_journeys=len(journeys),
            solved_journeys=solved_count,
            limit=limit,
            offset=offset,
        )
