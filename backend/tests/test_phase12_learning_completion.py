"""Offline unit, RBAC, and API tests for Phase 12 learning completion enhancements."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1.deps import (
    get_current_user,
    get_learning_history_service,
    get_notification_service,
    get_problem_service,
    get_teacher_analytics_service,
)
from app.core.config import Settings
from app.main import create_app
from app.repositories.identity import UserRecord
from app.schemas.admin import (
    AdminExecutionFailureStats,
    AdminOperationsHealthResponse,
    AdminUserActivityOverview,
)
from app.schemas.identity import RoleName
from app.services.classroom.analytics_service import TeacherAnalyticsService
from app.services.growth.history_service import LearningHistoryService
from app.services.notifications.service import NotificationService
from app.services.problems.service import ProblemService


def _make_user(*roles: RoleName, email: str | None = None) -> UserRecord:
    uid = uuid4()
    now = datetime.now(UTC)
    return UserRecord(
        id=uid,
        email=email or f"{roles[0]}-{uid.hex[:6]}@thinkfirst.test",
        full_name=f"Test {roles[0].title()}",
        avatar_url=None,
        onboarding_completed=True,
        onboarding_completed_at=now,
        created_at=now,
        roles=list(roles),
        preferences=None,
    )


class _FakeProblemRepo:
    def __init__(self, *, solved_id: UUID, weak_id: UUID) -> None:
        now = datetime.now(UTC)
        self._rows = [
            (
                SimpleNamespace(id=solved_id, slug="sum-two"),
                SimpleNamespace(
                    id=uuid4(),
                    title="Sum of Two Numbers",
                    difficulty="beginner",
                    track_slug="absolute_beginner",
                    mode="coding",
                    topics=["basics"],
                    skills=["variables"],
                    variants=[SimpleNamespace(language_slug="python")],
                    published_at=now,
                ),
            ),
            (
                SimpleNamespace(id=weak_id, slug="loop-bounds"),
                SimpleNamespace(
                    id=uuid4(),
                    title="Fix Off-By-One Loop",
                    difficulty="basic",
                    track_slug="basic_university",
                    mode="debugging",
                    topics=["loops"],
                    skills=["loops"],
                    variants=[
                        SimpleNamespace(language_slug="python"),
                        SimpleNamespace(language_slug="cpp"),
                    ],
                    published_at=now,
                ),
            ),
        ]
        self._solved_id = solved_id
        self._weak_id = weak_id

    async def list_published_problems(self, **_kw: Any) -> tuple[list[Any], int]:
        return self._rows, len(self._rows)

    async def get_student_problem_progress_map(self, _sid: UUID) -> dict[UUID, tuple[int, bool]]:
        return {self._solved_id: (2, True), self._weak_id: (1, False)}

    async def list_student_weak_skills(self, _sid: UUID) -> set[str]:
        return {"loops"}


class _FakeHistoryGrowthRepo:
    def __init__(self) -> None:
        now = datetime.now(UTC)
        old = now - timedelta(days=10)
        self._now = now
        self._old = old

    async def list_student_lesson_progress_with_meta(self, **_kw: Any) -> list[Any]:
        return []

    async def list_student_diagnostic_sessions(self, **_kw: Any) -> list[Any]:
        return []

    async def list_student_submissions_all(self, **_kw: Any) -> list[Any]:
        prob = SimpleNamespace(id=uuid4(), slug="loop-bounds")
        ver = SimpleNamespace(title="Fix Off-By-One Loop", skills=["loops"])
        return [
            (
                SimpleNamespace(
                    id=uuid4(),
                    submission_kind="submit",
                    verdict="accepted",
                    passed_tests=3,
                    total_tests=3,
                    language_slug="python",
                    created_at=self._now,
                ),
                prob,
                ver,
            ),
            (
                SimpleNamespace(
                    id=uuid4(),
                    submission_kind="run",
                    verdict="wrong_answer",
                    passed_tests=1,
                    total_tests=3,
                    language_slug="python",
                    created_at=self._old,
                ),
                prob,
                ver,
            ),
        ]

    async def list_student_revisions(self, **_kw: Any) -> list[Any]:
        return []

    async def list_student_mentor_turns(self, **_kw: Any) -> list[Any]:
        return []

    async def list_student_hint_events(self, **_kw: Any) -> list[Any]:
        return []

    async def list_student_verification_attempts_all(self, **_kw: Any) -> list[Any]:
        return []

    async def list_student_skill_transitions_all(self, **_kw: Any) -> list[Any]:
        return []

    async def list_student_completed_daily_tasks(self, **_kw: Any) -> list[Any]:
        return []

    async def list_retention_attempts(self, **_kw: Any) -> list[Any]:
        return []

    async def list_student_diagnoses(self, **_kw: Any) -> list[Any]:
        return [
            SimpleNamespace(
                id=uuid4(),
                predicted_error_code="loop_boundary_error",
                confidence=0.91,
                model_version_tag="error-clf-v1.0.0",
                created_at=self._now - timedelta(minutes=5),
            )
        ]


class _FakeNotifRepo:
    def __init__(self) -> None:
        self.rows: dict[UUID, Any] = {}
        self.keys: dict[tuple[UUID, str], UUID] = {}

    async def upsert_notification_by_source_key(
        self,
        *,
        recipient_user_id: UUID,
        actor_user_id: UUID | None,
        recipient_role: RoleName,
        category: str,
        title: str,
        body: str,
        href: str | None = None,
        source_key: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Any:
        if source_key and (recipient_user_id, source_key) in self.keys:
            return self.rows[self.keys[(recipient_user_id, source_key)]]
        nid = uuid4()
        row = SimpleNamespace(
            id=nid,
            recipient_user_id=recipient_user_id,
            actor_user_id=actor_user_id,
            recipient_role=recipient_role,
            category=category,
            title=title,
            body=body,
            href=href,
            source_key=source_key,
            metadata_json=metadata or {},
            is_read=False,
            read_at=None,
            created_at=datetime.now(UTC),
        )
        self.rows[nid] = row
        if source_key:
            self.keys[(recipient_user_id, source_key)] = nid
        return row

    async def list_notifications(
        self, *, recipient_user_id: UUID, **_kw: Any
    ) -> tuple[list[Any], int, int]:
        mine = [r for r in self.rows.values() if r.recipient_user_id == recipient_user_id]
        unread = sum(1 for r in mine if not r.is_read)
        return mine, len(mine), unread


class _FakeClassroomRepo:
    def __init__(self, *, teacher_id: UUID, student_id: UUID) -> None:
        self.course_id = uuid4()
        self.assignment_id = uuid4()
        self.student_id = student_id
        self.course = SimpleNamespace(
            id=self.course_id,
            teacher_id=teacher_id,
            code="CS202",
            title="Algorithms Lab",
        )
        self.membership = SimpleNamespace(
            id=uuid4(),
            course_id=self.course_id,
            student_id=student_id,
            status="active",
        )
        self.assignment = SimpleNamespace(
            id=self.assignment_id,
            course_id=self.course_id,
            teacher_id=teacher_id,
            title="Binary Search Debug",
            due_at=datetime.now(UTC) + timedelta(hours=18),
            max_marks=Decimal("100.00"),
        )
        self.sub = SimpleNamespace(
            id=uuid4(),
            assignment_id=self.assignment_id,
            student_id=student_id,
            status="in_progress",
            attempts_used=1,
            submitted_at=None,
            attempts=[SimpleNamespace(verdict="wrong_answer")],
            grade=None,
            feedback_entries=[
                SimpleNamespace(
                    id=uuid4(),
                    teacher_id=teacher_id,
                    body_md="Double check the right pointer boundary.",
                    is_visible_to_student=True,
                )
            ],
        )

    async def list_student_memberships(self, **_kw: Any) -> list[Any]:
        return [(self.membership, self.course)]

    async def list_assignments_for_courses(self, **_kw: Any) -> list[Any]:
        return [self.assignment]

    async def list_submissions_for_student(self, **_kw: Any) -> dict[UUID, Any]:
        return {self.assignment_id: self.sub}

    async def get_course_by_id(self, course_id: UUID) -> Any | None:
        return self.course if course_id == self.course_id else None

    async def get_membership(self, *, course_id: UUID, student_id: UUID) -> Any | None:
        if course_id == self.course_id and student_id == self.student_id:
            return self.membership
        return None

    async def get_profiles_map(self, user_ids: list[UUID]) -> dict[UUID, Any]:
        return {
            uid: SimpleNamespace(full_name="Enrolled Learner", email="learner@thinkfirst.test")
            for uid in user_ids
        }

    async def list_attempts_for_courses(self, _course_ids: list[UUID]) -> list[Any]:
        return [
            SimpleNamespace(
                course_id=self.course_id,
                student_id=self.student_id,
                verdict="wrong_answer",
                hints_used=1,
            )
        ]

    async def count_misconceptions_for_students(self, _sids: list[UUID]) -> list[tuple[str, int]]:
        return [("loop_boundary_error", 2)]

    async def aggregate_skill_gaps_for_students(
        self, _sids: list[UUID], *, limit: int | None = 8
    ) -> list[tuple[str, int, int]]:
        self.last_skill_limit = limit
        rows = [(f"dev_skill_{i}", 1, 0) for i in range(8)] + [("variables", 0, 1)]
        return rows if limit is None else rows[:limit]

    async def count_hints_and_transfers_for_students(self, _sids: list[UUID]) -> tuple[int, int]:
        return (2, 1)


@pytest.mark.asyncio
async def test_adaptive_problem_bank_and_history_filters_and_deadline_notifications() -> None:
    student = _make_user("student")
    teacher = _make_user("teacher")
    other_teacher = _make_user("teacher")
    solved_id = uuid4()
    weak_id = uuid4()

    prob_repo = _FakeProblemRepo(solved_id=solved_id, weak_id=weak_id)
    hist_repo = _FakeHistoryGrowthRepo()
    notif_repo = _FakeNotifRepo()
    cls_repo = _FakeClassroomRepo(teacher_id=teacher.id, student_id=student.id)

    active_user: dict[str, UserRecord] = {"user": student}
    app = create_app(Settings(app_env="test", rate_limit_enabled=False))
    app.dependency_overrides[get_current_user] = lambda: active_user["user"]
    app.dependency_overrides[get_problem_service] = lambda: ProblemService(
        prob_repo,  # type: ignore[arg-type]
        None,  # type: ignore[arg-type]
    )
    app.dependency_overrides[get_learning_history_service] = lambda: LearningHistoryService(
        growth_repo=hist_repo  # type: ignore[arg-type]
    )
    app.dependency_overrides[get_notification_service] = lambda: NotificationService(
        notification_repo=notif_repo,  # type: ignore[arg-type]
        classroom_repo=cls_repo,  # type: ignore[arg-type]
        growth_repo=None,
    )
    app.dependency_overrides[get_teacher_analytics_service] = lambda: TeacherAnalyticsService(
        repo=cls_repo,  # type: ignore[arg-type]
        course_service=None,  # type: ignore[arg-type]
        assignment_service=None,  # type: ignore[arg-type]
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Adaptive Problem Bank returns real completion_status + weak-concept recommendation
        all_probs = await client.get("/api/v1/problems")
        assert all_probs.status_code == 200
        by_id = {item["problem_id"]: item for item in all_probs.json()["items"]}
        assert by_id[str(solved_id)]["completion_status"] == "solved"
        assert by_id[str(solved_id)]["is_recommended"] is False
        assert by_id[str(weak_id)]["completion_status"] == "attempted"
        assert by_id[str(weak_id)]["is_recommended"] is True
        assert "loops" in (by_id[str(weak_id)]["recommendation_reason"] or "").lower()

        rec_only = await client.get("/api/v1/problems?recommended_only=true")
        assert rec_only.status_code == 200
        assert len(rec_only.json()["items"]) == 1
        assert rec_only.json()["items"][0]["problem_id"] == str(weak_id)

        # 2. Student Learning History filters (status_filter, date_from, ML diagnoses included)
        hist_all = await client.get("/api/v1/growth/history")
        assert hist_all.status_code == 200
        titles = [it["title_en"] for it in hist_all.json()["items"]]
        assert any("ML Error Diagnosis" in t for t in titles)

        hist_failed = await client.get("/api/v1/growth/history?status_filter=failed")
        assert hist_failed.status_code == 200
        assert len(hist_failed.json()["items"]) == 1
        assert hist_failed.json()["items"][0]["verdict_or_status"] == "wrong_answer"

        today_iso = datetime.now(UTC).date().isoformat()
        hist_recent = await client.get(f"/api/v1/growth/history?date_from={today_iso}")
        assert hist_recent.status_code == 200
        assert all(it["occurred_at"][:10] >= today_iso for it in hist_recent.json()["items"])

        # 3. Notification Automation: upcoming deadline reminder + published teacher feedback
        notifs = await client.get("/api/v1/notifications?role=student")
        assert notifs.status_code == 200
        notif_titles = [n["title"] for n in notifs.json()["items"]]
        assert any("Deadline approaching:" in t for t in notif_titles)
        assert any("Instructor feedback:" in t for t in notif_titles)

        # 4. Teacher Individual Student Drill-Down & RBAC
        active_user["user"] = teacher
        perf_ok = await client.get(
            f"/api/v1/teacher/classes/{cls_repo.course_id}/students/{student.id}/performance"
        )
        assert perf_ok.status_code == 200
        pdata = perf_ok.json()
        assert cls_repo.last_skill_limit is None
        assert pdata["verified_skills"] == ["variables"]
        assert len(pdata["developing_skills"]) == 8
        assert pdata["hints_used_total"] == 3
        assert len(pdata["assignments"]) == 1

        # Unrelated teacher is blocked (403)
        active_user["user"] = other_teacher
        perf_forb = await client.get(
            f"/api/v1/teacher/classes/{cls_repo.course_id}/students/{student.id}/performance"
        )
        assert perf_forb.status_code == 403

        # Non-enrolled student returns 404
        active_user["user"] = teacher
        perf_404 = await client.get(
            f"/api/v1/teacher/classes/{cls_repo.course_id}/students/{uuid4()}/performance"
        )
        assert perf_404.status_code == 404

    # 5. Admin observability schema integrity
    health_model = AdminOperationsHealthResponse(
        overall_status="ok",
        environment="test",
        rate_limit_enabled=True,
        llm_provider_mode="live_llm",
        llm_provider="gemini",
        llm_model="gemini-2.5-flash-lite",
        execution_stats=AdminExecutionFailureStats(
            window_days=7,
            total_executions=10,
            accepted_executions=7,
            failed_executions=3,
            failure_rate_pct=30.0,
            verdict_counts={"accepted": 7, "wrong_answer": 3},
            failures_by_language={"python": 3},
        ),
        activity_overview=AdminUserActivityOverview(
            active_learners_24h=4,
            active_learners_7d=9,
            submissions_24h=12,
            diagnoses_24h=5,
            notifications_total=20,
        ),
    )
    assert health_model.execution_stats is not None
    assert health_model.execution_stats.failure_rate_pct == 30.0
    assert health_model.activity_overview is not None
    assert health_model.activity_overview.active_learners_7d == 9


@pytest.mark.asyncio
async def test_pr10_hardening_eager_loads_and_submit_only_solved() -> None:
    """Verify eager-loaded assignment relations, submit-only solved, and full student skills."""
    from app.repositories.classroom import ClassroomRepository
    from app.repositories.problems import ProblemRepository

    captured_stmts: list[Any] = []

    class _CaptureSession:
        async def execute(self, stmt: Any) -> Any:
            captured_stmts.append(stmt)
            return SimpleNamespace(
                scalars=lambda: SimpleNamespace(all=lambda: []),
                all=lambda: [],
            )

    cap_sess = _CaptureSession()
    cls_repo = ClassroomRepository(cap_sess)  # type: ignore[arg-type]
    await cls_repo.list_submissions_for_student(
        student_id=uuid4(),
        assignment_ids=[uuid4()],
    )
    assert len(captured_stmts) == 1
    opt_paths = {str(opt.path) for opt in captured_stmts[0]._with_options if hasattr(opt, "path")}
    assert any("attempts" in p for p in opt_paths)
    assert any("grade" in p for p in opt_paths)
    assert any("feedback_entries" in p for p in opt_paths)

    captured_stmts.clear()
    prob_repo = ProblemRepository(cap_sess)  # type: ignore[arg-type]
    await prob_repo.get_student_problem_progress_map(uuid4())
    assert len(captured_stmts) == 1
    compiled_sql = str(captured_stmts[0].compile(compile_kwargs={"literal_binds": True})).lower()
    assert "submission_kind = 'submit'" in compiled_sql
    assert "verdict = 'accepted'" in compiled_sql

    # Verify aggregate_skill_gaps_for_students returns all skills when limit=None
    class _NineSkillSession:
        async def execute(self, _stmt: Any) -> Any:
            rows = [(f"dev_{i}", "guided", 1) for i in range(8)] + [
                ("verified_arrays", "independent", 1)
            ]
            return SimpleNamespace(all=lambda: rows)

    skill_repo = ClassroomRepository(_NineSkillSession())  # type: ignore[arg-type]
    all_rows = await skill_repo.aggregate_skill_gaps_for_students([uuid4()], limit=None)
    assert len(all_rows) == 9
    assert any(slug == "verified_arrays" and verif == 1 for slug, _u, verif in all_rows)
    capped_rows = await skill_repo.aggregate_skill_gaps_for_students([uuid4()])
    assert len(capped_rows) == 8
