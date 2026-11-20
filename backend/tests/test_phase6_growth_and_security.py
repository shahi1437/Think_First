"""Offline unit & security tests for Phase 6 Learning DNA, Daily Plan, History & Retention."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app
from app.services.growth.dna_service import classify_evidence_band


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
