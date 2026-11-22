"""Unit tests for Phase 3 Multi-Language Learning, Resilient Judge0->Piston Fallback,
Honest Multi-Language Diagnosis, and Language-Scoped RAG/Socratic Mentoring.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from app.core.config import Settings
from app.core.errors import AppError
from app.integrations.execution.router import ResilientExecutionClient
from app.integrations.judge0.client import Judge0ExecutionOutcome
from app.integrations.llm.client import SocraticLLMClient, TutorPromptContext
from app.integrations.piston.client import HttpPistonClient
from app.schemas.mentor import MLDiagnosisResponse
from app.services.mentor.knowledge_corpus import ALL_APPROVED_KNOWLEDGE_DOCS
from app.services.mentor.ml_inference import MLErrorClassifierService
from app.services.mentor.multilanguage_diagnosis import diagnose_non_python_submission
from ml.preprocessing.features import ExecutionSample


@dataclass
class _StubExecutor:
    provider: str
    outcome: Judge0ExecutionOutcome | None = None
    error: Exception | None = None
    calls: int = 0

    async def execute_test_case(
        self,
        *,
        source_code: str,
        judge0_language_id: int = 71,
        stdin: str = "",
        expected_output: str = "",
        cpu_time_limit_seconds: float = 2.0,
        memory_limit_kb: int = 128000,
        language_slug: str | None = None,
    ) -> Judge0ExecutionOutcome:
        _ = (
            source_code,
            judge0_language_id,
            stdin,
            expected_output,
            cpu_time_limit_seconds,
            memory_limit_kb,
            language_slug,
        )
        self.calls += 1
        if self.error is not None:
            raise self.error
        assert self.outcome is not None
        return self.outcome

    async def list_languages(self) -> list[dict[str, Any]]:
        return [{"id": 71, "name": "Python"}]

    async def check_health(self) -> tuple[bool, str]:
        return (self.error is None, f"{self.provider} ok")


_EXEC_KWARGS: dict[str, Any] = {
    "stdin": "",
    "expected_output": "42",
    "cpu_time_limit_seconds": 2.0,
    "memory_limit_kb": 128000,
}


def _make_outcome(
    verdict: str,
    *,
    provider: str = "judge0",
    stdout: str | None = "42\n",
    stderr: str | None = None,
    compile_output: str | None = None,
    status_id: int = 3,
    status_description: str = "Accepted",
) -> Judge0ExecutionOutcome:
    return Judge0ExecutionOutcome(
        token="tok-test",
        status_id=status_id,
        status_description=status_description,
        verdict=verdict,  # type: ignore[arg-type]
        stdout=stdout,
        stderr=stderr,
        compile_output=compile_output,
        runtime_ms=15,
        memory_kb=4096,
        execution_provider=provider,  # type: ignore[arg-type]
    )


@pytest.mark.asyncio
async def test_router_uses_primary_judge0_without_calling_fallback() -> None:
    primary = _StubExecutor("judge0", outcome=_make_outcome("accepted", provider="judge0"))
    fallback = _StubExecutor("piston", outcome=_make_outcome("accepted", provider="piston"))
    settings = Settings(execution_fallback_enabled=True, piston_enabled=True)
    router = ResilientExecutionClient(primary=primary, fallback=fallback, settings=settings)

    result = await router.execute_test_case(
        source_code="print(42)",
        judge0_language_id=71,
        language_slug="python",
        **_EXEC_KWARGS,
    )

    assert result.verdict == "accepted"
    assert result.execution_provider == "judge0"
    assert primary.calls == 1
    assert fallback.calls == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "student_verdict",
    [
        "wrong_answer",
        "compilation_error",
        "runtime_error",
        "time_limit_exceeded",
        "memory_limit_exceeded",
    ],
)
async def test_router_never_falls_back_on_student_code_errors(student_verdict: str) -> None:
    """Student code bugs MUST stay on Judge0 and NEVER trigger Piston fallback."""
    primary = _StubExecutor(
        "judge0",
        outcome=_make_outcome(
            student_verdict,
            provider="judge0",
            stderr="ZeroDivisionError: division by zero"
            if student_verdict == "runtime_error"
            else None,
            compile_output="main.c:3:1: error: expected ';'"
            if student_verdict == "compilation_error"
            else None,
        ),
    )
    fallback = _StubExecutor("piston", outcome=_make_outcome("accepted", provider="piston"))
    settings = Settings(execution_fallback_enabled=True, piston_enabled=True)
    router = ResilientExecutionClient(primary=primary, fallback=fallback, settings=settings)

    result = await router.execute_test_case(
        source_code="bad code",
        judge0_language_id=50,
        language_slug="c",
        **_EXEC_KWARGS,
    )

    assert result.verdict == student_verdict
    assert result.execution_provider == "judge0"
    assert primary.calls == 1
    assert fallback.calls == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error_code",
    [
        "EXECUTION_SERVICE_UNAVAILABLE",
        "EXECUTION_TIMEOUT",
        "EXECUTION_QUOTA_EXCEEDED",
        "EXECUTION_AUTH_FAILED",
    ],
)
async def test_router_falls_back_to_piston_on_judge0_infra_failure(error_code: str) -> None:
    primary = _StubExecutor(
        "judge0",
        error=AppError(code=error_code, message="Judge0 unreachable", status_code=503),
    )
    fallback = _StubExecutor("piston", outcome=_make_outcome("accepted", provider="piston"))
    settings = Settings(execution_fallback_enabled=True, piston_enabled=True)
    router = ResilientExecutionClient(primary=primary, fallback=fallback, settings=settings)

    result = await router.execute_test_case(
        source_code="console.log(42);",
        judge0_language_id=63,
        language_slug="javascript",
        **_EXEC_KWARGS,
    )

    assert result.verdict == "accepted"
    assert result.execution_provider == "piston"
    assert primary.calls == 1
    assert fallback.calls == 1


@pytest.mark.asyncio
async def test_router_falls_back_on_judge0_vm_init_oom() -> None:
    """If remote Judge0 cannot initialize V8/JVM under tight RLIMIT_AS, fallback to Piston."""
    primary = _StubExecutor(
        "judge0",
        outcome=_make_outcome(
            "runtime_error",
            provider="judge0",
            stderr="Fatal process OOM in CodeRange setup",
        ),
    )
    fallback = _StubExecutor("piston", outcome=_make_outcome("accepted", provider="piston"))
    settings = Settings(execution_fallback_enabled=True, piston_enabled=True)
    router = ResilientExecutionClient(primary=primary, fallback=fallback, settings=settings)

    result = await router.execute_test_case(
        source_code="console.log(42);",
        judge0_language_id=63,
        language_slug="javascript",
        **_EXEC_KWARGS,
    )

    assert result.verdict == "accepted"
    assert result.execution_provider == "piston"
    assert primary.calls == 1
    assert fallback.calls == 1


@pytest.mark.asyncio
async def test_router_raises_503_when_both_providers_unavailable() -> None:
    primary = _StubExecutor(
        "judge0",
        error=AppError(
            code="EXECUTION_SERVICE_UNAVAILABLE", message="Judge0 down", status_code=503
        ),
    )
    fallback = _StubExecutor(
        "piston",
        error=AppError(code="PISTON_UNAVAILABLE", message="Piston down", status_code=503),
    )
    settings = Settings(execution_fallback_enabled=True, piston_enabled=True)
    router = ResilientExecutionClient(primary=primary, fallback=fallback, settings=settings)

    with pytest.raises(AppError) as exc_info:
        await router.execute_test_case(
            source_code="print(1)",
            judge0_language_id=71,
            language_slug="python",
            **_EXEC_KWARGS,
        )

    assert exc_info.value.status_code == 503
    assert exc_info.value.code == "EXECUTION_SERVICE_UNAVAILABLE"
    assert primary.calls == 1
    assert fallback.calls == 1


@pytest.mark.asyncio
async def test_router_respects_fallback_disabled_flag() -> None:
    primary = _StubExecutor(
        "judge0",
        error=AppError(
            code="EXECUTION_SERVICE_UNAVAILABLE", message="Judge0 down", status_code=503
        ),
    )
    fallback = _StubExecutor("piston", outcome=_make_outcome("accepted", provider="piston"))
    settings = Settings(execution_fallback_enabled=False, piston_enabled=True)
    router = ResilientExecutionClient(primary=primary, fallback=fallback, settings=settings)

    with pytest.raises(AppError) as exc_info:
        await router.execute_test_case(
            source_code="print(1)",
            judge0_language_id=71,
            language_slug="python",
            **_EXEC_KWARGS,
        )

    assert exc_info.value.code == "EXECUTION_SERVICE_UNAVAILABLE"
    assert fallback.calls == 0


@pytest.mark.asyncio
async def test_piston_client_rejects_unknown_language_cleanly() -> None:
    client = HttpPistonClient(Settings(piston_base_url="http://127.0.0.1:2000"))
    with pytest.raises(AppError) as exc_info:
        await client.execute_test_case(
            source_code="echo hi",
            language_slug="brainfuck",
            **_EXEC_KWARGS,
        )
    assert exc_info.value.status_code == 400
    assert exc_info.value.code == "UNSUPPORTED_LANGUAGE"


def test_multilanguage_diagnosis_is_honest_about_ml_vs_rule_based() -> None:
    # 1. C compiler error -> rule_based
    c_diag = diagnose_non_python_submission(
        ExecutionSample(
            verdict="compilation_error",
            compile_output="main.c: In function 'main':\nmain.c:4:15: error: expected ';' before 'return'",
            stderr="",
            source_code='#include <stdio.h>\nint main(){ printf("hi") return 0; }',
        ),
        language_slug="c",
    )
    assert c_diag.diagnosis_source == "rule_based"
    assert c_diag.model_version == "rule-multilang-v1"
    assert c_diag.language_slug == "c"
    assert c_diag.predicted_error_code == "syntax_error"

    # 2. Java ArrayIndexOutOfBounds -> rule_based + indexing_error
    java_diag = diagnose_non_python_submission(
        ExecutionSample(
            verdict="runtime_error",
            compile_output="",
            stderr='Exception in thread "main" java.lang.ArrayIndexOutOfBoundsException: Index 5 out of bounds for length 5',
            source_code="public class Main { public static void main(String[] a){ int[] x = new int[5]; System.out.println(x[5]); } }",
        ),
        language_slug="java",
    )
    assert java_diag.diagnosis_source == "rule_based"
    assert java_diag.predicted_error_code == "indexing_error"

    # 3. JavaScript ReferenceError -> rule_based + runtime_error
    js_diag = diagnose_non_python_submission(
        ExecutionSample(
            verdict="runtime_error",
            compile_output="",
            stderr="ReferenceError: totalSum is not defined",
            source_code="console.log(totalSum);",
        ),
        language_slug="javascript",
    )
    assert js_diag.diagnosis_source == "rule_based"
    assert js_diag.predicted_error_code == "runtime_error"

    # 4. C++ off-by-one wrong answer -> rule_based + loop/logic
    cpp_diag = diagnose_non_python_submission(
        ExecutionSample(
            verdict="wrong_answer",
            compile_output="",
            stderr="",
            source_code="#include <iostream>\nint main(){ int s=0; for(int i=1;i<5;i++) s+=i; std::cout<<s; }",
            stdout_expected="15",
            stdout_actual="10",
        ),
        language_slug="cpp",
    )
    assert cpp_diag.diagnosis_source == "rule_based"
    assert cpp_diag.language_slug == "cpp"
    assert cpp_diag.predicted_error_code in {"loop_boundary_error", "logic_error"}

    # 5. Python routes through trained scikit-learn ML classifier (`ml_classifier`)
    svc = MLErrorClassifierService(Settings())
    py_diag = svc.predict_for_language(
        ExecutionSample(
            verdict="runtime_error",
            source_code="nums = [1, 2]\nprint(nums[5])",
            stderr="IndexError: list index out of range",
            compile_output="",
            stdout_expected="2",
            stdout_actual="",
        ),
        language_slug="python",
    )
    assert py_diag.diagnosis_source == "ml_classifier"
    assert py_diag.language_slug == "python"
    assert py_diag.predicted_error_code == "indexing_error"


def test_rag_corpus_covers_all_five_languages() -> None:
    langs = {doc.language_slug for doc in ALL_APPROVED_KNOWLEDGE_DOCS}
    assert langs == {"python", "javascript", "c", "cpp", "java"}
    for slug in ("python", "javascript", "c", "cpp", "java"):
        count = sum(1 for d in ALL_APPROVED_KNOWLEDGE_DOCS if d.language_slug == slug)
        assert count >= 4, f"Expected >=4 approved RAG docs for {slug}, found {count}"


def test_socratic_fallback_does_not_leak_python_syntax_into_c_or_java() -> None:
    client = SocraticLLMClient(Settings(llm_provider="none"))
    c_diag = MLDiagnosisResponse(
        model_version="rule-multilang-v1",
        diagnosis_source="rule_based",
        language_slug="c",
        predicted_error_code="loop_boundary_error",
        predicted_display_name="Loop Boundary Error",
        confidence=0.82,
        is_low_confidence=False,
        uncertainty_note="",
        top_candidates=[],
    )
    c_reply = client._build_deterministic_reply(
        TutorPromptContext(
            problem_title="Inclusive Range Sum",
            problem_mode="debugging",
            verdict="wrong_answer",
            passed_tests=0,
            total_tests=3,
            stderr_preview="",
            student_code="for (int i = a; i < b; i++) total += i;",
            student_message="",
            diagnosis=c_diag,
            citations=[],
            explanation_language="en",
            learner_level="beginner",
            next_state="giving_hint",
            requested_hint_level=1,
            programming_language="c",
        )
    )
    assert "range(" not in c_reply.guiding_question.lower()
    assert "range(" not in (c_reply.hint_text or "").lower()
    assert (
        "c (gcc)" in (c_reply.hint_text or "").lower() or "loop" in c_reply.guiding_question.lower()
    )

    java_diag = MLDiagnosisResponse(
        model_version="rule-multilang-v1",
        diagnosis_source="rule_based",
        language_slug="java",
        predicted_error_code="indexing_error",
        predicted_display_name="Indexing / Bounds Error",
        confidence=0.9,
        is_low_confidence=False,
        uncertainty_note="",
        top_candidates=[],
    )
    java_reply = client._build_deterministic_reply(
        TutorPromptContext(
            problem_title="Array Bounds",
            problem_mode="debugging",
            verdict="runtime_error",
            passed_tests=0,
            total_tests=3,
            stderr_preview="ArrayIndexOutOfBoundsException",
            student_code="int[] a = new int[3]; System.out.println(a[3]);",
            student_message="",
            diagnosis=java_diag,
            citations=[],
            explanation_language="en",
            learner_level="beginner",
            next_state="giving_hint",
            requested_hint_level=2,
            programming_language="java",
        )
    )
    assert "range(" not in java_reply.guiding_question.lower()
    assert "range(" not in (java_reply.hint_text or "").lower()
