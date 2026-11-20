"""Audit and isolate public GitHub-exposed demo assessments in live databases."""

from __future__ import annotations

import argparse
import asyncio

from sqlalchemy import text

from app.core.database import get_db_manager

# Slugs shipped in public GitHub seed files (`supabase/seed/001_*.sql` & `002_*.sql`).
# Their hidden test cases and reference solutions are publicly readable in Git and must
# be treated as demo-only (not real unseen assessment items) on public deployments.
PUBLIC_DEMO_PROBLEM_SLUGS: tuple[str, ...] = (
    "sum-of-even-numbers",
    "count-vowels",
    "debug-range-sum-off-by-one",
    "debug-max-negative-init",
    "transfer-step-range-sum",
    "transfer-negative-threshold-min",
)


async def _run(mode: str) -> int:
    db_manager = get_db_manager()
    try:
        async with db_manager.session() as session:
            active_demo_rows = (
                await session.execute(
                    text(
                        """
                        SELECT p.slug, pv.status
                        FROM public.problems p
                        LEFT JOIN public.problem_versions pv
                          ON pv.id = p.current_published_version_id
                        WHERE p.slug = ANY(:slugs) AND p.is_archived = false
                        ORDER BY p.slug
                        """
                    ),
                    {"slugs": list(PUBLIC_DEMO_PROBLEM_SLUGS)},
                )
            ).all()

            total_published_problems = (
                await session.execute(
                    text(
                        """
                        SELECT count(*)
                        FROM public.problems
                        WHERE is_archived = false
                          AND current_published_version_id IS NOT NULL
                        """
                    )
                )
            ).scalar_one()

            private_published_count = (
                await session.execute(
                    text(
                        """
                        SELECT count(*)
                        FROM public.problems
                        WHERE is_archived = false
                          AND current_published_version_id IS NOT NULL
                          AND NOT (slug = ANY(:slugs))
                        """
                    ),
                    {"slugs": list(PUBLIC_DEMO_PROBLEM_SLUGS)},
                )
            ).scalar_one()

            print(
                f"[audit] published_total={total_published_problems} "
                f"private_published={private_published_count} "
                f"active_public_demo={len(active_demo_rows)}"
            )
            for slug, status in active_demo_rows:
                print(f"  - public_demo_problem: slug={slug} status={status}")

            if mode == "archive-compromised-demo" and active_demo_rows:
                if private_published_count == 0:
                    print(
                        "[ABORT] Zero private protected problems found! Import protected "
                        "curriculum first via import_curriculum_bundle.py before archiving."
                    )
                    return 2
                await session.execute(
                    text(
                        """
                        UPDATE public.problems
                        SET is_archived = true, updated_at = now()
                        WHERE slug = ANY(:slugs) AND is_archived = false
                        """
                    ),
                    {"slugs": list(PUBLIC_DEMO_PROBLEM_SLUGS)},
                )
                await session.commit()
                print(f"[done] Archived {len(active_demo_rows)} public demo problems safely.")
    finally:
        await db_manager.dispose()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit or archive GitHub-exposed demo problems for production deployments."
    )
    parser.add_argument(
        "--mode",
        choices=("audit", "archive-compromised-demo"),
        default="audit",
    )
    args = parser.parse_args()
    return asyncio.run(_run(args.mode))


if __name__ == "__main__":
    raise SystemExit(main())
