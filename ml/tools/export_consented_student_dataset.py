"""Consent-gated, privacy-preserving real student debugging dataset exporter.

Security & Privacy Invariants:
- STRICT OPT-IN ONLY: exports records ONLY for students whose MOST RECENT
  `learning_events` row with `event_type = 'ml_data_consent_updated'` has
  `metadata->>'consent_granted' = 'true'`. If a student later revokes consent,
  all of their rows are immediately excluded.
- NEVER exports hidden test cases (`execution_results.is_hidden = false` only).
- NEVER exports emails, full names, or raw `student_id` UUIDs (replaces user IDs
  with an irreversible salted SHA-256 pseudonym and redacts emails/URLs in code).
- STRICT SEPARATION: writes ONLY to `ml/datasets/real_student_consented.csv` with
  `data_origin = 'real_student_consented'` and `review_status = 'pending_human_label'`
  so unverified real student predictions are never silently mixed into synthetic data
  or treated as ground-truth labels before human review.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from ml.preprocessing.features import ERROR_TAXONOMY, extract_exception_name

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_URL_RE = re.compile(r"https?://\S+")

CONSENT_EVENT_TYPE = "ml_data_consent_updated"
DEFAULT_OUTPUT_PATH = (
    Path(__file__).resolve().parents[1] / "datasets" / "real_student_consented.csv"
)

_EXPORT_COLUMNS = [
    "sample_id",
    "program_family",
    "topic",
    "mutation",
    "label",
    "source_code",
    "verdict",
    "exception_name",
    "stderr",
    "compile_output",
    "stdout_actual",
    "stdout_expected",
    "passed_tests",
    "total_tests",
    "data_origin",
    "license",
    "review_status",
    "student_pseudonym",
    "language_slug",
    "ml_confidence",
]


def sanitize_source_code(source_code: str) -> str:
    """Redact potential PII (emails, URLs) from student comments/strings."""
    cleaned = _EMAIL_RE.sub("<redacted-email>", source_code)
    cleaned = _URL_RE.sub("<redacted-url>", cleaned)
    return cleaned


def pseudonymize_student_id(student_id: str, salt: str) -> str:
    """Create a deterministic, non-reversible pseudonym for grouping without PII."""
    digest = hashlib.sha256(f"{salt}:{student_id}".encode()).hexdigest()
    return f"stu_{digest[:16]}"


def normalize_async_db_url(raw_url: str) -> str:
    url = raw_url.strip()
    if url.startswith("postgresql://"):
        return "postgresql+asyncpg://" + url[len("postgresql://") :]
    if url.startswith("postgres://"):
        return "postgresql+asyncpg://" + url[len("postgres://") :]
    return url


async def export_consented_student_events(
    *,
    database_url: str,
    output_csv: Path,
    pseudonym_salt: str,
    language_slug: str = "python",
    limit: int = 5000,
) -> dict[str, Any]:
    """Query PostgreSQL for opt-in consented failing submissions and write anonymized CSV."""
    engine = create_async_engine(normalize_async_db_url(database_url), future=True)

    sql = text(
        """
        WITH latest_consent AS (
            SELECT DISTINCT ON (student_id)
                student_id,
                COALESCE((metadata->>'consent_granted')::boolean, false) AS consent_granted,
                created_at AS consent_updated_at
            FROM public.learning_events
            WHERE event_type = :consent_event_type
            ORDER BY student_id, created_at DESC
        ),
        first_public_fail AS (
            SELECT DISTINCT ON (er.submission_id)
                er.submission_id,
                er.stderr,
                er.compile_output,
                er.stdout AS stdout_actual,
                tc.expected_output AS stdout_expected
            FROM public.execution_results er
            LEFT JOIN public.test_cases tc ON tc.id = er.test_case_id
            WHERE er.is_hidden = false
              AND er.verdict <> 'accepted'
            ORDER BY er.submission_id, er.created_at ASC
        ),
        latest_diag AS (
            SELECT DISTINCT ON (ed.submission_id)
                ed.submission_id,
                ed.predicted_error_code,
                ed.confidence
            FROM public.error_diagnoses ed
            ORDER BY ed.submission_id, ed.created_at DESC
        )
        SELECT
            s.id::text AS submission_id,
            s.student_id::text AS student_id,
            COALESCE(p.slug, 'unknown_problem') AS problem_slug,
            COALESCE(pv.topics[1], 'general') AS topic,
            s.language_slug,
            s.source_code,
            s.verdict,
            s.passed_tests,
            s.total_tests,
            COALESCE(f.stderr, '') AS stderr,
            COALESCE(f.compile_output, '') AS compile_output,
            COALESCE(f.stdout_actual, '') AS stdout_actual,
            COALESCE(f.stdout_expected, '') AS stdout_expected,
            COALESCE(d.predicted_error_code, 'logic_error') AS proposed_label,
            COALESCE(d.confidence, 0.0) AS ml_confidence
        FROM public.submissions s
        INNER JOIN latest_consent lc
            ON lc.student_id = s.student_id
           AND lc.consent_granted = true
        LEFT JOIN public.problems p ON p.id = s.problem_id
        LEFT JOIN public.problem_versions pv ON pv.id = s.problem_version_id
        LEFT JOIN first_public_fail f ON f.submission_id = s.id
        LEFT JOIN latest_diag d ON d.submission_id = s.id
        WHERE s.status = 'completed'
          AND s.verdict IN ('compilation_error', 'runtime_error', 'wrong_answer')
          AND s.language_slug = :language_slug
        ORDER BY s.created_at DESC
        LIMIT :row_limit
        """
    )

    try:
        async with engine.connect() as conn:
            result = await conn.execute(
                sql,
                {
                    "consent_event_type": CONSENT_EVENT_TYPE,
                    "language_slug": language_slug,
                    "row_limit": limit,
                },
            )
            fetched = result.mappings().all()
    finally:
        await engine.dispose()

    rows: list[dict[str, Any]] = []
    for item in fetched:
        proposed = str(item["proposed_label"])
        if proposed not in ERROR_TAXONOMY:
            proposed = "logic_error"
        stderr_str = str(item["stderr"] or "")
        compile_str = str(item["compile_output"] or "")
        rows.append(
            {
                "sample_id": f"stu_sub_{str(item['submission_id'])[:12]}",
                "program_family": f"problem_{item['problem_slug']}",
                "topic": str(item["topic"]),
                "mutation": "real_student_submission",
                "label": proposed,
                "source_code": sanitize_source_code(str(item["source_code"] or "")),
                "verdict": str(item["verdict"]),
                "exception_name": extract_exception_name(stderr_str, compile_str),
                "stderr": stderr_str[:800],
                "compile_output": compile_str[:800],
                "stdout_actual": str(item["stdout_actual"] or "")[:400],
                "stdout_expected": str(item["stdout_expected"] or "")[:400],
                "passed_tests": int(item["passed_tests"] or 0),
                "total_tests": int(item["total_tests"] or 1),
                "data_origin": "real_student_consented",
                "license": "ThinkFirst-Consented-Student-Data-v1",
                "review_status": "pending_human_label",
                "student_pseudonym": pseudonymize_student_id(
                    str(item["student_id"]), pseudonym_salt
                ),
                "language_slug": str(item["language_slug"]),
                "ml_confidence": round(float(item["ml_confidence"] or 0.0), 4),
            }
        )

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows, columns=_EXPORT_COLUMNS)
    df.to_csv(output_csv, index=False)

    summary = {
        "exported_rows": len(df),
        "language_slug": language_slug,
        "output_csv": str(output_csv),
        "data_origin": "real_student_consented",
        "review_status": "pending_human_label",
        "note": (
            "Exported rows require human verification via ml.tools.validate_and_label "
            "before inclusion in supervised training."
        ),
    }
    meta_path = output_csv.with_name(f"{output_csv.stem}_metadata.json")
    meta_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Export anonymized, opt-in consented student debugging events for ML review."
    )
    parser.add_argument(
        "--database-url",
        default=os.environ.get("DATABASE_URL", ""),
        help="PostgreSQL connection URL (defaults to DATABASE_URL env var).",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--language", default="python")
    parser.add_argument("--limit", type=int, default=5000)
    parser.add_argument(
        "--salt",
        default=os.environ.get("ML_EXPORT_PSEUDONYM_SALT", "thinkfirst-local-dev-salt"),
    )
    args = parser.parse_args(argv)
    if not args.database_url:
        print(
            "Error: --database-url or DATABASE_URL environment variable is required.",
            file=sys.stderr,
        )
        return 1

    summary = asyncio.run(
        export_consented_student_events(
            database_url=args.database_url,
            output_csv=args.output,
            pseudonym_salt=args.salt,
            language_slug=args.language,
            limit=args.limit,
        )
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
