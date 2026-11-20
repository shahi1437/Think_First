"""Admin Curriculum, Lesson Validation, Diagnostic Authoring & Protected Import Service."""

from __future__ import annotations

import ast
from typing import Any
from uuid import UUID

from fastapi import status

from app.core.errors import AppError
from app.integrations.judge0.client import Judge0Client
from app.models.learning import DiagnosticQuestion, Lesson, LessonVersion
from app.repositories.admin import AdminRepository
from app.repositories.identity import UserRecord
from app.repositories.learning import LearningRepository
from app.repositories.problems import ProblemRepository
from app.schemas.admin import (
    AdminCurriculumImportReport,
    AdminCurriculumImportRequest,
    AdminCurriculumValidateResponse,
    AdminDiagnosticQuestionDetail,
    AdminDiagnosticQuestionUpdateRequest,
    AdminLessonDetailView,
    AdminTrackUpdateRequest,
)
from app.schemas.learning import (
    DiagnosticOptionView,
    LearningTrackView,
    LessonExerciseTestCase,
    LessonGuidedExercise,
    LessonInteractiveExample,
)
from app.schemas.problems import AdminProblemUpdateRequest
from app.services.mentor.rag_service import RagKnowledgeService

DEFAULT_PYTHON_JUDGE0_ID = 71


def _to_admin_lesson_detail(lesson: Lesson, version: LessonVersion) -> AdminLessonDetailView:
    examples = [
        LessonInteractiveExample.model_validate(item)
        for item in (version.interactive_examples or [])
    ]
    exercise = LessonGuidedExercise.model_validate(version.guided_exercise or {})
    return AdminLessonDetailView(
        lesson_id=lesson.id,
        version_id=version.id,
        version_number=version.version_number,
        slug=lesson.slug,
        skill_slug=lesson.skill_slug,
        display_order=lesson.display_order,
        status=version.status,
        is_published_current=lesson.current_published_version_id == version.id,
        title_en=version.title_en,
        title_bn=version.title_bn,
        summary_en=version.summary_en,
        summary_bn=version.summary_bn,
        content_en_md=version.content_en_md,
        content_bn_md=version.content_bn_md,
        learning_objectives=list(version.learning_objectives or []),
        prerequisite_lesson_slugs=list(version.prerequisite_lesson_slugs or []),
        track_slugs=list(version.track_slugs or []),
        interactive_examples=examples,
        guided_exercise=exercise,
        estimated_minutes=version.estimated_minutes,
        published_at=version.published_at,
        updated_at=version.updated_at,
    )


def _to_admin_diagnostic_detail(q: DiagnosticQuestion) -> AdminDiagnosticQuestionDetail:
    ans = q.answer_key
    return AdminDiagnosticQuestionDetail(
        id=q.id,
        slug=q.slug,
        domain_slug=q.domain_slug,
        skill_slug=q.skill_slug,
        difficulty=q.difficulty,
        question_type=q.question_type,
        prompt_en=q.prompt_en,
        prompt_bn=q.prompt_bn,
        code_snippet=q.code_snippet,
        options=[DiagnosticOptionView.model_validate(opt) for opt in (q.options or [])],
        starter_code=q.starter_code,
        language_slug=q.language_slug,
        status=q.status,
        correct_option_id=ans.correct_option_id if ans else None,
        explanation_en=ans.explanation_en if ans else "",
        explanation_bn=ans.explanation_bn if ans else "",
        evaluation_tests=[
            LessonExerciseTestCase.model_validate(tc)
            for tc in ((ans.evaluation_tests if ans else None) or [])
        ],
        reference_solution=ans.reference_solution if ans else None,
        validation_summary=dict((ans.validation_summary if ans else None) or {}),
        published_at=q.published_at,
        updated_at=q.updated_at,
    )


