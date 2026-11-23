"""SQLAlchemy ORM models for the outbound execution worker queue."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ExecutionWorker(Base):
    """ORM mapping for public.execution_workers."""

    __tablename__ = "execution_workers"

    worker_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    display_name: Mapped[str] = mapped_column(Text, nullable=False, default="Local Judge0 Runner")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="online")
    judge0_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    supported_languages: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, default=list
    )
    active_job_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_jobs_completed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_jobs_failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_heartbeat_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ExecutionJob(Base):
    """ORM mapping for public.execution_jobs."""

    __tablename__ = "execution_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_type: Mapped[str] = mapped_column(String(16), nullable=False)
    submission_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("public.submissions.id", ondelete="CASCADE"),
        nullable=True,
    )
    requested_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("public.profiles.id", ondelete="CASCADE"),
        nullable=True,
    )
    language_slug: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("public.supported_languages.slug", ondelete="RESTRICT"),
        nullable=False,
    )
    judge0_language_id: Mapped[int] = mapped_column(Integer, nullable=False)
    dedup_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="queued")
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    result_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    claimed_by_worker_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("public.execution_workers.worker_id", ondelete="SET NULL"),
        nullable=True,
    )
    claim_token: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
