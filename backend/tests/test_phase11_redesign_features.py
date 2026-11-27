"""Offline unit, RBAC, and API tests for Timeline, Verified Progress, and Notifications."""

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
    get_debugging_timeline_service,
    get_notification_service,
    get_verified_progress_service,
)
from app.core.config import Settings
from app.main import create_app
from app.repositories.identity import UserRecord
from app.schemas.identity import RoleName
from app.schemas.notifications import NotificationCategory
from app.services.growth.debugging_timeline_service import DebuggingTimelineService
from app.services.growth.verified_progress_service import VerifiedProgressService
from app.services.notifications.service import NotificationService


def _make_user(*roles: RoleName, email: str | None = None) -> UserRecord:
    uid = uuid4()
    now = datetime.now(UTC)
    return UserRecord(
        id=uid,
        email=email or f"{roles[0]}-{uid.hex[:6]}@thinkfirst.test",
        full_name=f"Test {roles[0].title()}",
        avatar_url=None,
        roles=list(roles),
        onboarding_completed=True,
        onboarding_completed_at=now,
        created_at=now,
    )


class _InMemoryNotificationRepo:
    def __init__(self) -> None:
        self.rows: dict[UUID, SimpleNamespace] = {}
        self._source_keys: set[tuple[UUID, str]] = set()

    async def upsert_notification_by_source_key(
        self,
        *,
        recipient_user_id: UUID,
        actor_user_id: UUID | None,
        recipient_role: RoleName,
        category: NotificationCategory,
        title: str,
        body: str,
        href: str | None,
        source_key: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        key = (recipient_user_id, source_key)
        if key in self._source_keys:
            return
        self._source_keys.add(key)
        await self.create_notification(
            recipient_user_id=recipient_user_id,
            actor_user_id=actor_user_id,
            recipient_role=recipient_role,
            category=category,
            title=title,
            body=body,
            href=href,
            metadata=metadata,
        )

    async def create_notification(
        self,
        *,
        recipient_user_id: UUID,
        actor_user_id: UUID | None,
        recipient_role: RoleName,
        category: NotificationCategory,
        title: str,
        body: str,
        href: str | None,
        metadata: dict[str, Any] | None = None,
    ) -> Any:
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
            metadata_json=dict(metadata or {}),
            is_read=False,
            read_at=None,
            created_at=datetime.now(UTC),
        )
        self.rows[nid] = row
        return row

    async def list_notifications(
        self,
        *,
        recipient_user_id: UUID,
        role: RoleName | None = None,
        category: NotificationCategory | None = None,
        unread_only: bool = False,
        limit: int = 30,
        offset: int = 0,
    ) -> tuple[list[Any], int, int]:
        own = [r for r in self.rows.values() if r.recipient_user_id == recipient_user_id]
        if role is not None:
            own = [r for r in own if r.recipient_role == role]
        unread_count = sum(1 for r in own if not r.is_read)
        filtered = own
        if category is not None:
            filtered = [r for r in filtered if r.category == category]
        if unread_only:
            filtered = [r for r in filtered if not r.is_read]
        filtered.sort(key=lambda r: r.created_at, reverse=True)
        return filtered[offset : offset + limit], len(filtered), unread_count

    async def mark_read(self, *, recipient_user_id: UUID, notification_id: UUID) -> Any | None:
        row = self.rows.get(notification_id)
        if row is None or row.recipient_user_id != recipient_user_id:
            return None
        row.is_read = True
        row.read_at = datetime.now(UTC)
        return row

    async def mark_all_read(self, *, recipient_user_id: UUID, role: RoleName | None = None) -> int:
        count = 0
        for row in self.rows.values():
            if row.recipient_user_id != recipient_user_id:
                continue
            if role is not None and row.recipient_role != role:
                continue
            if not row.is_read:
                row.is_read = True
                row.read_at = datetime.now(UTC)
                count += 1
        return count


