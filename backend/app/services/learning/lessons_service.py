"""Learning Tracks & Beginner Python Lessons service with real Judge0 guided practice."""

from __future__ import annotations

from uuid import UUID

from fastapi import status

from app.core.errors import AppError
from app.integrations.judge0.client import Judge0Client
from app.models.learning import Lesson, LessonProgress, LessonVersion
from app.repositories.identity import UserRecord
from app.repositories.learning import LearningRepository
from app.repositories.mentor import MentorRepository
from app.repositories.problems import ProblemRepository
from app.schemas.learning import (
    AdminLessonCreateRequest,
    LearningTrackView,
    LessonDetailView,
    LessonExerciseCaseResult,
    LessonExerciseRunResponse,
    LessonGuidedExercise,
    LessonInteractiveExample,
    LessonProgressStatus,
    LessonSummaryView,
    StudentTrackStatus,
    TrackSlug,
)
from app.services.learning.skill_graph import SkillGraphService

DEFAULT_PYTHON_JUDGE0_ID = 71


def _initial_track_from_onboarding(user: UserRecord) -> tuple[TrackSlug, str]:
    """Conservative onboarding entry suggestion — explicitly notes diagnostic is needed for evidence."""
    exp = user.preferences.programming_experience if user.preferences else "none"
    if exp in ("none", "beginner"):
        return (
            "absolute_beginner",
            "Suggested from onboarding self-report; take the 8-domain diagnostic to confirm with evidence.",
        )
    if exp == "basic":
        return (
            "basic_university",
            "Suggested from onboarding self-report; take the 8-domain diagnostic to verify specific gaps.",
        )
    if exp == "intermediate":
        return (
            "intermediate",
            "Suggested from onboarding self-report; take the 8-domain diagnostic to verify topic readiness.",
        )
    return (
        "advanced",
        "Suggested from onboarding self-report; take the 8-domain diagnostic to confirm advanced placement.",
    )


