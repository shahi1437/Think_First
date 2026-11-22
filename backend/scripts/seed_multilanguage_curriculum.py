"""Idempotent Multi-Language Curriculum Seeder & Live Sandbox Verifier.

Non-destructively adds:
- 40 bilingual lessons (10 each for JavaScript, C, C++, Java) — preserves all 24 Python lessons
- 36 language-specific diagnostic questions (JS, C, C++, Java) with isolated private answer keys
- 32 multi-language problem variants (JS, C, C++, Java) for 8 core published problems
- 26 approved language-scoped RAG knowledge documents (10 Python + 16 JS/C/C++/Java)

Run with `--verify` to execute sample reference solutions against live sandbox engines.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import selectinload

_BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from scripts.multilang_diagnostics_and_problems import (  # noqa: E402
    MULTILANG_DIAGNOSTIC_QUESTIONS,
    MULTILANG_PROBLEM_VARIANTS,
)
from scripts.multilang_lessons_data import ALL_MULTILANG_LESSONS  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.core.database import DatabaseManager  # noqa: E402
from app.integrations.execution.router import ResilientExecutionClient  # noqa: E402
from app.integrations.judge0.client import HttpJudge0Client  # noqa: E402
from app.integrations.piston.client import HttpPistonClient, is_piston_configured  # noqa: E402
from app.models.learning import (  # noqa: E402
    DiagnosticQuestion,
    DiagnosticQuestionAnswer,
    Lesson,
    LessonVersion,
)
from app.models.problems import (  # noqa: E402
    Problem,
    ProblemLanguageVariant,
    ProblemReferenceSolution,
    ProblemVersion,
    SupportedLanguage,
)
from app.repositories.mentor import MentorRepository  # noqa: E402
from app.services.mentor.rag_service import RagKnowledgeService  # noqa: E402

LANGUAGE_REGISTRY_ROWS: tuple[dict[str, Any], ...] = (
    {
        "slug": "python",
        "display_name": "Python 3",
        "judge0_language_id": 71,
        "monaco_language": "python",
        "version_label": "Python (3.8.1)",
    },
    {
        "slug": "javascript",
        "display_name": "JavaScript (Node.js)",
        "judge0_language_id": 63,
        "monaco_language": "javascript",
        "version_label": "JavaScript (Node.js 12.14.0)",
    },
    {
        "slug": "c",
        "display_name": "C (GCC)",
        "judge0_language_id": 50,
        "monaco_language": "c",
        "version_label": "C (GCC 9.2.0)",
    },
    {
        "slug": "cpp",
        "display_name": "C++ (GCC)",
        "judge0_language_id": 54,
        "monaco_language": "cpp",
        "version_label": "C++ (GCC 9.2.0)",
    },
    {
        "slug": "java",
        "display_name": "Java (OpenJDK)",
        "judge0_language_id": 62,
        "monaco_language": "java",
        "version_label": "Java (OpenJDK 13.0.1)",
    },
)


async def seed_all(*, verify_sandbox: bool = False) -> None:
    settings = get_settings()
    db = DatabaseManager(settings)
    now = datetime.now(UTC)

    async for session in db.session():
        # 1. Ensure all 5 languages are enabled
        for lang_row in LANGUAGE_REGISTRY_ROWS:
            existing_lang = (
                await session.execute(
                    select(SupportedLanguage).where(SupportedLanguage.slug == lang_row["slug"])
                )
            ).scalar_one_or_none()
            if existing_lang is None:
                session.add(SupportedLanguage(**lang_row, is_enabled=True))
            else:
                existing_lang.display_name = lang_row["display_name"]
                existing_lang.judge0_language_id = lang_row["judge0_language_id"]
                existing_lang.monaco_language = lang_row["monaco_language"]
                existing_lang.version_label = lang_row["version_label"]
                existing_lang.is_enabled = True
        await session.commit()

        # 2. Idempotently seed 40 multi-language lessons (never touching Python lessons)
        lessons_upserted = 0
        for item in ALL_MULTILANG_LESSONS:
            lesson = (
                await session.execute(select(Lesson).where(Lesson.slug == item["slug"]))
            ).scalar_one_or_none()
            if lesson is None:
                lesson = Lesson(
                    slug=item["slug"],
                    language_slug=item["language_slug"],
                    skill_slug=item["skill_slug"],
                    display_order=item["display_order"],
                )
                session.add(lesson)
                await session.flush()
            else:
                lesson.language_slug = item["language_slug"]
                lesson.skill_slug = item["skill_slug"]
                lesson.display_order = item["display_order"]

            lv = (
                await session.execute(
                    select(LessonVersion)
                    .where(LessonVersion.lesson_id == lesson.id)
                    .order_by(LessonVersion.version_number.desc())
                    .limit(1)
                )
            ).scalar_one_or_none()

            if lv is None:
                lv = LessonVersion(
                    lesson_id=lesson.id,
                    version_number=1,
                    title_en=item["title_en"],
                    title_bn=item["title_bn"],
                    summary_en=item["summary_en"],
                    summary_bn=item["summary_bn"],
                    content_en_md=item["content_en_md"],
                    content_bn_md=item["content_bn_md"],
                    learning_objectives=item["learning_objectives"],
                    prerequisite_lesson_slugs=item["prerequisite_lesson_slugs"],
                    track_slugs=item["track_slugs"],
                    interactive_examples=item["interactive_examples"],
                    guided_exercise=item["guided_exercise"],
                    estimated_minutes=item["estimated_minutes"],
                    status="published",
                    published_at=now,
                )
                session.add(lv)
                await session.flush()
            else:
                lv.title_en = item["title_en"]
                lv.title_bn = item["title_bn"]
                lv.summary_en = item["summary_en"]
                lv.summary_bn = item["summary_bn"]
                lv.content_en_md = item["content_en_md"]
                lv.content_bn_md = item["content_bn_md"]
                lv.learning_objectives = item["learning_objectives"]
                lv.prerequisite_lesson_slugs = item["prerequisite_lesson_slugs"]
                lv.track_slugs = item["track_slugs"]
                lv.interactive_examples = item["interactive_examples"]
                lv.guided_exercise = item["guided_exercise"]
                lv.estimated_minutes = item["estimated_minutes"]
                lv.status = "published"
                if lv.published_at is None:
                    lv.published_at = now
            lesson.current_published_version_id = lv.id
            lessons_upserted += 1
        await session.commit()

        # 3. Idempotently seed 36 multi-language diagnostic questions with isolated answer keys
        diags_upserted = 0
        for q_item in MULTILANG_DIAGNOSTIC_QUESTIONS:
            q = (
                await session.execute(
                    select(DiagnosticQuestion)
                    .where(DiagnosticQuestion.slug == q_item["slug"])
                    .options(selectinload(DiagnosticQuestion.answer_key))
                )
            ).scalar_one_or_none()
            if q is None:
                q = DiagnosticQuestion(
                    slug=q_item["slug"],
                    language_slug=q_item["language_slug"],
                    domain_slug=q_item["domain_slug"],
                    skill_slug=q_item["skill_slug"],
                    difficulty=q_item["difficulty"],
                    question_type=q_item["question_type"],
                    prompt_en=q_item["prompt_en"],
                    prompt_bn=q_item["prompt_bn"],
                    code_snippet=q_item["code_snippet"],
                    options=q_item["options"],
                    starter_code=q_item["starter_code"],
                    status="published",
                    published_at=now,
                )
                session.add(q)
                await session.flush()
                session.add(
                    DiagnosticQuestionAnswer(
                        question_id=q.id,
                        correct_option_id=q_item["correct_option_id"],
                        explanation_en=q_item["explanation_en"],
                        explanation_bn=q_item["explanation_bn"],
                        evaluation_tests=q_item["evaluation_tests"],
                        reference_solution=q_item["reference_solution"],
                    )
                )
            else:
                q.language_slug = q_item["language_slug"]
                q.domain_slug = q_item["domain_slug"]
                q.skill_slug = q_item["skill_slug"]
                q.difficulty = q_item["difficulty"]
                q.question_type = q_item["question_type"]
                q.prompt_en = q_item["prompt_en"]
                q.prompt_bn = q_item["prompt_bn"]
                q.code_snippet = q_item["code_snippet"]
                q.options = q_item["options"]
                q.starter_code = q_item["starter_code"]
                q.status = "published"
                if q.published_at is None:
                    q.published_at = now
                if q.answer_key is None:
                    session.add(
                        DiagnosticQuestionAnswer(
                            question_id=q.id,
                            correct_option_id=q_item["correct_option_id"],
                            explanation_en=q_item["explanation_en"],
                            explanation_bn=q_item["explanation_bn"],
                            evaluation_tests=q_item["evaluation_tests"],
                            reference_solution=q_item["reference_solution"],
                        )
                    )
                else:
                    q.answer_key.correct_option_id = q_item["correct_option_id"]
                    q.answer_key.explanation_en = q_item["explanation_en"]
                    q.answer_key.explanation_bn = q_item["explanation_bn"]
                    q.answer_key.evaluation_tests = q_item["evaluation_tests"]
                    q.answer_key.reference_solution = q_item["reference_solution"]
            diags_upserted += 1
        await session.commit()

        # 4. Idempotently attach JS/C/C++/Java variants to 8 core published problems
        variants_upserted = 0
        for prob_slug, variants in MULTILANG_PROBLEM_VARIANTS.items():
            row = (
                await session.execute(
                    select(Problem, ProblemVersion)
                    .join(ProblemVersion, Problem.current_published_version_id == ProblemVersion.id)
                    .where(Problem.slug == prob_slug)
                    .options(
                        selectinload(ProblemVersion.variants).selectinload(
                            ProblemLanguageVariant.reference_solution
                        ),
                        selectinload(ProblemVersion.test_cases),
                    )
                )
            ).one_or_none()
            if row is None:
                print(f"WARNING: published problem '{prob_slug}' not found; skipping variants")
                continue
            _prob, version = row
            existing_by_lang = {v.language_slug: v for v in version.variants}
            for v_spec in variants:
                lang = v_spec["language_slug"]
                var = existing_by_lang.get(lang)
                if var is None:
                    var = ProblemLanguageVariant(
                        problem_version_id=version.id,
                        language_slug=lang,
                        starter_code=v_spec["starter_code"],
                        buggy_starter_code=v_spec.get("buggy_starter_code"),
                        debugging_prompt=v_spec.get("debugging_prompt"),
                    )
                    session.add(var)
                    await session.flush()
                    session.add(
                        ProblemReferenceSolution(
                            variant_id=var.id,
                            reference_solution=v_spec["reference_solution"],
                            expected_bug_summary=v_spec.get("expected_bug_summary"),
                            expected_failure_category=v_spec.get("expected_failure_category"),
                        )
                    )
                else:
                    var.starter_code = v_spec["starter_code"]
                    var.buggy_starter_code = v_spec.get("buggy_starter_code")
                    var.debugging_prompt = v_spec.get("debugging_prompt")
                    if var.reference_solution is None:
                        session.add(
                            ProblemReferenceSolution(
                                variant_id=var.id,
                                reference_solution=v_spec["reference_solution"],
                                expected_bug_summary=v_spec.get("expected_bug_summary"),
                                expected_failure_category=v_spec.get("expected_failure_category"),
                            )
                        )
                    else:
                        var.reference_solution.reference_solution = v_spec["reference_solution"]
                        var.reference_solution.expected_bug_summary = v_spec.get(
                            "expected_bug_summary"
                        )
                        var.reference_solution.expected_failure_category = v_spec.get(
                            "expected_failure_category"
                        )
                variants_upserted += 1
        await session.commit()

        # 5. Seed approved multi-language RAG documents (26 total: 10 Python + 16 JS/C/C++/Java)
        mentor_repo = MentorRepository(session)
        rag_service = RagKnowledgeService(repository=mentor_repo, settings=settings)
        rag_count = await rag_service.seed_approved_corpus()

        print(
            f"SEED COMPLETE: lessons_upserted={lessons_upserted}, "
            f"diagnostics_upserted={diags_upserted}, "
            f"problem_variants_upserted={variants_upserted}, "
            f"rag_documents_seeded={rag_count}"
        )
        break

    if verify_sandbox:
        await _verify_seeded_curriculum(settings)

    await db.dispose()


async def _verify_seeded_curriculum(settings: Any) -> None:
    """Verify all 40 multi-language lesson reference solutions + 8 diagnostic code checks live."""
    j0_id_map = {"python": 71, "javascript": 63, "c": 50, "cpp": 54, "java": 62}
    primary = HttpJudge0Client(settings)
    fallback = HttpPistonClient(settings) if is_piston_configured(settings) else None
    client = ResilientExecutionClient(primary=primary, fallback=fallback, settings=settings)

    lesson_ok = 0
    lesson_fail = 0
    for item in ALL_MULTILANG_LESSONS:
        lang = item["language_slug"]
        jid = j0_id_map[lang]
        ref = item["reference_solution"]
        tcs = item["guided_exercise"]["test_cases"]
        all_pass = True
        for tc in tcs:
            out = await client.execute_test_case(
                source_code=ref,
                judge0_language_id=jid,
                stdin=tc["input_data"],
                expected_output=tc["expected_output"],
                cpu_time_limit_seconds=4.0,
                memory_limit_kb=262144,
                language_slug=lang,
            )
            if out.verdict != "accepted":
                all_pass = False
                print(
                    f"  FAIL lesson={item['slug']} tc={tc['name']} provider={out.execution_provider} "
                    f"verdict={out.verdict} out={out.stdout!r} err={out.stderr!r} cmp={out.compile_output!r}"
                )
        if all_pass:
            lesson_ok += 1
        else:
            lesson_fail += 1

    diag_ok = 0
    diag_fail = 0
    for q in MULTILANG_DIAGNOSTIC_QUESTIONS:
        if q["question_type"] != "code_execution":
            continue
        lang = q["language_slug"]
        jid = j0_id_map[lang]
        all_pass = True
        for tc in q["evaluation_tests"]:
            out = await client.execute_test_case(
                source_code=q["reference_solution"],
                judge0_language_id=jid,
                stdin=tc["input_data"],
                expected_output=tc["expected_output"],
                cpu_time_limit_seconds=4.0,
                memory_limit_kb=262144,
                language_slug=lang,
            )
            if out.verdict != "accepted":
                all_pass = False
                print(
                    f"  FAIL diag={q['slug']} tc={tc['name']} provider={out.execution_provider} "
                    f"verdict={out.verdict} err={out.stderr!r} cmp={out.compile_output!r}"
                )
        if all_pass:
            diag_ok += 1
        else:
            diag_fail += 1

    print(
        f"LIVE VERIFICATION: lessons={lesson_ok}/{lesson_ok + lesson_fail} passed, "
        f"diagnostic_code_items={diag_ok}/{diag_ok + diag_fail} passed"
    )
    if lesson_fail or diag_fail:
        raise SystemExit(1)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true", help="Verify reference solutions live")
    args = parser.parse_args()
    asyncio.run(seed_all(verify_sandbox=args.verify))


if __name__ == "__main__":
    main()
