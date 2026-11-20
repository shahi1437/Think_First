"""Phase 5 offline unit, diagnostic placement, Skill Graph invariant, and security tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1.deps import get_current_user
from app.core.config import Settings
from app.main import create_app
from app.repositories.identity import PreferencesRecord, UserRecord
from app.services.learning.diagnostics_service import (
    ALL_EIGHT_DOMAINS,
    _summarize_domain_evidence,
    _to_public_question,
)
from app.services.learning.skill_graph import SkillGraphService


def _make_user(role: str = "student") -> UserRecord:
    uid = uuid4()
    now = datetime.now(UTC)
    return UserRecord(
        id=uid,
        email=f"{role}-{uid.hex[:6]}@thinkfirst.edu",
        full_name="Phase 5 Tester",
        avatar_url=None,
        roles=[role],  # type: ignore[list-item]
        onboarding_completed=True,
        onboarding_completed_at=now,
        created_at=now,
        preferences=PreferencesRecord(
            user_id=uid,
            programming_experience="beginner",
            preferred_language="python",
            learning_goal="university_coursework",
            daily_practice_minutes=30,
            preferred_explanation_language="en",
            starting_preference="diagnostic_assessment",
            recommended_entry_track="diagnostic_assessment",
        ),
    )


def test_diagnostic_evidence_recommends_four_tracks_deterministically() -> None:
    # Case 1: Heavy gaps -> absolute_beginner
    sess_beg = SimpleNamespace(
        responses=[
            SimpleNamespace(
                domain_slug=d, is_correct=(i < 1), difficulty="core", question_type="mcq"
            )
            for i, d in enumerate(ALL_EIGHT_DOMAINS)
        ]
    )
    ev1, track1, rat1 = _summarize_domain_evidence(sess_beg)  # type: ignore[arg-type]
    assert len(ev1) == 8
    assert track1 == "absolute_beginner"
    assert "Absolute Beginner" in rat1

    # Case 2: 4/8 demonstrated -> basic_university
    sess_basic = SimpleNamespace(
        responses=[
            SimpleNamespace(
                domain_slug=d, is_correct=(i < 4), difficulty="core", question_type="mcq"
            )
            for i, d in enumerate(ALL_EIGHT_DOMAINS)
        ]
    )
    _, track2, _ = _summarize_domain_evidence(sess_basic)  # type: ignore[arg-type]
    assert track2 == "basic_university"

    # Case 3: 6/8 MCQ demonstrated (no stretch execution) -> intermediate
    sess_int = SimpleNamespace(
        responses=[
            SimpleNamespace(
                domain_slug=d, is_correct=(i < 6), difficulty="core", question_type="mcq"
            )
            for i, d in enumerate(ALL_EIGHT_DOMAINS)
        ]
    )
    _, track3, _ = _summarize_domain_evidence(sess_int)  # type: ignore[arg-type]
    assert track3 == "intermediate"

    # Case 4: 8/8 demonstrated INCLUDING real Judge0 stretch execution -> advanced
    sess_adv = SimpleNamespace(
        responses=[
            SimpleNamespace(domain_slug=d, is_correct=True, difficulty="core", question_type="mcq")
            for d in ALL_EIGHT_DOMAINS
        ]
        + [
            SimpleNamespace(
                domain_slug="loop_boundaries",
                is_correct=True,
                difficulty="stretch",
                question_type="code_execution",
            )
        ]
    )
    _, track4, _ = _summarize_domain_evidence(sess_adv)  # type: ignore[arg-type]
    assert track4 == "advanced"


def test_public_diagnostic_question_never_leaks_private_answer_key() -> None:
    q = SimpleNamespace(
        id=uuid4(),
        slug="diag-var-core-1",
        domain_slug="variables",
        skill_slug="variables",
        difficulty="core",
        question_type="mcq",
        prompt_en="Prompt EN",
        prompt_bn="Prompt BN",
        code_snippet="x = 1",
        options=[{"id": "a", "text_en": "A", "text_bn": "ক"}],
        starter_code=None,
        language_slug="python",
        answer_key=SimpleNamespace(
            correct_option_id="a",
            evaluation_tests=[{"input_data": "secret", "expected_output": "42"}],
        ),
    )
    pub = _to_public_question(q)  # type: ignore[arg-type]
    dumped = pub.model_dump()
    assert "correct_option_id" not in dumped
    assert "evaluation_tests" not in dumped
    assert "secret" not in str(dumped)


@pytest.mark.asyncio
async def test_skill_graph_blocks_premature_retained_and_tracks_honest_states() -> None:
    class StubLearningRepo:
        def __init__(self) -> None:
            self.states: dict[str, Any] = {}
            self.transitions: list[dict[str, Any]] = []

        async def get_student_skill_state(self, *, student_id: UUID, skill_slug: str) -> Any | None:
            _ = student_id
            return self.states.get(skill_slug)

        async def upsert_skill_state(self, **kwargs: Any) -> Any:
            slug = kwargs["skill_slug"]
            prev = self.states.get(slug)
            now = datetime.now(UTC)
            first_v = prev.first_verified_at if prev else (now if kwargs["mark_verified"] else None)
            row = SimpleNamespace(
                skill_slug=slug,
                state=kwargs["new_state"],
                evidence_count=(prev.evidence_count + 1) if prev else 1,
                uncertainty_note=kwargs["uncertainty_note"],
                first_verified_at=first_v,
            )
            self.states[slug] = row
            self.transitions.append(
                {"to": kwargs["new_state"], "source": kwargs["evidence_source"]}
            )
            return row

    repo = StubLearningRepo()
    svc = SkillGraphService(
        learning_repo=repo,  # type: ignore[arg-type]
        mentor_repo=SimpleNamespace(),  # type: ignore[arg-type]
        problem_repo=SimpleNamespace(),  # type: ignore[arg-type]
    )
    uid = uuid4()

    # 1. Reading only -> introduced (NOT mastery)
    s1 = await svc.record_evidence(
        student_id=uid,
        skill_slug="loops",
        target_state="introduced",
        evidence_source="lesson_reading",
        evidence_ref_id="l1",
        reason="Read lesson",
        uncertainty_note="Reading only",
    )
    assert s1 == "introduced"

    # 2. Attempting to claim retained immediately MUST NOT succeed
    s_premature = await svc.record_evidence(
        student_id=uid,
        skill_slug="loops",
        target_state="retained",
        evidence_source="premature_attempt",
        evidence_ref_id="x",
        reason="Too early",
        uncertainty_note="Should stay introduced",
    )
    assert s_premature == "introduced"

    # 3. Transferred verified now, then re-verified >= 24h later -> retained!
    s_tr = await svc.record_evidence(
        student_id=uid,
        skill_slug="loops",
        target_state="transferred",
        evidence_source="phase4_transfer_verification",
        evidence_ref_id="att1",
        reason="Passed unseen transfer",
        uncertainty_note="Transfer verified",
    )
    assert s_tr == "transferred"

    # Simulate 25 hours elapsed since first verification
    repo.states["loops"].first_verified_at = datetime.now(UTC) - timedelta(hours=25)
    s_ret = await svc.record_evidence(
        student_id=uid,
        skill_slug="loops",
        target_state="independent",
        evidence_source="delayed_reverification",
        evidence_ref_id="att2",
        reason="Re-verified next day",
        uncertainty_note="Retained",
    )
    assert s_ret == "retained"


@pytest.mark.asyncio
async def test_phase5_auth_and_admin_rbac_guards() -> None:
    app = create_app(settings=Settings(app_env="test"))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        assert (await client.get("/api/v1/learning/dashboard")).status_code == 401
        assert (await client.get("/api/v1/learning/lessons")).status_code == 401
        assert (
            await client.post("/api/v1/learning/diagnostics/sessions", json={})
        ).status_code == 401
        assert (await client.get("/api/v1/learning/skill-graph")).status_code == 401
        assert (await client.post("/api/v1/admin/learning/lessons", json={})).status_code == 401

    # Authenticated student MUST get 403 on Admin Phase 5 publishing endpoints
    student = _make_user(role="student")
    app.dependency_overrides[get_current_user] = lambda: student
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp_lesson = await client.post("/api/v1/admin/learning/lessons", json={})
        assert resp_lesson.status_code == 403
        resp_q = await client.post("/api/v1/admin/learning/diagnostic-questions", json={})
        assert resp_q.status_code == 403
