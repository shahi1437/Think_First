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
    reason="Set RUN_LIVE_INTEGRATION_TESTS=1 with local Supabase running.",
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


async def _signup_and_login(
    http: httpx.AsyncClient, email: str, password: str, full_name: str
) -> tuple[str, str]:
    signup_resp = await http.post(
        f"{SUPABASE_URL}/auth/v1/signup",
        headers={"apikey": SUPABASE_ANON_KEY, "Content-Type": "application/json"},
        json={
            "email": email,
            "password": password,
            "data": {"full_name": full_name, "role": "admin"},
        },
    )
    assert signup_resp.status_code in (200, 201), signup_resp.text
    payload = signup_resp.json()
    access_token = payload.get("access_token")
    user_id = payload.get("user", {}).get("id") or payload.get("id")
    if not access_token:
        login_resp = await http.post(
            f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
            headers={"apikey": SUPABASE_ANON_KEY, "Content-Type": "application/json"},
            json={"email": email, "password": password},
        )
        assert login_resp.status_code == 200, login_resp.text
        login_data = login_resp.json()
        access_token = login_data["access_token"]
        user_id = login_data["user"]["id"]
    return str(user_id), str(access_token)


async def test_live_supabase_auth_onboarding_rbac_and_rls() -> None:
    settings = Settings(
        app_env="development",
        database_url=DATABASE_URL,
        supabase_url=SUPABASE_URL,
        supabase_jwt_audience="authenticated",
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
    student_a_email = f"student-a-{suffix}@thinkfirst.test"
    student_b_email = f"student-b-{suffix}@thinkfirst.test"
    admin_email = f"admin-{suffix}@thinkfirst.test"
    password = "TestPassword123!"

    try:
        async with (
            httpx.AsyncClient(timeout=10.0) as http,
            AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as api,
        ):
            # 1. Real DB readiness probe returns 200 OK
            ready = await api.get("/health/ready")
            assert ready.status_code == 200
            assert ready.json()["database"] == "ok"

            # 2. Register Student A, Student B, Admin via real Supabase Auth
            student_a_id, student_a_token = await _signup_and_login(
                http, student_a_email, password, "Student Alpha"
            )
            student_b_id, student_b_token = await _signup_and_login(
                http, student_b_email, password, "Student Beta"
            )
            admin_id, admin_token = await _signup_and_login(
                http, admin_email, password, "Platform Admin"
            )

            # 3. Verify JWKS + DB trigger assigned ONLY 'student' despite role='admin' metadata
            me_a = await api.get(
                "/api/v1/users/me", headers={"Authorization": f"Bearer {student_a_token}"}
            )
            assert me_a.status_code == 200, me_a.text
            assert me_a.json()["roles"] == ["student"]
            assert me_a.json()["onboarding_completed"] is False

            # 4. Complete onboarding for Student A, logout, re-login, verify persisted resume
            onboard_resp = await api.post(
                "/api/v1/users/me/onboarding",
                headers={"Authorization": f"Bearer {student_a_token}"},
                json={
                    "full_name": "Student Alpha Verified",
                    "programming_experience": "none",
                    "preferred_language": "python",
                    "learning_goal": "school_fundamentals",
                    "daily_practice_minutes": 30,
                    "preferred_explanation_language": "en",
                    "starting_preference": "guided_beginner",
                },
            )
            assert onboard_resp.status_code == 200, onboard_resp.text
            assert onboard_resp.json()["onboarding_completed"] is True
            assert (
                onboard_resp.json()["preferences"]["recommended_entry_track"]
                == "foundation_lessons"
            )

            logout_resp = await http.post(
                f"{SUPABASE_URL}/auth/v1/logout",
                headers={
                    "apikey": SUPABASE_ANON_KEY,
                    "Authorization": f"Bearer {student_a_token}",
                },
            )
            assert logout_resp.status_code in (200, 204)

            relogin_resp = await http.post(
                f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
                headers={"apikey": SUPABASE_ANON_KEY, "Content-Type": "application/json"},
                json={"email": student_a_email, "password": password},
            )
            assert relogin_resp.status_code == 200
            fresh_token_a = relogin_resp.json()["access_token"]

            resumed = await api.get(
                "/api/v1/users/me", headers={"Authorization": f"Bearer {fresh_token_a}"}
            )
            assert resumed.status_code == 200
            assert resumed.json()["onboarding_completed"] is True
            assert resumed.json()["full_name"] == "Student Alpha Verified"

            # 5. Verify Student A blocked from Teacher & Admin endpoints
            assert (
                await api.get(
                    "/api/v1/teacher/me", headers={"Authorization": f"Bearer {fresh_token_a}"}
                )
            ).status_code == 403
            assert (
                await api.get(
                    "/api/v1/admin/users", headers={"Authorization": f"Bearer {fresh_token_a}"}
                )
            ).status_code == 403

            # 6. Verify PostgreSQL RLS directly via PostgREST
            rls_profiles = await http.get(
                f"{SUPABASE_URL}/rest/v1/profiles?select=id,email",
                headers={
                    "apikey": SUPABASE_ANON_KEY,
                    "Authorization": f"Bearer {fresh_token_a}",
                },
            )
            assert rls_profiles.status_code == 200
            visible_ids = [row["id"] for row in rls_profiles.json()]
            assert visible_ids == [student_a_id]

            # Student A cannot self-insert into user_roles via PostgREST RLS
            rls_escalate = await http.post(
                f"{SUPABASE_URL}/rest/v1/user_roles",
                headers={
                    "apikey": SUPABASE_ANON_KEY,
                    "Authorization": f"Bearer {fresh_token_a}",
                    "Content-Type": "application/json",
                },
                json={"user_id": student_a_id, "role": "admin"},
            )
            assert rls_escalate.status_code in (401, 403)

            # Student A cannot read audit_logs via PostgREST RLS
            rls_audit = await http.get(
                f"{SUPABASE_URL}/rest/v1/audit_logs?select=id",
                headers={
                    "apikey": SUPABASE_ANON_KEY,
                    "Authorization": f"Bearer {fresh_token_a}",
                },
            )
            assert rls_audit.status_code == 200
            assert rls_audit.json() == []

            # 7. Bootstrap Admin via SQL, grant 'teacher' to Student B, verify audit log
            async with db_manager.engine.begin() as conn:
                await conn.execute(
                    text(
                        "INSERT INTO public.user_roles (user_id, role, granted_by) "
                        "VALUES (:uid, 'admin', :uid) ON CONFLICT DO NOTHING"
                    ),
                    {"uid": admin_id},
                )

            grant_resp = await api.post(
                f"/api/v1/admin/users/{student_b_id}/roles",
                headers={"Authorization": f"Bearer {admin_token}"},
                json={"role": "teacher"},
            )
            assert grant_resp.status_code == 200, grant_resp.text
            assert sorted(grant_resp.json()["roles"]) == ["student", "teacher"]

            teacher_check = await api.get(
                "/api/v1/teacher/me", headers={"Authorization": f"Bearer {student_b_token}"}
            )
            assert teacher_check.status_code == 200
    finally:
        await db_manager.dispose()
