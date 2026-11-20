"""Live PostgreSQL + Supabase Auth + Judge0 E2E tests for Phase 8 Admin Studio & Curriculum."""

from __future__ import annotations

import os
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import text

from app.core.config import Settings, get_settings
from app.core.database import DatabaseManager, get_db_manager, get_db_session
from app.main import create_app

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_LIVE_INTEGRATION_TESTS") != "1",
    reason="Set RUN_LIVE_INTEGRATION_TESTS=1 with local Supabase + Judge0 running",
)

SUPABASE_URL = os.getenv("SUPABASE_URL", "http://127.0.0.1:54321")
SUPABASE_ANON_KEY = os.getenv(
    "NEXT_PUBLIC_SUPABASE_ANON_KEY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9."
    "CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0",
)


async def _signup(client: httpx.AsyncClient, email: str, full_name: str) -> tuple[str, str]:
    resp = await client.post(
        f"{SUPABASE_URL}/auth/v1/signup",
        json={
            "email": email,
            "password": "TestPassword123!",
            "data": {"full_name": full_name},
        },
        headers={"apikey": SUPABASE_ANON_KEY},
    )
    assert resp.status_code in (200, 201), resp.text
    payload = resp.json()
    return payload["user"]["id"], payload["access_token"]


@pytest.mark.asyncio
async def test_phase8_live_admin_lifecycle_immutability_and_curriculum_counts() -> None:
    base_settings = get_settings()
    settings = Settings(
        database_url=os.getenv(
            "DATABASE_URL",
            "postgresql+asyncpg://postgres:postgres@127.0.0.1:54322/postgres",
        ),
        supabase_url=SUPABASE_URL,
        judge0_base_url=base_settings.judge0_base_url,
        app_env="test",
    )
    app = create_app(settings)
    db_manager = DatabaseManager(settings)

    async def _override_db():
        async for sess in db_manager.session():
            yield sess

    app.dependency_overrides[get_db_manager] = lambda: db_manager
    app.dependency_overrides[get_db_session] = _override_db
    app.dependency_overrides[get_settings] = lambda: settings

    suffix = uuid4().hex[:8]
    admin_email = f"p8-admin-{suffix}@thinkfirst.test"
    student_email = f"p8-student-{suffix}@thinkfirst.test"
    teacher_email = f"p8-teacher-{suffix}@thinkfirst.test"

    async with httpx.AsyncClient(timeout=20.0) as auth_client:
        admin_id, admin_token = await _signup(auth_client, admin_email, "Phase 8 Admin")
        student_id, student_token = await _signup(auth_client, student_email, "Phase 8 Student")
        teacher_id, teacher_token = await _signup(auth_client, teacher_email, "Phase 8 Teacher")

    async for sess in db_manager.session():
        await sess.execute(
            text(
                "INSERT INTO public.user_roles (user_id, role, granted_by) "
                "VALUES (:aid, 'admin', :aid), (:tid, 'teacher', :aid) "
                "ON CONFLICT DO NOTHING"
            ),
            {"aid": admin_id, "tid": teacher_id},
        )
        rls_rows = (
            await sess.execute(
                text(
                    "SELECT relrowsecurity, relforcerowsecurity "
                    "FROM pg_class WHERE relname = 'curriculum_validations'"
                )
            )
        ).first()
        assert rls_rows is not None
        assert bool(rls_rows[0]) and bool(rls_rows[1])
        await sess.commit()
        break

    transport = httpx.ASGITransport(app=app)
    try:
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver", timeout=40.0
        ) as api:
            # 1. Verify Student & Teacher are blocked from Admin routes
            for tok in (student_token, teacher_token):
                r1 = await api.get(
                    "/api/v1/admin/overview",
                    headers={"Authorization": f"Bearer {tok}"},
                )
                assert r1.status_code == 403
                r2 = await api.get(
                    "/api/v1/admin/audit-logs",
                    headers={"Authorization": f"Bearer {tok}"},
                )
                assert r2.status_code == 403

            # 2. Verify live Admin Overview reflects expanded curriculum
            ov_resp = await api.get(
                "/api/v1/admin/overview",
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            assert ov_resp.status_code == 200, ov_resp.text
            ov = ov_resp.json()
            assert ov["lessons_published"] >= 24
            assert ov["problems_intermediate_or_advanced"] >= 12
            assert ov["diagnostic_stretch_count"] >= 8
            assert ov["skill_nodes_count"] >= 18

            # 3. Draft -> Judge0 Validate -> Reject -> Revalidate -> Review -> Approve -> Publish
            slug = f"p8-live-{suffix}"
            starter_buggy = "a, b = map(int, input().split())\nprint(a * a + b * b)\n"
            ref_sol = "a, b = map(int, input().split())\nprint(a * a - b * b)\n"

            create_resp = await api.post(
                "/api/v1/admin/problems",
                headers={"Authorization": f"Bearer {admin_token}"},
                json={
                    "slug": slug,
                    "title": "Phase 8 Live Square Difference",
                    "statement_md": "Read a and b, print a*a - b*b.",
                    "difficulty": "intermediate",
                    "track_slug": "intermediate",
                    "mode": "debugging",
                    "topics": ["math", "debugging"],
                    "skills": ["debugging_basics"],
                    "prerequisites": ["variables"],
                    "variants": [
                        {
                            "language_slug": "python",
                            "starter_code": starter_buggy,
                            "buggy_starter_code": starter_buggy,
                            "debugging_prompt": "Fix the operator sign.",
                            "reference_solution": ref_sol,
                            "expected_failure_category": "wrong_answer",
                        }
                    ],
                    "test_cases": [
                        {
                            "ordinal": 1,
                            "name": "Public case",
                            "input_data": "5 3",
                            "expected_output": "16",
                            "is_hidden": False,
                        },
                        {
                            "ordinal": 2,
                            "name": "Hidden negative",
                            "input_data": "-4 2",
                            "expected_output": "12",
                            "is_hidden": True,
                        },
                    ],
                },
            )
            assert create_resp.status_code == 201, create_resp.text
            pid = create_resp.json()["problem_id"]

            val_resp = await api.post(
                f"/api/v1/admin/problems/{pid}/validate",
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            assert val_resp.status_code == 200, val_resp.text
            assert val_resp.json()["passed"] is True
            assert val_resp.json()["variant_results"][0]["buggy_starter_failed_as_expected"] is True

            # Reject with feedback -> Draft
            rej_resp = await api.post(
                f"/api/v1/admin/problems/{pid}/reject",
                headers={"Authorization": f"Bearer {admin_token}"},
                json={"notes": "Testing reviewer rejection loop cleanly."},
            )
            assert rej_resp.status_code == 200
            assert rej_resp.json()["status"] == "draft"

            # Re-validate -> Submit Review -> Approve -> Publish v1
            assert (
                await api.post(
                    f"/api/v1/admin/problems/{pid}/validate",
                    headers={"Authorization": f"Bearer {admin_token}"},
                )
            ).status_code == 200
            assert (
                await api.post(
                    f"/api/v1/admin/problems/{pid}/submit-review",
                    headers={"Authorization": f"Bearer {admin_token}"},
                    json={"notes": "Ready for review"},
                )
            ).json()["status"] == "in_review"
            assert (
                await api.post(
                    f"/api/v1/admin/problems/{pid}/approve",
                    headers={"Authorization": f"Bearer {admin_token}"},
                    json={"notes": "Approved"},
                )
            ).json()["status"] == "approved"
            pub_v1 = (
                await api.post(
                    f"/api/v1/admin/problems/{pid}/publish",
                    headers={"Authorization": f"Bearer {admin_token}"},
                    json={"notes": "Published v1"},
                )
            ).json()
            assert pub_v1["status"] == "published"
            v1_id = pub_v1["version_id"]

            # 4. Teacher pins v1; Admin branches v2; assignment MUST retain v1
            cls_resp = await api.post(
                "/api/v1/teacher/classes",
                headers={"Authorization": f"Bearer {teacher_token}"},
                json={"code": f"P8-{suffix[:4]}", "title": "P8 Version Compatibility"},
            )
            assert cls_resp.status_code == 201
            cid = cls_resp.json()["id"]
            asg_resp = await api.post(
                "/api/v1/teacher/assignments",
                headers={"Authorization": f"Bearer {teacher_token}"},
                json={
                    "course_id": cid,
                    "title": "Pinned v1 Compatibility Check",
                    "publish_now": True,
                    "problems": [{"problem_id": pid, "points": 50}],
                },
            )
            assert asg_resp.status_code == 201, asg_resp.text
            asg_id = asg_resp.json()["id"]

            patch_v2 = await api.patch(
                f"/api/v1/admin/problems/{pid}",
                headers={"Authorization": f"Bearer {admin_token}"},
                json={
                    "title": "Phase 8 Live Square Difference (v2)",
                    "statement_md": "Updated statement v2 for testing immutability.",
                    "difficulty": "intermediate",
                    "track_slug": "intermediate",
                    "mode": "debugging",
                    "topics": ["math"],
                    "skills": ["debugging_basics"],
                    "prerequisites": ["variables"],
                    "variants": [
                        {
                            "language_slug": "python",
                            "starter_code": starter_buggy,
                            "buggy_starter_code": starter_buggy,
                            "debugging_prompt": "Fix the operator.",
                            "reference_solution": ref_sol,
                        }
                    ],
                    "test_cases": [
                        {
                            "ordinal": 1,
                            "name": "Public case",
                            "input_data": "5 3",
                            "expected_output": "16",
                            "is_hidden": False,
                        },
                        {
                            "ordinal": 2,
                            "name": "Hidden",
                            "input_data": "-4 2",
                            "expected_output": "12",
                            "is_hidden": True,
                        },
                    ],
                },
            )
            assert patch_v2.status_code == 200
            assert patch_v2.json()["version_number"] == 2
            assert patch_v2.json()["status"] == "draft"

            vers = (
                await api.get(
                    f"/api/v1/admin/problems/{pid}/versions",
                    headers={"Authorization": f"Bearer {admin_token}"},
                )
            ).json()
            assert len(vers["versions"]) == 2

            t_asg = (
                await api.get(
                    f"/api/v1/teacher/assignments/{asg_id}",
                    headers={"Authorization": f"Bearer {teacher_token}"},
                )
            ).json()
            assert t_asg["problems"][0]["problem_version_id"] == v1_id
            assert t_asg["problems"][0]["title"] == "Phase 8 Live Square Difference"

            # 5. Student executes problem via Judge0 and sees zero hidden test details
            sub = (
                await api.post(
                    "/api/v1/submissions",
                    headers={"Authorization": f"Bearer {student_token}"},
                    json={
                        "problem_id": pid,
                        "language_slug": "python",
                        "submission_kind": "submit",
                        "source_code": ref_sol,
                    },
                )
            ).json()
            assert sub["verdict"] == "accepted"
            assert sub["passed_tests"] == 2
            hidden_items = [r for r in sub["results"] if r["is_hidden"]]
            assert len(hidden_items) == 1
            assert hidden_items[0]["input_data"] is None
            assert hidden_items[0]["expected_output"] is None

            # Archive synthetic test problem cleanly
            arch = (
                await api.post(
                    f"/api/v1/admin/problems/{pid}/archive",
                    headers={"Authorization": f"Bearer {admin_token}"},
                    json={"notes": "End of live test cleanup."},
                )
            ).json()
            assert arch["is_archived"] is True
            assert arch["assigned_courses_count"] == 1
            _ = student_id
    finally:
        app.dependency_overrides.clear()
        await db_manager.dispose()
