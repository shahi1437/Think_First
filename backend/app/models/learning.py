"""SQLAlchemy 2.x ORM models for Phase 5 Learning Tracks, Lessons, Diagnostics & Skill Graph."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
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


class LearningTrack(Base):
    __tablename__ = "learning_tracks"

    slug: Mapped[str] = mapped_column(String(48), primary_key=True)
    title_en: Mapped[str] = mapped_column(Text, nullable=False)
    title_bn: Mapped[str] = mapped_column(Text, nullable=False)
    summary_en: Mapped[str] = mapped_column(Text, nullable=False)
    summary_bn: Mapped[str] = mapped_column(Text, nullable=False)
    target_audience_en: Mapped[str] = mapped_column(Text, nullable=False)
    target_audience_bn: Mapped[str] = mapped_column(Text, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False)
    recommended_focus_skills: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, default=list
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class StudentTrackEnrollment(Base):
    __tablename__ = "student_track_enrollments"

    student_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("public.profiles.id", ondelete="CASCADE"),
        primary_key=True,
    )
    selected_track_slug: Mapped[str] = mapped_column(
        String(48),
        ForeignKey("public.learning_tracks.slug", ondelete="RESTRICT"),
        nullable=False,
    )
    recommended_track_slug: Mapped[str | None] = mapped_column(
        String(48),
        ForeignKey("public.learning_tracks.slug", ondelete="SET NULL"),
        nullable=True,
    )
    recommendation_source: Mapped[str] = mapped_column(
        String(32), nullable=False, default="onboarding_initial"
    )
    recommendation_reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    diagnostic_session_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class SkillNode(Base):
    __tablename__ = "skill_nodes"

    slug: Mapped[str] = mapped_column(String(64), primary_key=True)
    title_en: Mapped[str] = mapped_column(Text, nullable=False)
    title_bn: Mapped[str] = mapped_column(Text, nullable=False)
    description_en: Mapped[str] = mapped_column(Text, nullable=False)
    description_bn: Mapped[str] = mapped_column(Text, nullable=False)
    domain_slug: Mapped[str] = mapped_column(String(64), nullable=False)
    tier: Mapped[int] = mapped_column(Integer, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class SkillPrerequisite(Base):
    __tablename__ = "skill_prerequisites"

    skill_slug: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("public.skill_nodes.slug", ondelete="CASCADE"),
        primary_key=True,
    )
    prerequisite_slug: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("public.skill_nodes.slug", ondelete="CASCADE"),
        primary_key=True,
    )


class StudentSkillState(Base):
    __tablename__ = "student_skill_states"

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
    state: Mapped[str] = mapped_column(String(32), nullable=False, default="unobserved")
    evidence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    uncertainty_note: Mapped[str] = mapped_column(
        Text, nullable=False, default="No direct evidence recorded yet."
    )
    last_evidence_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_evidence_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    first_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class SkillStateTransition(Base):
    __tablename__ = "skill_state_transitions"

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
    from_state: Mapped[str] = mapped_column(String(32), nullable=False)
    to_state: Mapped[str] = mapped_column(String(32), nullable=False)
    evidence_source: Mapped[str] = mapped_column(String(64), nullable=False)
    evidence_ref_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Lesson(Base):
    __tablename__ = "lessons"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    slug: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    skill_slug: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("public.skill_nodes.slug", ondelete="RESTRICT"),
        nullable=False,
    )
    display_order: Mapped[int] = mapped_column(Integer, nullable=False)
    current_published_version_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("public.lesson_versions.id", ondelete="SET NULL", use_alter=True),
        nullable=True,
    )
    created_by: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("public.profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    versions: Mapped[list["LessonVersion"]] = relationship(
        back_populates="lesson",
        foreign_keys="LessonVersion.lesson_id",
        cascade="all, delete-orphan",
    )


class LessonVersion(Base):
    __tablename__ = "lesson_versions"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    lesson_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("public.lessons.id", ondelete="CASCADE"),
        nullable=False,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title_en: Mapped[str] = mapped_column(Text, nullable=False)
    title_bn: Mapped[str] = mapped_column(Text, nullable=False)
    summary_en: Mapped[str] = mapped_column(Text, nullable=False)
    summary_bn: Mapped[str] = mapped_column(Text, nullable=False)
    content_en_md: Mapped[str] = mapped_column(Text, nullable=False)
    content_bn_md: Mapped[str] = mapped_column(Text, nullable=False)
    learning_objectives: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, default=list
    )
    prerequisite_lesson_slugs: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, default=list
    )
    track_slugs: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)
    interactive_examples: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    guided_exercise: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    estimated_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=15)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    published_by: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("public.profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    lesson: Mapped[Lesson] = relationship(back_populates="versions", foreign_keys=[lesson_id])


class LessonProgress(Base):
    __tablename__ = "lesson_progress"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    student_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("public.profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    lesson_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("public.lessons.id", ondelete="CASCADE"),
        nullable=False,
    )
    lesson_version_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("public.lesson_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="in_progress")
    reading_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    exercise_passed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    exercise_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_verdict: Mapped[str | None] = mapped_column(String(48), nullable=True)
    last_stdout: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_stderr: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class DiagnosticQuestion(Base):
    __tablename__ = "diagnostic_questions"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    slug: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    domain_slug: Mapped[str] = mapped_column(String(48), nullable=False)
    skill_slug: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("public.skill_nodes.slug", ondelete="RESTRICT"),
        nullable=False,
    )
    difficulty: Mapped[str] = mapped_column(String(24), nullable=False)
    question_type: Mapped[str] = mapped_column(String(24), nullable=False)
    prompt_en: Mapped[str] = mapped_column(Text, nullable=False)
    prompt_bn: Mapped[str] = mapped_column(Text, nullable=False)
    code_snippet: Mapped[str | None] = mapped_column(Text, nullable=True)
    options: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    starter_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    language_slug: Mapped[str] = mapped_column(String(32), nullable=False, default="python")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="draft")
    reviewed_by: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("public.profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    answer_key: Mapped["DiagnosticQuestionAnswer | None"] = relationship(
        back_populates="question", uselist=False, cascade="all, delete-orphan"
    )


class DiagnosticQuestionAnswer(Base):
    __tablename__ = "diagnostic_question_answers"

    question_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("public.diagnostic_questions.id", ondelete="CASCADE"),
        primary_key=True,
    )
    correct_option_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    explanation_en: Mapped[str] = mapped_column(Text, nullable=False)
    explanation_bn: Mapped[str] = mapped_column(Text, nullable=False)
    evaluation_tests: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    question: Mapped[DiagnosticQuestion] = relationship(back_populates="answer_key")


class DiagnosticSession(Base):
    __tablename__ = "diagnostic_sessions"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    student_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("public.profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="in_progress")
    explanation_language: Mapped[str] = mapped_column(String(8), nullable=False, default="en")
    question_queue: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    current_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    adaptive_followups_added: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    recommended_track_slug: Mapped[str | None] = mapped_column(
        String(48),
        ForeignKey("public.learning_tracks.slug", ondelete="SET NULL"),
        nullable=True,
    )
    domain_summary: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    recommendation_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    responses: Mapped[list["DiagnosticResponse"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="DiagnosticResponse.created_at",
    )


class DiagnosticResponse(Base):
    __tablename__ = "diagnostic_responses"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    session_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("public.diagnostic_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    student_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("public.profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    question_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("public.diagnostic_questions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    domain_slug: Mapped[str] = mapped_column(String(48), nullable=False)
    difficulty: Mapped[str] = mapped_column(String(24), nullable=False)
    question_type: Mapped[str] = mapped_column(String(24), nullable=False)
    selected_option_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    submitted_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    execution_verdict: Mapped[str | None] = mapped_column(String(48), nullable=True)
    passed_tests: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_tests: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    execution_stderr: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    session: Mapped[DiagnosticSession] = relationship(back_populates="responses")


class StudentRecommendation(Base):
    __tablename__ = "student_recommendations"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    student_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("public.profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    recommendation_type: Mapped[str] = mapped_column(String(32), nullable=False)
    target_id: Mapped[str] = mapped_column(Text, nullable=False)
    target_slug: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False)
    reason_en: Mapped[str] = mapped_column(Text, nullable=False)
    reason_bn: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_factors: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
