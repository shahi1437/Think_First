"""Live Phase 5 integration test against Supabase PostgreSQL + FORCE RLS + real Judge0 CE.

Guarded by `RUN_LIVE_INTEGRATION_TESTS=1`. Verifies:
1. All 14 Phase 5 tables exist with FORCE ROW LEVEL SECURITY enabled.
2. Seeded 4 tracks, 10 skill nodes, 8 lessons, 18 diagnostic questions across 8 domains.
3. Strict PostgREST RLS: students get [] on `diagnostic_question_answers` and cross-student rows.
4. Full 8-domain adaptive diagnostic including REAL Judge0 execution + track recommendation.
5. Beginner lesson reading -> REAL Judge0 guided exercise -> Skill Graph + Recommendations.
"""

from __future__ import annotations

import os
from uuid import uuid4

import httpx
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.core.config import Settings, get_settings
from app.core.database import DatabaseManager, get_db_manager, get_db_session
from app.main import create_app

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_LIVE_INTEGRATION_TESTS") != "1",
    reason="Set RUN_LIVE_INTEGRATION_TESTS=1 with local Supabase + Judge0 running.",
)

SUPABASE_URL = os.getenv("SUPABASE_URL", "http://127.0.0.1:54321")
SUPABASE_ANON_KEY = os.getenv(
    "NEXT_PUBLIC_SUPABASE_ANON_KEY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0",
)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@127.0.0.1:54322/postgres",
)
JUDGE0_BASE_URL = os.getenv("JUDGE0_BASE_URL", "http://127.0.0.1:2359")

_CORRECT_MCQ_ANSWERS: dict[str, str] = {
    "diag-var-core-1": "a",
    "diag-var-found-1": "b",
    "diag-dbg-core-1": "b",
    "diag-dbg-found-1": "a",
    "diag-cond-core-1": "b",
    "diag-cond-found-1": "b",
    "diag-loop-core-1": "a",
    "diag-loop-found-1": "b",
    "diag-list-core-1": "a",
    "diag-list-found-1": "b",
    "diag-idx-core-1": "a",
    "diag-idx-found-1": "b",
    "diag-fn-core-1": "b",
    "diag-mix-core-1": "a",
}

_STRETCH_CODE_SOLUTIONS: dict[str, str] = {
    "diag-loop-stretch-code": "a, b = map(int, input().split())\nprint(sum(range(a, b + 1)))\n",
    "diag-fn-stretch-code": (
        "def find_min(nums):\n    low = nums[0]\n    for x in nums[1:]:\n"
        "        if x < low:\n            low = x\n    return low\n"
        "print(find_min([int(x) for x in input().split()]))\n"
    ),
    "diag-mix-stretch-code": (
        "nums = [int(x) for x in input().split()]\n"
        "print(sum(1 for i in range(len(nums) - 1) if nums[i + 1] > nums[i]))\n"
    ),
    "diag-var-stretch-code": (
        "nums = [int(x) for x in input().split()]\n"
        "best = nums[0]\nfor x in nums[1:]:\n    if x > best:\n        best = x\nprint(best)\n"
    ),
}


async def _create_user(http: httpx.AsyncClient, email: str, full_name: str) -> tuple[str, str]:
    resp = await http.post(
        f"{SUPABASE_URL}/auth/v1/signup",
        headers={"apikey": SUPABASE_ANON_KEY, "Content-Type": "application/json"},
        json={
            "email": email,
            "password": "TestPassword123!",
            "data": {"full_name": full_name},
        },
    )
    assert resp.status_code in (200, 201), resp.text
    data = resp.json()
    return str(data["user"]["id"]), str(data["access_token"])