class _FakeGrowthRepo:
    def __init__(self, *, problem_id: UUID, student_id: UUID) -> None:
        base = datetime.now(UTC) - timedelta(hours=1)
        prob = SimpleNamespace(id=problem_id, slug="debug-range-sum-off-by-one")
        ver = SimpleNamespace(
            id=uuid4(),
            problem_id=problem_id,
            title="Debug Range Sum Off-By-One",
            starter_code="def range_sum(a, b):\n    return sum(range(a, b))\n",
            skills=["loops"],
        )
        sub1_id = uuid4()
        sub2_id = uuid4()
        self._subs = [
            (
                SimpleNamespace(
                    id=sub1_id,
                    problem_id=problem_id,
                    language_slug="python",
                    submission_kind="run",
                    source_code="print(sum(range(1, 5)))",
                    verdict="wrong_answer",
                    passed_tests=0,
                    total_tests=3,
                    runtime_ms=28,
                    execution_provider="judge0",
                    execution_evidence={"stderr": ""},
                    created_at=base + timedelta(minutes=1),
                ),
                prob,
                ver,
            ),
            (
                SimpleNamespace(
                    id=sub2_id,
                    problem_id=problem_id,
                    language_slug="python",
                    submission_kind="submit",
                    source_code="print(sum(range(1, 6)))",
                    verdict="accepted",
                    passed_tests=3,
                    total_tests=3,
                    runtime_ms=22,
                    execution_provider="judge0",
                    execution_evidence={},
                    created_at=base + timedelta(minutes=8),
                ),
                prob,
                ver,
            ),
        ]
        self._diagnoses = [
            SimpleNamespace(
                id=uuid4(),
                submission_id=sub1_id,
                predicted_error_code="loop_boundary_error",
                confidence=0.87,
                is_low_confidence=False,
                model_version_tag="error-clf-v1.0.0",
                created_at=base + timedelta(minutes=2),
            )
        ]
        sess = SimpleNamespace(id=uuid4(), problem_id=problem_id, explanation_language="en")
        self._hints = [
            (
                SimpleNamespace(
                    id=uuid4(),
                    hint_level=1,
                    hint_text="Check whether Python range(a, b) includes b.",
                    created_at=base + timedelta(minutes=4),
                ),
                sess,
            )
        ]
        self._revs = [
            (
                SimpleNamespace(
                    id=uuid4(),
                    revision_type="debug_fix",
                    source_code="print(sum(range(1, 6)))",
                    prediction_text="Should print 15",
                    explanation_text="Added +1 to include upper bound",
                    created_at=base + timedelta(minutes=6),
                ),
                ver,
            )
        ]
        self._verifs = [
            SimpleNamespace(
                id=uuid4(),
                source_submission_id=sub2_id,
                transfer_problem_id=uuid4(),
                outcome="verified_independent",
                verdict="accepted",
                passed_tests=4,
                total_tests=4,
                hints_used=0,
                created_at=base + timedelta(minutes=12),
            )
        ]
        self._lessons = [
            (
                SimpleNamespace(
                    id=uuid4(),
                    status="completed",
                    exercise_passed=True,
                    completed_at=base,
                    updated_at=base,
                ),
                SimpleNamespace(id=uuid4(), slug="py-loops", language_slug="python"),
                SimpleNamespace(title_en="Loops"),
            )
        ]
        self._retentions = [
            SimpleNamespace(
                id=uuid4(),
                outcome="retained_verified",
                created_at=base + timedelta(minutes=20),
            )
        ]
        self._diags = [SimpleNamespace(id=uuid4(), status="completed")]
        self._schedules = [
            SimpleNamespace(
                id=uuid4(),
                student_id=student_id,
                skill_slug="loops",
                language_slug="python",
                status="due",
                due_at=datetime.now(UTC) - timedelta(hours=1),
            )
        ]

    async def list_student_submissions_all(self, **_kw: Any) -> list[Any]:
        return self._subs

    async def list_student_diagnoses(self, **_kw: Any) -> list[Any]:
        return self._diagnoses

    async def list_student_revisions(self, **_kw: Any) -> list[Any]:
        return self._revs

    async def list_student_hint_events_with_sessions(self, **_kw: Any) -> list[Any]:
        return self._hints

    async def list_student_mentor_turns(self, **_kw: Any) -> list[Any]:
        return []

    async def list_student_verification_attempts_all(self, **_kw: Any) -> list[Any]:
        return self._verifs

    async def list_student_lesson_progress_with_meta(self, **_kw: Any) -> list[Any]:
        return self._lessons

    async def list_retention_attempts(self, **_kw: Any) -> list[Any]:
        return self._retentions

    async def list_student_diagnostic_sessions(self, **_kw: Any) -> list[Any]:
        return self._diags

    async def list_retention_schedules(self, **_kw: Any) -> list[Any]:
        return self._schedules


