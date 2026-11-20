"""Live Phase 6 integration test against PostgreSQL, Supabase RLS, and real Judge0.

Verifies:
1. All 5 Phase 6 tables exist with FORCE ROW LEVEL SECURITY enabled.
2. Learning DNA computes 6 factual dimensions from real diagnostic, lesson, Judge0,
   and transfer evidence without fabricating mastery scores.
3. Adaptive Daily Learning Plan generates, updates task status, regenerates new versions,
   and preserves plan history.
4. Persistent Learning History searches and filters real events across categories.
5. Retention Verification enforces >= 24h spacing:
   - Passing early (< 24h) on real Judge0 records `passed_too_early` and does NOT mark `retained`.
   - After >= 24h elapsed, passing on real Judge0 records `retained_verified` and promotes
     the Skill Graph node to `retained`!
6. Strict cross-student isolation via FastAPI (403) and direct PostgREST RLS ([]).
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
    reason="Set RUN_LIVE_INTEGRATION_TESTS=1 with local Supabase + Judge0 Docker stack running.",
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
async def test_live_phase6_tables_and_force_rls() -> None:
    settings = Settings(
        app_env="development",
        database_url=DATABASE_URL,
        supabase_url=SUPABASE_URL,
        judge0_base_url=JUDGE0_BASE_URL,
    )
    db = DatabaseManager(settings)
    try:
        async with db.engine.connect() as conn:
            expected_tables = {
                "learning_dna_snapshots",
                "daily_learning_plans",
                "daily_plan_tasks",
                "retention_schedules",
                "retention_attempts",
            }
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
    finally:
        await db.dispose()


@pytest.mark.asyncio
async def test_live_phase6_dna_daily_plan_history_retention_and_rls() -> None:
    settings = Settings(
        app_env="development",
        database_url=DATABASE_URL,
        supabase_url=SUPABASE_URL,
        supabase_jwt_audience="authenticated",
        judge0_base_url=JUDGE0_BASE_URL,
        llm_provider="none",
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
        async with (
            httpx.AsyncClient(timeout=30.0) as http,
            AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as api,
        ):
            student_a_id, token_a = await _create_user(
                http, f"p6-student-a-{suffix}@thinkfirst.test", "Phase6 Student A"
            )
            _, token_b = await _create_user(
                http, f"p6-student-b-{suffix}@thinkfirst.test", "Phase6 Student B"
            )

            # 1. Fresh student: Learning DNA must report `unobserved` across all 6 dimensions
            dna0 = await api.get(
                "/api/v1/growth/learning-dna",
                headers={"Authorization": f"Bearer {token_a}"},
            )
            assert dna0.status_code == 200, dna0.text
            dna0_data = dna0.json()
            assert len(dna0_data["dimensions"]) == 6
            assert {d["dimension"] for d in dna0_data["dimensions"]} == {
                "tracing",
                "coding",
                "debugging",
                "testing",
                "transfer",
                "retention",
            }
            assert all(d["evidence_band"] == "unobserved" for d in dna0_data["dimensions"])

            # 2. Generate real evidence: complete lesson 1 reading + Judge0 guided exercise
            lessons_list = (
                await api.get(
                    "/api/v1/learning/lessons",
                    headers={"Authorization": f"Bearer {token_a}"},
                )
            ).json()
            intro_lesson = next(
                item for item in lessons_list if item["slug"] == "intro-to-programming"
            )
            intro_id = intro_lesson["lesson_id"]
            lsn_read = await api.post(
                f"/api/v1/learning/lessons/{intro_id}/reading",
                headers={"Authorization": f"Bearer {token_a}"},
                json={"reading_completed": True},
            )
            assert lsn_read.status_code == 200, lsn_read.text
            lsn_ex = await api.post(
                f"/api/v1/learning/lessons/{intro_id}/exercise/run",
                headers={"Authorization": f"Bearer {token_a}"},
                json={"source_code": 'print("CodeMentor")\nprint(6 * 7)\n'},
            )
            assert lsn_ex.status_code == 200, lsn_ex.text
            assert lsn_ex.json()["exercise_passed"] is True

            # Also solve `debug-range-sum-off-by-one` on real Judge0 to unlock transfer & retention
            probs = (
                await api.get(
                    "/api/v1/problems?mode=debugging",
                    headers={"Authorization": f"Bearer {token_a}"},
                )
            ).json()["items"]
            debug_prob = next(p for p in probs if p["slug"] == "debug-range-sum-off-by-one")
            prob_id = debug_prob["problem_id"]
            detail = (
                await api.get(
                    f"/api/v1/problems/{prob_id}",
                    headers={"Authorization": f"Bearer {token_a}"},
                )
            ).json()
            fixed_code = detail["variants"][0]["buggy_starter_code"].replace(
                "range(a, b)", "range(a, b + 1)"
            )
            sub_resp = await api.post(
                "/api/v1/submissions",
                headers={"Authorization": f"Bearer {token_a}"},
                json={
                    "problem_id": prob_id,
                    "language_slug": "python",
                    "submission_kind": "submit",
                    "source_code": fixed_code,
                    "prediction_text": "Buggy range(a, b) skips b.",
                    "explanation_text": "range(a, b + 1) includes upper endpoint b.",
                },
            )
            assert sub_resp.status_code == 200 and sub_resp.json()["verdict"] == "accepted"

            # 3. Learning DNA now reflects real coding, debugging, testing & tracing evidence
            dna1 = await api.get(
                "/api/v1/growth/learning-dna",
                headers={"Authorization": f"Bearer {token_a}"},
            )
            assert dna1.status_code == 200, dna1.text
            dims1 = {d["dimension"]: d for d in dna1.json()["dimensions"]}
            assert dims1["coding"]["evidence_band"] == "verified"
            assert dims1["debugging"]["evidence_band"] == "verified"
            assert dims1["retention"]["evidence_band"] != "verified"

            # 4. Adaptive Daily Plan: generate, complete a task, regenerate v2 & verify history
            plan1 = await api.get(
                "/api/v1/growth/daily-plan",
                headers={"Authorization": f"Bearer {token_a}"},
            )
            assert plan1.status_code == 200, plan1.text
            p1_data = plan1.json()
            assert p1_data["active_plan"]["version_number"] == 1
            assert len(p1_data["active_plan"]["tasks"]) >= 1
            first_task_id = p1_data["active_plan"]["tasks"][0]["id"]

            # Student B cannot modify Student A's daily task
            forbid_task = await api.patch(
                f"/api/v1/growth/daily-plan/tasks/{first_task_id}",
                headers={"Authorization": f"Bearer {token_b}"},
                json={"status": "completed"},
            )
            assert forbid_task.status_code == 403

            done_task = await api.patch(
                f"/api/v1/growth/daily-plan/tasks/{first_task_id}",
                headers={"Authorization": f"Bearer {token_a}"},
                json={"status": "completed"},
            )
            assert done_task.status_code == 200
            assert done_task.json()["completed_tasks"] == 1

            plan2 = await api.post(
                "/api/v1/growth/daily-plan/regenerate",
                headers={"Authorization": f"Bearer {token_a}"},
                json={"available_minutes": 30},
            )
            assert plan2.status_code == 201, plan2.text
            assert plan2.json()["active_plan"]["version_number"] == 2
            assert plan2.json()["active_plan"]["available_minutes"] == 30
            assert len(plan2.json()["history"]) >= 2

            # 5. Retention Verification: auto-scheduled, blocks premature `retained` (<24h),
            #    then promotes to `retained` ONLY once >=24h has elapsed!
            ret_ov = await api.get(
                "/api/v1/growth/retention",
                headers={"Authorization": f"Bearer {token_a}"},
            )
            assert ret_ov.status_code == 200, ret_ov.text
            schedules = ret_ov.json()["schedules"]
            assert len(schedules) >= 1
            # Pick first schedule & link it to `debug-range-sum-off-by-one` for test
            sched_id = schedules[0]["id"]
            sched_skill = schedules[0]["skill_slug"]

            # Ensure schedule points to `debug-range-sum-off-by-one` so our known fix passes Judge0
            async with db_manager.engine.begin() as conn:
                await conn.execute(
                    text("UPDATE public.retention_schedules SET problem_id = :pid WHERE id = :sid"),
                    {"pid": prob_id, "sid": sched_id},
                )

            # Student B cannot submit to Student A's retention schedule
            forbid_ret = await api.post(
                f"/api/v1/growth/retention/{sched_id}/attempts",
                headers={"Authorization": f"Bearer {token_b}"},
                json={
                    "language_slug": "python",
                    "source_code": fixed_code,
                    "student_explanation": "Cross-student attempt should be rejected.",
                },
            )
            assert forbid_ret.status_code == 403

            # Early Judge0 pass (<24h) -> MUST be `passed_too_early`, NOT `retained`
            early_att = await api.post(
                f"/api/v1/growth/retention/{sched_id}/attempts",
                headers={"Authorization": f"Bearer {token_a}"},
                json={
                    "language_slug": "python",
                    "source_code": fixed_code,
                    "student_explanation": (
                        "Included upper endpoint with range(a, b + 1) to sum a..b."
                    ),
                },
            )
            assert early_att.status_code == 201, early_att.text
            assert early_att.json()["verdict"] == "accepted"
            assert early_att.json()["outcome"] == "passed_too_early"

            # Simulate 26h elapsed -> real Judge0 pass grants `retained`
            async with db_manager.engine.begin() as conn:
                await conn.execute(
                    text(
                        "UPDATE public.retention_schedules "
                        "SET source_verified_at = NOW() - INTERVAL '26 hours', "
                        "    due_at = NOW() - INTERVAL '2 hours' "
                        "WHERE id = :sid"
                    ),
                    {"sid": sched_id},
                )
                await conn.execute(
                    text(
                        "UPDATE public.student_skill_states "
                        "SET first_verified_at = NOW() - INTERVAL '26 hours' "
                        "WHERE student_id = :uid AND skill_slug = :skill"
                    ),
                    {"uid": student_a_id, "skill": sched_skill},
                )

            due_att = await api.post(
                f"/api/v1/growth/retention/{sched_id}/attempts",
                headers={"Authorization": f"Bearer {token_a}"},
                json={
                    "language_slug": "python",
                    "source_code": fixed_code,
                    "student_explanation": (
                        "Re-verified after 26 hours using range(a, b + 1) for inclusive sum."
                    ),
                },
            )
            assert due_att.status_code == 201, due_att.text
            assert due_att.json()["outcome"] == "retained_verified"
            assert due_att.json()["elapsed_hours_since_initial"] >= 24.0

            # Verify Skill Graph promoted the skill to `retained`
            sg = (
                await api.get(
                    "/api/v1/learning/skill-graph",
                    headers={"Authorization": f"Bearer {token_a}"},
                )
            ).json()
            promoted = next(n for n in sg["nodes"] if n["slug"] == sched_skill)
            assert promoted["state"] == "retained"

            # 6. Persistent Learning History: search & category filter across real persisted events
            hist_all = await api.get(
                "/api/v1/growth/history",
                headers={"Authorization": f"Bearer {token_a}"},
            )
            assert hist_all.status_code == 200, hist_all.text
            h_data = hist_all.json()
            assert h_data["total"] >= 4
            assert "lesson" in h_data["category_counts"]
            assert "submission" in h_data["category_counts"]
            assert "retention" in h_data["category_counts"]
            assert "daily_plan" in h_data["category_counts"]

            hist_ret = await api.get(
                "/api/v1/growth/history?category=retention&q=retained_verified",
                headers={"Authorization": f"Bearer {token_a}"},
            )
            assert hist_ret.status_code == 200
            assert hist_ret.json()["total"] >= 1

            # 7. Direct PostgREST RLS cross-student isolation on all 5 Phase 6 tables
            for tbl in (
                "learning_dna_snapshots",
                "daily_learning_plans",
                "daily_plan_tasks",
                "retention_schedules",
                "retention_attempts",
            ):
                rls_b = await http.get(
                    f"{SUPABASE_URL}/rest/v1/{tbl}?select=id",
                    headers={"apikey": SUPABASE_ANON_KEY, "Authorization": f"Bearer {token_b}"},
                )
                assert rls_b.status_code == 200 and rls_b.json() == [], tbl
    finally:
        await db_manager.dispose()
