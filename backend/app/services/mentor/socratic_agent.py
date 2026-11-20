"""Bounded stateful Socratic AI Mentor orchestrator.

Combines:
1. Real Judge0 execution evidence from `submissions` & `execution_results`
2. Own trained scikit-learn ML error diagnosis (`MLErrorClassifierService`)
3. Approved PostgreSQL pgvector RAG retrieval (`RagKnowledgeService`)
4. Configurable Socratic LLM adapter with prompt-injection & solution-leakage guards
"""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from fastapi import status

from app.core.config import Settings
from app.core.errors import AppError
from app.integrations.llm.client import (
    SocraticLLMClient,
    TutorPromptContext,
    detect_prompt_injection,
)
from app.models.mentor import ErrorDiagnosis, MentorSession
from app.models.problems import Submission
from app.repositories.identity import UserRecord
from app.repositories.mentor import MentorRepository
from app.repositories.problems import ProblemRepository
from app.schemas.mentor import (
    MentorSessionCreateRequest,
    MentorSessionDetail,
    MentorState,
    MentorTurnCreateRequest,
    MentorTurnView,
    MLCandidateScore,
    MLDiagnosisResponse,
    RagCitation,
)
from app.services.mentor.ml_inference import DISPLAY_NAMES, MLErrorClassifierService
from app.services.mentor.rag_service import RagKnowledgeService
from ml.preprocessing.features import ExecutionSample


def _diagnosis_model_to_schema(diag: ErrorDiagnosis) -> MLDiagnosisResponse:
    candidates = [MLCandidateScore.model_validate(item) for item in (diag.top_candidates or [])]
    note = str((diag.feature_summary or {}).get("uncertainty_note", ""))
    return MLDiagnosisResponse(
        id=diag.id,
        submission_id=diag.submission_id,
        model_version=diag.model_version_tag,
        predicted_error_code=diag.predicted_error_code,
        predicted_display_name=DISPLAY_NAMES.get(
            diag.predicted_error_code, diag.predicted_error_code
        ),
        confidence=round(float(diag.confidence), 4),
        is_low_confidence=diag.is_low_confidence,
        uncertainty_note=note,
        top_candidates=candidates,
    )


