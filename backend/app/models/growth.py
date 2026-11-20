"""SQLAlchemy 2.x ORM models for Phase 6 Learning DNA, Daily Plans, and Retention."""

from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class LearningDnaSnapshot(Base):
    __tablename__ = "learning_dna_snapshots"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    student_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("public.profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    selected_track_slug: Mapped[str] = mapped_column(
        String(48),
        ForeignKey("public.learning_tracks.slug", ondelete="RESTRICT"),
        nullable=False,
    )
    dimensions_json: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    skill_state_summary: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    strengths: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)
    growth_areas: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)
    source_counts: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class DailyLearningPlan(Base):
    __tablename__ = "daily_learning_plans"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    student_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("public.profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    plan_date: Mapped[date] = mapped_column(Date, nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    selected_track_slug: Mapped[str] = mapped_column(
        String(48),
        ForeignKey("public.learning_tracks.slug", ondelete="RESTRICT"),
        nullable=False,
    )
    available_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=45)
    total_estimated_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    generation_reason_en: Mapped[str] = mapped_column(Text, nullable=False, default="")
    generation_reason_bn: Mapped[str] = mapped_column(Text, nullable=False, default="")
    evidence_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    tasks: Mapped[list["DailyPlanTask"]] = relationship(
        back_populates="plan",
        cascade="all, delete-orphan",
        order_by="DailyPlanTask.task_order",
    )


class DailyPlanTask(Base):
    __tablename__ = "daily_plan_tasks"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    plan_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("public.daily_learning_plans.id", ondelete="CASCADE"),
        nullable=False,
    )
    student_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("public.profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    task_order: Mapped[int] = mapped_column(Integer, nullable=False)
    task_type: Mapped[str] = mapped_column(String(32), nullable=False)
    skill_slug: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("public.skill_nodes.slug", ondelete="SET NULL"),
        nullable=True,
    )
    target_id: Mapped[str] = mapped_column(Text, nullable=False)
    target_slug: Mapped[str] = mapped_column(Text, nullable=False)
    title_en: Mapped[str] = mapped_column(Text, nullable=False)
    title_bn: Mapped[str] = mapped_column(Text, nullable=False)
    reason_en: Mapped[str] = mapped_column(Text, nullable=False)
    reason_bn: Mapped[str] = mapped_column(Text, nullable=False)
    href: Mapped[str] = mapped_column(Text, nullable=False)
    estimated_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=15)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completion_evidence_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    plan: Mapped[DailyLearningPlan] = relationship(back_populates="tasks")


class RetentionSchedule(Base):
    __tablename__ = "retention_schedules"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    student_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("public.profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    skill_slug: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("public.skill_nodes.slug", ondelete="CASCADE"),
        nullable=False,
    )
    problem_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("public.problems.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_evidence_type: Mapped[str] = mapped_column(String(48), nullable=False)
    source_evidence_ref_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_verified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    interval_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=24)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="scheduled")
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class RetentionAttempt(Base):
    __tablename__ = "retention_attempts"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    schedule_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("public.retention_schedules.id", ondelete="CASCADE"),
        nullable=False,
    )
    student_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("public.profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    skill_slug: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("public.skill_nodes.slug", ondelete="CASCADE"),
        nullable=False,
    )
    problem_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("public.problems.id", ondelete="CASCADE"),
        nullable=False,
    )
    submission_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("public.submissions.id", ondelete="SET NULL"),
        nullable=True,
    )
    language_slug: Mapped[str] = mapped_column(String(32), nullable=False, default="python")
    source_code: Mapped[str] = mapped_column(Text, nullable=False)
    student_explanation: Mapped[str] = mapped_column(Text, nullable=False)
    verdict: Mapped[str] = mapped_column(String(32), nullable=False)
    passed_tests: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_tests: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    elapsed_hours_since_initial: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    outcome: Mapped[str] = mapped_column(String(32), nullable=False)
    summary_message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
