from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.mentor import (
    ErrorDiagnosis,
    HintEvent,
    KnowledgeChunk,
    KnowledgeDocument,
    LearningEvent,
    MentorSession,
    MentorTurn,
    ModelVersion,
    VerificationAttempt,
    VerificationLink,
)
from app.models.problems import Problem, ProblemVersion, Submission


class MentorRepository:
    """Async SQLAlchemy repository for ML diagnoses, pgvector RAG, Mentor, and Verification."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # --- Model Versions & Error Diagnoses ---

    async def ensure_model_version(
        self,
        *,
        version_tag: str,
        model_type: str,
        dataset_version: str,
        artifact_path: str,
        metrics: dict[str, Any],
    ) -> ModelVersion:
        stmt = select(ModelVersion).where(ModelVersion.version_tag == version_tag)
        existing = (await self._session.execute(stmt)).scalar_one_or_none()
        if existing is not None:
            return existing
        mv = ModelVersion(
            version_tag=version_tag,
            model_type=model_type,
            dataset_version=dataset_version,
            artifact_path=artifact_path,
            metrics=metrics,
            is_active=True,
        )
        self._session.add(mv)
        await self._session.commit()
        await self._session.refresh(mv)
        return mv

    async def save_diagnosis(
        self,
        *,
        submission_id: UUID,
        student_id: UUID,
        model_version_id: UUID | None,
        model_version_tag: str,
        predicted_error_code: str,
        confidence: float,
        is_low_confidence: bool,
        top_candidates: list[dict[str, Any]],
        feature_summary: dict[str, Any],
    ) -> ErrorDiagnosis:
        diag = ErrorDiagnosis(
            submission_id=submission_id,
            student_id=student_id,
            model_version_id=model_version_id,
            model_version_tag=model_version_tag,
            predicted_error_code=predicted_error_code,
            confidence=confidence,
            is_low_confidence=is_low_confidence,
            top_candidates=top_candidates,
            feature_summary=feature_summary,
        )
        self._session.add(diag)
        await self._session.commit()
        await self._session.refresh(diag)
        return diag

    async def get_latest_diagnosis_for_submission(
        self, submission_id: UUID
    ) -> ErrorDiagnosis | None:
        stmt = (
            select(ErrorDiagnosis)
            .where(ErrorDiagnosis.submission_id == submission_id)
            .order_by(ErrorDiagnosis.created_at.desc())
            .limit(1)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    # --- RAG Knowledge Base (pgvector) ---

    async def upsert_knowledge_document(
        self,
        *,
        slug: str,
        title: str,
        language_slug: str,
        topic: str,
        error_codes: list[str],
        source_name: str,
        source_version: str,
        content_md: str,
        status: str,
        approved_by: UUID | None,
        chunks: list[tuple[int, str, str, list[float]]],
    ) -> KnowledgeDocument:
        stmt = (
            select(KnowledgeDocument)
            .where(KnowledgeDocument.slug == slug)
            .options(selectinload(KnowledgeDocument.chunks))
            .execution_options(populate_existing=True)
        )
        doc = (await self._session.execute(stmt)).scalar_one_or_none()
        now = datetime.now(UTC)

        if doc is None:
            doc = KnowledgeDocument(
                slug=slug,
                title=title,
                language_slug=language_slug,
                topic=topic,
                error_codes=error_codes,
                source_name=source_name,
                source_version=source_version,
                content_md=content_md,
                status=status,
                approved_by=approved_by if status == "approved" else None,
                approved_at=now if status == "approved" else None,
            )
            self._session.add(doc)
            await self._session.flush()
        else:
            doc.title = title
            doc.language_slug = language_slug
            doc.topic = topic
            doc.error_codes = error_codes
            doc.source_name = source_name
            doc.source_version = source_version
            doc.content_md = content_md
            doc.status = status
            if status == "approved" and doc.approved_at is None:
                doc.approved_by = approved_by
                doc.approved_at = now
            for existing_chunk in list(doc.chunks):
                await self._session.delete(existing_chunk)
            await self._session.flush()

        for chunk_idx, heading, text_body, vec in chunks:
            self._session.add(
                KnowledgeChunk(
                    document_id=doc.id,
                    chunk_index=chunk_idx,
                    heading=heading,
                    content=text_body,
                    topic=topic,
                    error_codes=error_codes,
                    token_count=len(text_body.split()),
                    embedding=vec,
                )
            )
        await self._session.commit()

        reloaded = (await self._session.execute(stmt)).scalar_one()
        return reloaded

    async def list_knowledge_documents(
        self, *, approved_only: bool = False
    ) -> list[KnowledgeDocument]:
        stmt = (
            select(KnowledgeDocument)
            .options(selectinload(KnowledgeDocument.chunks))
            .order_by(KnowledgeDocument.topic.asc(), KnowledgeDocument.title.asc())
        )
        if approved_only:
            stmt = stmt.where(KnowledgeDocument.status == "approved")
        return list((await self._session.execute(stmt)).scalars().all())

    async def update_knowledge_status(
        self, *, document_id: UUID, new_status: str, actor_id: UUID
    ) -> KnowledgeDocument | None:
        stmt = (
            select(KnowledgeDocument)
            .where(KnowledgeDocument.id == document_id)
            .options(selectinload(KnowledgeDocument.chunks))
            .execution_options(populate_existing=True)
        )
        doc = (await self._session.execute(stmt)).scalar_one_or_none()
        if doc is None:
            return None
        doc.status = new_status
        if new_status == "approved":
            doc.approved_by = actor_id
            doc.approved_at = datetime.now(UTC)
        await self._session.commit()
        return (await self._session.execute(stmt)).scalar_one()

    async def search_approved_chunks_pgvector(
        self,
        *,
        query_embedding: list[float],
        limit: int = 8,
        topic: str | None = None,
        language_slug: str | None = None,
    ) -> list[tuple[KnowledgeChunk, KnowledgeDocument, float]]:
        """Execute real PostgreSQL pgvector cosine similarity query on approved docs ONLY."""
        distance_expr = KnowledgeChunk.embedding.cosine_distance(query_embedding)
        stmt = (
            select(KnowledgeChunk, KnowledgeDocument, (1.0 - distance_expr).label("similarity"))
            .join(KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id)
            .where(KnowledgeDocument.status == "approved")
        )
        if language_slug:
            stmt = stmt.where(KnowledgeDocument.language_slug == language_slug)
        stmt = stmt.order_by(distance_expr.asc()).limit(limit)
        if topic:
            _ = topic
        rows = (await self._session.execute(stmt)).all()
        return [(row[0], row[1], float(row[2])) for row in rows]

    async def get_chunks_by_ids(
        self, chunk_ids: list[UUID]
    ) -> dict[UUID, tuple[KnowledgeChunk, KnowledgeDocument]]:
        if not chunk_ids:
            return {}
        stmt = (
            select(KnowledgeChunk, KnowledgeDocument)
            .join(KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id)
            .where(
                KnowledgeChunk.id.in_(chunk_ids),
                KnowledgeDocument.status == "approved",
            )
        )
        rows = (await self._session.execute(stmt)).all()
        return {row[0].id: (row[0], row[1]) for row in rows}

    # --- Mentor Sessions, Turns & Hints ---

    async def count_recent_mentor_turns(self, *, student_id: UUID, minutes: int = 1) -> int:
        since = datetime.now(UTC) - timedelta(minutes=minutes)
        stmt = (
            select(func.count())
            .select_from(MentorTurn)
            .join(MentorSession, MentorTurn.session_id == MentorSession.id)
            .where(
                MentorSession.student_id == student_id,
                MentorTurn.role == "mentor",
                MentorTurn.created_at >= since,
            )
        )
        return int((await self._session.execute(stmt)).scalar_one())

    async def get_or_create_session(
        self,
        *,
        student_id: UUID,
        problem_id: UUID,
        problem_version_id: UUID,
        explanation_language: str,
        learner_level: str,
        latest_submission_id: UUID | None,
    ) -> MentorSession:
        stmt = (
            select(MentorSession)
            .where(
                MentorSession.student_id == student_id,
                MentorSession.problem_id == problem_id,
                MentorSession.problem_version_id == problem_version_id,
            )
            .options(selectinload(MentorSession.turns))
            .order_by(MentorSession.updated_at.desc())
            .limit(1)
            .execution_options(populate_existing=True)
        )
        existing = (await self._session.execute(stmt)).scalar_one_or_none()
        if existing is not None:
            if latest_submission_id is not None:
                existing.latest_submission_id = latest_submission_id
            existing.explanation_language = explanation_language
            await self._session.commit()
            return (await self._session.execute(stmt)).scalar_one()

        session_obj = MentorSession(
            student_id=student_id,
            problem_id=problem_id,
            problem_version_id=problem_version_id,
            latest_submission_id=latest_submission_id,
            current_state="awaiting_submission",
            explanation_language=explanation_language,
            learner_level=learner_level,
            hints_used=0,
            provider_mode="deterministic_fallback",
        )
        self._session.add(session_obj)
        await self._session.commit()
        return (await self._session.execute(stmt)).scalar_one()

    async def get_session_by_id(self, session_id: UUID) -> MentorSession | None:
        stmt = (
            select(MentorSession)
            .where(MentorSession.id == session_id)
            .options(selectinload(MentorSession.turns))
            .execution_options(populate_existing=True)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def append_turn(
        self,
        *,
        session: MentorSession,
        role: str,
        state_after: str,
        message_text: str,
        structured_payload: dict[str, Any],
        cited_chunk_ids: list[UUID],
        diagnosis_id: UUID | None,
        provider_mode: str,
        increment_hint: bool = False,
        latest_submission_id: UUID | None = None,
    ) -> MentorTurn:
        next_index = (max((t.turn_index for t in session.turns), default=0)) + 1
        turn = MentorTurn(
            session_id=session.id,
            turn_index=next_index,
            role=role,
            state_after=state_after,
            message_text=message_text,
            structured_payload=structured_payload,
            cited_chunk_ids=cited_chunk_ids,
            diagnosis_id=diagnosis_id,
            provider_mode=provider_mode,
        )
        session.current_state = state_after
        session.provider_mode = provider_mode
        if latest_submission_id is not None:
            session.latest_submission_id = latest_submission_id
        if increment_hint and session.hints_used < 3:
            session.hints_used += 1
        session.turns.append(turn)
        self._session.add(turn)
        await self._session.commit()
        await self._session.refresh(turn)
        return turn

    async def record_hint_event(
        self,
        *,
        session_id: UUID,
        student_id: UUID,
        submission_id: UUID | None,
        hint_level: int,
        hint_text: str,
        cited_chunk_ids: list[UUID],
    ) -> HintEvent:
        ev = HintEvent(
            session_id=session_id,
            student_id=student_id,
            submission_id=submission_id,
            hint_level=hint_level,
            hint_text=hint_text,
            cited_chunk_ids=cited_chunk_ids,
        )
        self._session.add(ev)
        await self._session.commit()
        await self._session.refresh(ev)
        return ev

    async def record_learning_event(
        self,
        *,
        student_id: UUID,
        problem_id: UUID | None,
        problem_version_id: UUID | None,
        language_slug: str | None,
        submission_id: UUID | None,
        diagnosis_id: UUID | None,
        event_type: str,
        hints_used: int = 0,
        verdict: str | None = None,
        verification_outcome: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> LearningEvent:
        ev = LearningEvent(
            student_id=student_id,
            problem_id=problem_id,
            problem_version_id=problem_version_id,
            language_slug=language_slug,
            submission_id=submission_id,
            diagnosis_id=diagnosis_id,
            event_type=event_type,
            hints_used=hints_used,
            verdict=verdict,
            verification_outcome=verification_outcome,
            metadata_json=metadata or {},
        )
        self._session.add(ev)
        await self._session.commit()
        await self._session.refresh(ev)
        return ev

    async def list_learning_events(
        self, *, student_id: UUID, limit: int = 30
    ) -> list[LearningEvent]:
        stmt = (
            select(LearningEvent)
            .where(LearningEvent.student_id == student_id)
            .order_by(LearningEvent.created_at.desc())
            .limit(limit)
        )
        return list((await self._session.execute(stmt)).scalars().all())

    # --- Verification Links & Attempts ---

    async def get_verification_link_for_source_problem(
        self, source_problem_id: UUID
    ) -> tuple[VerificationLink, Problem, ProblemVersion] | None:
        stmt = (
            select(VerificationLink, Problem, ProblemVersion)
            .join(Problem, VerificationLink.transfer_problem_id == Problem.id)
            .join(ProblemVersion, Problem.current_published_version_id == ProblemVersion.id)
            .where(
                VerificationLink.source_problem_id == source_problem_id,
                VerificationLink.is_active.is_(True),
            )
            .limit(1)
        )
        row = (await self._session.execute(stmt)).one_or_none()
        if row is None:
            return None
        return row[0], row[1], row[2]

    async def get_verification_link_by_id(
        self, link_id: UUID
    ) -> tuple[VerificationLink, Problem, ProblemVersion] | None:
        stmt = (
            select(VerificationLink, Problem, ProblemVersion)
            .join(Problem, VerificationLink.transfer_problem_id == Problem.id)
            .join(ProblemVersion, Problem.current_published_version_id == ProblemVersion.id)
            .where(VerificationLink.id == link_id, VerificationLink.is_active.is_(True))
        )
        row = (await self._session.execute(stmt)).one_or_none()
        if row is None:
            return None
        return row[0], row[1], row[2]

    async def get_verification_link_for_transfer_problem(
        self, transfer_problem_id: UUID
    ) -> VerificationLink | None:
        stmt = (
            select(VerificationLink)
            .where(
                VerificationLink.transfer_problem_id == transfer_problem_id,
                VerificationLink.is_active.is_(True),
            )
            .limit(1)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def count_hints_used_for_problem(self, *, student_id: UUID, problem_id: UUID) -> int:
        stmt = select(func.coalesce(func.sum(MentorSession.hints_used), 0)).where(
            MentorSession.student_id == student_id,
            MentorSession.problem_id == problem_id,
        )
        return int((await self._session.execute(stmt)).scalar_one())

    async def has_accepted_submit(self, *, student_id: UUID, problem_id: UUID) -> Submission | None:
        stmt = (
            select(Submission)
            .where(
                Submission.student_id == student_id,
                Submission.problem_id == problem_id,
                Submission.submission_kind == "submit",
                Submission.verdict == "accepted",
            )
            .order_by(Submission.created_at.desc())
            .limit(1)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def get_latest_verification_attempt(
        self, *, student_id: UUID, verification_link_id: UUID
    ) -> VerificationAttempt | None:
        stmt = (
            select(VerificationAttempt)
            .where(
                VerificationAttempt.student_id == student_id,
                VerificationAttempt.verification_link_id == verification_link_id,
            )
            .order_by(VerificationAttempt.created_at.desc())
            .limit(1)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def save_verification_attempt(
        self,
        *,
        student_id: UUID,
        verification_link_id: UUID,
        source_submission_id: UUID | None,
        transfer_submission_id: UUID,
        transfer_problem_id: UUID,
        hints_used: int,
        student_explanation: str,
        outcome: str,
        verdict: str,
        passed_tests: int,
        total_tests: int,
    ) -> VerificationAttempt:
        attempt = VerificationAttempt(
            student_id=student_id,
            verification_link_id=verification_link_id,
            source_submission_id=source_submission_id,
            transfer_submission_id=transfer_submission_id,
            transfer_problem_id=transfer_problem_id,
            hints_used=hints_used,
            student_explanation=student_explanation,
            outcome=outcome,
            verdict=verdict,
            passed_tests=passed_tests,
            total_tests=total_tests,
        )
        self._session.add(attempt)
        await self._session.commit()
        await self._session.refresh(attempt)
        return attempt

    async def list_verification_attempts(
        self, *, student_id: UUID, verification_link_id: UUID | None = None
    ) -> list[VerificationAttempt]:
        stmt = select(VerificationAttempt).where(VerificationAttempt.student_id == student_id)
        if verification_link_id is not None:
            stmt = stmt.where(VerificationAttempt.verification_link_id == verification_link_id)
        stmt = stmt.order_by(VerificationAttempt.created_at.desc()).limit(25)
        return list((await self._session.execute(stmt)).scalars().all())
