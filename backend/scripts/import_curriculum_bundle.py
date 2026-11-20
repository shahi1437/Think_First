"""Admin CLI importer that validates and publishes a protected curriculum bundle via Judge0."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from sqlalchemy import text

from app.core.config import get_settings
from app.core.database import get_db_manager
from app.integrations.judge0.client import HttpJudge0Client
from app.repositories.admin import AdminRepository
from app.repositories.identity import SQLAlchemyIdentityRepository, UserRecord
from app.repositories.learning import LearningRepository
from app.repositories.mentor import MentorRepository
from app.repositories.problems import ProblemRepository
from app.schemas.admin import AdminCurriculumImportRequest
from app.services.admin.curriculum_service import AdminCurriculumService
from app.services.mentor.rag_service import RagKnowledgeService
from app.services.problems.service import ProblemService


async def _resolve_admin_actor(session: Any) -> UserRecord:
    row = (
        await session.execute(
            text(
                """
                SELECT p.id
                FROM public.profiles p
                JOIN public.user_roles ur ON ur.user_id = p.id
                WHERE ur.role = 'admin'
                ORDER BY p.created_at ASC
                LIMIT 1
                """
            )
        )
    ).first()
    if row is None:
        raise RuntimeError("No admin account exists in public.user_roles to audit import.")
    identity_repo = SQLAlchemyIdentityRepository(session)
    user = await identity_repo.get_user_by_id(row[0])
    if user is None:
        raise RuntimeError("Failed to resolve admin profile.")
    return user


async def run_import(bundle_path: Path) -> int:
    raw = json.loads(bundle_path.read_text(encoding="utf-8"))
    payload = AdminCurriculumImportRequest.model_validate(raw)

    settings = get_settings()
    db_manager = get_db_manager()
    judge0 = HttpJudge0Client(settings)

    async for session in db_manager.session():
        actor = await _resolve_admin_actor(session)
        admin_repo = AdminRepository(session)
        learning_repo = LearningRepository(session)
        problem_repo = ProblemRepository(session)
        mentor_repo = MentorRepository(session)
        rag_service = RagKnowledgeService(repository=mentor_repo, settings=settings)
        problem_service = ProblemService(repository=problem_repo, judge0=judge0)
        curriculum_service = AdminCurriculumService(
            admin_repo=admin_repo,
            learning_repo=learning_repo,
            problem_repo=problem_repo,
            judge0=judge0,
            rag_service=rag_service,
        )

        report = await curriculum_service.import_curriculum_bundle(
            actor=actor,
            payload=payload,
            problem_service=problem_service,
            request_id="cli-curriculum-import",
        )
        break

    await db_manager.dispose()
    print(json.dumps(report.model_dump(), indent=2))
    if report.errors:
        print("Validation errors occurred during import!")
        return 1
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Import & validate protected curriculum bundle.")
    parser.add_argument("bundle", type=Path, help="Path to local protected JSON curriculum file.")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(run_import(args.bundle)))


if __name__ == "__main__":
    main()
