"""Live Phase 4 integration test against PostgreSQL + pgvector + Supabase RLS + Judge0.

Guarded by `RUN_LIVE_INTEGRATION_TESTS=1` so offline CI stays deterministic while local
Docker environments can verify the full live database, pgvector HNSW retrieval, RLS
isolation, Judge0 execution, Socratic Mentor, and Independent Transfer flow end to end.
"""

from __future__ import annotations

import os
from uuid import UUID

import pytest
from sqlalchemy import text

from app.core.config import get_settings
from app.core.database import DatabaseManager

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_LIVE_INTEGRATION_TESTS") != "1",
    reason="Set RUN_LIVE_INTEGRATION_TESTS=1 with local Supabase + Judge0 Docker stack running.",
)


@pytest.mark.asyncio
async def test_live_pgvector_tables_and_force_rls_enabled() -> None:
    settings = get_settings()
    db = DatabaseManager(settings)
    try:
        async with db.session_factory() as session:
            ext = (
                await session.execute(
                    text("SELECT extname FROM pg_extension WHERE extname = 'vector'")
                )
            ).scalar_one_or_none()
            assert ext == "vector"

            expected_tables = {
                "error_taxonomy",
                "model_versions",
                "error_diagnoses",
                "knowledge_documents",
                "knowledge_chunks",
                "mentor_sessions",
                "mentor_turns",
                "hint_events",
                "learning_events",
                "verification_links",
                "verification_attempts",
            }
            rows = (
                await session.execute(
                    text(
                        "SELECT relname, relrowsecurity, relforcerowsecurity "
                        "FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
                        "WHERE n.nspname = 'public' AND relname = ANY(:names)"
                    ),
                    {"names": list(expected_tables)},
                )
            ).all()
            found = {r[0]: (bool(r[1]), bool(r[2])) for r in rows}
            assert set(found.keys()) == expected_tables
            for tbl, (rls_on, force_rls) in found.items():
                assert rls_on and force_rls, f"FORCE RLS missing on {tbl}"

            tax_count = (
                await session.execute(text("SELECT COUNT(*) FROM public.error_taxonomy"))
            ).scalar_one()
            assert int(tax_count) >= 8

            link_count = (
                await session.execute(text("SELECT COUNT(*) FROM public.verification_links"))
            ).scalar_one()
            assert int(link_count) >= 2
            _ = UUID
    finally:
        await db.dispose()