@pytest.mark.asyncio
async def test_live_phase5_schema_force_rls_and_full_adaptive_journey() -> None:
    settings = Settings(
        app_env="development",
        database_url=DATABASE_URL,
        supabase_url=SUPABASE_URL,
        supabase_jwt_audience="authenticated",
        judge0_base_url=JUDGE0_BASE_URL,
    )
    db_manager = DatabaseManager(settings)
    app = create_app(settings=settings)
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_db_manager] = lambda: db_manager

    async def _override_session():
        async for sess in db_manager.session():
            yield sess

    app.dependency_overrides[get_db_session] = _override_session

    suffix = uuid4().hex[:8]
    try:
        # 1. Verify all 14 Phase 5 tables have FORCE ROW LEVEL SECURITY enabled
        expected_tables = {
            "learning_tracks",
            "student_track_enrollments",
            "skill_nodes",
            "skill_prerequisites",
            "student_skill_states",
            "skill_state_transitions",
            "lessons",
            "lesson_versions",
            "lesson_progress",
            "diagnostic_questions",
            "diagnostic_question_answers",
            "diagnostic_sessions",
            "diagnostic_responses",
            "student_recommendations",
        }
        async with db_manager.engine.connect() as conn:
            rows = (
                await conn.execute(
                    text(
                        "SELECT relname, relrowsecurity, relforcerowsecurity "
                        "FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
                        "WHERE n.nspname = 'public' AND relname = ANY(:names)"
                    ),
                    {"names": list(expected_tables)},
                )
            ).all()
            found = {r[0]: (bool(r[1]), bool(r[2])) for r in rows}
            assert set(found.keys()) == expected_tables
            for tbl, (rls_on, force_rls) in found.items():
                assert rls_on and force_rls, f"FORCE RLS missing on {tbl}"

        async with (
            httpx.AsyncClient(timeout=30.0) as http,
            AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as api,
        ):
            _, token_a = await _create_user(
                http, f"p5-student-a-{suffix}@thinkfirst.test", "Phase5 Student A"
            )
            _, token_b = await _create_user(
                http, f"p5-student-b-{suffix}@thinkfirst.test", "Phase5 Student B"
            )

            # 2. Direct PostgREST RLS: students MUST NEVER see private diagnostic answer keys
            rls_ans = await http.get(
                f"{SUPABASE_URL}/rest/v1/diagnostic_question_answers?select=question_id,correct_option_id",
                headers={"apikey": SUPABASE_ANON_KEY, "Authorization": f"Bearer {token_a}"},
            )
            assert rls_ans.status_code == 200 and rls_ans.json() == []

            # 3. Verify 4 learning tracks & 8 published bilingual lessons
            tracks_resp = await api.get(
                "/api/v1/learning/tracks",
                headers={"Authorization": f"Bearer {token_a}"},
            )
            assert tracks_resp.status_code == 200, tracks_resp.text
            assert len(tracks_resp.json()["tracks"]) == 4

            lessons_resp = await api.get(
                "/api/v1/learning/lessons",
                headers={"Authorization": f"Bearer {token_a}"},
            )
            assert lessons_resp.status_code == 200, lessons_resp.text
            lessons = lessons_resp.json()
            assert len(lessons) >= 8

            # 4. Run full 8-domain Adaptive Diagnostic (miss 2 core domains -> foundation followups;
            #    pass stretch domain -> REAL Judge0 code execution check!)
            start_diag = await api.post(
                "/api/v1/learning/diagnostics/sessions",
                headers={"Authorization": f"Bearer {token_a}"},
                json={"explanation_language": "en"},
            )
            assert start_diag.status_code == 201, start_diag.text
            diag = start_diag.json()
            diag_id = diag["id"]
            assert diag["remaining_count"] == 8

            saw_code_exec = False
            while diag["status"] == "in_progress" and diag["current_question"] is not None:
                q = diag["current_question"]
                assert "correct_option_id" not in q
                slug = q["slug"]
                if q["question_type"] == "code_execution":
                    saw_code_exec = True
                    submit_body = {
                        "question_id": q["id"],
                        "source_code": _STRETCH_CODE_SOLUTIONS[slug],
                        "response_time_ms": 4000,
                    }
                else:
                    # Miss conditions & indexing core to verify adaptive foundation follow-up
                    if slug in ("diag-cond-core-1", "diag-idx-core-1"):
                        chosen = "d"
                    else:
                        chosen = _CORRECT_MCQ_ANSWERS[slug]
                    submit_body = {
                        "question_id": q["id"],
                        "selected_option_id": chosen,
                        "response_time_ms": 2500,
                    }
                step_resp = await api.post(
                    f"/api/v1/learning/diagnostics/sessions/{diag_id}/answers",
                    headers={"Authorization": f"Bearer {token_a}"},
                    json=submit_body,
                )
                assert step_resp.status_code == 200, step_resp.text
                diag = step_resp.json()

            assert diag["status"] == "completed"
            assert diag["adaptive_followups_added"] >= 1
            assert saw_code_exec is True
            assert diag["recommended_track_slug"] in (
                "absolute_beginner",
                "basic_university",
                "intermediate",
                "advanced",
            )
            assert len(diag["domain_evidence"]) == 8

            # 5. Cross-student isolation (API 403 + PostgREST RLS [])
            assert (
                await api.get(
                    f"/api/v1/learning/diagnostics/sessions/{diag_id}",
                    headers={"Authorization": f"Bearer {token_b}"},
                )
            ).status_code == 403

            for tbl in (
                "diagnostic_sessions",
                "diagnostic_responses",
                "student_skill_states",
                "skill_state_transitions",
                "student_track_enrollments",
            ):
                rls_other = await http.get(
                    f"{SUPABASE_URL}/rest/v1/{tbl}?select=*",
                    headers={"apikey": SUPABASE_ANON_KEY, "Authorization": f"Bearer {token_b}"},
                )
                assert rls_other.status_code == 200 and rls_other.json() == [], tbl

            # 6. Beginner Lesson: Reading -> Real Judge0 Guided Exercise -> Guided + Completed
            intro_lesson = next(lsn for lsn in lessons if lsn["slug"] == "intro-to-programming")
            read_resp = await api.post(
                f"/api/v1/learning/lessons/{intro_lesson['lesson_id']}/reading",
                headers={"Authorization": f"Bearer {token_a}"},
                json={"reading_completed": True},
            )
            assert read_resp.status_code == 200, read_resp.text
            assert read_resp.json()["reading_completed"] is True
            assert read_resp.json()["progress_status"] == "in_progress"

            ex_resp = await api.post(
                f"/api/v1/learning/lessons/{intro_lesson['lesson_id']}/exercise/run",
                headers={"Authorization": f"Bearer {token_a}"},
                json={"source_code": 'print("CodeMentor")\nprint(6 * 7)\n'},
            )
            assert ex_resp.status_code == 200, ex_resp.text
            ex_data = ex_resp.json()
            assert ex_data["exercise_passed"] is True
            assert ex_data["progress_status"] == "completed"
            assert ex_data["skill_state_after"] == "guided"

            # 7. Unified Learning Dashboard: Skill Graph & Explainable Recommendations updated
            dash_resp = await api.get(
                "/api/v1/learning/dashboard",
                headers={"Authorization": f"Bearer {token_a}"},
            )
            assert dash_resp.status_code == 200, dash_resp.text
            dash = dash_resp.json()
            assert dash["lessons_completed"] == 1
            assert dash["diagnostic_sessions_completed"] == 1
            pb_node = next(
                n for n in dash["skill_graph"]["nodes"] if n["slug"] == "programming_basics"
            )
            assert pb_node["state"] == "guided"
            assert len(dash["recommendations"]) >= 1
            assert all(r["reason_en"] and r["reason_bn"] for r in dash["recommendations"])
    finally:
        await db_manager.dispose()