class _FakeLearningRepo:
    async def list_student_skill_states(self, **_kw: Any) -> list[Any]:
        return [
            SimpleNamespace(skill_slug="loops", state="retained"),
            SimpleNamespace(skill_slug="functions", state="guided"),
        ]


class _FakeClassroomRepo:
    def __init__(self, *, teacher_id: UUID, student_id: UUID) -> None:
        self.course_id = uuid4()
        self.assignment_id = uuid4()
        self.course = SimpleNamespace(
            id=self.course_id,
            teacher_id=teacher_id,
            code="CS101",
            title="Intro to CS",
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
            title="Loops Lab 1",
            due_at=datetime.now(UTC) + timedelta(days=2),
        )
        self.sub = SimpleNamespace(
            id=uuid4(),
            assignment_id=self.assignment_id,
            student_id=student_id,
            status="graded",
            attempts_used=1,
            attempts=[SimpleNamespace(verdict="accepted")],
            grade=SimpleNamespace(
                id=uuid4(),
                status="published",
                marks_awarded=Decimal("92.00"),
                max_marks=Decimal("100.00"),
                graded_by=teacher_id,
            ),
        )

    async def list_student_memberships(self, **_kw: Any) -> list[Any]:
        return [(self.membership, self.course)]

    async def list_assignments_for_courses(self, **_kw: Any) -> list[Any]:
        return [self.assignment]

    async def list_submissions_for_student(self, **_kw: Any) -> dict[UUID, Any]:
        return {self.assignment_id: self.sub}

    async def list_teacher_courses(self, **_kw: Any) -> list[Any]:
        return [self.course]

    async def list_submissions_for_assignment(self, **_kw: Any) -> list[Any]:
        return [self.sub]

    async def get_course_by_id(self, course_id: UUID) -> Any | None:
        return self.course if course_id == self.course_id else None

    async def list_course_memberships(self, course_id: UUID) -> list[Any]:
        return [self.membership] if course_id == self.course_id else []


