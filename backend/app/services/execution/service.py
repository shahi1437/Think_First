from typing import Any
from uuid import UUID

from fastapi import status

from app.core.config import Settings
from app.core.errors import AppError
from app.integrations.execution.router import ResilientExecutionClient
from app.integrations.judge0.client import (
    HttpJudge0Client,
    Judge0Client,
    is_judge0_configured,
)
from app.integrations.piston.client import is_piston_configured
from app.models.problems import CodeRevision, ExecutionResult, Submission, TestCase
from app.repositories.identity import UserRecord
from app.repositories.problems import ProblemRepository
from app.schemas.common import PaginatedResponse
from app.schemas.problems import (
    RevisionResponse,
    RevisionSaveRequest,
    SubmissionCreateRequest,
    SubmissionResponse,
    SubmissionSummaryItem,
    TestCaseExecutionView,
    Verdict,
)

_VERDICT_PRIORITY: dict[str, int] = {
    "compilation_error": 6,
    "runtime_error": 5,
    "time_limit_exceeded": 4,
    "memory_limit_exceeded": 3,
    "internal_error": 2,
    "wrong_answer": 1,
    "accepted": 0,
}


def _aggregate_verdict(verdicts: list[Verdict]) -> Verdict:
    if not verdicts:
        return "internal_error"
    return max(verdicts, key=lambda v: _VERDICT_PRIORITY.get(v, 0))


def _sanitize_results(
    results: list[ExecutionResult],
    test_map: dict[UUID, TestCase],
    *,
    reveal_hidden: bool = False,
) -> list[TestCaseExecutionView]:
    views: list[TestCaseExecutionView] = []
    ordered = sorted(
        results,
        key=lambda r: test_map[r.test_case_id].ordinal if r.test_case_id in test_map else 9999,
    )
    for res in ordered:
        tc = test_map.get(res.test_case_id)
        ordinal = tc.ordinal if tc else 0
        is_hidden = res.is_hidden or (tc.is_hidden if tc else False)
        if is_hidden and not reveal_hidden:
            views.append(
                TestCaseExecutionView(
                    ordinal=ordinal,
                    name=f"Hidden Test #{ordinal}",
                    is_hidden=True,
                    verdict=res.verdict,
                    input_data=None,
                    expected_output=None,
                    stdout=None,
                    stderr=None,
                    compile_output=res.compile_output,
                    runtime_ms=res.runtime_ms,
                    memory_kb=res.memory_kb,
                )
            )
        else:
            views.append(
                TestCaseExecutionView(
                    ordinal=ordinal,
                    name=tc.name if tc else f"Test #{ordinal}",
                    is_hidden=is_hidden,
                    verdict=res.verdict,
                    input_data=tc.input_data if tc else None,
                    expected_output=tc.expected_output if tc else None,
                    stdout=res.stdout,
                    stderr=res.stderr,
                    compile_output=res.compile_output,
                    runtime_ms=res.runtime_ms,
                    memory_kb=res.memory_kb,
                )
            )
    return views


def _to_submission_response(
    submission: Submission,
    test_map: dict[UUID, TestCase],
    *,
    reveal_hidden: bool = False,
) -> SubmissionResponse:
    return SubmissionResponse(
        id=submission.id,
        problem_id=submission.problem_id,
        problem_version_id=submission.problem_version_id,
        language_slug=submission.language_slug,
        submission_kind=submission.submission_kind,
        source_code=submission.source_code,
        prediction_text=submission.prediction_text,
        explanation_text=submission.explanation_text,
        status=submission.status,
        verdict=submission.verdict,
        passed_tests=submission.passed_tests,
        total_tests=submission.total_tests,
        runtime_ms=submission.runtime_ms,
        memory_kb=submission.memory_kb,
        execution_provider=submission.execution_provider,
        execution_evidence=dict(submission.execution_evidence or {}),
        results=_sanitize_results(list(submission.results), test_map, reveal_hidden=reveal_hidden),
        created_at=submission.created_at,
    )