class LessonsAndTracksService:
    """Manages 4 learner tracks, bilingual lessons, Judge0 guided exercises, and progress."""

    def __init__(
        self,
        *,
        learning_repo: LearningRepository,
        problem_repo: ProblemRepository,
        mentor_repo: MentorRepository,
        judge0: Judge0Client,
        skill_graph: SkillGraphService,
    ) -> None:
        self._learning_repo = learning_repo
        self._problem_repo = problem_repo
        self._mentor_repo = mentor_repo
        self._judge0 = judge0
        self._skill_graph = skill_graph

    async def get_track_status(self, user: UserRecord) -> StudentTrackStatus:
        tracks = await self._learning_repo.list_tracks()
        enrollment = await self._learning_repo.get_track_enrollment(user.id)
        diag_sessions = await self._learning_repo.list_student_diagnostic_sessions(
            student_id=user.id, limit=5
        )
        completed_diag = any(s.status == "completed" for s in diag_sessions)

        if enrollment is None:
            initial_slug, reason = _initial_track_from_onboarding(user)
            enrollment = await self._learning_repo.upsert_track_enrollment(
                student_id=user.id,
                selected_track_slug=initial_slug,
                recommended_track_slug=None,
                recommendation_source="onboarding_initial",
                recommendation_reason=reason,
            )

        return StudentTrackStatus(
            selected_track_slug=enrollment.selected_track_slug,
            recommended_track_slug=enrollment.recommended_track_slug,
            recommendation_source=enrollment.recommendation_source,
            recommendation_reason=enrollment.recommendation_reason,
            diagnostic_completed=completed_diag,
            tracks=[
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
                for t in tracks
            ],
        )

    async def select_track(self, *, user: UserRecord, track_slug: TrackSlug) -> StudentTrackStatus:
        tracks = await self._learning_repo.list_tracks()
        if not any(t.slug == track_slug for t in tracks):
            raise AppError(
                code="TRACK_NOT_FOUND",
                message="Selected learning track does not exist.",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        existing = await self._learning_repo.get_track_enrollment(user.id)
        await self._learning_repo.upsert_track_enrollment(
            student_id=user.id,
            selected_track_slug=track_slug,
            recommended_track_slug=existing.recommended_track_slug if existing else None,
            recommendation_source="manual_selection",
            recommendation_reason=(
                existing.recommendation_reason
                if existing and existing.recommended_track_slug
                else f"Learner selected {track_slug.replace('_', ' ')} track manually."
            ),
        )
        return await self.get_track_status(user)

    def _to_summary(
        self,
        lesson: Lesson,
        version: LessonVersion,
        progress_map: dict[UUID, LessonProgress],
        completed_slugs: set[str],
    ) -> LessonSummaryView:
        prog = progress_map.get(lesson.id)
        prereqs = list(version.prerequisite_lesson_slugs or [])
        prereqs_met = all(p in completed_slugs for p in prereqs)
        p_status: LessonProgressStatus = (
            prog.status if prog is not None else "not_started"  # type: ignore[assignment]
        )
        return LessonSummaryView(
            lesson_id=lesson.id,
            version_id=version.id,
            slug=lesson.slug,
            skill_slug=lesson.skill_slug,
            display_order=lesson.display_order,
            title_en=version.title_en,
            title_bn=version.title_bn,
            summary_en=version.summary_en,
            summary_bn=version.summary_bn,
            prerequisite_lesson_slugs=prereqs,
            track_slugs=list(version.track_slugs or []),
            estimated_minutes=version.estimated_minutes,
            progress_status=p_status,
            reading_completed=prog.reading_completed if prog else False,
            exercise_passed=prog.exercise_passed if prog else False,
            exercise_attempts=prog.exercise_attempts if prog else 0,
            prerequisites_met=prereqs_met,
        )

    async def list_lessons(
        self, *, user: UserRecord, track_slug: str | None = None
    ) -> list[LessonSummaryView]:
        rows = await self._learning_repo.list_published_lessons()
        progress_map = await self._learning_repo.list_student_lesson_progress(user.id)
        completed_slugs = {
            lesson.slug
            for lesson, _ in rows
            if lesson.id in progress_map and progress_map[lesson.id].status == "completed"
        }

        out: list[LessonSummaryView] = []
        for lesson, version in rows:
            if track_slug and track_slug not in (version.track_slugs or []):
                continue
            out.append(self._to_summary(lesson, version, progress_map, completed_slugs))
        return out

    async def get_lesson_detail(self, *, user: UserRecord, slug: str) -> LessonDetailView:
        found = await self._learning_repo.get_published_lesson_by_slug(slug)
        if found is None:
            raise AppError(
                code="LESSON_NOT_FOUND",
                message="Published lesson not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        lesson, version = found
        all_rows = await self._learning_repo.list_published_lessons()
        progress_map = await self._learning_repo.list_student_lesson_progress(user.id)
        completed_slugs = {
            lsn.slug
            for lsn, _ in all_rows
            if lsn.id in progress_map and progress_map[lsn.id].status == "completed"
        }
        summary = self._to_summary(lesson, version, progress_map, completed_slugs)
        prog = progress_map.get(lesson.id)

        examples = [
            LessonInteractiveExample.model_validate(item)
            for item in (version.interactive_examples or [])
        ]
        exercise = LessonGuidedExercise.model_validate(version.guided_exercise or {})

        return LessonDetailView(
            **summary.model_dump(),
            content_en_md=version.content_en_md,
            content_bn_md=version.content_bn_md,
            learning_objectives=list(version.learning_objectives or []),
            interactive_examples=examples,
            guided_exercise=exercise,
            last_code=prog.last_code if prog else None,
            last_verdict=prog.last_verdict if prog else None,
            last_stdout=prog.last_stdout if prog else None,
            last_stderr=prog.last_stderr if prog else None,
            completed_at=prog.completed_at if prog else None,
        )

    async def mark_reading_complete(self, *, user: UserRecord, lesson_id: UUID) -> LessonDetailView:
        found = await self._learning_repo.get_published_lesson_by_id(lesson_id)
        if found is None:
            raise AppError(
                code="LESSON_NOT_FOUND",
                message="Published lesson not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        lesson, version = found
        await self._learning_repo.upsert_lesson_progress(
            student_id=user.id,
            lesson_id=lesson.id,
            lesson_version_id=version.id,
            reading_completed=True,
        )
        # Reading introduces the concept — NEVER claims mastery!
        await self._skill_graph.record_evidence(
            student_id=user.id,
            skill_slug=lesson.skill_slug,
            target_state="introduced",
            evidence_source="lesson_reading",
            evidence_ref_id=str(lesson.id),
            reason=f"Completed reading lesson '{version.title_en}' (concept introduced; execution practice still required).",
            uncertainty_note="Concept introduced through reading only — pass guided and independent Judge0 tasks to prove understanding.",
        )
        return await self.get_lesson_detail(user=user, slug=lesson.slug)

    async def run_guided_exercise(
        self, *, user: UserRecord, lesson_id: UUID, source_code: str
    ) -> LessonExerciseRunResponse:
        found = await self._learning_repo.get_published_lesson_by_id(lesson_id)
        if found is None:
            raise AppError(
                code="LESSON_NOT_FOUND",
                message="Published lesson not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        lesson, version = found
        exercise = LessonGuidedExercise.model_validate(version.guided_exercise or {})
        if not exercise.test_cases:
            raise AppError(
                code="EXERCISE_HAS_NO_TESTS",
                message="Guided exercise has no configured Judge0 test cases.",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        lang_row = await self._problem_repo.get_language_by_slug(exercise.language_slug)
        judge0_lang_id = lang_row.judge0_language_id if lang_row else DEFAULT_PYTHON_JUDGE0_ID

        case_results: list[LessonExerciseCaseResult] = []
        passed_count = 0
        overall_verdict = "accepted"
        first_stdout: str | None = None
        first_stderr: str | None = None

        for tc in exercise.test_cases:
            outcome = await self._judge0.execute_test_case(
                source_code=source_code,
                judge0_language_id=judge0_lang_id,
                stdin=tc.input_data,
                expected_output=tc.expected_output,
                cpu_time_limit_seconds=2.0,
                memory_limit_kb=131072,
            )
            passed = outcome.verdict == "accepted"
            if passed:
                passed_count += 1
            elif overall_verdict == "accepted":
                overall_verdict = outcome.verdict

            if first_stdout is None and outcome.stdout is not None:
                first_stdout = outcome.stdout
            if first_stderr is None and (outcome.stderr or outcome.compile_output):
                first_stderr = outcome.stderr or outcome.compile_output

            case_results.append(
                LessonExerciseCaseResult(
                    name=tc.name,
                    input_data=tc.input_data,
                    expected_output=tc.expected_output,
                    actual_output=outcome.stdout,
                    stderr=outcome.stderr,
                    compile_output=outcome.compile_output,
                    verdict=outcome.verdict,
                    passed=passed,
                )
            )

        all_passed = passed_count == len(exercise.test_cases)
        prog = await self._learning_repo.upsert_lesson_progress(
            student_id=user.id,
            lesson_id=lesson.id,
            lesson_version_id=version.id,
            reading_completed=True,
            exercise_passed=all_passed,
            increment_attempts=True,
            last_code=source_code,
            last_verdict=overall_verdict,
            last_stdout=first_stdout,
            last_stderr=first_stderr,
        )

        # Guided Judge0 exercise updates Skill Graph to `guided` (never over-claims `transferred`)
        if all_passed:
            new_skill_state = await self._skill_graph.record_evidence(
                student_id=user.id,
                skill_slug=lesson.skill_slug,
                target_state="guided",
                evidence_source="lesson_guided_judge0",
                evidence_ref_id=str(lesson.id),
                reason=(
                    f"Passed guided Judge0 exercise for '{version.title_en}' "
                    f"({passed_count}/{len(exercise.test_cases)} tests)."
                ),
                uncertainty_note=(
                    "Guided practice passed on Judge0; independent debugging and transfer "
                    "challenges are still needed to prove unassisted mastery."
                ),
            )
        else:
            new_skill_state = await self._skill_graph.record_evidence(
                student_id=user.id,
                skill_slug=lesson.skill_slug,
                target_state="introduced",
                evidence_source="lesson_guided_attempt",
                evidence_ref_id=str(lesson.id),
                reason=(
                    f"Attempted guided Judge0 exercise for '{version.title_en}' "
                    f"({passed_count}/{len(exercise.test_cases)} passed, verdict={overall_verdict})."
                ),
                uncertainty_note="Guided exercise not yet passed; review the concept and retry.",
            )

        await self._mentor_repo.record_learning_event(
            student_id=user.id,
            problem_id=None,
            problem_version_id=None,
            language_slug=exercise.language_slug,
            submission_id=None,
            diagnosis_id=None,
            event_type="lesson.exercise_run",
            hints_used=0,
            verdict=overall_verdict,
            metadata={
                "lesson_slug": lesson.slug,
                "skill_slug": lesson.skill_slug,
                "passed_tests": passed_count,
                "total_tests": len(exercise.test_cases),
                "exercise_passed": all_passed,
            },
        )

        return LessonExerciseRunResponse(
            lesson_id=lesson.id,
            verdict=overall_verdict,
            passed_tests=passed_count,
            total_tests=len(exercise.test_cases),
            exercise_passed=all_passed,
            progress_status=prog.status,
            skill_state_after=new_skill_state,
            case_results=case_results,
        )

    async def create_admin_lesson(
        self, *, admin: UserRecord, payload: AdminLessonCreateRequest
    ) -> LessonSummaryView:
        lesson, version = await self._learning_repo.create_admin_lesson(
            actor_id=admin.id,
            slug=payload.slug,
            skill_slug=payload.skill_slug,
            display_order=payload.display_order,
            version_data={
                "title_en": payload.title_en,
                "title_bn": payload.title_bn,
                "summary_en": payload.summary_en,
                "summary_bn": payload.summary_bn,
                "content_en_md": payload.content_en_md,
                "content_bn_md": payload.content_bn_md,
                "learning_objectives": payload.learning_objectives,
                "prerequisite_lesson_slugs": payload.prerequisite_lesson_slugs,
                "track_slugs": list(payload.track_slugs),
                "interactive_examples": [e.model_dump() for e in payload.interactive_examples],
                "guided_exercise": payload.guided_exercise.model_dump(),
                "estimated_minutes": payload.estimated_minutes,
            },
            publish=payload.publish,
        )
        return self._to_summary(lesson, version, {}, set())
