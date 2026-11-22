import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class SupportedLanguage(Base):
    """ORM mapping for public.supported_languages."""

    __tablename__ = "supported_languages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    judge0_language_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    monaco_language: Mapped[str] = mapped_column(String(32), nullable=False)
    version_label: Mapped[str] = mapped_column(Text, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Problem(Base):
    """ORM mapping for public.problems."""

    __tablename__ = "problems"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    current_published_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("public.problem_versions.id", ondelete="SET NULL", use_alter=True),
        nullable=True,
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("public.profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    versions: Mapped[list["ProblemVersion"]] = relationship(
        back_populates="problem",
        foreign_keys="ProblemVersion.problem_id",
        cascade="all, delete-orphan",
    )


class ProblemVersion(Base):
    """ORM mapping for public.problem_versions."""

    __tablename__ = "problem_versions"
    __table_args__ = (
        UniqueConstraint("problem_id", "version_number", name="uq_problem_versions_problem_num"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    problem_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("public.problems.id", ondelete="CASCADE"),
        nullable=False,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    statement_md: Mapped[str] = mapped_column(Text, nullable=False)
    difficulty: Mapped[str] = mapped_column(String(32), nullable=False)
    mode: Mapped[str] = mapped_column(String(32), nullable=False)
    topics: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)
    skills: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)
    prerequisites: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)
    learning_objectives: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, default=list
    )
    examples: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    time_limit_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=2000)
    memory_limit_kb: Mapped[int] = mapped_column(Integer, nullable=False, default=131072)
    track_slug: Mapped[str | None] = mapped_column(String(48), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("public.profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    problem: Mapped[Problem] = relationship(back_populates="versions", foreign_keys=[problem_id])
    variants: Mapped[list["ProblemLanguageVariant"]] = relationship(
        back_populates="version", cascade="all, delete-orphan"
    )
    test_cases: Mapped[list["TestCase"]] = relationship(
        back_populates="version", cascade="all, delete-orphan"
    )
    reviews: Mapped[list["ContentReview"]] = relationship(
        back_populates="version", cascade="all, delete-orphan"
    )


class ProblemLanguageVariant(Base):
    """ORM mapping for public.problem_language_variants."""

    __tablename__ = "problem_language_variants"
    __table_args__ = (
        UniqueConstraint(
            "problem_version_id", "language_slug", name="uq_problem_language_variants_ver_lang"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    problem_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("public.problem_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    language_slug: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("public.supported_languages.slug", ondelete="RESTRICT"),
        nullable=False,
    )
    starter_code: Mapped[str] = mapped_column(Text, nullable=False)
    buggy_starter_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    debugging_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    version: Mapped[ProblemVersion] = relationship(back_populates="variants")
    reference_solution: Mapped["ProblemReferenceSolution | None"] = relationship(
        back_populates="variant", uselist=False, cascade="all, delete-orphan"
    )


class ProblemReferenceSolution(Base):
    """ORM mapping for public.problem_reference_solutions (Admin-only private table)."""

    __tablename__ = "problem_reference_solutions"

    variant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("public.problem_language_variants.id", ondelete="CASCADE"),
        primary_key=True,
    )
    reference_solution: Mapped[str] = mapped_column(Text, nullable=False)
    expected_bug_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_failure_category: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    variant: Mapped[ProblemLanguageVariant] = relationship(back_populates="reference_solution")


class TestCase(Base):
    """ORM mapping for public.test_cases."""

    __tablename__ = "test_cases"
    __table_args__ = (
        UniqueConstraint("problem_version_id", "ordinal", name="uq_test_cases_version_ordinal"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    problem_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("public.problem_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    input_data: Mapped[str] = mapped_column(Text, nullable=False, default="")
    expected_output: Mapped[str] = mapped_column(Text, nullable=False)
    is_hidden: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    weight: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    version: Mapped[ProblemVersion] = relationship(back_populates="test_cases")


class Submission(Base):
    """ORM mapping for public.submissions."""

    __tablename__ = "submissions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("public.profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    problem_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("public.problems.id", ondelete="CASCADE"),
        nullable=False,
    )
    problem_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("public.problem_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    language_slug: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("public.supported_languages.slug", ondelete="RESTRICT"),
        nullable=False,
    )
    submission_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    source_code: Mapped[str] = mapped_column(Text, nullable=False)
    prediction_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    explanation_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="queued")
    verdict: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    passed_tests: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_tests: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    runtime_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    memory_kb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    execution_provider: Mapped[str] = mapped_column(String(16), nullable=False, default="judge0")
    execution_evidence: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    results: Mapped[list["ExecutionResult"]] = relationship(
        back_populates="submission", cascade="all, delete-orphan"
    )


class ExecutionResult(Base):
    """ORM mapping for public.execution_results."""

    __tablename__ = "execution_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    submission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("public.submissions.id", ondelete="CASCADE"),
        nullable=False,
    )
    test_case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("public.test_cases.id", ondelete="RESTRICT"),
        nullable=False,
    )
    is_hidden: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    execution_provider: Mapped[str] = mapped_column(String(16), nullable=False, default="judge0")
    judge0_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    judge0_status_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    verdict: Mapped[str] = mapped_column(String(32), nullable=False)
    stdout: Mapped[str | None] = mapped_column(Text, nullable=True)
    stderr: Mapped[str | None] = mapped_column(Text, nullable=True)
    compile_output: Mapped[str | None] = mapped_column(Text, nullable=True)
    runtime_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    memory_kb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    submission: Mapped[Submission] = relationship(back_populates="results")


class CodeRevision(Base):
    """ORM mapping for public.code_revisions."""

    __tablename__ = "code_revisions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("public.profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    problem_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("public.problem_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    language_slug: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("public.supported_languages.slug", ondelete="RESTRICT"),
        nullable=False,
    )
    source_code: Mapped[str] = mapped_column(Text, nullable=False)
    prediction_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    explanation_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    revision_type: Mapped[str] = mapped_column(String(16), nullable=False, default="autosave")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ContentReview(Base):
    """ORM mapping for public.content_reviews."""

    __tablename__ = "content_reviews"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    problem_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("public.problem_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    reviewer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("public.profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    validation_summary: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    version: Mapped[ProblemVersion] = relationship(back_populates="reviews")
