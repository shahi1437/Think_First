import os
from uuid import uuid4

import httpx
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.core.config import Settings, get_settings
from app.core.database import DatabaseManager, get_db_manager, get_db_session
from app.main import create_app

LIVE_ENABLED = os.getenv("RUN_LIVE_INTEGRATION_TESTS") == "1"
pytestmark = pytest.mark.skipif(
    not LIVE_ENABLED,
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


async def test_live_phase3_problem_bank_judge0_rls_and_admin_studio() -> None:
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
        async with (
            httpx.AsyncClient(timeout=20.0) as http,
            AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as api,
        ):
            student_a_id, token_a = await _create_user(
                http, f"coder-a-{suffix}@thinkfirst.test", "Coder Alpha"
            )
            _, token_b = await _create_user(http, f"coder-b-{suffix}@thinkfirst.test", "Coder Beta")
            admin_id, admin_token = await _create_user(
                http, f"studio-admin-{suffix}@thinkfirst.test", "Studio Admin"
            )

            async with db_manager.engine.begin() as conn:
                await conn.execute(
                    text(
                        "INSERT INTO public.user_roles (user_id, role, granted_by) "
                        "VALUES (:uid, 'admin', :uid) ON CONFLICT DO NOTHING"
                    ),
                    {"uid": admin_id},
                )

            # 1. Admin syncs real Judge0 CE language registry
            sync_resp = await api.post(
                "/api/v1/admin/languages/sync",
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            assert sync_resp.status_code == 200, sync_resp.text
            assert sync_resp.json()["synced_count"] >= 1

            # 2. Student lists published problems (4 seeded Python problems) & filters debugging
            list_resp = await api.get(
                "/api/v1/problems?mode=debugging",
                headers={"Authorization": f"Bearer {token_a}"},
            )
            assert list_resp.status_code == 200, list_resp.text
            debug_items = list_resp.json()["items"]
            assert len(debug_items) >= 2
            range_problem = next(
                p for p in debug_items if p["slug"] == "debug-range-sum-off-by-one"
            )

            # 3. Student fetches problem detail: zero private solution, zero hidden inputs
            detail_resp = await api.get(
                f"/api/v1/problems/{range_problem['problem_id']}",
                headers={"Authorization": f"Bearer {token_a}"},
            )
            assert detail_resp.status_code == 200, detail_resp.text
            detail = detail_resp.json()
            assert detail["hidden_test_count"] == 3
            assert len(detail["public_test_cases"]) == 2
            assert "reference_solution" not in str(detail)

            # 4. Direct PostgREST RLS prevents student reading private solutions & hidden tests
            rls_ref = await http.get(
                f"{SUPABASE_URL}/rest/v1/problem_reference_solutions?select=variant_id",
                headers={"apikey": SUPABASE_ANON_KEY, "Authorization": f"Bearer {token_a}"},
            )
            assert rls_ref.status_code == 200
            assert rls_ref.json() == []

            rls_hidden = await http.get(
                f"{SUPABASE_URL}/rest/v1/test_cases?select=id,is_hidden&is_hidden=eq.true",
                headers={"apikey": SUPABASE_ANON_KEY, "Authorization": f"Bearer {token_a}"},
            )
            assert rls_hidden.status_code == 200
            assert rls_hidden.json() == []

            # 5. Student blocked from Admin Problem Studio
            assert (
                await api.get(
                    "/api/v1/admin/problems",
                    headers={"Authorization": f"Bearer {token_a}"},
                )
            ).status_code == 403

            # 6. Student runs buggy starter code via real Judge0 -> Wrong Answer
            buggy_code = detail["variants"][0]["buggy_starter_code"]
            run_buggy = await api.post(
                "/api/v1/submissions",
                headers={"Authorization": f"Bearer {token_a}"},
                json={
                    "problem_id": range_problem["problem_id"],
                    "language_slug": "python",
                    "submission_kind": "run",
                    "source_code": buggy_code,
                    "prediction_text": "I think range(3, 5) will print 7 instead of 12.",
                },
            )
            assert run_buggy.status_code == 200, run_buggy.text
            run_data = run_buggy.json()
            assert run_data["verdict"] == "wrong_answer"
            assert run_data["total_tests"] == 2
            assert run_data["passed_tests"] == 0
            assert run_data["results"][0]["stdout"].strip() == "7"

            # 7. Student saves autosave revision and retrieves history
            rev_resp = await api.put(
                "/api/v1/workspace/revisions",
                headers={"Authorization": f"Bearer {token_a}"},
                json={
                    "problem_version_id": detail["version_id"],
                    "language_slug": "python",
                    "source_code": buggy_code.replace("range(a, b)", "range(a, b + 1)"),
                    "prediction_text": "Should now include b.",
                    "explanation_text": "Python range stops before b, so b + 1 includes b.",
                    "revision_type": "autosave",
                },
            )
            assert rev_resp.status_code == 200, rev_resp.text

            # 8. Student submits runtime-error code -> Real Judge0 runtime_error
            run_err = await api.post(
                "/api/v1/submissions",
                headers={"Authorization": f"Bearer {token_a}"},
                json={
                    "problem_id": range_problem["problem_id"],
                    "language_slug": "python",
                    "submission_kind": "run",
                    "source_code": "print(1 / 0)\n",
                },
            )
            assert run_err.status_code == 200, run_err.text
            assert run_err.json()["verdict"] == "runtime_error"
            assert "ZeroDivisionError" in (run_err.json()["results"][0]["stderr"] or "")

            # 9. Student fixes code and submits against public + hidden tests -> Accepted (5/5)
            fixed_code = buggy_code.replace("range(a, b)", "range(a, b + 1)")
            submit_ok = await api.post(
                "/api/v1/submissions",
                headers={"Authorization": f"Bearer {token_a}"},
                json={
                    "problem_id": range_problem["problem_id"],
                    "language_slug": "python",
                    "submission_kind": "submit",
                    "source_code": fixed_code,
                    "prediction_text": "Will print 12 for 3 5.",
                    "explanation_text": "range(a, b) excluded b; changed to range(a, b + 1).",
                },
            )
            assert submit_ok.status_code == 200, submit_ok.text
            sub_data = submit_ok.json()
            assert sub_data["verdict"] == "accepted"
            assert sub_data["passed_tests"] == 5
            assert sub_data["total_tests"] == 5
            hidden_views = [r for r in sub_data["results"] if r["is_hidden"]]
            assert len(hidden_views) == 3
            assert all(
                r["input_data"] is None and r["expected_output"] is None for r in hidden_views
            )

            # 10. Student B cannot read Student A's submission -> 403
            cross_read = await api.get(
                f"/api/v1/submissions/{sub_data['id']}",
                headers={"Authorization": f"Bearer {token_b}"},
            )
            assert cross_read.status_code == 403

            # 11. Admin Studio: Draft -> Refuse Untested -> Validate -> Approve -> Publish
            new_slug = f"double-number-{suffix}"
            create_resp = await api.post(
                "/api/v1/admin/problems",
                headers={"Authorization": f"Bearer {admin_token}"},
                json={
                    "slug": new_slug,
                    "title": "Double the Integer",
                    "statement_md": "Read a single integer `n` and print `2 * n`.",
                    "difficulty": "beginner",
                    "mode": "coding",
                    "topics": ["arithmetic"],
                    "skills": ["basic-io"],
                    "prerequisites": ["variables"],
                    "learning_objectives": ["Read integer input and print doubled output"],
                    "examples": [{"input": "7", "output": "14", "explanation": "2 * 7 = 14"}],
                    "variants": [
                        {
                            "language_slug": "python",
                            "starter_code": "n = int(input())\n# print doubled value\n",
                            "reference_solution": "n = int(input())\nprint(n * 2)\n",
                        }
                    ],
                    "test_cases": [
                        {
                            "ordinal": 1,
                            "name": "Positive",
                            "input_data": "7",
                            "expected_output": "14",
                            "is_hidden": False,
                        },
                        {
                            "ordinal": 2,
                            "name": "Negative hidden",
                            "input_data": "-5",
                            "expected_output": "-10",
                            "is_hidden": True,
                        },
                    ],
                },
            )
            assert create_resp.status_code == 201, create_resp.text
            created_id = create_resp.json()["problem_id"]

            # Refuse publishing unvalidated problem
            unvalidated_pub = await api.post(
                f"/api/v1/admin/problems/{created_id}/publish",
                headers={"Authorization": f"Bearer {admin_token}"},
                json={"notes": "Attempt premature publish"},
            )
            assert unvalidated_pub.status_code == 409
            assert unvalidated_pub.json()["code"] == "CANNOT_PUBLISH_UNVALIDATED"

            # Automated Judge0 validation passes
            val_resp = await api.post(
                f"/api/v1/admin/problems/{created_id}/validate",
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            assert val_resp.status_code == 200, val_resp.text
            assert val_resp.json()["passed"] is True
            assert val_resp.json()["new_status"] == "validated"

            # Approve & Publish
            app_resp = await api.post(
                f"/api/v1/admin/problems/{created_id}/approve",
                headers={"Authorization": f"Bearer {admin_token}"},
                json={"notes": "Reviewed tests and statement."},
            )
            assert app_resp.status_code == 200, app_resp.text
            assert app_resp.json()["status"] == "approved"

            pub_resp = await api.post(
                f"/api/v1/admin/problems/{created_id}/publish",
                headers={"Authorization": f"Bearer {admin_token}"},
                json={"notes": "Ready for students."},
            )
            assert pub_resp.status_code == 200, pub_resp.text
            assert pub_resp.json()["status"] == "published"

            # Newly published problem is immediately visible to Student A
            student_lookup = await api.get(
                f"/api/v1/problems/{created_id}",
                headers={"Authorization": f"Bearer {token_a}"},
            )
            assert student_lookup.status_code == 200
            assert student_lookup.json()["slug"] == new_slug
            _ = student_a_id
    finally:
        await db_manager.dispose()