@pytest.mark.asyncio
async def test_debugging_timeline_and_verified_progress_return_real_chronology_and_separation() -> (
    None
):
    student = _make_user("student")
    teacher = _make_user("teacher")
    prob_id = uuid4()

    growth_repo = _FakeGrowthRepo(problem_id=prob_id, student_id=student.id)
    learning_repo = _FakeLearningRepo()
    classroom_repo = _FakeClassroomRepo(teacher_id=teacher.id, student_id=student.id)

    app = create_app(Settings(app_env="test", rate_limit_enabled=False))
    app.dependency_overrides[get_current_user] = lambda: student
    app.dependency_overrides[get_debugging_timeline_service] = lambda: DebuggingTimelineService(
        growth_repo=growth_repo  # type: ignore[arg-type]
    )
    app.dependency_overrides[get_verified_progress_service] = lambda: VerifiedProgressService(
        growth_repo=growth_repo,  # type: ignore[arg-type]
        learning_repo=learning_repo,  # type: ignore[arg-type]
        classroom_repo=classroom_repo,  # type: ignore[arg-type]
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        tl_res = await client.get("/api/v1/growth/debugging-timeline")
        vp_res = await client.get("/api/v1/growth/verified-progress")

    assert tl_res.status_code == 200
    tl = tl_res.json()
    assert tl["total_journeys"] == 1
    assert tl["solved_journeys"] == 1
    journey = tl["journeys"][0]
    assert journey["outcome_status"] == "verified_transfer"
    assert journey["attempts_count"] == 2
    assert journey["hints_used"] == 1
    assert journey["diagnoses_count"] == 1
    step_kinds = [s["step_kind"] for s in journey["steps"]]
    assert step_kinds == [
        "problem_started",
        "initial_attempt",
        "error_diagnosed",
        "ai_hint",
        "student_correction",
        "successful_execution",
        "learning_outcome",
    ]

    assert vp_res.status_code == 200
    vp = vp_res.json()
    assert vp["problems_attempted"] == 1
    assert vp["problems_solved_verified"] == 1
    assert vp["concepts_mastered_verified"] == ["loops"]
    assert vp["concepts_in_progress"] == ["functions"]
    assert vp["assignments_completed_verified"] == 1
    assert vp["average_published_grade_pct"] == 92.0
    assert vp["transfer_verifications_passed"] == 1
    assert vp["retention_checks_passed"] == 1
    assert vp["improvement_trend"] == "insufficient_data"  # <4 attempts -> never fabricated
    assert vp["estimated_lessons_completed"] == 1
    assert vp["estimated_guided_skills_count"] == 1


@pytest.mark.asyncio
async def test_notification_center_rbac_dedup_read_states_and_teacher_announcement() -> None:
    student = _make_user("student")
    other_student = _make_user("student")
    teacher = _make_user("teacher")
    other_teacher = _make_user("teacher")

    notif_repo = _InMemoryNotificationRepo()
    classroom_repo = _FakeClassroomRepo(teacher_id=teacher.id, student_id=student.id)
    growth_repo = _FakeGrowthRepo(problem_id=uuid4(), student_id=student.id)
    notif_service = NotificationService(
        notification_repo=notif_repo,  # type: ignore[arg-type]
        classroom_repo=classroom_repo,  # type: ignore[arg-type]
        growth_repo=growth_repo,  # type: ignore[arg-type]
    )

    active_user: dict[str, UserRecord] = {"user": teacher}
    app = create_app(Settings(app_env="test", rate_limit_enabled=False))
    app.dependency_overrides[get_current_user] = lambda: active_user["user"]
    app.dependency_overrides[get_notification_service] = lambda: notif_service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Teacher posts class announcement -> delivered to active enrolled student
        ann_res = await client.post(
            f"/api/v1/teacher/classes/{classroom_repo.course_id}/announcements",
            json={"title": "Lab 2 Reminder", "body": "Submit before Friday 18:00 UTC."},
        )
        assert ann_res.status_code == 201
        assert ann_res.json()["recipients_notified"] == 1

        # 2. Unrelated teacher gets 403 on course announcement
        active_user["user"] = other_teacher
        forbidden_teacher = await client.post(
            f"/api/v1/teacher/classes/{classroom_repo.course_id}/announcements",
            json={"title": "Unauthorized", "body": "Should be blocked."},
        )
        assert forbidden_teacher.status_code == 403

        # 3. Student cannot post class announcements (403) or read teacher role notifications (403)
        active_user["user"] = student
        forbidden_student = await client.post(
            f"/api/v1/teacher/classes/{classroom_repo.course_id}/announcements",
            json={"title": "Student Try", "body": "Should be blocked."},
        )
        assert forbidden_student.status_code == 403

        wrong_role = await client.get("/api/v1/notifications?role=teacher")
        assert wrong_role.status_code == 403

        # 4. Student lists notifications twice -> idempotent sync (no duplicate reminders!)
        list1 = await client.get("/api/v1/notifications?role=student")
        list2 = await client.get("/api/v1/notifications?role=student")
        assert list1.status_code == 200
        assert list2.status_code == 200
        assert list1.json()["total"] == list2.json()["total"]
        # announcement + classroom + assignment + grade + retention
        assert list1.json()["unread_count"] >= 4
        categories = {item["category"] for item in list1.json()["items"]}
        assert {"announcement", "assignment", "grading", "classroom", "ai_reminder"}.issubset(
            categories
        )

        # 5. Another student CANNOT mark student's notification read (404)
        first_id = list1.json()["items"][0]["id"]
        active_user["user"] = other_student
        cross_read = await client.patch(f"/api/v1/notifications/{first_id}/read")
        assert cross_read.status_code == 404

        # 6. Owner marks one read, then marks all read
        active_user["user"] = student
        one_read = await client.patch(f"/api/v1/notifications/{first_id}/read")
        assert one_read.status_code == 200
        assert one_read.json()["is_read"] is True

        all_read = await client.post("/api/v1/notifications/read-all", json={"role": "student"})
        assert all_read.status_code == 200
        assert all_read.json()["unread_count"] == 0