def _to_revision_response(rev: CodeRevision) -> RevisionResponse:
    return RevisionResponse(
        id=rev.id,
        problem_version_id=rev.problem_version_id,
        language_slug=rev.language_slug,
        source_code=rev.source_code,
        prediction_text=rev.prediction_text,
        explanation_text=rev.explanation_text,
        revision_type=rev.revision_type,
        created_at=rev.created_at,
    )


class ExecutionService:
    """Orchestrates quota-checked, server-controlled Judge0 code execution."""

    def __init__(
        self,
        repository: ProblemRepository,
        judge0: Judge0Client,
        settings: Settings,
    ) -> None:
        self._repo = repository
        self._judge0 = judge0
        self._settings = settings

    async def execute_submission(
        self,
        *,
        user: UserRecord,
        payload: SubmissionCreateRequest,
    ) -> SubmissionResponse:
        # 1. Validate source code byte size
        code_bytes = len(payload.source_code.encode("utf-8"))
        if code_bytes > self._settings.max_source_code_bytes:
            raise AppError(
                code="SOURCE_CODE_TOO_LARGE",
                message=(
                    f"Source code exceeds the {self._settings.max_source_code_bytes}-byte limit."
                ),
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # 2. Enforce per-minute rate limit and daily execution quota
        per_minute, per_day = await self._repo.get_quota_counts(user.id)
        if per_minute >= self._settings.execution_rate_limit_per_minute:
            raise AppError(
                code="RATE_LIMIT_EXCEEDED",
                message="Too many code execution requests. Please wait a moment and try again.",
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        if per_day >= self._settings.execution_daily_quota:
            raise AppError(
                code="DAILY_QUOTA_EXCEEDED",
                message="Daily code execution quota reached.",
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        # 3. Validate published problem & language support
        found = await self._repo.get_published_problem(payload.problem_id)
        if found is None:
            raise AppError(
                code="PROBLEM_NOT_FOUND",
                message="Published problem not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        problem, version = found

        language = await self._repo.get_language_by_slug(payload.language_slug)
        if language is None or not language.is_enabled:
            raise AppError(
                code="UNSUPPORTED_LANGUAGE",
                message=f"Language '{payload.language_slug}' is not enabled.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        supported_slugs = {v.language_slug for v in version.variants}
        if payload.language_slug not in supported_slugs:
            raise AppError(
                code="LANGUAGE_NOT_SUPPORTED_FOR_PROBLEM",
                message=(f"Language '{payload.language_slug}' is not available for this problem."),
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # 4. Select authorized test group: run -> public only; submit -> public + hidden
        sorted_tests = sorted(version.test_cases, key=lambda tc: tc.ordinal)
        selected_tests = (
            [tc for tc in sorted_tests if not tc.is_hidden]
            if payload.submission_kind == "run"
            else sorted_tests
        )
        if not selected_tests:
            raise AppError(
                code="NO_TESTS_CONFIGURED",
                message="No executable test cases configured for this problem.",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # 4b. Fail clearly before creating a submission row if execution engine(s) are disabled
        if isinstance(self._judge0, HttpJudge0Client) and not is_judge0_configured(self._settings):
            raise AppError(
                code="EXECUTION_SERVICE_UNAVAILABLE",
                message=(
                    "Live code execution is temporarily unavailable while the remote sandbox is "
                    "offline. Your draft can still be saved as a revision while you read lessons "
                    "and complete MCQ diagnostics."
                ),
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        if (
            isinstance(self._judge0, ResilientExecutionClient)
            and not is_judge0_configured(self._settings)
            and not is_piston_configured(self._settings)
        ):
            raise AppError(
                code="EXECUTION_SERVICE_UNAVAILABLE",
                message=(
                    "Live code execution is temporarily unavailable while the remote sandbox is "
                    "offline. Your draft can still be saved as a revision while you read lessons "
                    "and complete MCQ diagnostics."
                ),
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        # 5. Persist submission + revision snapshot
        submission = await self._repo.create_submission(
            student_id=user.id,
            problem_id=problem.id,
            problem_version_id=version.id,
            language_slug=language.slug,
            submission_kind=payload.submission_kind,
            source_code=payload.source_code,
            prediction_text=payload.prediction_text,
            explanation_text=payload.explanation_text,
            total_tests=len(selected_tests),
        )
        await self._repo.save_revision(
            student_id=user.id,
            problem_version_id=version.id,
            language_slug=language.slug,
            source_code=payload.source_code,
            prediction_text=payload.prediction_text,
            explanation_text=payload.explanation_text,
            revision_type=payload.submission_kind,
        )

        # 6. Execute each test case inside isolated sandbox (Judge0 CE primary, Piston fallback)
        execution_rows: list[ExecutionResult] = []
        verdicts: list[Verdict] = []
        providers_used: list[str] = []
        passed_count = 0
        public_passed = 0
        public_total = 0
        hidden_passed = 0
        hidden_total = 0
        max_runtime_ms: int | None = None
        max_memory_kb: int | None = None
        first_failing_public_ordinal: int | None = None
        observed_stderr_snippet: str | None = None
        observed_compile_snippet: str | None = None

        try:
            for tc in selected_tests:
                outcome = await self._judge0.execute_test_case(
                    source_code=payload.source_code,
                    judge0_language_id=language.judge0_language_id,
                    stdin=tc.input_data,
                    expected_output=tc.expected_output,
                    cpu_time_limit_seconds=version.time_limit_ms / 1000.0,
                    memory_limit_kb=version.memory_limit_kb,
                )
                verdicts.append(outcome.verdict)
                provider_name = outcome.execution_provider
                providers_used.append(provider_name)

                if tc.is_hidden:
                    hidden_total += 1
                    if outcome.verdict == "accepted":
                        hidden_passed += 1
                else:
                    public_total += 1
                    if outcome.verdict == "accepted":
                        public_passed += 1
                    elif first_failing_public_ordinal is None:
                        first_failing_public_ordinal = tc.ordinal

                if outcome.verdict == "accepted":
                    passed_count += 1

                if outcome.runtime_ms is not None:
                    max_runtime_ms = (
                        outcome.runtime_ms
                        if max_runtime_ms is None
                        else max(max_runtime_ms, outcome.runtime_ms)
                    )
                if outcome.memory_kb is not None:
                    max_memory_kb = (
                        outcome.memory_kb
                        if max_memory_kb is None
                        else max(max_memory_kb, outcome.memory_kb)
                    )
                if not tc.is_hidden and outcome.stderr and observed_stderr_snippet is None:
                    observed_stderr_snippet = outcome.stderr[:500]
                if outcome.compile_output and observed_compile_snippet is None:
                    observed_compile_snippet = outcome.compile_output[:500]

                execution_rows.append(
                    ExecutionResult(
                        submission_id=submission.id,
                        test_case_id=tc.id,
                        is_hidden=tc.is_hidden,
                        execution_provider=provider_name,
                        judge0_token=outcome.token,
                        judge0_status_id=outcome.status_id,
                        verdict=outcome.verdict,
                        stdout=outcome.stdout,
                        stderr=outcome.stderr,
                        compile_output=outcome.compile_output,
                        runtime_ms=outcome.runtime_ms,
                        memory_kb=outcome.memory_kb,
                    )
                )
        except AppError:
            await self._repo.finalize_submission(
                submission=submission,
                status_value="failed",
                verdict="internal_error",
                passed_tests=passed_count,
                total_tests=len(selected_tests),
                runtime_ms=max_runtime_ms,
                memory_kb=max_memory_kb,
                execution_provider="piston" if "piston" in providers_used else "judge0",
                execution_evidence={"engine_error": "execution_service_unavailable"},
                results=execution_rows,
            )
            raise

        overall_verdict = _aggregate_verdict(verdicts)
        effective_provider = "piston" if "piston" in providers_used else "judge0"
        # Structured objective execution evidence for ML / Rule-based Diagnosis & Socratic Mentor
        evidence: dict[str, Any] = {
            "mode": version.mode,
            "submission_kind": payload.submission_kind,
            "language_slug": language.slug,
            "execution_provider": effective_provider,
            "fallback_used": effective_provider == "piston",
            "overall_verdict": overall_verdict,
            "public_passed": public_passed,
            "public_total": public_total,
            "hidden_passed": hidden_passed,
            "hidden_total": hidden_total,
            "first_failing_public_ordinal": first_failing_public_ordinal,
            "has_compile_error": overall_verdict == "compilation_error",
            "has_runtime_error": overall_verdict == "runtime_error",
            "has_prediction": bool(payload.prediction_text and payload.prediction_text.strip()),
            "has_explanation": bool(payload.explanation_text and payload.explanation_text.strip()),
            "stderr_preview": observed_stderr_snippet,
            "compile_output_preview": observed_compile_snippet,
            "ai_diagnosis_ready_for_phase_4": True,
        }

        finalized = await self._repo.finalize_submission(
            submission=submission,
            status_value="completed",
            verdict=overall_verdict,
            passed_tests=passed_count,
            total_tests=len(selected_tests),
            runtime_ms=max_runtime_ms,
            memory_kb=max_memory_kb,
            execution_provider=effective_provider,
            execution_evidence=evidence,
            results=execution_rows,
        )
        test_map = {tc.id: tc for tc in sorted_tests}
        return _to_submission_response(finalized, test_map, reveal_hidden=False)

    async def get_submission(self, *, user: UserRecord, submission_id: UUID) -> SubmissionResponse:
        submission = await self._repo.get_submission_by_id(submission_id)
        if submission is None:
            raise AppError(
                code="SUBMISSION_NOT_FOUND",
                message="Submission not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        is_admin = "admin" in user.roles
        if submission.student_id != user.id and not is_admin:
            raise AppError(
                code="FORBIDDEN",
                message="You do not have permission to view this submission.",
                status_code=status.HTTP_403_FORBIDDEN,
            )
        test_map = await self._repo.get_test_cases_map(submission.problem_version_id)
        return _to_submission_response(submission, test_map, reveal_hidden=is_admin)

    async def list_my_submissions(
        self,
        *,
        user: UserRecord,
        problem_id: UUID | None = None,
        limit: int = 25,
        offset: int = 0,
    ) -> PaginatedResponse[SubmissionSummaryItem]:
        rows, total = await self._repo.list_student_submissions(
            student_id=user.id,
            problem_id=problem_id,
            limit=limit,
            offset=offset,
        )
        items = [
            SubmissionSummaryItem(
                id=s.id,
                problem_id=s.problem_id,
                problem_version_id=s.problem_version_id,
                language_slug=s.language_slug,
                submission_kind=s.submission_kind,
                status=s.status,
                verdict=s.verdict,
                passed_tests=s.passed_tests,
                total_tests=s.total_tests,
                runtime_ms=s.runtime_ms,
                memory_kb=s.memory_kb,
                execution_provider=s.execution_provider,
                created_at=s.created_at,
            )
            for s in rows
        ]
        return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)

    async def save_revision(
        self,
        *,
        user: UserRecord,
        payload: RevisionSaveRequest,
    ) -> RevisionResponse:
        if len(payload.source_code.encode("utf-8")) > self._settings.max_source_code_bytes:
            raise AppError(
                code="SOURCE_CODE_TOO_LARGE",
                message="Revision source code exceeds size limit.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        language = await self._repo.get_language_by_slug(payload.language_slug)
        if language is None:
            raise AppError(
                code="UNSUPPORTED_LANGUAGE",
                message=f"Language '{payload.language_slug}' is not registered.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        rev = await self._repo.save_revision(
            student_id=user.id,
            problem_version_id=payload.problem_version_id,
            language_slug=payload.language_slug,
            source_code=payload.source_code,
            prediction_text=payload.prediction_text,
            explanation_text=payload.explanation_text,
            revision_type=payload.revision_type,
        )
        return _to_revision_response(rev)

    async def list_revisions(
        self,
        *,
        user: UserRecord,
        problem_version_id: UUID,
        limit: int = 20,
    ) -> list[RevisionResponse]:
        revisions = await self._repo.list_revisions(
            student_id=user.id,
            problem_version_id=problem_version_id,
            limit=limit,
        )
        return [_to_revision_response(rev) for rev in revisions]
