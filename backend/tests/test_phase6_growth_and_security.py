"""Offline unit & security tests for Phase 6 Learning DNA, Daily Plan, History & Retention."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app
from app.services.growth.daily_plan_service import _format_task_title
from app.services.growth.dna_service import classify_evidence_band


def test_daily_plan_task_title_never_duplicates_debug_or_transfer_prefix() -> None:
    assert (
        _format_task_title("Debug", "Debug: Inclusive Range Sum", strip_prefixes=("Debug",))
        == "Debug: Inclusive Range Sum"
    )
    assert (
        _format_task_title("Debug", "Debug: Debug: Loop Boundary Bug", strip_prefixes=("Debug",))
        == "Debug: Loop Boundary Bug"
    )
    assert (
        _format_task_title("Solve", "Sum of Even Numbers", strip_prefixes=("Debug", "Solve"))
        == "Solve: Sum of Even Numbers"
    )
    assert (
        _format_task_title(
            "Transfer Check",
            "Transfer: Step Range Sum",
            strip_prefixes=("Transfer",),
        )
        == "Transfer Check: Step Range Sum"
    )
    assert (
        _format_task_title(
            "ডিবাগ অনুশীলন",
            "Debug: Maximum Value in Any Integer List",
            strip_prefixes=("Debug", "Solve"),
        )
        == "ডিবাগ অনুশীলন: Maximum Value in Any Integer List"
    )


def test_dna_evidence_band_never_fabricates_mastery_from_zero_evidence() -> None:
    assert (
        classify_evidence_band(evidence_count=0, verified_count=0, developing_count=0)
        == "unobserved"
    )
    assert (
        classify_evidence_band(evidence_count=1, verified_count=0, developing_count=0) == "emerging"
    )
    assert (
        classify_evidence_band(evidence_count=2, verified_count=0, developing_count=1)
        == "developing"
    )
    assert (
        classify_evidence_band(evidence_count=4, verified_count=0, developing_count=0)
        == "developing"
    )
    assert (
        classify_evidence_band(evidence_count=1, verified_count=1, developing_count=0) == "verified"
    )


@pytest.mark.asyncio
async def test_phase6_routes_require_authentication() -> None:
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        for method, path in (
            ("GET", "/api/v1/growth/learning-dna"),
            ("GET", "/api/v1/growth/daily-plan"),
            ("POST", "/api/v1/growth/daily-plan/regenerate"),
            ("GET", "/api/v1/growth/history"),
            ("GET", "/api/v1/growth/retention"),
        ):
            resp = await client.request(
                method,
                path,
                json={"available_minutes": 45} if method == "POST" else None,
            )
            assert resp.status_code == 401, f"{method} {path} returned {resp.status_code}"
