from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.identity import AuditLog
from app.models.problems import (
    CodeRevision,
    ContentReview,
    ExecutionResult,
    Problem,
    ProblemLanguageVariant,
    ProblemReferenceSolution,
    ProblemVersion,
    Submission,
    SupportedLanguage,
    TestCase,
)
from app.schemas.problems import (
    AdminProblemCreateRequest,
    AdminProblemUpdateRequest,
    Difficulty,
    ProblemMode,
    ProblemStatus,
)


class ProblemRepository:
    """Async SQLAlchemy repository for Problem Bank, Execution, Revisions, and Governance."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # --- Languages ---

    async def list_languages(self, *, enabled_only: bool = True) -> list[SupportedLanguage]:
        stmt = select(SupportedLanguage).order_by(SupportedLanguage.display_name.asc())
        if enabled_only:
            stmt = stmt.where(SupportedLanguage.is_enabled.is_(True))
        return list((await self._session.execute(stmt)).scalars().all())

    async def get_language_by_slug(self, slug: str) -> SupportedLanguage | None:
        stmt = select(SupportedLanguage).where(SupportedLanguage.slug == slug)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def upsert_language(
        self,
        *,
        slug: str,
        display_name: str,
        judge0_language_id: int,
        monaco_language: str,
        version_label: str,
        is_enabled: bool,
    ) -> SupportedLanguage:
        existing = await self.get_language_by_slug(slug)
        if existing is None:
            lang = SupportedLanguage(
                slug=slug,
                display_name=display_name,
                judge0_language_id=judge0_language_id,
                monaco_language=monaco_language,
                version_label=version_label,
                is_enabled=is_enabled,
            )
            self._session.add(lang)
            await self._session.flush()
            return lang
        existing.display_name = display_name
        existing.judge0_language_id = judge0_language_id
        existing.monaco_language = monaco_language
        existing.version_label = version_label
        await self._session.flush()
        return existing

    # --- Student Published Problem Queries ---

    async def list_published_problems(
        self,
        *,
        search: str | None = None,
        difficulty: Difficulty | None = None,
        mode: ProblemMode | None = None,
        topic: str | None = None,
        track: str | None = None,
        language: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[tuple[Problem, ProblemVersion]], int]:
        base = (
            select(Problem, ProblemVersion)
            .join(ProblemVersion, Problem.current_published_version_id == ProblemVersion.id)
            .where(Problem.is_archived.is_(False), ProblemVersion.status == "published")
            .options(selectinload(ProblemVersion.variants))
        )

        if search:
            pattern = f"%{search.strip()}%"
            base = base.where(
                or_(
                    ProblemVersion.title.ilike(pattern),
                    Problem.slug.ilike(pattern),
                    ProblemVersion.statement_md.ilike(pattern),
                )
            )
        if difficulty:
            base = base.where(ProblemVersion.difficulty == difficulty)
        if mode:
            base = base.where(ProblemVersion.mode == mode)
        if topic:
            base = base.where(ProblemVersion.topics.contains([topic]))
        if track:
            base = base.where(ProblemVersion.track_slug == track)
        if language:
            base = base.where(
                ProblemVersion.variants.any(ProblemLanguageVariant.language_slug == language)
            )

        count_stmt = select(func.count()).select_from(base.subquery())
        total = int((await self._session.execute(count_stmt)).scalar_one())

        rows_stmt = (
            base.order_by(ProblemVersion.published_at.desc(), ProblemVersion.title.asc())
            .limit(limit)
            .offset(offset)
        )
        rows = [(p, pv) for p, pv in (await self._session.execute(rows_stmt)).all()]
        return rows, total

    async def get_published_problem(
        self, problem_id: UUID
    ) -> tuple[Problem, ProblemVersion] | None:
        stmt = (
            select(Problem, ProblemVersion)
            .join(ProblemVersion, Problem.current_published_version_id == ProblemVersion.id)
            .where(
                Problem.id == problem_id,
                Problem.is_archived.is_(False),
                ProblemVersion.status == "published",
            )
            .options(
                selectinload(ProblemVersion.variants),
                selectinload(ProblemVersion.test_cases),
            )
            .execution_options(populate_existing=True)
        )
        row = (await self._session.execute(stmt)).one_or_none()
        if row is None:
            return None
        return row[0], row[1]

    # --- Admin Problem Queries & Mutations ---

    async def get_problem_by_slug(self, slug: str) -> Problem | None:
        stmt = select(Problem).where(Problem.slug == slug)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list_admin_problems(
        self,
        *,
        status_filter: ProblemStatus | None = None,
        mode: ProblemMode | None = None,
        search: str | None = None,
        limit: int = 25,
        offset: int = 0,
    ) -> tuple[list[tuple[Problem, ProblemVersion]], int]:
        latest_subq = (
            select(
                ProblemVersion.problem_id,
                func.max(ProblemVersion.version_number).label("max_ver"),
            )
            .group_by(ProblemVersion.problem_id)
            .subquery()
        )
        base = (
            select(Problem, ProblemVersion)
            .join(latest_subq, Problem.id == latest_subq.c.problem_id)
            .join(
                ProblemVersion,
                (ProblemVersion.problem_id == latest_subq.c.problem_id)
                & (ProblemVersion.version_number == latest_subq.c.max_ver),
            )
        )
        if status_filter:
            base = base.where(ProblemVersion.status == status_filter)
        if mode:
            base = base.where(ProblemVersion.mode == mode)
        if search:
            pattern = f"%{search.strip()}%"
            base = base.where(or_(ProblemVersion.title.ilike(pattern), Problem.slug.ilike(pattern)))

        total = int(
            (
                await self._session.execute(select(func.count()).select_from(base.subquery()))
            ).scalar_one()
        )
        rows_stmt = base.order_by(ProblemVersion.updated_at.desc()).limit(limit).offset(offset)
        rows = [(p, pv) for p, pv in (await self._session.execute(rows_stmt)).all()]
        return rows, total

    async def get_admin_problem_latest(
        self, problem_id: UUID
    ) -> tuple[Problem, ProblemVersion] | None:
        stmt = (
            select(Problem, ProblemVersion)
            .join(ProblemVersion, ProblemVersion.problem_id == Problem.id)
            .where(Problem.id == problem_id)
            .order_by(ProblemVersion.version_number.desc())
            .limit(1)
            .options(
                selectinload(ProblemVersion.variants).selectinload(
                    ProblemLanguageVariant.reference_solution
                ),
                selectinload(ProblemVersion.test_cases),
                selectinload(ProblemVersion.reviews),
            )
            .execution_options(populate_existing=True)
        )
        row = (await self._session.execute(stmt)).one_or_none()
        if row is None:
            return None
        return row[0], row[1]

    async def create_problem_with_draft_version(
        self, *, payload: AdminProblemCreateRequest, actor_id: UUID
    ) -> tuple[Problem, ProblemVersion]:
        problem = Problem(slug=payload.slug, created_by=actor_id)
        self._session.add(problem)
        await self._session.flush()

        version = ProblemVersion(
            problem_id=problem.id,
            version_number=1,
            title=payload.title.strip(),
            statement_md=payload.statement_md,
            difficulty=payload.difficulty,
            track_slug=payload.track_slug,
            mode=payload.mode,
            topics=payload.topics,
            skills=payload.skills,
            prerequisites=payload.prerequisites,
            learning_objectives=payload.learning_objectives,
            examples=[e.model_dump() for e in payload.examples],
            time_limit_ms=payload.time_limit_ms,
            memory_limit_kb=payload.memory_limit_kb,
            status="draft",
            created_by=actor_id,
        )
        self._session.add(version)
        await self._session.flush()

        await self._replace_version_children(
            version=version,
            variants=payload.variants,
            test_cases=payload.test_cases,
        )
        await self._session.commit()

        loaded = await self.get_admin_problem_latest(problem.id)
        if loaded is None:
            raise RuntimeError("Failed to reload created problem")
        return loaded

    async def update_or_branch_problem_version(
        self,
        *,
        problem: Problem,
        latest_version: ProblemVersion,
        payload: AdminProblemUpdateRequest,
        actor_id: UUID,
    ) -> tuple[Problem, ProblemVersion]:
        # Preserve published versions immutably by creating a new version_number
        if latest_version.status == "published":
            new_version = ProblemVersion(
                problem_id=problem.id,
                version_number=latest_version.version_number + 1,
                title=payload.title.strip(),
                statement_md=payload.statement_md,
                difficulty=payload.difficulty,
                track_slug=payload.track_slug,
                mode=payload.mode,
                topics=payload.topics,
                skills=payload.skills,
                prerequisites=payload.prerequisites,
                learning_objectives=payload.learning_objectives,
                examples=[e.model_dump() for e in payload.examples],
                time_limit_ms=payload.time_limit_ms,
                memory_limit_kb=payload.memory_limit_kb,
                status="draft",
                created_by=actor_id,
            )
            self._session.add(new_version)
            await self._session.flush()
            target_version = new_version
        else:
            latest_version.title = payload.title.strip()
            latest_version.statement_md = payload.statement_md
            latest_version.difficulty = payload.difficulty
            latest_version.track_slug = payload.track_slug
            latest_version.mode = payload.mode
            latest_version.topics = payload.topics
            latest_version.skills = payload.skills
            latest_version.prerequisites = payload.prerequisites
            latest_version.learning_objectives = payload.learning_objectives
            latest_version.examples = [e.model_dump() for e in payload.examples]
            latest_version.time_limit_ms = payload.time_limit_ms
            latest_version.memory_limit_kb = payload.memory_limit_kb
            # Any content edit resets governance status back to draft
            latest_version.status = "draft"
            latest_version.validated_at = None
            target_version = latest_version

        await self._replace_version_children(
            version=target_version,
            variants=payload.variants,
            test_cases=payload.test_cases,
        )
        await self._session.commit()

        loaded = await self.get_admin_problem_latest(problem.id)
        if loaded is None:
            raise RuntimeError("Failed to reload updated problem")
        return loaded

    async def _replace_version_children(
        self,
        *,
        version: ProblemVersion,
        variants: list[Any],
        test_cases: list[Any],
    ) -> None:
        existing_variants = list(
            (
                await self._session.execute(
                    select(ProblemLanguageVariant).where(
                        ProblemLanguageVariant.problem_version_id == version.id
                    )
                )
            )
            .scalars()
            .all()
        )
        for v in existing_variants:
            await self._session.delete(v)

        existing_tests = list(
            (
                await self._session.execute(
                    select(TestCase).where(TestCase.problem_version_id == version.id)
                )
            )
            .scalars()
            .all()
        )
        for t in existing_tests:
            await self._session.delete(t)
        await self._session.flush()

        for v_in in variants:
            variant = ProblemLanguageVariant(
                problem_version_id=version.id,
                language_slug=v_in.language_slug,
                starter_code=v_in.starter_code,
                buggy_starter_code=v_in.buggy_starter_code,
                debugging_prompt=v_in.debugging_prompt,
            )
            self._session.add(variant)
            await self._session.flush()
            ref = ProblemReferenceSolution(
                variant_id=variant.id,
                reference_solution=v_in.reference_solution,
                expected_bug_summary=v_in.expected_bug_summary,
                expected_failure_category=getattr(v_in, "expected_failure_category", None),
            )
            self._session.add(ref)

        for t_in in test_cases:
            tc = TestCase(
                problem_version_id=version.id,
                ordinal=t_in.ordinal,
                name=t_in.name,
                input_data=t_in.input_data,
                expected_output=t_in.expected_output,
                is_hidden=t_in.is_hidden,
                weight=t_in.weight,
            )
            self._session.add(tc)

    async def record_content_review(
        self,
        *,
        version: ProblemVersion,
        reviewer_id: UUID,
        action: str,
        new_status: ProblemStatus,
        notes: str = "",
        validation_summary: dict[str, Any] | None = None,
        publish_problem: Problem | None = None,
    ) -> None:
        now = datetime.now(UTC)
        version.status = new_status
        if action == "validated" and new_status == "validated":
            version.validated_at = now
        if action == "published" and publish_problem is not None:
            version.published_at = now
            publish_problem.current_published_version_id = version.id

        review = ContentReview(
            problem_version_id=version.id,
            reviewer_id=reviewer_id,
            action=action,
            notes=notes,
            validation_summary=validation_summary or {},
        )
        self._session.add(review)
        await self._session.commit()

    async def list_problem_versions(
        self, problem_id: UUID
    ) -> tuple[Problem, list[ProblemVersion]] | None:
        problem = (
            await self._session.execute(select(Problem).where(Problem.id == problem_id))
        ).scalar_one_or_none()
        if problem is None:
            return None
        stmt = (
            select(ProblemVersion)
            .where(ProblemVersion.problem_id == problem_id)
            .order_by(ProblemVersion.version_number.desc())
            .options(
                selectinload(ProblemVersion.test_cases),
                selectinload(ProblemVersion.reviews),
            )
            .execution_options(populate_existing=True)
        )
        versions = list((await self._session.execute(stmt)).scalars().all())
        return problem, versions

    async def count_assigned_courses_for_problem(self, problem_id: UUID) -> int:
        from app.models.classroom import Assignment, AssignmentProblemLink

        stmt = (
            select(func.count(func.distinct(Assignment.course_id)))
            .select_from(AssignmentProblemLink)
            .join(Assignment, Assignment.id == AssignmentProblemLink.assignment_id)
            .where(AssignmentProblemLink.problem_id == problem_id)
        )
        return int((await self._session.execute(stmt)).scalar_one() or 0)

    async def archive_problem_version(
        self,
        *,
        problem: Problem,
        version: ProblemVersion,
        reviewer_id: UUID,
        notes: str,
    ) -> None:
        problem.is_archived = True
        version.status = "archived"
        self._session.add(
            ContentReview(
                problem_version_id=version.id,
                reviewer_id=reviewer_id,
                action="archived",
                notes=notes or "Archived in Admin Problem Studio.",
                validation_summary={},
            )
        )
        await self._session.commit()

    async def record_curriculum_validation(
        self,
        *,
        target_type: str,
        target_id: UUID,
        validator_id: UUID,
        passed: bool,
        summary: dict[str, Any],
    ) -> None:
        from app.models.learning import CurriculumValidation

        self._session.add(
            CurriculumValidation(
                target_type=target_type,
                target_id=target_id,
                validator_id=validator_id,
                passed=passed,
                summary=summary,
            )
        )
        await self._session.commit()

    # --- Submissions, Execution Results, Quotas & Revisions ---

    async def count_recent_submissions(self, *, student_id: UUID, since: datetime) -> int:
        stmt = (
            select(func.count())
            .select_from(Submission)
            .where(Submission.student_id == student_id, Submission.created_at >= since)
        )
        return int((await self._session.execute(stmt)).scalar_one())

    async def get_quota_counts(self, student_id: UUID) -> tuple[int, int]:
        now = datetime.now(UTC)
        last_minute = await self.count_recent_submissions(
            student_id=student_id, since=now - timedelta(minutes=1)
        )
        last_day = await self.count_recent_submissions(
            student_id=student_id, since=now - timedelta(hours=24)
        )
        return last_minute, last_day

    async def create_submission(
        self,
        *,
        student_id: UUID,
        problem_id: UUID,
        problem_version_id: UUID,
        language_slug: str,
        submission_kind: str,
        source_code: str,
        prediction_text: str | None,
        explanation_text: str | None,
        total_tests: int,
    ) -> Submission:
        sub = Submission(
            student_id=student_id,
            problem_id=problem_id,
            problem_version_id=problem_version_id,
            language_slug=language_slug,
            submission_kind=submission_kind,
            source_code=source_code,
            prediction_text=prediction_text,
            explanation_text=explanation_text,
            status="running",
            verdict="pending",
            passed_tests=0,
            total_tests=total_tests,
        )
        self._session.add(sub)
        await self._session.commit()
        await self._session.refresh(sub)
        return sub

    async def finalize_submission(
        self,
        *,
        submission: Submission,
        status_value: str,
        verdict: str,
        passed_tests: int,
        total_tests: int,
        runtime_ms: int | None,
        memory_kb: int | None,
        execution_evidence: dict[str, Any],
        results: list[ExecutionResult],
        execution_provider: str = "judge0",
    ) -> Submission:
        submission.status = status_value
        submission.verdict = verdict
        submission.passed_tests = passed_tests
        submission.total_tests = total_tests
        submission.runtime_ms = runtime_ms
        submission.memory_kb = memory_kb
        submission.execution_provider = execution_provider
        submission.execution_evidence = execution_evidence
        for res in results:
            self._session.add(res)
        await self._session.commit()

        loaded = await self.get_submission_by_id(submission.id)
        if loaded is None:
            raise RuntimeError("Failed to reload finalized submission")
        return loaded

    async def get_submission_by_id(self, submission_id: UUID) -> Submission | None:
        stmt = (
            select(Submission)
            .where(Submission.id == submission_id)
            .options(selectinload(Submission.results))
            .execution_options(populate_existing=True)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def get_test_cases_map(self, version_id: UUID) -> dict[UUID, TestCase]:
        stmt = select(TestCase).where(TestCase.problem_version_id == version_id)
        tests = list((await self._session.execute(stmt)).scalars().all())
        return {tc.id: tc for tc in tests}

    async def list_student_submissions(
        self,
        *,
        student_id: UUID,
        problem_id: UUID | None = None,
        limit: int = 25,
        offset: int = 0,
    ) -> tuple[list[Submission], int]:
        base = select(Submission).where(Submission.student_id == student_id)
        if problem_id:
            base = base.where(Submission.problem_id == problem_id)

        total = int(
            (
                await self._session.execute(select(func.count()).select_from(base.subquery()))
            ).scalar_one()
        )
        rows = list(
            (
                await self._session.execute(
                    base.order_by(Submission.created_at.desc()).limit(limit).offset(offset)
                )
            )
            .scalars()
            .all()
        )
        return rows, total

    async def save_revision(
        self,
        *,
        student_id: UUID,
        problem_version_id: UUID,
        language_slug: str,
        source_code: str,
        prediction_text: str | None,
        explanation_text: str | None,
        revision_type: str,
    ) -> CodeRevision:
        revision = CodeRevision(
            student_id=student_id,
            problem_version_id=problem_version_id,
            language_slug=language_slug,
            source_code=source_code,
            prediction_text=prediction_text,
            explanation_text=explanation_text,
            revision_type=revision_type,
        )
        self._session.add(revision)
        await self._session.commit()
        await self._session.refresh(revision)
        return revision

    async def list_revisions(
        self,
        *,
        student_id: UUID,
        problem_version_id: UUID,
        limit: int = 20,
    ) -> list[CodeRevision]:
        stmt = (
            select(CodeRevision)
            .where(
                CodeRevision.student_id == student_id,
                CodeRevision.problem_version_id == problem_version_id,
            )
            .order_by(CodeRevision.created_at.desc())
            .limit(limit)
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def record_audit(
        self,
        *,
        actor_user_id: UUID,
        action: str,
        target_type: str,
        target_id: str,
        metadata: dict[str, Any],
        request_id: str | None,
    ) -> None:
        self._session.add(
            AuditLog(
                actor_user_id=actor_user_id,
                action=action,
                target_type=target_type,
                target_id=target_id,
                metadata_json=metadata,
                request_id=request_id,
            )
        )
        await self._session.commit()
