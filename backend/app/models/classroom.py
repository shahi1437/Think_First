"""SQLAlchemy 2.x ORM models for Phase 7 Classrooms, Assignments, Grading & Audit."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    teacher_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("public.profiles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    term: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    enrollment_policy: Mapped[str] = mapped_column(
        String(32), nullable=False, default="open_with_code"
    )
    allow_student_leave: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="active")
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    invitations: Mapped[list["ClassInvitation"]] = relationship(
        back_populates="course", cascade="all, delete-orphan"
    )
    memberships: Mapped[list["CourseMembership"]] = relationship(
        back_populates="course", cascade="all, delete-orphan"
    )
    assignments: Mapped[list["Assignment"]] = relationship(
        back_populates="course", cascade="all, delete-orphan"
    )


class ClassInvitation(Base):
    __tablename__ = "class_invitations"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    course_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("public.courses.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_by: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("public.profiles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    code_hash: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    code_preview: Mapped[str] = mapped_column(String(32), nullable=False)
    max_uses: Mapped[int | None] = mapped_column(Integer, nullable=True)
    uses_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    course: Mapped[Course] = relationship(back_populates="invitations")


class CourseMembership(Base):
    __tablename__ = "course_memberships"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    course_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("public.courses.id", ondelete="CASCADE"),
        nullable=False,
    )
    student_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("public.profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="active")
    joined_via_invitation_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("public.class_invitations.id", ondelete="SET NULL"),
        nullable=True,
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    approved_by: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("public.profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    course: Mapped[Course] = relationship(back_populates="memberships")


class Assignment(Base):
    __tablename__ = "assignments"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    course_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("public.courses.id", ondelete="CASCADE"),
        nullable=False,
    )
    teacher_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("public.profiles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    instructions_md: Mapped[str] = mapped_column(Text, nullable=False, default="")
    opens_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    max_marks: Mapped[Decimal] = mapped_column(
        Numeric(6, 2), nullable=False, default=Decimal("100.00")
    )
    grading_policy: Mapped[str] = mapped_column(
        String(32), nullable=False, default="judge0_assisted_manual"
    )
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    allow_ai_hints: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    hint_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    allow_late_submissions: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    allow_resubmission_on_revision: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="draft")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    course: Mapped[Course] = relationship(back_populates="assignments")
    problem_links: Mapped[list["AssignmentProblemLink"]] = relationship(
        back_populates="assignment",
        cascade="all, delete-orphan",
        order_by="AssignmentProblemLink.ordinal",
    )


class AssignmentProblemLink(Base):
    __tablename__ = "assignment_problem_links"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    assignment_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("public.assignments.id", ondelete="CASCADE"),
        nullable=False,
    )
    problem_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("public.problems.id", ondelete="RESTRICT"),
        nullable=False,
    )
    problem_version_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("public.problem_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    points: Mapped[Decimal] = mapped_column(
        Numeric(6, 2), nullable=False, default=Decimal("100.00")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    assignment: Mapped[Assignment] = relationship(back_populates="problem_links")


class AssignmentSubmission(Base):
    __tablename__ = "assignment_submissions"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    assignment_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("public.assignments.id", ondelete="CASCADE"),
        nullable=False,
    )
    course_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("public.courses.id", ondelete="CASCADE"),
        nullable=False,
    )
    student_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("public.profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="in_progress")
    attempts_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    latest_attempt_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    is_late: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resubmitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    attempts: Mapped[list["AssignmentAttempt"]] = relationship(
        back_populates="assignment_submission",
        cascade="all, delete-orphan",
        order_by="AssignmentAttempt.submitted_at.desc()",
    )
    grade: Mapped["AssignmentGrade | None"] = relationship(
        back_populates="assignment_submission",
        uselist=False,
        cascade="all, delete-orphan",
    )
    feedback_entries: Mapped[list["TeacherFeedback"]] = relationship(
        back_populates="assignment_submission",
        cascade="all, delete-orphan",
        order_by="TeacherFeedback.created_at.desc()",
    )


class AssignmentAttempt(Base):
    __tablename__ = "assignment_attempts"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    assignment_submission_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("public.assignment_submissions.id", ondelete="CASCADE"),
        nullable=False,
    )
    assignment_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("public.assignments.id", ondelete="CASCADE"),
        nullable=False,
    )
    course_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("public.courses.id", ondelete="CASCADE"),
        nullable=False,
    )
    student_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("public.profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    problem_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("public.problems.id", ondelete="RESTRICT"),
        nullable=False,
    )
    problem_version_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("public.problem_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    execution_submission_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("public.submissions.id", ondelete="SET NULL"),
        nullable=True,
    )
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    language_slug: Mapped[str] = mapped_column(String(32), nullable=False, default="python")
    source_code: Mapped[str] = mapped_column(Text, nullable=False)
    student_notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    verdict: Mapped[str] = mapped_column(String(32), nullable=False)
    passed_tests: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_tests: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    hints_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_late: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    assignment_submission: Mapped[AssignmentSubmission] = relationship(back_populates="attempts")


class AssignmentGrade(Base):
    __tablename__ = "assignment_grades"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    assignment_submission_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("public.assignment_submissions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    assignment_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("public.assignments.id", ondelete="CASCADE"),
        nullable=False,
    )
    course_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("public.courses.id", ondelete="CASCADE"),
        nullable=False,
    )
    student_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("public.profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    graded_by: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("public.profiles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    marks_awarded: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    max_marks: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="draft")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    assignment_submission: Mapped[AssignmentSubmission] = relationship(back_populates="grade")


class TeacherFeedback(Base):
    __tablename__ = "teacher_feedback"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    assignment_submission_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("public.assignment_submissions.id", ondelete="CASCADE"),
        nullable=False,
    )
    assignment_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("public.assignments.id", ondelete="CASCADE"),
        nullable=False,
    )
    course_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("public.courses.id", ondelete="CASCADE"),
        nullable=False,
    )
    student_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("public.profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    teacher_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("public.profiles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    feedback_type: Mapped[str] = mapped_column(String(32), nullable=False, default="comment")
    body_md: Mapped[str] = mapped_column(Text, nullable=False)
    is_visible_to_student: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    assignment_submission: Mapped[AssignmentSubmission] = relationship(
        back_populates="feedback_entries"
    )


class GradingAuditEvent(Base):
    __tablename__ = "grading_audit_events"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    assignment_submission_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("public.assignment_submissions.id", ondelete="CASCADE"),
        nullable=False,
    )
    assignment_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("public.assignments.id", ondelete="CASCADE"),
        nullable=False,
    )
    course_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("public.courses.id", ondelete="CASCADE"),
        nullable=False,
    )
    actor_user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("public.profiles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    previous_marks: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    new_marks: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    previous_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    new_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
