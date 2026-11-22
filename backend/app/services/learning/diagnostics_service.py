"""Adaptive 8-domain Diagnostic Assessment service with real Judge0 execution checks.

Never fabricates marks, IQ/ability scores, or mastery percentages:
- Tracks exact observed attempts, observed correct counts, and real Judge0 execution outcomes per domain.
- Adaptively queues `foundation` follow-ups when a student misses a `core` probe.
- Adaptively queues `stretch` Judge0 code-execution checks when a student passes key `core` probes.
- Deterministically recommends one of the 4 learning tracks from observed evidence alone.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import status

from app.core.errors import AppError
from app.integrations.judge0.client import Judge0Client
from app.models.learning import DiagnosticQuestion, DiagnosticSession
from app.repositories.identity import UserRecord
from app.repositories.learning import LearningRepository
from app.repositories.mentor import MentorRepository
from app.repositories.problems import ProblemRepository
from app.schemas.learning import (
    AdminDiagnosticQuestionCreateRequest,
    AssessmentMode,
    DiagnosticAnswerSubmitRequest,
    DiagnosticDomain,
    DiagnosticDomainEvidence,
    DiagnosticOptionView,
    DiagnosticQuestionPublicView,
    DiagnosticResponseFeedback,
    DiagnosticSessionView,
    JourneyActionView,
    TrackSlug,
)
from app.services.learning.lessons_service import resolve_user_language
from app.services.learning.skill_graph import SkillGraphService

ALL_EIGHT_DOMAINS: tuple[DiagnosticDomain, ...] = (
    "variables",
    "syntax_runtime_debugging",
    "conditions",
    "loop_boundaries",
    "arrays_lists",
    "indexing",
    "functions",
    "mixed_logic",
)
READINESS_DOMAINS: tuple[DiagnosticDomain, ...] = (
    "variables",
    "syntax_runtime_debugging",
    "conditions",
    "loop_boundaries",
)
MAX_ADAPTIVE_FOLLOWUPS = 3
MAX_READINESS_FOLLOWUPS = 1
DEFAULT_PYTHON_JUDGE0_ID = 71
LANG_DISPLAY_NAMES: dict[str, str] = {
    "python": "Python",
    "javascript": "JavaScript",
    "c": "C",
    "cpp": "C++",
    "java": "Java",
}


def _extract_assessment_mode(session: DiagnosticSession) -> AssessmentMode:
    summary = getattr(session, "domain_summary", None) or {}
    meta = summary.get("_meta") if isinstance(summary, dict) else None
    if isinstance(meta, dict) and meta.get("assessment_mode") == "readiness":
        return "readiness"
    return "full"


def _to_public_question(q: DiagnosticQuestion) -> DiagnosticQuestionPublicView:
    """Strictly omit private correct_option_id and evaluation_tests."""
    return DiagnosticQuestionPublicView(
        id=q.id,
        slug=q.slug,
        domain_slug=q.domain_slug,
        skill_slug=q.skill_slug,
        difficulty=q.difficulty,
        question_type=q.question_type,
        prompt_en=q.prompt_en,
        prompt_bn=q.prompt_bn,
        code_snippet=q.code_snippet,
        options=[DiagnosticOptionView.model_validate(opt) for opt in (q.options or [])],
        starter_code=q.starter_code,
        language_slug=q.language_slug,
    )


def _summarize_domain_evidence(
    session: DiagnosticSession,
) -> tuple[list[DiagnosticDomainEvidence], TrackSlug, str]:
    """Compute factual per-domain evidence & deterministic 4-track recommendation."""
    by_domain: dict[str, list[tuple[bool, str, str]]] = {d: [] for d in ALL_EIGHT_DOMAINS}
    for r in session.responses:
        by_domain.setdefault(r.domain_slug, []).append(
            (bool(r.is_correct), r.difficulty, r.question_type)
        )

    evidence_list: list[DiagnosticDomainEvidence] = []
    domains_demonstrated = 0
    domains_strong_exec = 0
    foundation_gaps = 0

    for dom in ALL_EIGHT_DOMAINS:
        entries = by_domain.get(dom, [])
        attempts = len(entries)
        correct = sum(1 for ok, _, _ in entries if ok)
        exec_verified = any(ok and qtype == "code_execution" for ok, _, qtype in entries)
        missed_foundation = any((not ok) and diff == "foundation" for ok, diff, _ in entries)

        if attempts == 0:
            ev_status = "insufficient_evidence"
            note_en = "Not yet observed in this session."
            note_bn = "এই সেশনে এখনো পর্যবেক্ষিত হয়নি।"
        elif exec_verified and correct == attempts:
            ev_status = "demonstrated_strong"
            domains_demonstrated += 1
            domains_strong_exec += 1
            note_en = f"Passed all {attempts} checks including real Judge0 execution."
            note_bn = f"আসল Judge0 কোড এক্সিকিউশনসহ {attempts}টি যাচাইয়ের সবকটি পাস করেছে।"
        elif correct == attempts:
            ev_status = "demonstrated_basic"
            domains_demonstrated += 1
            note_en = f"Answered {correct}/{attempts} diagnostic checks correctly (execution transfer not yet verified)."
            note_bn = (
                f"{attempts}টির মধ্যে {correct}টি সঠিক উত্তর দিয়েছে (স্বাধীন কোড ট্রান্সফার এখনো যাচাই হয়নি)।"
            )
        elif correct > 0 and not missed_foundation:
            ev_status = "guided_needed"
            note_en = f"Mixed evidence ({correct}/{attempts} correct); targeted guided practice recommended."
            note_bn = f"মিশ্র ফলাফল ({attempts}টির মধ্যে {correct}টি সঠিক); নির্দেশিত অনুশীলন প্রয়োজন।"
        else:
            ev_status = "gap_detected"
            foundation_gaps += 1
            note_en = f"Direct gap observed ({correct}/{attempts} correct); start from foundational lesson."
            note_bn = f"ভিত্তিগত ঘাটতি চিহ্নিত ({attempts}টির মধ্যে {correct}টি সঠিক); বেসিক লেসন থেকে শুরু করো।"

        evidence_list.append(
            DiagnosticDomainEvidence(
                domain_slug=dom,
                observed_attempts=attempts,
                observed_correct=correct,
                execution_verified=exec_verified,
                evidence_status=ev_status,
                note_en=note_en,
                note_bn=note_bn,
            )
        )

    mode = _extract_assessment_mode(session)
    raw_lang = getattr(session, "language_slug", None) or "python"
    lang_label = LANG_DISPLAY_NAMES.get(raw_lang, raw_lang.capitalize())

    # Deterministic, explainable track placement rule (zero fabricated ability score!)
    if mode == "readiness":
        # Short 4-domain beginner readiness check: conservatively places in Absolute Beginner
        # or Basic University — never prematurely awards Intermediate/Advanced from 4 checks.
        if domains_demonstrated >= 3 and foundation_gaps == 0:
            track: TrackSlug = "basic_university"
            rationale = (
                f"Recommended Basic University track for {lang_label}: readiness check demonstrated "
                f"{domains_demonstrated}/4 foundational areas cleanly. Take the full 8-domain "
                "diagnostic anytime if you want to verify Intermediate or Advanced placement."
            )
        else:
            track = "absolute_beginner"
            rationale = (
                f"Recommended Absolute Beginner track for {lang_label}: readiness check observed "
                f"{domains_demonstrated}/4 foundational areas demonstrated ({foundation_gaps} gap(s)). "
                "Continue with guided foundation lessons to build rock-solid fundamentals."
            )
        return evidence_list, track, rationale

    if domains_demonstrated <= 2 or foundation_gaps >= 5:
        track = "absolute_beginner"
        rationale = (
            f"Recommended Absolute Beginner track: diagnostic showed gaps in {foundation_gaps} "
            f"domains ({domains_demonstrated}/8 domains demonstrated). Start with guided {lang_label} "
            "foundation lessons before tackling debugging sets."
        )
    elif domains_demonstrated <= 5:
        track = "basic_university"
        rationale = (
            f"Recommended Basic University track: demonstrated {domains_demonstrated}/8 core "
            f"domains with targeted gaps in {foundation_gaps} areas. Pair foundational {lang_label} "
            "lessons with structured debugging practice."
        )
    elif domains_demonstrated >= 7 and domains_strong_exec >= 1:
        track = "advanced"
        rationale = (
            f"Recommended Advanced track: demonstrated {domains_demonstrated}/8 domains including "
            f"{domains_strong_exec} verified sandbox stretch execution check(s). Ready for complex "
            f"{lang_label} debugging and zero-hint transfer verification."
        )
    else:
        track = "intermediate"
        rationale = (
            f"Recommended Intermediate track: demonstrated {domains_demonstrated}/8 core domains. "
            f"Focus on {lang_label} boundary debugging, edge cases, and independent execution challenges."
        )

    return evidence_list, track, rationale


class DiagnosticAssessmentService:
    """Orchestrates adaptive 8-domain diagnostics with real Judge0 execution."""

    def __init__(
        self,
        *,
        learning_repo: LearningRepository,
        problem_repo: ProblemRepository,
        mentor_repo: MentorRepository,
        judge0: Judge0Client,
        skill_graph: SkillGraphService,
    ) -> None:
        self._learning_repo = learning_repo
        self._problem_repo = problem_repo
        self._mentor_repo = mentor_repo
        self._judge0 = judge0
        self._skill_graph = skill_graph

    async def _build_session_view(
        self,
        session: DiagnosticSession,
        last_feedback: DiagnosticResponseFeedback | None = None,
    ) -> DiagnosticSessionView:
        queue = list(session.question_queue or [])
        answered = len(session.responses)
        remaining = max(len(queue) - session.current_index, 0)

        current_q: DiagnosticQuestionPublicView | None = None
        if session.status == "in_progress" and session.current_index < len(queue):
            qid = UUID(queue[session.current_index])
            q_row = await self._learning_repo.get_diagnostic_question_with_answer(qid)
            if q_row is not None:
                current_q = _to_public_question(q_row)

        domain_ev, _, _ = _summarize_domain_evidence(session)
        mode = _extract_assessment_mode(session)
        next_action: JourneyActionView | None = None
        if session.status == "completed":
            lang_label = LANG_DISPLAY_NAMES.get(
                session.language_slug, session.language_slug.capitalize()
            )
            has_gaps = any(
                ev.evidence_status in ("gap_detected", "guided_needed") for ev in domain_ev
            )
            if has_gaps or session.recommended_track_slug in (
                "absolute_beginner",
                "basic_university",
            ):
                next_action = JourneyActionView(
                    action_type="lesson",
                    target_id=f"lessons-{session.language_slug}",
                    target_slug="lessons",
                    href="/student/lessons",
                    cta_label_en=f"Start {lang_label} Guided Lessons →",
                    cta_label_bn=f"{lang_label} গাইডেড লেসন শুরু করো →",
                    title_en=f"Recommended {lang_label} Guided Lessons",
                    title_bn=f"প্রস্তাবিত {lang_label} গাইডেড লেসনসমূহ",
                    reason_en="Start with prerequisite-ready lessons targeted to your diagnostic findings.",
                    reason_bn="ডায়াগনস্টিকের ফলাফল অনুযায়ী তোমার উপযুক্ত গাইডেড লেসন থেকে শুরু করো।",
                    evidence_factors=[
                        f"track:{session.recommended_track_slug or 'absolute_beginner'}"
                    ],
                    priority=5,
                    estimated_minutes=15,
                )
            else:
                next_action = JourneyActionView(
                    action_type="problem",
                    target_id=f"problems-{session.language_slug}",
                    target_slug="problems",
                    href="/student/problems",
                    cta_label_en=f"Open {lang_label} Practice & Debugging →",
                    cta_label_bn=f"{lang_label} প্র্যাকটিস ও ডিবাগিং শুরু করো →",
                    title_en=f"{lang_label} Adaptive Coding & Debugging Practice",
                    title_bn=f"{lang_label} অ্যাডাপ্টিভ কোডিং ও ডিবাগিং অনুশীলন",
                    reason_en="Your baseline is strong — move directly into hands-on sandbox debugging and transfer checks.",
                    reason_bn="তোমার ভিত্তি শক্ত — সরাসরি আসল স্যান্ডবক্স ডিবাগিং ও ট্রান্সফার চ্যালেঞ্জে এগিয়ে যাও।",
                    evidence_factors=[f"track:{session.recommended_track_slug or 'intermediate'}"],
                    priority=8,
                    estimated_minutes=20,
                )
        return DiagnosticSessionView(
            id=session.id,
            language_slug=session.language_slug,
            assessment_mode=mode,
            status=session.status,
            explanation_language=session.explanation_language,
            answered_count=answered,
            remaining_count=remaining if session.status == "in_progress" else 0,
            adaptive_followups_added=session.adaptive_followups_added,
            current_question=current_q,
            last_feedback=last_feedback,
            recommended_track_slug=session.recommended_track_slug,
            recommendation_rationale=session.recommendation_rationale,
            domain_evidence=domain_ev,
            started_at=session.started_at,
            completed_at=session.completed_at,
            next_recommended_action=next_action,
        )

    async def start_or_resume_session(
        self,
        *,
        user: UserRecord,
        explanation_language: str,
        language_slug: str | None = None,
        assessment_mode: AssessmentMode = "full",
    ) -> DiagnosticSessionView:
        lang = resolve_user_language(user, language_slug)
        existing_sessions = await self._learning_repo.list_student_diagnostic_sessions(
            student_id=user.id, limit=5, language_slug=lang
        )
        for s in existing_sessions:
            if s.status == "in_progress":
                return await self._build_session_view(s)

        published = await self._learning_repo.list_published_diagnostic_questions(
            language_slug=lang
        )
        if not published:
            raise AppError(
                code="DIAGNOSTIC_BANK_EMPTY",
                message=f"No published diagnostic questions are available yet for '{lang}'.",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        # Build queue based on assessment_mode ("readiness" = 4 foundational domains; "full" = all 8)
        initial_queue: list[str] = []
        if assessment_mode == "readiness":
            for dom in READINESS_DOMAINS:
                dom_qs = [q for q in published if q.domain_slug == dom]
                pick = (
                    next((q for q in dom_qs if q.difficulty == "foundation"), None)
                    or next((q for q in dom_qs if q.difficulty == "core"), None)
                    or (dom_qs[0] if dom_qs else None)
                )
                if pick is not None:
                    initial_queue.append(str(pick.id))
        else:
            for dom in ALL_EIGHT_DOMAINS:
                dom_qs = [q for q in published if q.domain_slug == dom]
                pick = next((q for q in dom_qs if q.difficulty == "core"), None) or (
                    dom_qs[0] if dom_qs else None
                )
                if pick is not None:
                    initial_queue.append(str(pick.id))

        session = await self._learning_repo.create_diagnostic_session(
            student_id=user.id,
            language_slug=lang,
            explanation_language=explanation_language,
            question_queue=initial_queue,
            domain_summary={"_meta": {"assessment_mode": assessment_mode}},
        )
        return await self._build_session_view(session)

    async def get_session(self, *, user: UserRecord, session_id: UUID) -> DiagnosticSessionView:
        session = await self._learning_repo.get_diagnostic_session(session_id)
        if session is None:
            raise AppError(
                code="DIAGNOSTIC_SESSION_NOT_FOUND",
                message="Diagnostic session not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        if session.student_id != user.id and "admin" not in user.roles:
            raise AppError(
                code="FORBIDDEN",
                message="You cannot inspect another student's diagnostic session.",
                status_code=status.HTTP_403_FORBIDDEN,
            )
        return await self._build_session_view(session)

    async def list_my_sessions(
        self, *, user: UserRecord, language_slug: str | None = None
    ) -> list[DiagnosticSessionView]:
        lang = resolve_user_language(user, language_slug) if language_slug else None
        rows = await self._learning_repo.list_student_diagnostic_sessions(
            student_id=user.id, limit=10, language_slug=lang
        )
        return [await self._build_session_view(r) for r in rows]

    async def submit_answer(
        self,
        *,
        user: UserRecord,
        session_id: UUID,
        payload: DiagnosticAnswerSubmitRequest,
    ) -> DiagnosticSessionView:
        session = await self._learning_repo.get_diagnostic_session(session_id)
        if session is None:
            raise AppError(
                code="DIAGNOSTIC_SESSION_NOT_FOUND",
                message="Diagnostic session not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        if session.student_id != user.id and "admin" not in user.roles:
            raise AppError(
                code="FORBIDDEN",
                message="You cannot submit answers to another student's diagnostic session.",
                status_code=status.HTTP_403_FORBIDDEN,
            )
        if session.status != "in_progress":
            raise AppError(
                code="DIAGNOSTIC_ALREADY_COMPLETED",
                message="This diagnostic session is already completed.",
                status_code=status.HTTP_409_CONFLICT,
            )

        queue = list(session.question_queue or [])
        if session.current_index >= len(queue):
            raise AppError(
                code="DIAGNOSTIC_QUEUE_EXHAUSTED",
                message="No remaining questions in this diagnostic session.",
                status_code=status.HTTP_409_CONFLICT,
            )

        expected_qid = UUID(queue[session.current_index])
        if payload.question_id != expected_qid:
            raise AppError(
                code="DIAGNOSTIC_OUT_OF_ORDER",
                message="Submitted question_id does not match the active diagnostic question.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        question = await self._learning_repo.get_diagnostic_question_with_answer(expected_qid)
        if question is None or question.answer_key is None:
            raise AppError(
                code="DIAGNOSTIC_QUESTION_INVALID",
                message="Diagnostic question answer key is unavailable.",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        is_correct = False
        execution_verdict: str | None = None
        passed_tests = 0
        total_tests = 0
        exec_stderr: str | None = None

        if question.question_type == "mcq":
            if not payload.selected_option_id:
                raise AppError(
                    code="OPTION_REQUIRED",
                    message="Select an answer option before submitting.",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
            is_correct = payload.selected_option_id == question.answer_key.correct_option_id
        else:
            # Real Judge0 code execution evaluation using private answer_key.evaluation_tests
            if not payload.source_code or not payload.source_code.strip():
                raise AppError(
                    code="CODE_REQUIRED",
                    message="Provide source code to run this diagnostic execution check.",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
            tests = list(question.answer_key.evaluation_tests or [])
            total_tests = len(tests)
            lang_row = await self._problem_repo.get_language_by_slug(question.language_slug)
            j0_lang = lang_row.judge0_language_id if lang_row else DEFAULT_PYTHON_JUDGE0_ID
            execution_verdict = "accepted"
            for tc in tests:
                out = await self._judge0.execute_test_case(
                    source_code=payload.source_code,
                    judge0_language_id=j0_lang,
                    stdin=str(tc.get("input_data", "")),
                    expected_output=str(tc.get("expected_output", "")),
                    cpu_time_limit_seconds=2.0,
                    memory_limit_kb=131072,
                )
                if out.verdict == "accepted":
                    passed_tests += 1
                elif execution_verdict == "accepted":
                    execution_verdict = out.verdict
                if exec_stderr is None and (out.stderr or out.compile_output):
                    exec_stderr = out.stderr or out.compile_output
            is_correct = total_tests > 0 and passed_tests == total_tests

        # Adaptive follow-up queue selection (strictly scoped to the session's language & mode)
        published = await self._learning_repo.list_published_diagnostic_questions(
            language_slug=session.language_slug
        )
        session_mode = _extract_assessment_mode(session)
        max_followups = (
            MAX_READINESS_FOLLOWUPS if session_mode == "readiness" else MAX_ADAPTIVE_FOLLOWUPS
        )
        followups_added = session.adaptive_followups_added
        adaptive_action: str | None = None

        if followups_added < max_followups and question.difficulty == "core":
            if not is_correct:
                # Queue a foundation follow-up in the same domain to pinpoint fundamental gap
                cand = next(
                    (
                        q
                        for q in published
                        if q.domain_slug == question.domain_slug
                        and q.difficulty == "foundation"
                        and str(q.id) not in queue
                    ),
                    None,
                )
                if cand is not None:
                    queue.append(str(cand.id))
                    followups_added += 1
                    adaptive_action = (
                        f"Added adaptive foundation check in '{question.domain_slug}' "
                        "to pinpoint whether foundational lesson support is needed."
                    )
            else:
                # Queue a stretch real-Judge0 execution check if available for this domain
                cand = next(
                    (
                        q
                        for q in published
                        if q.domain_slug == question.domain_slug
                        and q.difficulty == "stretch"
                        and str(q.id) not in queue
                    ),
                    None,
                )
                if cand is not None:
                    queue.append(str(cand.id))
                    followups_added += 1
                    adaptive_action = (
                        f"Added adaptive Judge0 execution check in '{question.domain_slug}' "
                        "to verify practical coding readiness beyond MCQ recognition."
                    )

        next_index = session.current_index + 1
        completed = next_index >= len(queue)

        # Update language-scoped Skill Graph honestly from this single diagnostic item
        if question.question_type == "code_execution" and is_correct:
            await self._skill_graph.record_evidence(
                student_id=user.id,
                language_slug=session.language_slug,
                skill_slug=question.skill_slug,
                target_state="independent",
                evidence_source="diagnostic_judge0_execution",
                evidence_ref_id=str(question.id),
                reason=(
                    f"Passed diagnostic {session.language_slug} execution check "
                    f"({passed_tests}/{total_tests}) in {question.domain_slug}."
                ),
                uncertainty_note=(
                    "Verified on a diagnostic coding check; unseen transfer and "
                    "later retention are not yet proven."
                ),
            )
        else:
            await self._skill_graph.record_evidence(
                student_id=user.id,
                language_slug=session.language_slug,
                skill_slug=question.skill_slug,
                target_state="introduced",
                evidence_source="diagnostic_mcq",
                evidence_ref_id=str(question.id),
                reason=(
                    f"Diagnostic probe in '{question.domain_slug}' ({session.language_slug}) "
                    f"({'correct' if is_correct else 'gap observed'})."
                ),
                uncertainty_note=(
                    "MCQ recognition alone does not prove independent coding mastery; "
                    "complete guided and independent coding exercises."
                ),
            )

        # Save response (temporarily advance), then finalize track recommendation if completed
        updated_session = await self._learning_repo.save_diagnostic_response_and_advance(
            session=session,
            response_data={
                "question_id": question.id,
                "domain_slug": question.domain_slug,
                "difficulty": question.difficulty,
                "question_type": question.question_type,
                "selected_option_id": payload.selected_option_id,
                "submitted_code": payload.source_code,
                "is_correct": is_correct,
                "execution_verdict": execution_verdict,
                "passed_tests": passed_tests,
                "total_tests": total_tests,
                "execution_stderr": exec_stderr,
                "response_time_ms": payload.response_time_ms,
            },
            updated_queue=queue,
            next_index=next_index,
            followups_added=followups_added,
            completed=False,
        )

        if completed:
            domain_ev, rec_track, rationale = _summarize_domain_evidence(updated_session)
            summary_payload: dict[str, object] = {
                ev.domain_slug: ev.model_dump() for ev in domain_ev
            }
            summary_payload["_meta"] = {"assessment_mode": session_mode}
            updated_session = await self._learning_repo.finalize_diagnostic_session(
                session_id=updated_session.id,
                recommended_track_slug=rec_track,
                recommendation_rationale=rationale,
                domain_summary=summary_payload,
            )
            await self._learning_repo.upsert_track_enrollment(
                student_id=user.id,
                language_slug=updated_session.language_slug,
                selected_track_slug=rec_track,
                recommended_track_slug=rec_track,
                recommendation_source="diagnostic_evidence",
                recommendation_reason=rationale,
                diagnostic_session_id=updated_session.id,
            )
            await self._mentor_repo.record_learning_event(
                student_id=user.id,
                problem_id=None,
                problem_version_id=None,
                language_slug=updated_session.language_slug,
                submission_id=None,
                diagnosis_id=None,
                event_type="diagnostic.completed",
                hints_used=0,
                verdict=rec_track,
                metadata={
                    "diagnostic_session_id": str(updated_session.id),
                    "language_slug": updated_session.language_slug,
                    "recommended_track_slug": rec_track,
                    "answered_count": len(updated_session.responses),
                },
            )

        feedback = DiagnosticResponseFeedback(
            question_id=question.id,
            domain_slug=question.domain_slug,
            difficulty=question.difficulty,
            question_type=question.question_type,
            is_correct=is_correct,
            execution_verdict=execution_verdict,
            passed_tests=passed_tests,
            total_tests=total_tests,
            execution_stderr=exec_stderr,
            feedback_en=question.answer_key.explanation_en,
            feedback_bn=question.answer_key.explanation_bn,
            adaptive_action=adaptive_action,
        )
        return await self._build_session_view(updated_session, last_feedback=feedback)

    async def create_admin_question(
        self, *, admin: UserRecord, payload: AdminDiagnosticQuestionCreateRequest
    ) -> DiagnosticQuestionPublicView:
        q = await self._learning_repo.create_admin_diagnostic_question(
            actor_id=admin.id,
            question_data={
                "slug": payload.slug,
                "language_slug": payload.language_slug,
                "domain_slug": payload.domain_slug,
                "skill_slug": payload.skill_slug,
                "difficulty": payload.difficulty,
                "question_type": payload.question_type,
                "prompt_en": payload.prompt_en,
                "prompt_bn": payload.prompt_bn,
                "code_snippet": payload.code_snippet,
                "options": [o.model_dump() for o in payload.options],
                "starter_code": payload.starter_code,
            },
            answer_data={
                "correct_option_id": payload.correct_option_id,
                "explanation_en": payload.explanation_en,
                "explanation_bn": payload.explanation_bn,
                "evaluation_tests": [t.model_dump() for t in payload.evaluation_tests],
            },
            publish=payload.publish,
        )
        return _to_public_question(q)
