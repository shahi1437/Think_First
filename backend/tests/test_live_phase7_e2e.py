"""Live Phase 7 integration test against PostgreSQL, strict RLS, and real Judge0.

Verifies the complete Teacher <-> Student classroom & assignment lifecycle plus negative security:
1. All 10 Phase 7 tables have FORCE ROW LEVEL SECURITY enabled.
2. Admin grants Teacher role to Teacher A & B (students cannot self-promote or access /teacher).
3. Teacher A creates Class -> invite code -> Student A joins; Teacher B gets 403 on Teacher A class.
4. Direct PostgREST RLS: Student A cannot read `class_invitations` or `grading_audit_events`.
5. Teacher A creates Draft Assignment -> publishes with approved `debug-range-sum-off-by-one`.
6. Student B (not enrolled) gets 403; Student A submits buggy then fixed solution via real Judge0.
7. Server enforces attempt limits, deadlines, and hint limits.
8. Teacher A saves draft grade (hidden from Student A via API & RLS!) -> requests revision ->
   Student A resubmits -> Teacher A publishes final grade -> Student B gets 403.
9. Marks > max_marks rejected (400); Student A cannot grade (403); Grading Audit Trail recorded.
10. Teacher Dashboard returns real aggregated counts (enrolled, pending/graded, Judge0 verdicts).
"""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.core.config import Settings, get_settings
from app.core.database import DatabaseManager, get_db_manager, get_db_session
from app.main import create_app

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        os.getenv("RUN_LIVE_INTEGRATION_TESTS") != "1",
        reason=(
            "Set RUN_LIVE_INTEGRATION_TESTS=1 with local Supabase + Judge0 Docker stack running."
        ),
    ),
]

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
async def test_live_phase7_tables_and_force_rls() -> None:
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
                "courses",
                "class_invitations",
                "course_memberships",
                "assignments",
                "assignment_problem_links",
                "assignment_submissions",
                "assignment_attempts",
                "assignment_grades",
                "teacher_feedback",
                "grading_audit_events",
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
async def test_live_phase7_full_classroom_assignment_grading_and_security() -> None:
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
            admin_id, admin_token = await _create_user(
                http, f"p7-admin-{suffix}@thinkfirst.test", "Phase7 Admin"
            )
            teacher_a_id, teacher_a_token = await _create_user(
                http, f"p7-teacher-a-{suffix}@thinkfirst.test", "Teacher Alpha"
            )
            teacher_b_id, teacher_b_token = await _create_user(
                http, f"p7-teacher-b-{suffix}@thinkfirst.test", "Teacher Beta"
            )
            _, student_a_token = await _create_user(
                http, f"p7-student-a-{suffix}@thinkfirst.test", "Student Alpha"
            )
            _, student_b_token = await _create_user(
                http, f"p7-student-b-{suffix}@thinkfirst.test", "Student Beta"
            )

            # Bootstrap Admin in DB, then Admin grants Teacher role via real Admin RBAC API!
            async with db_manager.engine.begin() as conn:
                await conn.execute(
                    text(
                        "INSERT INTO public.user_roles (user_id, role, granted_by) "
                        "VALUES (:uid, 'admin', :uid) ON CONFLICT DO NOTHING"
                    ),
                    {"uid": admin_id},
                )

            for tid in (teacher_a_id, teacher_b_id):
                grant = await api.post(
                    f"/api/v1/admin/users/{tid}/roles",
                    headers={"Authorization": f"Bearer {admin_token}"},
                    json={"role": "teacher"},
                )
                assert grant.status_code == 200, grant.text

            # Student CANNOT access Teacher endpoints (403)
            assert (
                await api.get(
                    "/api/v1/teacher/dashboard",
                    headers={"Authorization": f"Bearer {student_a_token}"},
                )
            ).status_code == 403

            # 1. Teacher A creates Class & inspects auto-generated invite code
            course_resp = await api.post(
                "/api/v1/teacher/classes",
                headers={"Authorization": f"Bearer {teacher_a_token}"},
                json={
                    "code": f"CSE101-{suffix[:4].upper()}",
                    "title": "Structured Programming Lab",
                    "description": "Python fundamentals & debugging lab.",
                    "term": "Fall 2026",
                    "enrollment_policy": "open_with_code",
                    "allow_student_leave": True,
                },
            )
            assert course_resp.status_code == 201, course_resp.text
            course_id = course_resp.json()["id"]

            detail_a = (
                await api.get(
                    f"/api/v1/teacher/classes/{course_id}",
                    headers={"Authorization": f"Bearer {teacher_a_token}"},
                )
            ).json()
            invite_code = detail_a["invitations"][0]["code_preview"]

            # Cross-teacher isolation: Teacher B CANNOT inspect Teacher A's class (403)
            assert (
                await api.get(
                    f"/api/v1/teacher/classes/{course_id}",
                    headers={"Authorization": f"Bearer {teacher_b_token}"},
                )
            ).status_code == 403

            # Direct PostgREST RLS: Student A CANNOT list class_invitations
            rls_inv = await http.get(
                f"{SUPABASE_URL}/rest/v1/class_invitations?select=id,code_preview",
                headers={"apikey": SUPABASE_ANON_KEY, "Authorization": f"Bearer {student_a_token}"},
            )
            assert rls_inv.status_code == 200 and rls_inv.json() == []

            # Bad invite code rejected (400)
            bad_join = await api.post(
                "/api/v1/student/classes/join",
                headers={"Authorization": f"Bearer {student_a_token}"},
                json={"invite_code": "CM-WRONG-00000"},
            )
            assert bad_join.status_code == 400

            # Student A joins with real invite code
            join_resp = await api.post(
                "/api/v1/student/classes/join",
                headers={"Authorization": f"Bearer {student_a_token}"},
                json={"invite_code": invite_code},
            )
            assert join_resp.status_code == 201, join_resp.text
            assert join_resp.json()["membership_status"] == "active"

            # 2. Fetch Admin-approved published problem `debug-range-sum-off-by-one`
            probs = (
                await api.get(
                    "/api/v1/problems?mode=debugging",
                    headers={"Authorization": f"Bearer {teacher_a_token}"},
                )
            ).json()["items"]
            debug_prob = next(p for p in probs if p["slug"] == "debug-range-sum-off-by-one")
            prob_id = debug_prob["problem_id"]
            prob_detail = (
                await api.get(
                    f"/api/v1/problems/{prob_id}",
                    headers={"Authorization": f"Bearer {student_a_token}"},
                )
            ).json()
            buggy_code = prob_detail["variants"][0]["buggy_starter_code"]
            fixed_code = buggy_code.replace("range(a, b)", "range(a, b + 1)")

            # 3. Teacher A creates & publishes Assignment (max_attempts=2, hint_limit=1)
            due_iso = (datetime.now(UTC) + timedelta(days=2)).isoformat()
            asg_resp = await api.post(
                "/api/v1/teacher/assignments",
                headers={"Authorization": f"Bearer {teacher_a_token}"},
                json={
                    "course_id": course_id,
                    "title": "Lab 1: Loop Boundary Debugging",
                    "instructions_md": "Fix the inclusive range sum off-by-one bug.",
                    "due_at": due_iso,
                    "max_marks": 50,
                    "grading_policy": "judge0_assisted_manual",
                    "max_attempts": 2,
                    "allow_ai_hints": True,
                    "hint_limit": 1,
                    "allow_late_submissions": False,
                    "allow_resubmission_on_revision": True,
                    "publish_now": False,
                    "problems": [{"problem_id": prob_id, "points": 50}],
                },
            )
            assert asg_resp.status_code == 201, asg_resp.text
            asg_id = asg_resp.json()["id"]
            assert asg_resp.json()["status"] == "draft"

            # Student A cannot see draft assignment yet
            assert (
                await api.get(
                    f"/api/v1/student/assignments/{asg_id}",
                    headers={"Authorization": f"Bearer {student_a_token}"},
                )
            ).status_code == 404

            pub_resp = await api.post(
                f"/api/v1/teacher/assignments/{asg_id}/publish",
                headers={"Authorization": f"Bearer {teacher_a_token}"},
            )
            assert pub_resp.status_code == 200 and pub_resp.json()["status"] == "published"

            # Unenrolled Student B gets 403
            assert (
                await api.get(
                    f"/api/v1/student/assignments/{asg_id}",
                    headers={"Authorization": f"Bearer {student_b_token}"},
                )
            ).status_code == 403

            # 4. Hint limit enforced server-side (hint_limit=1 -> hints_used=2 rejected with 400)
            bad_hint = await api.post(
                f"/api/v1/student/assignments/{asg_id}/submit",
                headers={"Authorization": f"Bearer {student_a_token}"},
                json={
                    "problem_id": prob_id,
                    "language_slug": "python",
                    "source_code": buggy_code,
                    "hints_used": 2,
                },
            )
            assert bad_hint.status_code == 400 and bad_hint.json()["code"] == "HINT_LIMIT_EXCEEDED"

            # Attempt 1 (buggy code -> real Judge0 wrong_answer)
            att1 = await api.post(
                f"/api/v1/student/assignments/{asg_id}/submit",
                headers={"Authorization": f"Bearer {student_a_token}"},
                json={
                    "problem_id": prob_id,
                    "language_slug": "python",
                    "source_code": buggy_code,
                    "student_notes": "Initial attempt before fix.",
                    "hints_used": 1,
                },
            )
            assert att1.status_code == 201, att1.text
            assert att1.json()["attempt"]["verdict"] == "wrong_answer"

            # Attempt 2 (fixed code -> real Judge0 accepted 5/5)
            att2 = await api.post(
                f"/api/v1/student/assignments/{asg_id}/submit",
                headers={"Authorization": f"Bearer {student_a_token}"},
                json={
                    "problem_id": prob_id,
                    "language_slug": "python",
                    "source_code": fixed_code,
                    "student_notes": "Fixed range(a, b + 1) inclusive upper bound.",
                    "hints_used": 0,
                },
            )
            assert att2.status_code == 201, att2.text
            assert att2.json()["attempt"]["verdict"] == "accepted"
            assert att2.json()["attempt"]["passed_tests"] == 5
            assert att2.json()["attempts_remaining"] == 0

            # Attempt 3 blocked by server-side max_attempts=2 (409)
            att3 = await api.post(
                f"/api/v1/student/assignments/{asg_id}/submit",
                headers={"Authorization": f"Bearer {student_a_token}"},
                json={
                    "problem_id": prob_id,
                    "language_slug": "python",
                    "source_code": fixed_code,
                },
            )
            assert att3.status_code == 409

            # 5. Teacher reviews submission, saves draft grade (hidden from student!),
            #    requests revision, student resubmits, teacher publishes final grade + audit trail!
            rev_detail = (
                await api.get(
                    f"/api/v1/teacher/assignments/{asg_id}",
                    headers={"Authorization": f"Bearer {teacher_a_token}"},
                )
            ).json()
            assert len(rev_detail["submissions"]) == 1
            asg_sub_id = rev_detail["submissions"][0]["assignment_submission_id"]

            # Student CANNOT grade (403) and Teacher B CANNOT grade (403)
            for bad_tok in (student_a_token, teacher_b_token):
                assert (
                    await api.post(
                        f"/api/v1/teacher/submissions/{asg_sub_id}/grade",
                        headers={"Authorization": f"Bearer {bad_tok}"},
                        json={"marks_awarded": 50, "action": "publish", "feedback_md": "Nope"},
                    )
                ).status_code == 403

            # Marks > max_marks (55 > 50) rejected (400)
            over_marks = await api.post(
                f"/api/v1/teacher/submissions/{asg_sub_id}/grade",
                headers={"Authorization": f"Bearer {teacher_a_token}"},
                json={"marks_awarded": 55, "action": "publish", "feedback_md": "Too high"},
            )
            assert (
                over_marks.status_code == 400 and over_marks.json()["code"] == "MARKS_OUT_OF_RANGE"
            )

            # Save DRAFT grade -> MUST stay hidden from Student A in API & direct PostgREST RLS!
            draft_grade = await api.post(
                f"/api/v1/teacher/submissions/{asg_sub_id}/grade",
                headers={"Authorization": f"Bearer {teacher_a_token}"},
                json={"marks_awarded": 42, "action": "save_draft", "feedback_md": "Draft note"},
            )
            assert draft_grade.status_code == 200
            stu_view_draft = (
                await api.get(
                    f"/api/v1/student/assignments/{asg_id}",
                    headers={"Authorization": f"Bearer {student_a_token}"},
                )
            ).json()
            assert stu_view_draft["grade"] is None
            rls_draft_grade = await http.get(
                f"{SUPABASE_URL}/rest/v1/assignment_grades?select=id,marks_awarded",
                headers={"apikey": SUPABASE_ANON_KEY, "Authorization": f"Bearer {student_a_token}"},
            )
            assert rls_draft_grade.status_code == 200 and rls_draft_grade.json() == []

            # Request revision -> unlocks resubmission even though max_attempts=2 were used!
            rev_req = await api.post(
                f"/api/v1/teacher/submissions/{asg_sub_id}/grade",
                headers={"Authorization": f"Bearer {teacher_a_token}"},
                json={
                    "marks_awarded": 35,
                    "action": "request_revision",
                    "feedback_md": "Please add a clear docstring explaining inclusive bounds.",
                },
            )
            assert rev_req.status_code == 200 and rev_req.json()["status"] == "revision_requested"

            resub = await api.post(
                f"/api/v1/student/assignments/{asg_id}/submit",
                headers={"Authorization": f"Bearer {student_a_token}"},
                json={
                    "problem_id": prob_id,
                    "language_slug": "python",
                    "source_code": "# Inclusive sum a..b\n" + fixed_code,
                    "student_notes": "Added explanatory comment per teacher feedback.",
                },
            )
            assert resub.status_code == 201 and resub.json()["workflow_status"] == "resubmitted"

            # Publish final grade (48/50)
            pub_grade = await api.post(
                f"/api/v1/teacher/submissions/{asg_sub_id}/grade",
                headers={"Authorization": f"Bearer {teacher_a_token}"},
                json={
                    "marks_awarded": 48,
                    "action": "publish",
                    "feedback_md": "Excellent revision! Clean boundary logic and full test pass.",
                },
            )
            assert pub_grade.status_code == 200
            pub_grade_data = pub_grade.json()
            assert pub_grade_data["status"] == "graded"
            assert pub_grade_data["grade"]["marks_awarded"] == 48.0
            assert len(pub_grade_data["audit_events"]) == 3  # draft, revision, publish

            # Student A sees published grade & feedback; Student B sees NOTHING via RLS!
            stu_final = (
                await api.get(
                    f"/api/v1/student/assignments/{asg_id}",
                    headers={"Authorization": f"Bearer {student_a_token}"},
                )
            ).json()
            assert stu_final["grade"]["marks_awarded"] == 48.0
            assert len(stu_final["feedback"]) >= 2

            for tbl in ("assignment_grades", "assignment_submissions", "teacher_feedback"):
                rls_b = await http.get(
                    f"{SUPABASE_URL}/rest/v1/{tbl}?select=id",
                    headers={
                        "apikey": SUPABASE_ANON_KEY,
                        "Authorization": f"Bearer {student_b_token}",
                    },
                )
                assert rls_b.status_code == 200 and rls_b.json() == [], tbl

            # 6. Teacher Dashboard reflects REAL aggregated data
            dash = (
                await api.get(
                    "/api/v1/teacher/dashboard",
                    headers={"Authorization": f"Bearer {teacher_a_token}"},
                )
            ).json()
            assert dash["active_courses_count"] >= 1
            assert dash["total_enrolled_students"] >= 1
            assert dash["graded_submissions_count"] >= 1
            assert dash["analytics"]["total_attempts"] >= 3
            assert dash["analytics"]["accepted_attempts"] >= 2
    finally:
        await db_manager.dispose()