class SocraticMentorService:
    """State-machine tutor grounded in Judge0 evidence, ML diagnosis, and approved RAG."""

    def __init__(
        self,
        *,
        mentor_repo: MentorRepository,
        problem_repo: ProblemRepository,
        ml_service: MLErrorClassifierService,
        rag_service: RagKnowledgeService,
        llm_client: SocraticLLMClient,
        settings: Settings,
    ) -> None:
        self._mentor_repo = mentor_repo
        self._problem_repo = problem_repo
        self._ml = ml_service
        self._rag = rag_service
        self._llm = llm_client
        self._settings = settings

    async def _check_rate_limit(self, student_id: UUID) -> None:
        recent = await self._mentor_repo.count_recent_mentor_turns(student_id=student_id, minutes=1)
        if recent >= self._settings.mentor_rate_limit_per_minute:
            raise AppError(
                code="MENTOR_RATE_LIMIT_EXCEEDED",
                message="Too many mentor requests in the last minute. Take a moment to trace your code and try again.",
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            )

    async def _resolve_submission(
        self, *, user: UserRecord, problem_id: UUID, submission_id: UUID | None
    ) -> Submission | None:
        if submission_id is not None:
            sub = await self._problem_repo.get_submission_by_id(submission_id)
            if sub is None:
                raise AppError(
                    code="SUBMISSION_NOT_FOUND",
                    message="Referenced submission was not found.",
                    status_code=status.HTTP_404_NOT_FOUND,
                )
            if sub.student_id != user.id and "admin" not in user.roles:
                raise AppError(
                    code="FORBIDDEN",
                    message="You cannot inspect another student's submission.",
                    status_code=status.HTTP_403_FORBIDDEN,
                )
            return sub

        subs, _ = await self._problem_repo.list_student_submissions(
            student_id=user.id, problem_id=problem_id, limit=1, offset=0
        )
        if not subs:
            return None
        return await self._problem_repo.get_submission_by_id(subs[0].id)

    async def diagnose_submission(
        self, *, user: UserRecord, submission: Submission
    ) -> tuple[ErrorDiagnosis, MLDiagnosisResponse]:
        """Run our own trained ML classifier over real Judge0 execution evidence and persist."""
        existing = await self._mentor_repo.get_latest_diagnosis_for_submission(submission.id)
        if existing is not None:
            return existing, _diagnosis_model_to_schema(existing)

        test_map = await self._problem_repo.get_test_cases_map(submission.problem_version_id)
        first_stderr = ""
        first_compile = ""
        first_actual = ""
        first_expected = ""
        for res in submission.results:
            if res.verdict != "accepted":
                if not res.is_hidden:
                    tc = test_map.get(res.test_case_id)
                    first_actual = res.stdout or ""
                    first_expected = tc.expected_output if tc else ""
                    first_stderr = res.stderr or ""
                first_compile = res.compile_output or first_compile
                if first_stderr or first_actual or first_compile:
                    break

        sample = ExecutionSample(
            source_code=submission.source_code,
            verdict=submission.verdict,
            stderr=first_stderr,
            compile_output=first_compile,
            stdout_actual=first_actual,
            stdout_expected=first_expected,
            passed_tests=submission.passed_tests,
            total_tests=max(submission.total_tests, 1),
        )
        prediction = self._ml.predict(sample)

        mv = await self._mentor_repo.ensure_model_version(
            version_tag=prediction.model_version,
            model_type="tfidf_logistic_regression",
            dataset_version="python_errors_v1",
            artifact_path=self._settings.ml_model_artifact_path,
            metrics={},
        )
        saved = await self._mentor_repo.save_diagnosis(
            submission_id=submission.id,
            student_id=user.id,
            model_version_id=mv.id,
            model_version_tag=prediction.model_version,
            predicted_error_code=prediction.predicted_error_code,
            confidence=prediction.confidence,
            is_low_confidence=prediction.is_low_confidence,
            top_candidates=[c.model_dump() for c in prediction.top_candidates],
            feature_summary={
                "verdict": submission.verdict,
                "passed_tests": submission.passed_tests,
                "total_tests": submission.total_tests,
                "uncertainty_note": prediction.uncertainty_note,
            },
        )
        prediction.id = saved.id
        prediction.submission_id = submission.id
        return saved, prediction

    async def _build_session_detail(
        self, *, user: UserRecord, session: MentorSession
    ) -> MentorSessionDetail:
        all_chunk_ids: list[UUID] = []
        for t in session.turns:
            all_chunk_ids.extend(t.cited_chunk_ids or [])
        chunk_lookup = await self._mentor_repo.get_chunks_by_ids(list(set(all_chunk_ids)))

        turn_views: list[MentorTurnView] = []
        latest_citations: list[RagCitation] = []
        for t in sorted(session.turns, key=lambda item: item.turn_index):
            cites: list[RagCitation] = []
            for cid in t.cited_chunk_ids or []:
                pair = chunk_lookup.get(cid)
                if pair is not None:
                    ch, doc = pair
                    cites.append(
                        RagCitation(
                            chunk_id=ch.id,
                            document_id=doc.id,
                            document_slug=doc.slug,
                            source_title=doc.title,
                            source_name=doc.source_name,
                            source_version=doc.source_version,
                            topic=doc.topic,
                            heading=ch.heading,
                            excerpt=ch.content[:360],
                            similarity=float(
                                (t.structured_payload or {})
                                .get("citation_scores", {})
                                .get(str(cid), 0.5)
                            ),
                        )
                    )
            if cites:
                latest_citations = cites
            turn_views.append(
                MentorTurnView(
                    id=t.id,
                    turn_index=t.turn_index,
                    role=t.role,
                    state_after=t.state_after,
                    message_text=t.message_text,
                    structured_payload=dict(t.structured_payload or {}),
                    citations=cites,
                    provider_mode=t.provider_mode,
                    created_at=t.created_at,
                )
            )

        latest_diagnosis: MLDiagnosisResponse | None = None
        if session.latest_submission_id is not None:
            diag_row = await self._mentor_repo.get_latest_diagnosis_for_submission(
                session.latest_submission_id
            )
            if diag_row is not None:
                latest_diagnosis = _diagnosis_model_to_schema(diag_row)

        # Check whether linked transfer verification is unlocked (real Accepted Submit on Judge0)
        link_tuple = await self._mentor_repo.get_verification_link_for_source_problem(
            session.problem_id
        )
        accepted_sub = await self._mentor_repo.has_accepted_submit(
            student_id=user.id, problem_id=session.problem_id
        )
        transfer_unlocked = bool(link_tuple is not None and accepted_sub is not None)

        return MentorSessionDetail(
            id=session.id,
            problem_id=session.problem_id,
            problem_version_id=session.problem_version_id,
            latest_submission_id=session.latest_submission_id,
            current_state=session.current_state,
            explanation_language=session.explanation_language,
            learner_level=session.learner_level,
            hints_used=session.hints_used,
            max_hints=3,
            provider_mode=session.provider_mode,
            latest_diagnosis=latest_diagnosis,
            latest_citations=latest_citations,
            turns=turn_views,
            transfer_unlocked=transfer_unlocked,
            verification_link_id=link_tuple[0].id if link_tuple else None,
            created_at=session.created_at,
            updated_at=session.updated_at,
        )

    async def start_or_get_session(
        self, *, user: UserRecord, payload: MentorSessionCreateRequest
    ) -> MentorSessionDetail:
        found = await self._problem_repo.get_published_problem(payload.problem_id)
        if found is None:
            raise AppError(
                code="PROBLEM_NOT_FOUND",
                message="Published problem not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        problem, version = found

        # Ensure approved RAG knowledge base is seeded for fresh databases
        existing_docs = await self._mentor_repo.list_knowledge_documents(approved_only=True)
        if not existing_docs:
            await self._rag.seed_approved_corpus()

        pref_lang: Literal["en", "bn"] = payload.explanation_language or (
            user.preferences.preferred_explanation_language if user.preferences else "en"
        )
        learner_level = user.preferences.programming_experience if user.preferences else "beginner"
        submission = await self._resolve_submission(
            user=user, problem_id=problem.id, submission_id=payload.submission_id
        )

        session = await self._mentor_repo.get_or_create_session(
            student_id=user.id,
            problem_id=problem.id,
            problem_version_id=version.id,
            explanation_language=pref_lang,
            learner_level=learner_level,
            latest_submission_id=submission.id if submission else None,
        )

        # If a failing submission exists and the session has no turns yet, auto-diagnose cleanly
        if submission is not None and len(session.turns) == 0:
            return await self.process_turn(
                user=user,
                session_id=session.id,
                payload=MentorTurnCreateRequest(
                    action="diagnose",
                    submission_id=submission.id,
                    explanation_language=pref_lang,
                ),
            )

        return await self._build_session_detail(user=user, session=session)

    async def get_session(self, *, user: UserRecord, session_id: UUID) -> MentorSessionDetail:
        session = await self._mentor_repo.get_session_by_id(session_id)
        if session is None:
            raise AppError(
                code="MENTOR_SESSION_NOT_FOUND",
                message="Mentor session not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        if session.student_id != user.id and "admin" not in user.roles:
            raise AppError(
                code="FORBIDDEN",
                message="You do not have permission to access this mentor session.",
                status_code=status.HTTP_403_FORBIDDEN,
            )
        return await self._build_session_detail(user=user, session=session)

    async def process_turn(
        self,
        *,
        user: UserRecord,
        session_id: UUID,
        payload: MentorTurnCreateRequest,
    ) -> MentorSessionDetail:
        session = await self._mentor_repo.get_session_by_id(session_id)
        if session is None:
            raise AppError(
                code="MENTOR_SESSION_NOT_FOUND",
                message="Mentor session not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        if session.student_id != user.id and "admin" not in user.roles:
            raise AppError(
                code="FORBIDDEN",
                message="You cannot interact with another student's mentor session.",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        await self._check_rate_limit(user.id)

        found = await self._problem_repo.get_published_problem(session.problem_id)
        if found is None:
            raise AppError(
                code="PROBLEM_NOT_FOUND",
                message="Problem not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        problem, version = found

        lang: Literal["en", "bn"] = (
            payload.explanation_language or session.explanation_language  # type: ignore[assignment]
        )
        session.explanation_language = lang

        submission = await self._resolve_submission(
            user=user,
            problem_id=problem.id,
            submission_id=payload.submission_id or session.latest_submission_id,
        )
        if submission is None:
            msg = (
                "প্রথমে একবার Run Code বা Submit Code চালিয়ে দেখো, যাতে আসল Judge0 ফলাফলের ভিত্তিতে তোমাকে সাহায্য করতে পারি।"
                if lang == "bn"
                else "Run or submit your code at least once first so I can analyze real Judge0 execution evidence."
            )
            await self._mentor_repo.append_turn(
                session=session,
                role="mentor",
                state_after="awaiting_submission",
                message_text=msg,
                structured_payload={"guiding_question": msg, "concept_focus": "execution_first"},
                cited_chunk_ids=[],
                diagnosis_id=None,
                provider_mode="deterministic_fallback",
            )
            reloaded = await self._mentor_repo.get_session_by_id(session.id)
            return await self._build_session_detail(user=user, session=reloaded or session)

        # Record student turn if student sent a response message
        if payload.action == "respond" and payload.student_message.strip():
            await self._mentor_repo.append_turn(
                session=session,
                role="student",
                state_after="diagnosing",
                message_text=payload.student_message.strip(),
                structured_payload={"action": "respond"},
                cited_chunk_ids=[],
                diagnosis_id=None,
                provider_mode=session.provider_mode,
                latest_submission_id=submission.id,
            )

        # Determine hint policy & state transition
        requested_hint_level: int | None = None
        next_state: MentorState
        if submission.verdict == "accepted":
            next_state = "verifying"
        elif payload.action == "request_hint":
            transfer_link = await self._mentor_repo.get_verification_link_for_transfer_problem(
                problem.id
            )
            if transfer_link is not None and session.hints_used >= transfer_link.max_hints_allowed:
                raise AppError(
                    code="TRANSFER_HINTS_DISABLED",
                    message=(
                        "AI hints are disabled for this independent transfer verification challenge "
                        f"(max hints allowed: {transfer_link.max_hints_allowed})."
                    ),
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
            if session.hints_used >= 3:
                raise AppError(
                    code="HINT_LIMIT_REACHED",
                    message="All 3 progressive hint levels have been used for this session. Try revising your code and running Judge0.",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
            requested_hint_level = payload.requested_hint_level or (session.hints_used + 1)
            requested_hint_level = min(max(requested_hint_level, 1), 3)
            next_state = "giving_hint"
        elif payload.action == "respond":
            next_state = "awaiting_revision"
        else:
            next_state = "asking_question"

        # 1. Own ML Diagnosis (only on non-accepted submissions)
        diag_row: ErrorDiagnosis | None = None
        diag_resp: MLDiagnosisResponse | None = None
        if submission.verdict != "accepted":
            diag_row, diag_resp = await self.diagnose_submission(user=user, submission=submission)

        # 2. Verified pgvector RAG retrieval (strictly approved documents)
        primary_topic = version.topics[0] if version.topics else None
        rag_query = (
            f"{version.title} {submission.verdict} "
            f"{diag_resp.predicted_error_code if diag_resp else ''} "
            f"{payload.student_message[:180]}"
        )
        rag_result = await self._rag.retrieve(
            query=rag_query,
            topic=primary_topic,
            error_code=diag_resp.predicted_error_code if diag_resp else None,
            top_k=2,
        )

        # 3. Load private reference solution ONLY server-side for solution-leakage blocking
        admin_loaded = await self._problem_repo.get_admin_problem_latest(problem.id)
        ref_code_for_guard: str | None = None
        if admin_loaded is not None:
            for v in admin_loaded[1].variants:
                if v.language_slug == submission.language_slug and v.reference_solution:
                    ref_code_for_guard = v.reference_solution.reference_solution
                    break

        stderr_preview = str((submission.execution_evidence or {}).get("stderr_preview") or "")
        ctx = TutorPromptContext(
            problem_title=version.title,
            problem_mode=version.mode,
            verdict=submission.verdict,
            passed_tests=submission.passed_tests,
            total_tests=submission.total_tests,
            stderr_preview=stderr_preview,
            student_code=submission.source_code,
            student_message=payload.student_message,
            diagnosis=diag_resp,
            citations=rag_result.citations,
            explanation_language=lang,
            learner_level=session.learner_level,
            next_state=next_state,
            requested_hint_level=requested_hint_level,
            reference_solution_for_leak_check=ref_code_for_guard,
        )

        reply, provider_mode = await self._llm.generate_socratic_reply(ctx)
        cited_ids = [c.chunk_id for c in rag_result.citations]
        citation_scores = {str(c.chunk_id): c.similarity for c in rag_result.citations}

        mentor_message = reply.guiding_question
        if reply.hint_text:
            mentor_message = (
                f"Hint (Level {reply.hint_level}): {reply.hint_text}\n\n{reply.guiding_question}"
            )

        structured_payload = {
            **reply.model_dump(),
            "rag_matched": rag_result.matched,
            "rag_fallback_note": rag_result.fallback_note,
            "citation_scores": citation_scores,
            "injection_detected": detect_prompt_injection(payload.student_message),
        }

        await self._mentor_repo.append_turn(
            session=session,
            role="mentor",
            state_after=reply.next_state,
            message_text=mentor_message,
            structured_payload=structured_payload,
            cited_chunk_ids=cited_ids,
            diagnosis_id=diag_row.id if diag_row else None,
            provider_mode=provider_mode,
            increment_hint=bool(requested_hint_level is not None and not reply.safety_blocked),
            latest_submission_id=submission.id,
        )

        if requested_hint_level is not None and reply.hint_text and not reply.safety_blocked:
            await self._mentor_repo.record_hint_event(
                session_id=session.id,
                student_id=user.id,
                submission_id=submission.id,
                hint_level=requested_hint_level,
                hint_text=reply.hint_text,
                cited_chunk_ids=cited_ids,
            )

        await self._mentor_repo.record_learning_event(
            student_id=user.id,
            problem_id=problem.id,
            problem_version_id=version.id,
            language_slug=submission.language_slug,
            submission_id=submission.id,
            diagnosis_id=diag_row.id if diag_row else None,
            event_type=(
                "mentor.hint_given" if requested_hint_level is not None else "mentor.diagnosis_turn"
            ),
            hints_used=session.hints_used,
            verdict=submission.verdict,
            metadata={
                "state_after": reply.next_state,
                "provider_mode": provider_mode,
                "predicted_error_code": diag_resp.predicted_error_code if diag_resp else None,
                "rag_citations_count": len(cited_ids),
            },
        )

        reloaded = await self._mentor_repo.get_session_by_id(session.id)
        return await self._build_session_detail(user=user, session=reloaded or session)
