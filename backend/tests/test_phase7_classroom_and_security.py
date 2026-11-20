"""Offline unit & security tests for Phase 7 Classrooms, Assignments, Deadlines & RBAC."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app
from app.services.classroom.assignment_service import evaluate_submission_eligibility
from app.services.classroom.course_service import generate_invite_code, hash_invite_code


def test_invite_code_generation_has_high_entropy_and_deterministic_hash() -> None:
    codes = {generate_invite_code() for _ in range(30)}
    assert len(codes) == 30
    sample = next(iter(codes))
    assert sample.startswith("CM-") and len(sample) == 14
    assert hash_invite_code(sample) == hash_invite_code(f"  {sample.lower()}  ")


def test_server_side_deadline_attempts_and_revision_eligibility() -> None:
    now = datetime.now(UTC)
    past = now - timedelta(hours=2)
    future = now + timedelta(hours=4)

    # Past deadline with late disabled -> blocked
    asg_closed = SimpleNamespace(
        status="published",
        opens_at=None,
        due_at=past,
        allow_late_submissions=False,
        max_attempts=3,
        allow_resubmission_on_revision=True,
    )
    ok, reason, is_late = evaluate_submission_eligibility(
        assignment=asg_closed, submission=None, now=now
    )
    assert ok is False and is_late is True and reason is not None

    # Past deadline with revision requested -> resubmission permitted
    rev_sub = SimpleNamespace(status="revision_requested", attempts_used=3)
    ok2, reason2, _ = evaluate_submission_eligibility(
        assignment=asg_closed, submission=rev_sub, now=now
    )
    assert ok2 is True and reason2 is None

    # Open assignment with max attempts exhausted -> blocked
    asg_open = SimpleNamespace(
        status="published",
        opens_at=None,
        due_at=future,
        allow_late_submissions=False,
        max_attempts=2,
        allow_resubmission_on_revision=True,
    )
    maxed_sub = SimpleNamespace(status="submitted", attempts_used=2)
    ok3, reason3, _ = evaluate_submission_eligibility(
        assignment=asg_open, submission=maxed_sub, now=now
    )
    assert ok3 is False and reason3 is not None


@pytest.mark.asyncio
async def test_phase7_teacher_and_student_routes_require_authentication() -> None:
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        for method, path in (
            ("GET", "/api/v1/teacher/dashboard"),
            ("GET", "/api/v1/teacher/classes"),
            ("POST", "/api/v1/teacher/classes"),
            ("GET", "/api/v1/teacher/assignments"),
            ("GET", "/api/v1/student/classes"),
            ("POST", "/api/v1/student/classes/join"),
            ("GET", "/api/v1/student/assignments"),
        ):
            resp = await client.request(method, path, json={} if method == "POST" else None)
            assert resp.status_code == 401, f"{method} {path} returned {resp.status_code}"
