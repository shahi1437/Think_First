"""Live Multi-Language Learning + Judge0 Primary / Piston Fallback Integration Tests.

Tests against REAL running local services (Supabase PostgreSQL, Judge0 CE, Self-Hosted Piston):
1. All 5 languages (python, javascript, c, cpp, java):
   - valid code -> accepted (provider=judge0)
   - wrong answer -> wrong_answer (provider=judge0, NO Piston fallback)
   - syntax/compiler error -> compilation_error/runtime_error (provider=judge0, NO Piston fallback)
   - hidden tests remain stripped on submit
2. Controlled Judge0 outage -> REAL Piston fallback (provider=piston) for all 5 languages
   with ZERO duplicate submission rows
3. Both Judge0 and Piston unavailable -> clear HTTP 503 (never fake success)
4. Per-language progress & Skill Graph isolation + persistence across language switches
5. Honest ML (Python) vs Rule-Based (JS/C/C++/Java) diagnosis + language-scoped RAG
6. Admin Operations Health checks both `judge0` and `piston_fallback` as `ok`
7. Student RBAC / cross-student isolation preserved

Run with:
  RUN_LIVE_INTEGRATION_TESTS=1 pytest tests/test_live_multilanguage_and_fallback.py -v
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

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        os.getenv("RUN_LIVE_INTEGRATION_TESTS") != "1",
        reason="Set RUN_LIVE_INTEGRATION_TESTS=1 with local Supabase + Judge0 + Piston running.",
    ),
]

SUPABASE_URL = os.getenv("SUPABASE_URL", "http://127.0.0.1:54321")
SUPABASE_ANON_KEY = os.getenv(
    "NEXT_PUBLIC_SUPABASE_ANON_KEY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0",
)

# Solutions for seeded problem `sum-of-even-numbers` (reads space-separated ints, prints sum of evens)
SUM_EVEN_VALID: dict[str, str] = {
    "python": "nums = [int(x) for x in input().split()]\nprint(sum(x for x in nums if x % 2 == 0))\n",
    "javascript": (
        "const fs = require('fs');\n"
        "const nums = fs.readFileSync(0, 'utf8').trim().split(/\\s+/).map(Number);\n"
        "let total = 0;\n"
        "for (const x of nums) if (x % 2 === 0) total += x;\n"
        "console.log(total);\n"
    ),
    "c": (
        "#include <stdio.h>\n"
        "int main(void) {\n"
        "    long long x = 0, total = 0;\n"
        '    while (scanf("%lld", &x) == 1) { if (x % 2 == 0) total += x; }\n'
        '    printf("%lld\\n", total);\n'
        "    return 0;\n"
        "}\n"
    ),
    "cpp": (
        "#include <iostream>\n"
        "int main() {\n"
        "    long long x = 0, total = 0;\n"
        "    while (std::cin >> x) { if (x % 2 == 0) total += x; }\n"
        "    std::cout << total << '\\n';\n"
        "    return 0;\n"
        "}\n"
    ),
    "java": (
        "import java.util.*;\n"
        "public class Main {\n"
        "    public static void main(String[] args) {\n"
        "        Scanner sc = new Scanner(System.in);\n"
        "        long total = 0;\n"
        "        while (sc.hasNextLong()) {\n"
        "            long x = sc.nextLong();\n"
        "            if (x % 2 == 0) total += x;\n"
        "        }\n"
        "        System.out.println(total);\n"
        "    }\n"
        "}\n"
    ),
}

SUM_EVEN_WRONG: dict[str, str] = {
    "python": "nums = [int(x) for x in input().split()]\nprint(sum(x for x in nums if x % 2 != 0))\n",
    "javascript": (
        "const fs = require('fs');\n"
        "const nums = fs.readFileSync(0, 'utf8').trim().split(/\\s+/).map(Number);\n"
        "let total = 0;\n"
        "for (const x of nums) if (x % 2 !== 0) total += x;\n"
        "console.log(total);\n"
    ),
    "c": (
        "#include <stdio.h>\n"
        "int main(void) {\n"
        "    long long x = 0, total = 0;\n"
        '    while (scanf("%lld", &x) == 1) { if (x % 2 != 0) total += x; }\n'
        '    printf("%lld\\n", total);\n'
        "    return 0;\n"
        "}\n"
    ),
    "cpp": (
        "#include <iostream>\n"
        "int main() {\n"
        "    long long x = 0, total = 0;\n"
        "    while (std::cin >> x) { if (x % 2 != 0) total += x; }\n"
        "    std::cout << total << '\\n';\n"
        "    return 0;\n"
        "}\n"
    ),
    "java": (
        "import java.util.*;\n"
        "public class Main {\n"
        "    public static void main(String[] args) {\n"
        "        Scanner sc = new Scanner(System.in);\n"
        "        long total = 0;\n"
        "        while (sc.hasNextLong()) {\n"
        "            long x = sc.nextLong();\n"
        "            if (x % 2 != 0) total += x;\n"
        "        }\n"
        "        System.out.println(total);\n"
        "    }\n"
        "}\n"
    ),
}

SUM_EVEN_SYNTAX_ERROR: dict[str, str] = {
    "python": "nums = [int(x) for x in input().split(\nprint(nums)\n",
    "javascript": "const x = ;\nconsole.log(x);\n",
    "c": '#include <stdio.h>\nint main(void) { printf("hi") return 0; }\n',
    "cpp": '#include <iostream>\nint main() { std::cout << "hi" return 0; }\n',
    "java": "public class Main { public static void main(String[] args) { System.out.println(1) } }\n",
}


async def _signup_user(http: httpx.AsyncClient, email: str, name: str) -> tuple[str, str]:
    resp = await http.post(
        f"{SUPABASE_URL}/auth/v1/signup",
        headers={"apikey": SUPABASE_ANON_KEY, "Content-Type": "application/json"},
        json={"email": email, "password": "TestPassword123!", "data": {"full_name": name}},
    )
    assert resp.status_code in (200, 201), resp.text
    payload = resp.json()
    return str(payload["user"]["id"]), str(payload["access_token"])


def _build_test_app(settings: Settings, db_manager: DatabaseManager):
    app = create_app(settings=settings)
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_db_manager] = lambda: db_manager

    async def _override_session():
        async for sess in db_manager.session():
            yield sess

    app.dependency_overrides[get_db_session] = _override_session
    return app


@pytest.mark.asyncio
async def test_live_five_languages_execution_isolation_and_piston_fallback() -> None:
    """End-to-end live verification of all 5 languages, Judge0 primary, Piston fallback, and isolation."""
    get_settings.cache_clear()
    base_settings = Settings()
    db_manager = DatabaseManager(base_settings)
    app = _build_test_app(base_settings, db_manager)

    suffix = uuid4().hex[:8]
    try:
        async with (
            httpx.AsyncClient(timeout=30.0) as http,
            AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as api,
        ):
            user_a_id, token_a = await _signup_user(
                http, f"ml-student-a-{suffix}@thinkfirst.test", "MultiLang Student A"
            )
            _, token_b = await _signup_user(
                http, f"ml-student-b-{suffix}@thinkfirst.test", "MultiLang Student B"
            )
            hdr_a = {"Authorization": f"Bearer {token_a}"}
            hdr_b = {"Authorization": f"Bearer {token_b}"}

            # Complete onboarding for Student A
            ob_resp = await api.post(
                "/api/v1/users/me/onboarding",
                headers=hdr_a,
                json={
                    "full_name": "MultiLang Student A",
                    "programming_experience": "beginner",
                    "preferred_language": "python",
                    "learning_goal": "university_coursework",
                    "daily_practice_minutes": 30,
                    "preferred_explanation_language": "en",
                    "starting_preference": "guided_beginner",
                },
            )
            assert ob_resp.status_code == 200, ob_resp.text

            # 1. Verify all 5 languages exposed with accurate lesson counts
            langs_resp = await api.get("/api/v1/learning/languages", headers=hdr_a)
            assert langs_resp.status_code == 200, langs_resp.text
            langs_data = langs_resp.json()
            assert langs_data["active_language_slug"] == "python"
            lang_map = {item["slug"]: item for item in langs_data["languages"]}
            assert set(lang_map.keys()) == {"python", "javascript", "c", "cpp", "java"}
            assert lang_map["python"]["lessons_total"] >= 24
            for slug in ("javascript", "c", "cpp", "java"):
                assert lang_map[slug]["lessons_total"] == 10

            # 2. Fetch `sum-of-even-numbers` problem (has all 5 language variants)
            probs = (await api.get("/api/v1/problems?search=even", headers=hdr_a)).json()["items"]
            sum_prob = next(p for p in probs if p["slug"] == "sum-of-even-numbers")
            prob_id = sum_prob["problem_id"]
            assert {"python", "javascript", "c", "cpp", "java"}.issubset(
                set(sum_prob["supported_languages"])
            )

            # 3. LIVE Judge0 Primary across all 5 languages: accepted + wrong_answer + syntax/compile error
            first_sub_id = None
            c_wrong_sub_id = None
            py_wrong_sub_id = None
            for slug in ("python", "javascript", "c", "cpp", "java"):
                # 3a. Valid code on `submit` -> accepted + hidden tests protected + provider=judge0
                ok_resp = await api.post(
                    "/api/v1/submissions",
                    headers=hdr_a,
                    json={
                        "problem_id": prob_id,
                        "language_slug": slug,
                        "submission_kind": "submit",
                        "source_code": SUM_EVEN_VALID[slug],
                    },
                )
                assert ok_resp.status_code == 200, f"{slug} valid failed: {ok_resp.text}"
                ok_body = ok_resp.json()
                assert ok_body["verdict"] == "accepted", f"{slug}: {ok_body}"
                assert ok_body["execution_provider"] == "judge0"
                assert ok_body["passed_tests"] == ok_body["total_tests"]
                hidden_cases = [r for r in ok_body["results"] if r["is_hidden"]]
                assert len(hidden_cases) >= 1
                for hc in hidden_cases:
                    assert hc["input_data"] is None
                    assert hc["expected_output"] is None
                if first_sub_id is None:
                    first_sub_id = ok_body["id"]

                # 3b. Wrong answer -> wrong_answer + provider=judge0 (NO Piston fallback!)
                wa_resp = await api.post(
                    "/api/v1/submissions",
                    headers=hdr_a,
                    json={
                        "problem_id": prob_id,
                        "language_slug": slug,
                        "submission_kind": "run",
                        "source_code": SUM_EVEN_WRONG[slug],
                    },
                )
                assert wa_resp.status_code == 200, wa_resp.text
                wa_body = wa_resp.json()
                assert wa_body["verdict"] == "wrong_answer", f"{slug} WA: {wa_body}"
                assert wa_body["execution_provider"] == "judge0"
                if slug == "c":
                    c_wrong_sub_id = wa_body["id"]
                if slug == "python":
                    py_wrong_sub_id = wa_body["id"]

                # 3c. Syntax / compile error -> provider=judge0 (NO Piston fallback!)
                ce_resp = await api.post(
                    "/api/v1/submissions",
                    headers=hdr_a,
                    json={
                        "problem_id": prob_id,
                        "language_slug": slug,
                        "submission_kind": "run",
                        "source_code": SUM_EVEN_SYNTAX_ERROR[slug],
                    },
                )
                assert ce_resp.status_code == 200, ce_resp.text
                ce_body = ce_resp.json()
                assert ce_body["verdict"] in {"compilation_error", "runtime_error"}, (
                    f"{slug} syntax err: {ce_body}"
                )
                assert ce_body["execution_provider"] == "judge0"

            # 4. Verify honest ML vs Rule-Based diagnosis + Socratic AI Mentor + language-scoped RAG
            assert py_wrong_sub_id is not None and c_wrong_sub_id is not None
            py_diag = (
                await api.post(f"/api/v1/mentor/diagnose/{py_wrong_sub_id}", headers=hdr_a)
            ).json()
            assert py_diag["diagnosis_source"] == "ml_classifier"
            assert py_diag["language_slug"] == "python"

            c_diag = (
                await api.post(f"/api/v1/mentor/diagnose/{c_wrong_sub_id}", headers=hdr_a)
            ).json()
            assert c_diag["diagnosis_source"] == "rule_based"
            assert c_diag["language_slug"] == "c"
            assert c_diag["model_version"] == "rule-multilang-v1"

            # Verify Socratic AI Mentor session + hint turn on a C submission (no Python leakage)
            c_mentor_sess = await api.post(
                "/api/v1/mentor/sessions",
                headers=hdr_a,
                json={"problem_id": prob_id, "explanation_language": "en"},
            )
            assert c_mentor_sess.status_code in (200, 201), c_mentor_sess.text
            c_sess_id = c_mentor_sess.json()["id"]
            c_mentor_turn = await api.post(
                f"/api/v1/mentor/sessions/{c_sess_id}/turns",
                headers=hdr_a,
                json={
                    "action": "diagnose",
                    "submission_id": c_wrong_sub_id,
                    "student_message": "Why does my C loop sum odd numbers instead of even ones?",
                },
            )
            assert c_mentor_turn.status_code == 200, c_mentor_turn.text
            c_turn_data = c_mentor_turn.json()
            assert len(c_turn_data["turns"]) >= 1
            mentor_reply_text = " ".join(
                (t.get("content") or "") + " " + (t.get("hint_text") or "")
                for t in c_turn_data["turns"]
                if t.get("role") == "mentor"
            )
            assert "range(" not in mentor_reply_text.lower()

            # 5. Per-language guided lessons, diagnostics & Skill Graph isolation across ALL 5 languages
            lesson_solutions: dict[str, str] = {
                "python": "print('CodeMentor')\nprint(6 * 7)\n",
                "javascript": "console.log('Hello JavaScript');\nconsole.log(5 * 5);\n",
                "c": '#include <stdio.h>\nint main(void){ printf("Hello C\\n%d\\n", 7*7); return 0; }\n',
                "cpp": '#include <iostream>\nint main(){ std::cout << "Hello C++\\n" << (8*8) << "\\n"; return 0; }\n',
                "java": 'public class Main { public static void main(String[] a){ System.out.println("Hello Java"); System.out.println(9*9); } }\n',
            }

            # First complete Python lesson #1 -> Python becomes 1/24
            py_lessons = (
                await api.get("/api/v1/learning/lessons?language=python", headers=hdr_a)
            ).json()
            assert len(py_lessons) >= 24
            py_run = await api.post(
                f"/api/v1/learning/lessons/{py_lessons[0]['lesson_id']}/exercise/run",
                headers=hdr_a,
                json={"source_code": lesson_solutions["python"]},
            )
            assert py_run.status_code == 200, py_run.text
            assert py_run.json()["exercise_passed"] is True
            assert py_run.json()["progress_status"] == "completed"

            # Now switch to JS, C, C++, Java in turn: run guided lesson #1 + verify language-specific diagnostic
            for slug in ("javascript", "c", "cpp", "java"):
                sel_resp = await api.post(
                    "/api/v1/learning/languages/select",
                    headers=hdr_a,
                    json={"language_slug": slug},
                )
                assert sel_resp.status_code == 200, sel_resp.text
                assert sel_resp.json()["active_language_slug"] == slug

                lang_lessons = (await api.get("/api/v1/learning/lessons", headers=hdr_a)).json()
                assert len(lang_lessons) == 10
                assert all(lsn["language_slug"] == slug for lsn in lang_lessons)

                run_lsn = await api.post(
                    f"/api/v1/learning/lessons/{lang_lessons[0]['lesson_id']}/exercise/run",
                    headers=hdr_a,
                    json={"source_code": lesson_solutions[slug]},
                )
                assert run_lsn.status_code == 200, f"{slug} lesson run failed: {run_lsn.text}"
                assert run_lsn.json()["exercise_passed"] is True
                assert run_lsn.json()["progress_status"] == "completed"

                lang_dash = (await api.get("/api/v1/learning/dashboard", headers=hdr_a)).json()
                assert lang_dash["language_slug"] == slug
                assert lang_dash["lessons_completed"] == 1
                assert lang_dash["lessons_total"] == 10

                # Start language-specific diagnostic session & confirm question belongs to this language
                diag_start = await api.post(
                    "/api/v1/learning/diagnostics/sessions",
                    headers=hdr_a,
                    json={"explanation_language": "en", "language_slug": slug},
                )
                assert diag_start.status_code in (200, 201), (
                    f"{slug} diag failed: {diag_start.text}"
                )
                diag_body = diag_start.json()
                assert diag_body["language_slug"] == slug
                assert diag_body["current_question"] is not None
                assert diag_body["current_question"]["language_slug"] == slug

            # Switch back to Python -> confirm Python progress remained 1/24 (uncorrupted) AND diag works
            sel_py = await api.post(
                "/api/v1/learning/languages/select",
                headers=hdr_a,
                json={"language_slug": "python"},
            )
            assert sel_py.status_code == 200
            py_dash = (await api.get("/api/v1/learning/dashboard", headers=hdr_a)).json()
            assert py_dash["language_slug"] == "python"
            assert py_dash["lessons_completed"] == 1
            assert py_dash["lessons_total"] >= 24

            py_diag_start = await api.post(
                "/api/v1/learning/diagnostics/sessions",
                headers=hdr_a,
                json={"explanation_language": "en", "language_slug": "python"},
            )
            assert py_diag_start.status_code in (200, 201), py_diag_start.text
            assert py_diag_start.json()["language_slug"] == "python"

            # Verify overview reports all 5 independent progress counters accurately
            overview_after = (await api.get("/api/v1/learning/languages", headers=hdr_a)).json()
            after_map = {x["slug"]: x for x in overview_after["languages"]}
            assert after_map["python"]["lessons_completed"] == 1
            assert after_map["python"]["lessons_total"] >= 24
            for slug in ("javascript", "c", "cpp", "java"):
                assert after_map[slug]["lessons_completed"] == 1
                assert after_map[slug]["lessons_total"] == 10
                assert after_map[slug]["submissions_count"] >= 3

            # 6. Security: Cross-student isolation & RBAC preserved
            assert first_sub_id is not None
            other_sub = await api.get(f"/api/v1/submissions/{first_sub_id}", headers=hdr_b)
            assert other_sub.status_code in (403, 404)
            student_admin_probe = await api.get("/api/v1/admin/operations/health", headers=hdr_a)
            assert student_admin_probe.status_code == 403

            # 7. CONTROLLED JUDGE0 OUTAGE -> LIVE PISTON FALLBACK FOR ALL 5 LANGUAGES (ZERO DUPLICATES!)
            outage_settings = base_settings.model_copy(
                update={
                    "judge0_base_url": "http://127.0.0.1:19999",
                    "execution_fallback_enabled": True,
                    "piston_enabled": True,
                }
            )
            outage_app = _build_test_app(outage_settings, db_manager)
            async with AsyncClient(
                transport=ASGITransport(app=outage_app), base_url="http://testserver"
            ) as outage_api:
                before_count = (
                    await outage_api.get(f"/api/v1/submissions?problem_id={prob_id}", headers=hdr_a)
                ).json()["total"]

                for slug in ("python", "javascript", "c", "cpp", "java"):
                    fb_resp = await outage_api.post(
                        "/api/v1/submissions",
                        headers=hdr_a,
                        json={
                            "problem_id": prob_id,
                            "language_slug": slug,
                            "submission_kind": "run",
                            "source_code": SUM_EVEN_VALID[slug],
                        },
                    )
                    assert fb_resp.status_code == 200, (
                        f"Piston fallback {slug} failed: {fb_resp.text}"
                    )
                    fb_body = fb_resp.json()
                    assert fb_body["verdict"] == "accepted", f"Piston {slug}: {fb_body}"
                    assert fb_body["execution_provider"] == "piston"

                after_count = (
                    await outage_api.get(f"/api/v1/submissions?problem_id={prob_id}", headers=hdr_a)
                ).json()["total"]
                assert after_count == before_count + 5, (
                    f"Expected exactly 5 submissions (no duplicates), got {after_count - before_count}"
                )

            # 8. BOTH JUDGE0 AND PISTON UNAVAILABLE -> CLEAR 503 (NEVER FAKE SUCCESS)
            both_down_settings = base_settings.model_copy(
                update={
                    "judge0_base_url": "http://127.0.0.1:19999",
                    "piston_base_url": "http://127.0.0.1:19998",
                    "execution_fallback_enabled": True,
                    "piston_enabled": True,
                }
            )
            down_app = _build_test_app(both_down_settings, db_manager)
            async with AsyncClient(
                transport=ASGITransport(app=down_app), base_url="http://testserver"
            ) as down_api:
                down_resp = await down_api.post(
                    "/api/v1/submissions",
                    headers=hdr_a,
                    json={
                        "problem_id": prob_id,
                        "language_slug": "python",
                        "submission_kind": "run",
                        "source_code": SUM_EVEN_VALID["python"],
                    },
                )
                assert down_resp.status_code == 503, down_resp.text

            # 9. Admin Operations Health reports BOTH judge0 & piston_fallback as ok
            async for sess in db_manager.session():
                await sess.execute(
                    text(
                        "INSERT INTO public.user_roles (user_id, role) "
                        "VALUES (:uid, 'admin') "
                        "ON CONFLICT (user_id, role) DO NOTHING"
                    ),
                    {"uid": user_a_id},
                )
                await sess.commit()
                break

            ops_resp = await api.get("/api/v1/admin/operations/health", headers=hdr_a)
            assert ops_resp.status_code == 200, ops_resp.text
            checks = {c["name"]: c for c in ops_resp.json()["checks"]}
            assert checks["judge0"]["status"] == "ok", checks["judge0"]
            assert checks["piston_fallback"]["status"] == "ok", checks["piston_fallback"]
    finally:
        await db_manager.dispose()
