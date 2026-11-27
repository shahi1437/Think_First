import ast
from typing import Any
from uuid import UUID

from fastapi import status

from app.core.errors import AppError
from app.integrations.judge0.client import Judge0Client
from app.models.problems import Problem, ProblemVersion, SupportedLanguage
from app.repositories.identity import UserRecord
from app.repositories.problems import ProblemRepository
from app.schemas.common import PaginatedResponse
from app.schemas.problems import (
    AdminContentReviewItem,
    AdminLanguageSyncResponse,
    AdminProblemArchiveResponse,
    AdminProblemCreateRequest,
    AdminProblemDetail,
    AdminProblemListItem,
    AdminProblemUpdateRequest,
    AdminProblemVersionsResponse,
    AdminProblemVersionSummary,
    AdminTestCaseDetail,
    AdminValidationReport,
    AdminValidationVariantResult,
    AdminVariantDetail,
    Difficulty,
    LanguageItem,
    ProblemCompletionStatus,
    ProblemExample,
    ProblemMode,
    ProblemStatus,
    PublicTestCaseView,
    StudentLanguageVariantView,
    StudentProblemDetail,
    StudentProblemListItem,
    TrackSlug,
)

_FAILURE_PRIORITY: dict[str, int] = {
    "compilation_error": 5,
    "runtime_error": 4,
    "time_limit_exceeded": 3,
    "memory_limit_exceeded": 2,
    "wrong_answer": 1,
}


def _check_python_syntax(label: str, code: str) -> str | None:
    """Parse Python AST strictly without executing any code."""
    try:
        ast.parse(code)
        return None
    except SyntaxError as exc:
        return f"{label} syntax error at line {exc.lineno or '?'}: {exc.msg}"


def _analyze_test_suite(tests: list[Any]) -> tuple[list[str], list[str]]:
    """Detect contradictory, duplicate, or ineffective test cases."""
    errors: list[str] = []
    warnings: list[str] = []
    by_input: dict[str, set[str]] = {}
    seen_pairs: set[tuple[str, str]] = set()
    distinct_outputs: set[str] = set()

    for tc in tests:
        norm_in = tc.input_data.strip()
        norm_out = tc.expected_output.strip()
        distinct_outputs.add(norm_out)
        pair = (norm_in, norm_out)
        if pair in seen_pairs:
            warnings.append(
                f"Duplicate test case #{tc.ordinal} ({tc.name}): "
                "identical stdin and expected output already covered."
            )
        seen_pairs.add(pair)
        by_input.setdefault(norm_in, set()).add(norm_out)

    for norm_in, outputs in by_input.items():
        if len(outputs) > 1:
            preview = norm_in[:40].replace("\n", "\\n")
            errors.append(
                f"Contradictory test cases for identical input '{preview}': "
                "multiple distinct expected outputs."
            )

    if len(tests) >= 2 and len(distinct_outputs) == 1:
        warnings.append(
            "All test cases share the exact same expected output; consider adding "
            "negative/boundary cases to prevent constant-output solutions from passing."
        )
    return errors, warnings


def _classify_buggy_failure(verdicts: list[str]) -> str | None:
    non_accepted = [v for v in verdicts if v != "accepted"]
    if not non_accepted:
        return None
    return max(non_accepted, key=lambda v: _FAILURE_PRIORITY.get(v, 0))


_LANGUAGE_MATCH_RULES: tuple[tuple[str, str, str, str, bool], ...] = (
    ("python", "Python 3", "python", "Python (3.", True),
    ("javascript", "JavaScript (Node.js)", "javascript", "JavaScript (Node.js", True),
    ("c", "C (GCC)", "c", "C (GCC", True),
    ("cpp", "C++ (GCC)", "cpp", "C++ (GCC", True),
    ("java", "Java (OpenJDK)", "java", "Java (OpenJDK", True),
)


_LANGUAGE_ORDER: dict[str, int] = {
    "python": 0,
    "javascript": 1,
    "c": 2,
    "cpp": 3,
    "java": 4,
}


