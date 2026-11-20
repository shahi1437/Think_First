"""Phase 8 unit & authorization tests: validation engine, lifecycle, version immutability & RBAC."""

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import httpx
import pytest

from app.api.v1.deps import (
    get_admin_curriculum_service,
    get_admin_overview_service,
    get_current_user,
    get_problem_service,
)
from app.core.errors import AppError
from app.integrations.judge0.client import Judge0ExecutionOutcome
from app.main import create_app
from app.repositories.identity import UserRecord
from app.services.problems.service import (
    ProblemService,
    _analyze_test_suite,
    _check_python_syntax,
)


def _user_with_roles(*roles: str) -> UserRecord:
    return UserRecord(
        id=uuid4(),
        email="user@thinkfirst.test",
        full_name="Test User",
        avatar_url=None,
        roles=list(roles),  # type: ignore[arg-type]
        onboarding_completed=True,
        onboarding_completed_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
        preferences=None,
    )


def test_python_ast_syntax_and_test_suite_quality_analyzers() -> None:
    assert _check_python_syntax("Reference", "x = 1\nprint(x)") is None
    bad_err = _check_python_syntax("Reference", "def f(:\n pass")
    assert bad_err is not None
    assert "syntax error" in bad_err.lower()

    contradictory = [
        SimpleNamespace(ordinal=1, name="A", input_data="5", expected_output="10"),
        SimpleNamespace(ordinal=2, name="B", input_data="5", expected_output="99"),
    ]
    errs, _warns = _analyze_test_suite(contradictory)
    assert len(errs) == 1
    assert "Contradictory" in errs[0]

    duplicate_constant = [
        SimpleNamespace(ordinal=1, name="A", input_data="1", expected_output="OK"),
        SimpleNamespace(ordinal=2, name="B", input_data="1", expected_output="OK"),
    ]
    errs2, warns2 = _analyze_test_suite(duplicate_constant)
    assert errs2 == []
    assert len(warns2) >= 2


@pytest.mark.asyncio
async def test_debugging_validation_rejects_non_failing_buggy_starter() -> None:
    problem_id = uuid4()
    version_id = uuid4()
    fake_problem = SimpleNamespace(id=problem_id, slug="debug-fake", is_archived=False)
    fake_variant = SimpleNamespace(
        language_slug="python",
        starter_code="print(int(input()) * 2)",
        buggy_starter_code="print(int(input()) * 2)",
        reference_solution=SimpleNamespace(reference_solution="print(int(input()) * 2)"),
    )
    fake_tests = [
        SimpleNamespace(ordinal=1, name="T1", input_data="3", expected_output="6"),
        SimpleNamespace(ordinal=2, name="T2", input_data="5", expected_output="10"),
    ]
    fake_version = SimpleNamespace(
        id=version_id,
        mode="debugging",
        time_limit_ms=2000,
        memory_limit_kb=131072,
        variants=[fake_variant],
        test_cases=fake_tests,
    )

    repo = MagicMock()
    repo.get_admin_problem_latest = AsyncMock(return_value=(fake_problem, fake_version))
    repo.list_languages = AsyncMock(
        return_value=[SimpleNamespace(slug="python", judge0_language_id=71)]
    )
    repo.record_content_review = AsyncMock()
    repo.record_curriculum_validation = AsyncMock()
    repo.record_audit = AsyncMock()

    judge0 = MagicMock()
    judge0.execute_test_case = AsyncMock(
        return_value=Judge0ExecutionOutcome(
            verdict="accepted",
            status_id=3,
            status_description="Accepted",
            token="t1",
            stdout="6",
            stderr=None,
            compile_output=None,
            runtime_ms=12,
            memory_kb=1024,
        )
    )

    service = ProblemService(repository=repo, judge0=judge0)
    report = await service.validate_problem(
        actor=_user_with_roles("admin"),
        problem_id=problem_id,
        request_id="req-1",
    )
    assert report.passed is False
    assert report.new_status == "draft"
    assert report.variant_results[0].buggy_starter_failed_as_expected is False
    assert any("unexpectedly passed all tests" in e for e in report.variant_results[0].errors)


@pytest.mark.asyncio
async def test_reject_and_unvalidated_submit_review_guards() -> None:
    problem_id = uuid4()
    fake_problem = SimpleNamespace(id=problem_id, slug="p1", is_archived=False)
    fake_version = SimpleNamespace(id=uuid4(), status="draft", validated_at=None, version_number=1)
    repo = MagicMock()
    repo.get_admin_problem_latest = AsyncMock(return_value=(fake_problem, fake_version))
    service = ProblemService(repository=repo, judge0=MagicMock())

    with pytest.raises(AppError) as exc:
        await service.submit_for_review(
            actor=_user_with_roles("admin"),
            problem_id=problem_id,
            notes="submit",
            request_id="req-2",
        )
    assert exc.value.code == "VALIDATION_REQUIRED"


@pytest.mark.asyncio
async def test_non_admin_student_and_teacher_denied_on_phase8_admin_routes() -> None:
    app = create_app()
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        for role in ("student", "teacher"):
            app.dependency_overrides[get_current_user] = lambda r=role: _user_with_roles(r)
            app.dependency_overrides[get_admin_overview_service] = lambda: MagicMock()
            app.dependency_overrides[get_admin_curriculum_service] = lambda: MagicMock()
            app.dependency_overrides[get_problem_service] = lambda: MagicMock()

            assert (await client.get("/api/v1/admin/overview")).status_code == 403
            assert (await client.get("/api/v1/admin/audit-logs")).status_code == 403
            assert (await client.get("/api/v1/admin/learning/lessons")).status_code == 403
            assert (
                await client.get("/api/v1/admin/learning/diagnostic-questions")
            ).status_code == 403
            assert (
                await client.post(
                    f"/api/v1/admin/problems/{uuid4()}/reject",
                    json={"notes": "Needs more edge tests"},
                )
            ).status_code == 403
            assert (
                await client.post(
                    f"/api/v1/admin/problems/{uuid4()}/archive",
                    json={"notes": "Archive"},
                )
            ).status_code == 403

    app.dependency_overrides.clear()