class AdminCurriculumService:
    """Manages tracks, bilingual lessons, diagnostics, Judge0 validation & curriculum import."""

    def __init__(
        self,
        *,
        admin_repo: AdminRepository,
        learning_repo: LearningRepository,
        problem_repo: ProblemRepository,
        judge0: Judge0Client,
        rag_service: RagKnowledgeService,
    ) -> None:
        self._admin_repo = admin_repo
        self._learning_repo = learning_repo
        self._problem_repo = problem_repo
        self._judge0 = judge0
        self._rag_service = rag_service

    # --- Tracks ---

    async def list_tracks(self) -> list[LearningTrackView]:
        rows = await self._admin_repo.list_tracks()
        return [
            LearningTrackView(
                slug=t.slug,
                title_en=t.title_en,
                title_bn=t.title_bn,
                summary_en=t.summary_en,
                summary_bn=t.summary_bn,
                target_audience_en=t.target_audience_en,
                target_audience_bn=t.target_audience_bn,
                display_order=t.display_order,
                recommended_focus_skills=list(t.recommended_focus_skills or []),
            )
            for t in rows
        ]

    async def update_track(
        self,
        *,
        actor: UserRecord,
        track_slug: str,
        payload: AdminTrackUpdateRequest,
        request_id: str | None,
    ) -> LearningTrackView:
        updated = await self._admin_repo.update_track(
            track_slug=track_slug,
            title_en=payload.title_en.strip(),
            title_bn=payload.title_bn.strip(),
            summary_en=payload.summary_en.strip(),
            summary_bn=payload.summary_bn.strip(),
            recommended_focus_skills=payload.recommended_focus_skills,
        )
        if updated is None:
            raise AppError(
                code="TRACK_NOT_FOUND",
                message="Learning track not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        await self._problem_repo.record_audit(
            actor_user_id=actor.id,
            action="track.updated",
            target_type="learning_track",
            target_id=track_slug,
            metadata={"focus_skills": payload.recommended_focus_skills},
            request_id=request_id,
        )
        return LearningTrackView(
            slug=updated.slug,
            title_en=updated.title_en,
            title_bn=updated.title_bn,
            summary_en=updated.summary_en,
            summary_bn=updated.summary_bn,
            target_audience_en=updated.target_audience_en,
            target_audience_bn=updated.target_audience_bn,
            display_order=updated.display_order,
            recommended_focus_skills=list(updated.recommended_focus_skills or []),
        )

    # --- Lessons ---

    async def list_admin_lessons(self) -> list[AdminLessonDetailView]:
        rows = await self._admin_repo.list_all_lessons_with_latest()
        return [_to_admin_lesson_detail(lesson, version) for lesson, version in rows]

    async def get_admin_lesson(self, lesson_id: UUID) -> AdminLessonDetailView:
        found = await self._admin_repo.get_lesson_latest(lesson_id)
        if found is None:
            raise AppError(
                code="LESSON_NOT_FOUND",
                message="Lesson not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        return _to_admin_lesson_detail(found[0], found[1])

    async def update_lesson_status(
        self,
        *,
        actor: UserRecord,
        lesson_id: UUID,
        new_status: str,
        request_id: str | None,
    ) -> AdminLessonDetailView:
        found = await self._admin_repo.get_lesson_latest(lesson_id)
        if found is None:
            raise AppError(
                code="LESSON_NOT_FOUND",
                message="Lesson not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        lesson, version = found
        await self._admin_repo.set_lesson_status(
            lesson=lesson,
            version=version,
            status_value=new_status,
            actor_id=actor.id,
        )
        await self._problem_repo.record_audit(
            actor_user_id=actor.id,
            action=f"lesson.{new_status}",
            target_type="lesson",
            target_id=str(lesson.id),
            metadata={"slug": lesson.slug, "version_number": version.version_number},
            request_id=request_id,
        )
        return await self.get_admin_lesson(lesson.id)

    async def validate_lesson_exercise(
        self,
        *,
        actor: UserRecord,
        lesson_id: UUID,
        reference_solution: str,
        request_id: str | None,
    ) -> AdminCurriculumValidateResponse:
        found = await self._admin_repo.get_lesson_latest(lesson_id)
        if found is None:
            raise AppError(
                code="LESSON_NOT_FOUND",
                message="Lesson not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        lesson, version = found
        exercise = LessonGuidedExercise.model_validate(version.guided_exercise or {})
        errors: list[str] = []
        warnings: list[str] = []

        try:
            ast.parse(reference_solution)
        except SyntaxError as exc:
            errors.append(f"Reference syntax error at line {exc.lineno or '?'}: {exc.msg}")

        lang_row = await self._problem_repo.get_language_by_slug(exercise.language_slug)
        j0_id = lang_row.judge0_language_id if lang_row else DEFAULT_PYTHON_JUDGE0_ID
        passed_count = 0

        for idx, tc in enumerate(exercise.test_cases, start=1):
            out = await self._judge0.execute_test_case(
                source_code=reference_solution,
                judge0_language_id=j0_id,
                stdin=tc.input_data,
                expected_output=tc.expected_output,
                cpu_time_limit_seconds=2.0,
                memory_limit_kb=131072,
            )
            if out.verdict == "accepted":
                passed_count += 1
            else:
                errors.append(f"Guided test #{idx} ({tc.name}) failed: {out.verdict}")

        if not exercise.test_cases:
            warnings.append("Lesson has no guided Judge0 test cases configured.")

        passed = (
            len(errors) == 0
            and len(exercise.test_cases) > 0
            and passed_count == len(exercise.test_cases)
        )
        await self._admin_repo.record_validation(
            target_type="lesson_version",
            target_id=version.id,
            validator_id=actor.id,
            passed=passed,
            summary={
                "slug": lesson.slug,
                "passed_tests": passed_count,
                "total_tests": len(exercise.test_cases),
                "errors": errors,
            },
        )
        await self._problem_repo.record_audit(
            actor_user_id=actor.id,
            action="lesson.validated",
            target_type="lesson_version",
            target_id=str(version.id),
            metadata={"slug": lesson.slug, "passed": passed},
            request_id=request_id,
        )
        return AdminCurriculumValidateResponse(
            target_type="lesson_version",
            target_id=version.id,
            passed=passed,
            passed_tests=passed_count,
            total_tests=len(exercise.test_cases),
            errors=errors,
            warnings=warnings,
        )

    # --- Diagnostic Questions ---

    async def list_admin_diagnostics(self) -> list[AdminDiagnosticQuestionDetail]:
        rows = await self._admin_repo.list_all_diagnostic_questions()
        return [_to_admin_diagnostic_detail(q) for q in rows]

    async def update_admin_diagnostic(
        self,
        *,
        actor: UserRecord,
        question_id: UUID,
        payload: AdminDiagnosticQuestionUpdateRequest,
        request_id: str | None,
    ) -> AdminDiagnosticQuestionDetail:
        q = await self._admin_repo.get_diagnostic_question(question_id)
        if q is None:
            raise AppError(
                code="DIAGNOSTIC_NOT_FOUND",
                message="Diagnostic question not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        updated = await self._admin_repo.update_diagnostic_question(
            question=q,
            question_data={
                "domain_slug": payload.domain_slug,
                "skill_slug": payload.skill_slug,
                "difficulty": payload.difficulty,
                "question_type": payload.question_type,
                "prompt_en": payload.prompt_en,
                "prompt_bn": payload.prompt_bn,
                "code_snippet": payload.code_snippet,
                "options": [o.model_dump() for o in payload.options],
                "starter_code": payload.starter_code,
            },
            answer_data={
                "correct_option_id": payload.correct_option_id,
                "explanation_en": payload.explanation_en,
                "explanation_bn": payload.explanation_bn,
                "evaluation_tests": [t.model_dump() for t in payload.evaluation_tests],
                "reference_solution": payload.reference_solution,
            },
        )
        await self._problem_repo.record_audit(
            actor_user_id=actor.id,
            action="diagnostic.updated",
            target_type="diagnostic_question",
            target_id=str(updated.id),
            metadata={"slug": updated.slug},
            request_id=request_id,
        )
        return _to_admin_diagnostic_detail(updated)

    async def update_diagnostic_status(
        self,
        *,
        actor: UserRecord,
        question_id: UUID,
        new_status: str,
        request_id: str | None,
    ) -> AdminDiagnosticQuestionDetail:
        q = await self._admin_repo.get_diagnostic_question(question_id)
        if q is None:
            raise AppError(
                code="DIAGNOSTIC_NOT_FOUND",
                message="Diagnostic question not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        updated = await self._admin_repo.set_diagnostic_status(
            question=q, status_value=new_status, actor_id=actor.id
        )
        await self._problem_repo.record_audit(
            actor_user_id=actor.id,
            action=f"diagnostic.{new_status}",
            target_type="diagnostic_question",
            target_id=str(updated.id),
            metadata={"slug": updated.slug},
            request_id=request_id,
        )
        return _to_admin_diagnostic_detail(updated)

    async def validate_diagnostic_question(
        self,
        *,
        actor: UserRecord,
        question_id: UUID,
        reference_solution: str | None,
        request_id: str | None,
    ) -> AdminCurriculumValidateResponse:
        q = await self._admin_repo.get_diagnostic_question(question_id)
        if q is None or q.answer_key is None:
            raise AppError(
                code="DIAGNOSTIC_NOT_FOUND",
                message="Diagnostic question not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        errors: list[str] = []
        warnings: list[str] = []
        tests = list(q.answer_key.evaluation_tests or [])
        passed_count = 0

        if q.question_type == "mcq":
            option_ids = {str(o.get("id")) for o in (q.options or [])}
            if (
                not q.answer_key.correct_option_id
                or q.answer_key.correct_option_id not in option_ids
            ):
                errors.append("MCQ correct_option_id does not match any option ID.")
            passed = len(errors) == 0
            total = 1
            passed_count = 1 if passed else 0
        else:
            ref = reference_solution or q.answer_key.reference_solution
            total = len(tests)
            if not ref or not ref.strip():
                errors.append("Reference solution is required to validate code_execution item.")
            elif not tests:
                errors.append("No evaluation tests configured.")
            else:
                try:
                    ast.parse(ref)
                except SyntaxError as exc:
                    errors.append(f"Syntax error line {exc.lineno or '?'}: {exc.msg}")
                lang_row = await self._problem_repo.get_language_by_slug(q.language_slug)
                j0_id = lang_row.judge0_language_id if lang_row else DEFAULT_PYTHON_JUDGE0_ID
                for idx, tc in enumerate(tests, start=1):
                    out = await self._judge0.execute_test_case(
                        source_code=ref,
                        judge0_language_id=j0_id,
                        stdin=str(tc.get("input_data", "")),
                        expected_output=str(tc.get("expected_output", "")),
                        cpu_time_limit_seconds=2.0,
                        memory_limit_kb=131072,
                    )
                    if out.verdict == "accepted":
                        passed_count += 1
                    else:
                        errors.append(f"Evaluation test #{idx} failed: {out.verdict}")
                if reference_solution:
                    q.answer_key.reference_solution = reference_solution
            passed = len(errors) == 0 and total > 0 and passed_count == total

        summary = {
            "passed": passed,
            "passed_tests": passed_count,
            "total_tests": total,
            "errors": errors,
        }
        q.answer_key.validation_summary = summary
        await self._admin_repo.record_validation(
            target_type="diagnostic_question",
            target_id=q.id,
            validator_id=actor.id,
            passed=passed,
            summary=summary,
        )
        await self._problem_repo.record_audit(
            actor_user_id=actor.id,
            action="diagnostic.validated",
            target_type="diagnostic_question",
            target_id=str(q.id),
            metadata={"slug": q.slug, "passed": passed},
            request_id=request_id,
        )
        return AdminCurriculumValidateResponse(
            target_type="diagnostic_question",
            target_id=q.id,
            passed=passed,
            passed_tests=passed_count,
            total_tests=total,
            errors=errors,
            warnings=warnings,
        )

    # --- Protected Curriculum Bundle Import (Admin-only, Judge0 Validated) ---

    async def import_curriculum_bundle(
        self,
        *,
        actor: UserRecord,
        payload: AdminCurriculumImportRequest,
        problem_service: Any,
        request_id: str | None,
    ) -> AdminCurriculumImportReport:
        lessons_imported = 0
        lessons_validated = 0
        problems_imported = 0
        problems_published = 0
        diagnostics_imported = 0
        knowledge_imported = 0
        errors: list[str] = []

        for l_item in payload.lessons:
            lesson, _ver = await self._learning_repo.create_admin_lesson(
                actor_id=actor.id,
                slug=l_item.slug,
                skill_slug=l_item.skill_slug,
                display_order=l_item.display_order,
                version_data={
                    "title_en": l_item.title_en,
                    "title_bn": l_item.title_bn,
                    "summary_en": l_item.summary_en,
                    "summary_bn": l_item.summary_bn,
                    "content_en_md": l_item.content_en_md,
                    "content_bn_md": l_item.content_bn_md,
                    "learning_objectives": l_item.learning_objectives,
                    "prerequisite_lesson_slugs": l_item.prerequisite_lesson_slugs,
                    "track_slugs": list(l_item.track_slugs),
                    "interactive_examples": [e.model_dump() for e in l_item.interactive_examples],
                    "guided_exercise": l_item.guided_exercise.model_dump(),
                    "estimated_minutes": l_item.estimated_minutes,
                },
                publish=l_item.publish,
            )
            lessons_imported += 1
            if l_item.validate_with_judge0 and l_item.reference_solution:
                v_res = await self.validate_lesson_exercise(
                    actor=actor,
                    lesson_id=lesson.id,
                    reference_solution=l_item.reference_solution,
                    request_id=request_id,
                )
                if v_res.passed:
                    lessons_validated += 1
                else:
                    errors.append(
                        f"Lesson '{l_item.slug}' Judge0 check failed: {'; '.join(v_res.errors)}"
                    )

        for p_item in payload.problems:
            existing = await self._problem_repo.get_problem_by_slug(p_item.slug)
            if existing is None:
                detail = await problem_service.create_problem(
                    actor=actor,
                    payload=p_item,
                    request_id=request_id,
                )
            else:
                upd = AdminProblemUpdateRequest(
                    title=p_item.title,
                    statement_md=p_item.statement_md,
                    difficulty=p_item.difficulty,
                    track_slug=p_item.track_slug,
                    mode=p_item.mode,
                    topics=p_item.topics,
                    skills=p_item.skills,
                    prerequisites=p_item.prerequisites,
                    learning_objectives=p_item.learning_objectives,
                    examples=p_item.examples,
                    time_limit_ms=p_item.time_limit_ms,
                    memory_limit_kb=p_item.memory_limit_kb,
                    variants=p_item.variants,
                    test_cases=p_item.test_cases,
                )
                detail = await problem_service.update_problem(
                    actor=actor,
                    problem_id=existing.id,
                    payload=upd,
                    request_id=request_id,
                )
            problems_imported += 1

            if p_item.validate_with_judge0:
                val_report = await problem_service.validate_problem(
                    actor=actor,
                    problem_id=detail.problem_id,
                    request_id=request_id,
                )
                if val_report.passed and p_item.publish:
                    await problem_service.publish_problem(
                        actor=actor,
                        problem_id=detail.problem_id,
                        notes="Validated via Judge0 during Admin curriculum import.",
                        request_id=request_id,
                    )
                    problems_published += 1
                elif not val_report.passed:
                    errs = [e for vr in val_report.variant_results for e in vr.errors]
                    errors.append(f"Problem '{p_item.slug}' failed Judge0 validation: {errs}")

        for d_item in payload.diagnostic_questions:
            existing_q = await self._admin_repo.get_diagnostic_question_by_slug(d_item.slug)
            if existing_q is None:
                q_row = await self._learning_repo.create_admin_diagnostic_question(
                    actor_id=actor.id,
                    question_data={
                        "slug": d_item.slug,
                        "domain_slug": d_item.domain_slug,
                        "skill_slug": d_item.skill_slug,
                        "difficulty": d_item.difficulty,
                        "question_type": d_item.question_type,
                        "prompt_en": d_item.prompt_en,
                        "prompt_bn": d_item.prompt_bn,
                        "code_snippet": d_item.code_snippet,
                        "options": [o.model_dump() for o in d_item.options],
                        "starter_code": d_item.starter_code,
                    },
                    answer_data={
                        "correct_option_id": d_item.correct_option_id,
                        "explanation_en": d_item.explanation_en,
                        "explanation_bn": d_item.explanation_bn,
                        "evaluation_tests": [t.model_dump() for t in d_item.evaluation_tests],
                        "reference_solution": d_item.reference_solution,
                    },
                    publish=d_item.publish,
                )
            else:
                await self._admin_repo.update_diagnostic_question(
                    question=existing_q,
                    question_data={
                        "domain_slug": d_item.domain_slug,
                        "skill_slug": d_item.skill_slug,
                        "difficulty": d_item.difficulty,
                        "question_type": d_item.question_type,
                        "prompt_en": d_item.prompt_en,
                        "prompt_bn": d_item.prompt_bn,
                        "code_snippet": d_item.code_snippet,
                        "options": [o.model_dump() for o in d_item.options],
                        "starter_code": d_item.starter_code,
                    },
                    answer_data={
                        "correct_option_id": d_item.correct_option_id,
                        "explanation_en": d_item.explanation_en,
                        "explanation_bn": d_item.explanation_bn,
                        "evaluation_tests": [t.model_dump() for t in d_item.evaluation_tests],
                        "reference_solution": d_item.reference_solution,
                    },
                )
                q_row = existing_q
                if d_item.publish:
                    await self._admin_repo.set_diagnostic_status(
                        question=q_row, status_value="published", actor_id=actor.id
                    )
            diagnostics_imported += 1
            if d_item.validate_with_judge0 and d_item.question_type == "code_execution":
                q_val = await self.validate_diagnostic_question(
                    actor=actor,
                    question_id=q_row.id,
                    reference_solution=d_item.reference_solution,
                    request_id=request_id,
                )
                if not q_val.passed:
                    errors.append(
                        f"Diagnostic '{d_item.slug}' failed Judge0 validation: {q_val.errors}"
                    )

        for k_item in payload.knowledge_documents:
            await self._rag_service.create_or_update_document(actor=actor, payload=k_item)
            knowledge_imported += 1

        await self._problem_repo.record_audit(
            actor_user_id=actor.id,
            action="curriculum.imported",
            target_type="curriculum_bundle",
            target_id="bulk_import",
            metadata={
                "lessons_imported": lessons_imported,
                "problems_imported": problems_imported,
                "problems_published": problems_published,
                "diagnostics_imported": diagnostics_imported,
                "knowledge_imported": knowledge_imported,
                "error_count": len(errors),
            },
            request_id=request_id,
        )
        return AdminCurriculumImportReport(
            lessons_imported=lessons_imported,
            lessons_validated=lessons_validated,
            problems_imported=problems_imported,
            problems_validated_and_published=problems_published,
            diagnostic_questions_imported=diagnostics_imported,
            knowledge_documents_imported=knowledge_imported,
            errors=errors,
        )