def _to_language_item(lang: SupportedLanguage) -> LanguageItem:
    return LanguageItem(
        slug=lang.slug,
        display_name=lang.display_name,
        judge0_language_id=lang.judge0_language_id,
        monaco_language=lang.monaco_language,
        version_label=lang.version_label,
        is_enabled=lang.is_enabled,
    )


class ProblemService:
    """Handles student problem discovery and Admin authoring/validation/publishing workflows."""

    def __init__(self, repository: ProblemRepository, judge0: Judge0Client) -> None:
        self._repo = repository
        self._judge0 = judge0

    # --- Languages ---

    async def list_languages(self, *, enabled_only: bool = True) -> list[LanguageItem]:
        languages = await self._repo.list_languages(enabled_only=enabled_only)
        return [_to_language_item(lang) for lang in languages]

    async def sync_languages_from_judge0(
        self, *, actor: UserRecord, request_id: str | None
    ) -> AdminLanguageSyncResponse:
        remote_languages = await self._judge0.list_languages()
        synced: list[SupportedLanguage] = []
        for slug, display_name, monaco_lang, prefix, default_enabled in _LANGUAGE_MATCH_RULES:
            matches = [rl for rl in remote_languages if rl.name.startswith(prefix)]
            if not matches:
                continue
            chosen = max(matches, key=lambda item: item.id)
            saved = await self._repo.upsert_language(
                slug=slug,
                display_name=display_name,
                judge0_language_id=chosen.id,
                monaco_language=monaco_lang,
                version_label=chosen.name,
                is_enabled=default_enabled,
            )
            synced.append(saved)

        await self._repo.record_audit(
            actor_user_id=actor.id,
            action="languages.synced",
            target_type="supported_languages",
            target_id="judge0_registry",
            metadata={"synced_slugs": [s.slug for s in synced]},
            request_id=request_id,
        )
        all_langs = await self._repo.list_languages(enabled_only=False)
        return AdminLanguageSyncResponse(
            synced_count=len(synced),
            languages=[_to_language_item(lang) for lang in all_langs],
        )

    # --- Student Problem Bank ---

    async def list_published_problems(
        self,
        *,
        search: str | None = None,
        difficulty: Difficulty | None = None,
        mode: ProblemMode | None = None,
        topic: str | None = None,
        track: TrackSlug | None = None,
        language: str | None = None,
        student_id: UUID | None = None,
        completion_status: ProblemCompletionStatus | None = None,
        recommended_only: bool = False,
        limit: int = 20,
        offset: int = 0,
    ) -> PaginatedResponse[StudentProblemListItem]:
        # When student-scoped adaptive filters are active, fetch full page set to filter accurately
        needs_post_filter = student_id is not None and (
            completion_status is not None or recommended_only
        )
        rows, total = await self._repo.list_published_problems(
            search=search,
            difficulty=difficulty,
            mode=mode,
            topic=topic,
            track=track,
            language=language,
            limit=200 if needs_post_filter else limit,
            offset=0 if needs_post_filter else offset,
        )

        progress_map: dict[UUID, tuple[int, bool]] = {}
        weak_skills: set[str] = set()
        if student_id is not None:
            if hasattr(self._repo, "get_student_problem_progress_map"):
                progress_map = await self._repo.get_student_problem_progress_map(student_id)
            if hasattr(self._repo, "list_student_weak_skills"):
                weak_skills = await self._repo.list_student_weak_skills(student_id)

        solved_count = sum(1 for _, solved in progress_map.values() if solved)
        next_diff_tier: set[str] = (
            {"beginner", "basic"}
            if solved_count < 3
            else ({"basic", "intermediate"} if solved_count < 8 else {"intermediate", "advanced"})
        )

        items: list[StudentProblemListItem] = []
        for problem, version in rows:
            attempts_cnt, is_solved = progress_map.get(problem.id, (0, False))
            status_val: ProblemCompletionStatus = (
                "solved" if is_solved else ("attempted" if attempts_cnt > 0 else "unattempted")
            )
            matching_weak = [
                sk for sk in (list(version.skills) + list(version.topics)) if sk in weak_skills
            ]
            is_rec = False
            rec_reason: str | None = None
            if student_id is not None and not is_solved:
                if matching_weak:
                    is_rec = True
                    rec_reason = f"Targets developing concept: {matching_weak[0].replace('_', ' ')}"
                elif attempts_cnt > 0:
                    is_rec = True
                    rec_reason = f"In progress ({attempts_cnt} attempt(s)) — finish and verify fix"
                elif version.difficulty in next_diff_tier:
                    is_rec = True
                    rec_reason = (
                        f"Matches your progressive {version.difficulty} difficulty tier "
                        f"({solved_count} solved so far)"
                    )

            items.append(
                StudentProblemListItem(
                    problem_id=problem.id,
                    version_id=version.id,
                    slug=problem.slug,
                    title=version.title,
                    difficulty=version.difficulty,
                    track_slug=version.track_slug,
                    mode=version.mode,
                    topics=list(version.topics),
                    skills=list(version.skills),
                    supported_languages=sorted(
                        {v.language_slug for v in version.variants},
                        key=lambda slug: (_LANGUAGE_ORDER.get(slug, 99), slug),
                    ),
                    published_at=version.published_at,
                    completion_status=status_val,
                    attempts_count=attempts_cnt,
                    is_recommended=is_rec,
                    recommendation_reason=rec_reason,
                )
            )

        if completion_status is not None:
            items = [it for it in items if it.completion_status == completion_status]
        if recommended_only:
            items = [it for it in items if it.is_recommended]
        if needs_post_filter:
            total = len(items)
            items = items[offset : offset + limit]

        return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)

    async def get_published_problem(self, problem_id: UUID) -> StudentProblemDetail:
        found = await self._repo.get_published_problem(problem_id)
        if found is None:
            raise AppError(
                code="PROBLEM_NOT_FOUND",
                message="Published problem not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        problem, version = found
        languages = {
            lang.slug: lang for lang in await self._repo.list_languages(enabled_only=False)
        }

        variant_views = [
            StudentLanguageVariantView(
                language_slug=v.language_slug,
                display_name=(
                    languages[v.language_slug].display_name
                    if v.language_slug in languages
                    else v.language_slug
                ),
                monaco_language=(
                    languages[v.language_slug].monaco_language
                    if v.language_slug in languages
                    else v.language_slug
                ),
                starter_code=v.starter_code,
                buggy_starter_code=v.buggy_starter_code,
                debugging_prompt=v.debugging_prompt,
            )
            for v in sorted(
                version.variants,
                key=lambda item: (_LANGUAGE_ORDER.get(item.language_slug, 99), item.language_slug),
            )
        ]

        sorted_tests = sorted(version.test_cases, key=lambda tc: tc.ordinal)
        public_tests = [
            PublicTestCaseView(
                id=tc.id,
                ordinal=tc.ordinal,
                name=tc.name,
                input_data=tc.input_data,
                expected_output=tc.expected_output,
            )
            for tc in sorted_tests
            if not tc.is_hidden
        ]
        hidden_count = sum(1 for tc in sorted_tests if tc.is_hidden)
        examples = [ProblemExample.model_validate(item) for item in (version.examples or [])]

        return StudentProblemDetail(
            problem_id=problem.id,
            version_id=version.id,
            version_number=version.version_number,
            slug=problem.slug,
            title=version.title,
            statement_md=version.statement_md,
            difficulty=version.difficulty,
            track_slug=version.track_slug,
            mode=version.mode,
            topics=list(version.topics),
            skills=list(version.skills),
            prerequisites=list(version.prerequisites),
            learning_objectives=list(version.learning_objectives),
            examples=examples,
            time_limit_ms=version.time_limit_ms,
            memory_limit_kb=version.memory_limit_kb,
            variants=variant_views,
            public_test_cases=public_tests,
            hidden_test_count=hidden_count,
        )

    # --- Admin Problem Studio ---

    def _validate_authoring_payload(
        self,
        *,
        mode: ProblemMode,
        variants: list[Any],
        test_cases: list[Any],
        known_languages: set[str],
    ) -> None:
        if not any(not tc.is_hidden for tc in test_cases):
            raise AppError(
                code="INVALID_TEST_SUITE",
                message="A problem must define at least one public test case.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        if not any(tc.is_hidden for tc in test_cases):
            raise AppError(
                code="INVALID_TEST_SUITE",
                message="A problem must define at least one hidden test case.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        ordinals = [tc.ordinal for tc in test_cases]
        if len(ordinals) != len(set(ordinals)):
            raise AppError(
                code="DUPLICATE_TEST_ORDINAL",
                message="Test case ordinals must be unique.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        seen_langs: set[str] = set()
        for v in variants:
            if v.language_slug not in known_languages:
                raise AppError(
                    code="UNSUPPORTED_LANGUAGE",
                    message=f"Language '{v.language_slug}' is not registered.",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
            if v.language_slug in seen_langs:
                raise AppError(
                    code="DUPLICATE_LANGUAGE_VARIANT",
                    message=f"Duplicate language variant '{v.language_slug}'.",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
            seen_langs.add(v.language_slug)
            if mode == "debugging" and (
                not v.buggy_starter_code or not v.buggy_starter_code.strip()
            ):
                raise AppError(
                    code="MISSING_BUGGY_STARTER",
                    message="Debugging problems must include buggy_starter_code for every variant.",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

    def _to_admin_detail(
        self,
        problem: Problem,
        version: ProblemVersion,
        *,
        assigned_courses_count: int = 0,
    ) -> AdminProblemDetail:
        variants = [
            AdminVariantDetail(
                id=v.id,
                language_slug=v.language_slug,
                starter_code=v.starter_code,
                buggy_starter_code=v.buggy_starter_code,
                debugging_prompt=v.debugging_prompt,
                reference_solution=(
                    v.reference_solution.reference_solution if v.reference_solution else ""
                ),
                expected_bug_summary=(
                    v.reference_solution.expected_bug_summary if v.reference_solution else None
                ),
                expected_failure_category=(
                    v.reference_solution.expected_failure_category if v.reference_solution else None
                ),
            )
            for v in sorted(
                version.variants,
                key=lambda item: (_LANGUAGE_ORDER.get(item.language_slug, 99), item.language_slug),
            )
        ]
        test_cases = [
            AdminTestCaseDetail(
                id=tc.id,
                ordinal=tc.ordinal,
                name=tc.name,
                input_data=tc.input_data,
                expected_output=tc.expected_output,
                is_hidden=tc.is_hidden,
                weight=tc.weight,
            )
            for tc in sorted(version.test_cases, key=lambda item: item.ordinal)
        ]
        reviews = [
            AdminContentReviewItem(
                id=r.id,
                action=r.action,
                notes=r.notes,
                validation_summary=dict(r.validation_summary or {}),
                created_at=r.created_at,
            )
            for r in sorted(version.reviews, key=lambda item: item.created_at, reverse=True)
        ]
        examples = [ProblemExample.model_validate(item) for item in (version.examples or [])]
        return AdminProblemDetail(
            problem_id=problem.id,
            slug=problem.slug,
            version_id=version.id,
            version_number=version.version_number,
            title=version.title,
            statement_md=version.statement_md,
            difficulty=version.difficulty,
            track_slug=version.track_slug,
            mode=version.mode,
            status=version.status,
            is_archived=problem.is_archived,
            topics=list(version.topics),
            skills=list(version.skills),
            prerequisites=list(version.prerequisites),
            learning_objectives=list(version.learning_objectives),
            examples=examples,
            time_limit_ms=version.time_limit_ms,
            memory_limit_kb=version.memory_limit_kb,
            variants=variants,
            test_cases=test_cases,
            reviews=reviews,
            assigned_courses_count=assigned_courses_count,
            validated_at=version.validated_at,
            published_at=version.published_at,
        )

    async def list_admin_problems(
        self,
        *,
        status_filter: ProblemStatus | None = None,
        mode: ProblemMode | None = None,
        search: str | None = None,
        limit: int = 25,
        offset: int = 0,
    ) -> PaginatedResponse[AdminProblemListItem]:
        rows, total = await self._repo.list_admin_problems(
            status_filter=status_filter,
            mode=mode,
            search=search,
            limit=limit,
            offset=offset,
        )
        items = [
            AdminProblemListItem(
                problem_id=p.id,
                slug=p.slug,
                latest_version_id=pv.id,
                latest_version_number=pv.version_number,
                title=pv.title,
                difficulty=pv.difficulty,
                track_slug=pv.track_slug,
                mode=pv.mode,
                status=pv.status,
                topics=list(pv.topics),
                is_published=p.current_published_version_id is not None,
                is_archived=p.is_archived,
                updated_at=pv.updated_at,
            )
            for p, pv in rows
        ]
        return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)

    async def get_admin_problem(self, problem_id: UUID) -> AdminProblemDetail:
        found = await self._repo.get_admin_problem_latest(problem_id)
        if found is None:
            raise AppError(
                code="PROBLEM_NOT_FOUND",
                message="Problem not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        assigned_count = await self._repo.count_assigned_courses_for_problem(problem_id)
        return self._to_admin_detail(found[0], found[1], assigned_courses_count=assigned_count)

    async def list_problem_versions(self, problem_id: UUID) -> AdminProblemVersionsResponse:
        found = await self._repo.list_problem_versions(problem_id)
        if found is None:
            raise AppError(
                code="PROBLEM_NOT_FOUND",
                message="Problem not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        problem, versions = found
        items = [
            AdminProblemVersionSummary(
                version_id=pv.id,
                version_number=pv.version_number,
                title=pv.title,
                statement_md=pv.statement_md,
                difficulty=pv.difficulty,
                track_slug=pv.track_slug,
                mode=pv.mode,
                status=pv.status,
                topics=list(pv.topics),
                skills=list(pv.skills),
                time_limit_ms=pv.time_limit_ms,
                memory_limit_kb=pv.memory_limit_kb,
                test_case_count=len(pv.test_cases),
                hidden_test_count=sum(1 for tc in pv.test_cases if tc.is_hidden),
                is_current_published=problem.current_published_version_id == pv.id,
                validated_at=pv.validated_at,
                published_at=pv.published_at,
                created_at=pv.created_at,
                reviews=[
                    AdminContentReviewItem(
                        id=r.id,
                        action=r.action,
                        notes=r.notes,
                        validation_summary=dict(r.validation_summary or {}),
                        created_at=r.created_at,
                    )
                    for r in sorted(pv.reviews, key=lambda item: item.created_at, reverse=True)
                ],
            )
            for pv in versions
        ]
        return AdminProblemVersionsResponse(
            problem_id=problem.id,
            slug=problem.slug,
            current_published_version_id=problem.current_published_version_id,
            versions=items,
        )

    async def create_problem(
        self,
        *,
        actor: UserRecord,
        payload: AdminProblemCreateRequest,
        request_id: str | None,
    ) -> AdminProblemDetail:
        existing = await self._repo.get_problem_by_slug(payload.slug)
        if existing is not None:
            raise AppError(
                code="PROBLEM_SLUG_EXISTS",
                message=f"A problem with slug '{payload.slug}' already exists.",
                status_code=status.HTTP_409_CONFLICT,
            )
        known_langs = {lang.slug for lang in await self._repo.list_languages(enabled_only=False)}
        self._validate_authoring_payload(
            mode=payload.mode,
            variants=payload.variants,
            test_cases=payload.test_cases,
            known_languages=known_langs,
        )
        problem, version = await self._repo.create_problem_with_draft_version(
            payload=payload, actor_id=actor.id
        )
        await self._repo.record_audit(
            actor_user_id=actor.id,
            action="problem.created",
            target_type="problem",
            target_id=str(problem.id),
            metadata={"slug": problem.slug, "version_number": version.version_number},
            request_id=request_id,
        )
        return self._to_admin_detail(problem, version)

    async def update_problem(
        self,
        *,
        actor: UserRecord,
        problem_id: UUID,
        payload: AdminProblemUpdateRequest,
        request_id: str | None,
    ) -> AdminProblemDetail:
        found = await self._repo.get_admin_problem_latest(problem_id)
        if found is None:
            raise AppError(
                code="PROBLEM_NOT_FOUND",
                message="Problem not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        problem, latest = found
        known_langs = {lang.slug for lang in await self._repo.list_languages(enabled_only=False)}
        self._validate_authoring_payload(
            mode=payload.mode,
            variants=payload.variants,
            test_cases=payload.test_cases,
            known_languages=known_langs,
        )
        updated_problem, updated_version = await self._repo.update_or_branch_problem_version(
            problem=problem,
            latest_version=latest,
            payload=payload,
            actor_id=actor.id,
        )
        await self._repo.record_audit(
            actor_user_id=actor.id,
            action="problem.updated",
            target_type="problem",
            target_id=str(problem.id),
            metadata={"version_number": updated_version.version_number},
            request_id=request_id,
        )
        return self._to_admin_detail(updated_problem, updated_version)

    async def validate_problem(
        self,
        *,
        actor: UserRecord,
        problem_id: UUID,
        request_id: str | None,
    ) -> AdminValidationReport:
        """Execute every reference solution against ALL tests (and buggy starter for debugging)."""
        found = await self._repo.get_admin_problem_latest(problem_id)
        if found is None:
            raise AppError(
                code="PROBLEM_NOT_FOUND",
                message="Problem not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        problem, version = found
        languages = {
            lang.slug: lang for lang in await self._repo.list_languages(enabled_only=False)
        }
        sorted_tests = sorted(version.test_cases, key=lambda tc: tc.ordinal)
        suite_errors, quality_warnings = _analyze_test_suite(sorted_tests)

        variant_results: list[AdminValidationVariantResult] = []
        overall_passed = len(suite_errors) == 0

        for variant in version.variants:
            lang = languages.get(variant.language_slug)
            if lang is None:
                overall_passed = False
                variant_results.append(
                    AdminValidationVariantResult(
                        language_slug=variant.language_slug,
                        syntax_ok=False,
                        reference_passed=0,
                        total_tests=len(sorted_tests),
                        reference_all_passed=False,
                        buggy_starter_tested=False,
                        errors=[f"Language '{variant.language_slug}' missing from registry."],
                    )
                )
                continue

            ref_code = (
                variant.reference_solution.reference_solution if variant.reference_solution else ""
            )
            syntax_errors: list[str] = []
            if variant.language_slug == "python":
                ref_syntax_err = _check_python_syntax("Reference solution", ref_code)
                if ref_syntax_err:
                    syntax_errors.append(ref_syntax_err)
                starter_syntax_err = _check_python_syntax("Starter code", variant.starter_code)
                if starter_syntax_err:
                    syntax_errors.append(starter_syntax_err)
            syntax_ok = len(syntax_errors) == 0

            ref_passed = 0
            errors: list[str] = [*suite_errors, *syntax_errors]
            max_runtime_ms = 0
            max_memory_kb = 0

            for tc in sorted_tests:
                outcome = await self._judge0.execute_test_case(
                    source_code=ref_code,
                    judge0_language_id=lang.judge0_language_id,
                    stdin=tc.input_data,
                    expected_output=tc.expected_output,
                    cpu_time_limit_seconds=version.time_limit_ms / 1000.0,
                    memory_limit_kb=version.memory_limit_kb,
                )
                if outcome.runtime_ms is not None:
                    max_runtime_ms = max(max_runtime_ms, outcome.runtime_ms)
                if outcome.memory_kb is not None:
                    max_memory_kb = max(max_memory_kb, outcome.memory_kb)
                if outcome.verdict == "accepted":
                    ref_passed += 1
                else:
                    errors.append(
                        f"Reference failed test #{tc.ordinal} ({tc.name}): {outcome.verdict}"
                    )

            ref_all_passed = ref_passed == len(sorted_tests) and len(sorted_tests) > 0
            buggy_tested = False
            buggy_failed_expected: bool | None = None
            observed_buggy_category: str | None = None

            if version.mode == "debugging" and variant.buggy_starter_code:
                buggy_tested = True
                buggy_passed = 0
                buggy_verdicts: list[str] = []
                for tc in sorted_tests:
                    bug_outcome = await self._judge0.execute_test_case(
                        source_code=variant.buggy_starter_code,
                        judge0_language_id=lang.judge0_language_id,
                        stdin=tc.input_data,
                        expected_output=tc.expected_output,
                        cpu_time_limit_seconds=version.time_limit_ms / 1000.0,
                        memory_limit_kb=version.memory_limit_kb,
                    )
                    buggy_verdicts.append(bug_outcome.verdict)
                    if bug_outcome.verdict == "accepted":
                        buggy_passed += 1
                buggy_failed_expected = buggy_passed < len(sorted_tests)
                observed_buggy_category = _classify_buggy_failure(buggy_verdicts)
                if not buggy_failed_expected:
                    errors.append(
                        "Debugging starter code unexpectedly passed all tests; "
                        "it must contain a verifiable bug."
                    )

            variant_ok = (
                syntax_ok
                and ref_all_passed
                and (buggy_failed_expected is not False)
                and not suite_errors
            )
            if not variant_ok:
                overall_passed = False

            variant_results.append(
                AdminValidationVariantResult(
                    language_slug=variant.language_slug,
                    syntax_ok=syntax_ok,
                    syntax_errors=syntax_errors,
                    reference_passed=ref_passed,
                    total_tests=len(sorted_tests),
                    reference_all_passed=ref_all_passed,
                    buggy_starter_tested=buggy_tested,
                    buggy_starter_failed_as_expected=buggy_failed_expected,
                    observed_buggy_failure_category=observed_buggy_category,
                    max_runtime_ms=max_runtime_ms or None,
                    max_memory_kb=max_memory_kb or None,
                    errors=errors,
                )
            )

        new_status: ProblemStatus = "validated" if overall_passed else "draft"
        summary = {
            "passed": overall_passed,
            "quality_warnings": quality_warnings,
            "variants": [vr.model_dump() for vr in variant_results],
        }
        await self._repo.record_content_review(
            version=version,
            reviewer_id=actor.id,
            action="validated",
            new_status=new_status,
            notes=(
                "Automated Judge0 validation passed."
                if overall_passed
                else "Automated Judge0 validation failed."
            ),
            validation_summary=summary,
        )
        await self._repo.record_curriculum_validation(
            target_type="problem_version",
            target_id=version.id,
            validator_id=actor.id,
            passed=overall_passed,
            summary=summary,
        )
        await self._repo.record_audit(
            actor_user_id=actor.id,
            action="problem.validated",
            target_type="problem_version",
            target_id=str(version.id),
            metadata={"passed": overall_passed, "new_status": new_status},
            request_id=request_id,
        )
        return AdminValidationReport(
            problem_id=problem.id,
            version_id=version.id,
            passed=overall_passed,
            new_status=new_status,
            quality_warnings=quality_warnings,
            variant_results=variant_results,
        )

    async def submit_for_review(
        self,
        *,
        actor: UserRecord,
        problem_id: UUID,
        notes: str,
        request_id: str | None,
    ) -> AdminProblemDetail:
        found = await self._repo.get_admin_problem_latest(problem_id)
        if found is None:
            raise AppError(
                code="PROBLEM_NOT_FOUND",
                message="Problem not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        problem, version = found
        if version.status != "validated" or version.validated_at is None:
            raise AppError(
                code="VALIDATION_REQUIRED",
                message="Run and pass automated Judge0 validation before submitting for review.",
                status_code=status.HTTP_409_CONFLICT,
            )
        await self._repo.record_content_review(
            version=version,
            reviewer_id=actor.id,
            action="submitted_for_review",
            new_status="in_review",
            notes=notes or "Submitted for human curriculum review.",
        )
        await self._repo.record_audit(
            actor_user_id=actor.id,
            action="problem.submitted_for_review",
            target_type="problem_version",
            target_id=str(version.id),
            metadata={"notes": notes},
            request_id=request_id,
        )
        return await self.get_admin_problem(problem.id)

    async def approve_problem(
        self,
        *,
        actor: UserRecord,
        problem_id: UUID,
        notes: str,
        request_id: str | None,
    ) -> AdminProblemDetail:
        found = await self._repo.get_admin_problem_latest(problem_id)
        if found is None:
            raise AppError(
                code="PROBLEM_NOT_FOUND",
                message="Problem not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        problem, version = found
        if version.status not in ("validated", "in_review") or version.validated_at is None:
            raise AppError(
                code="VALIDATION_REQUIRED",
                message="Problem must pass automated Judge0 validation before approval.",
                status_code=status.HTTP_409_CONFLICT,
            )
        await self._repo.record_content_review(
            version=version,
            reviewer_id=actor.id,
            action="approved",
            new_status="approved",
            notes=notes or "Approved by reviewer.",
        )
        await self._repo.record_audit(
            actor_user_id=actor.id,
            action="problem.approved",
            target_type="problem_version",
            target_id=str(version.id),
            metadata={"notes": notes},
            request_id=request_id,
        )
        return await self.get_admin_problem(problem.id)

    async def reject_problem(
        self,
        *,
        actor: UserRecord,
        problem_id: UUID,
        notes: str,
        request_id: str | None,
    ) -> AdminProblemDetail:
        found = await self._repo.get_admin_problem_latest(problem_id)
        if found is None:
            raise AppError(
                code="PROBLEM_NOT_FOUND",
                message="Problem not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        problem, version = found
        if version.status not in ("validated", "in_review", "approved"):
            raise AppError(
                code="INVALID_STATE_TRANSITION",
                message=(
                    "Only validated, in-review, or approved drafts can be rejected with feedback."
                ),
                status_code=status.HTTP_409_CONFLICT,
            )
        await self._repo.record_content_review(
            version=version,
            reviewer_id=actor.id,
            action="rejected",
            new_status="draft",
            notes=notes,
        )
        await self._repo.record_audit(
            actor_user_id=actor.id,
            action="problem.rejected",
            target_type="problem_version",
            target_id=str(version.id),
            metadata={"notes": notes},
            request_id=request_id,
        )
        return await self.get_admin_problem(problem.id)

    async def publish_problem(
        self,
        *,
        actor: UserRecord,
        problem_id: UUID,
        notes: str,
        request_id: str | None,
    ) -> AdminProblemDetail:
        found = await self._repo.get_admin_problem_latest(problem_id)
        if found is None:
            raise AppError(
                code="PROBLEM_NOT_FOUND",
                message="Problem not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        problem, version = found
        if version.status not in ("validated", "approved") or version.validated_at is None:
            raise AppError(
                code="CANNOT_PUBLISH_UNVALIDATED",
                message="Refusing to publish untested content. Run automated validation first.",
                status_code=status.HTTP_409_CONFLICT,
            )
        problem.is_archived = False
        await self._repo.record_content_review(
            version=version,
            reviewer_id=actor.id,
            action="published",
            new_status="published",
            notes=notes or "Published to Student Problem Bank.",
            publish_problem=problem,
        )
        await self._repo.record_audit(
            actor_user_id=actor.id,
            action="problem.published",
            target_type="problem_version",
            target_id=str(version.id),
            metadata={"slug": problem.slug, "version_number": version.version_number},
            request_id=request_id,
        )
        return await self.get_admin_problem(problem.id)

    async def archive_problem(
        self,
        *,
        actor: UserRecord,
        problem_id: UUID,
        notes: str,
        request_id: str | None,
    ) -> AdminProblemArchiveResponse:
        found = await self._repo.get_admin_problem_latest(problem_id)
        if found is None:
            raise AppError(
                code="PROBLEM_NOT_FOUND",
                message="Problem not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        problem, version = found
        assigned_courses = await self._repo.count_assigned_courses_for_problem(problem.id)
        await self._repo.archive_problem_version(
            problem=problem,
            version=version,
            reviewer_id=actor.id,
            notes=notes,
        )
        await self._repo.record_audit(
            actor_user_id=actor.id,
            action="problem.archived",
            target_type="problem_version",
            target_id=str(version.id),
            metadata={
                "slug": problem.slug,
                "version_number": version.version_number,
                "assigned_courses_count": assigned_courses,
            },
            request_id=request_id,
        )
        return AdminProblemArchiveResponse(
            problem_id=problem.id,
            slug=problem.slug,
            is_archived=True,
            latest_version_status="archived",
            assigned_courses_count=assigned_courses,
            message=(
                f"Problem archived from new discovery while preserving historical "
                f"version v{version.version_number} for {assigned_courses} assigned course(s)."
            ),
        )
