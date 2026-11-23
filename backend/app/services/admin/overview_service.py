"""Real DB-backed Admin Studio Dashboard & Audit Log inspection service."""

from __future__ import annotations

from app.repositories.admin import AdminRepository
from app.schemas.admin import (
    AdminAuditLogItem,
    AdminDashboardOverview,
    AdminReviewQueueItem,
    AdminTrackCoverageItem,
)
from app.schemas.common import PaginatedResponse
from app.schemas.learning import TrackSlug

_DIFF_TO_TRACK: dict[str, str] = {
    "beginner": "absolute_beginner",
    "basic": "basic_university",
    "intermediate": "intermediate",
    "advanced": "advanced",
}


class AdminOverviewService:
    """Aggregates factual curriculum, problem, RAG, and audit counts for Admin Studio."""

    def __init__(self, *, repo: AdminRepository) -> None:
        self._repo = repo

    async def get_overview(self) -> AdminDashboardOverview:
        problem_rows = await self._repo.get_latest_problem_status_rows()
        lesson_rows = await self._repo.list_lesson_overview_rows()
        diagnostic_published, diagnostic_stretch = await self._repo.get_diagnostic_question_counts()
        tracks = await self._repo.list_tracks()
        knowledge_approved, knowledge_total = await self._repo.list_knowledge_status_counts()
        skill_nodes_count = await self._repo.count_skill_nodes()
        platform_counts = await self._repo.get_role_and_classroom_counts()
        audit_rows, _ = await self._repo.list_audit_logs(limit=15, offset=0)

        published = sum(
            1 for p, pv in problem_rows if not p.is_archived and pv.status == "published"
        )
        draft = sum(1 for p, pv in problem_rows if not p.is_archived and pv.status == "draft")
        validated = sum(
            1 for p, pv in problem_rows if not p.is_archived and pv.status == "validated"
        )
        in_review = sum(
            1 for p, pv in problem_rows if not p.is_archived and pv.status == "in_review"
        )
        approved = sum(1 for p, pv in problem_rows if not p.is_archived and pv.status == "approved")
        archived = sum(1 for p, pv in problem_rows if p.is_archived or pv.status == "archived")
        inter_adv = sum(
            1
            for p, pv in problem_rows
            if not p.is_archived
            and pv.status == "published"
            and pv.difficulty in ("intermediate", "advanced")
        )

        review_queue = [
            AdminReviewQueueItem(
                problem_id=p.id,
                version_id=pv.id,
                slug=p.slug,
                title=pv.title,
                difficulty=pv.difficulty,
                mode=pv.mode,
                status=pv.status,
                version_number=pv.version_number,
                updated_at=pv.updated_at,
            )
            for p, pv in problem_rows
            if not p.is_archived and pv.status in ("in_review", "validated", "approved")
        ][:12]

        track_coverage: list[AdminTrackCoverageItem] = []
        for track in tracks:
            l_cnt = sum(
                1
                for pub_ver_id, track_slugs in lesson_rows
                if pub_ver_id is not None and track.slug in track_slugs
            )
            p_cnt = sum(
                1
                for p, pv in problem_rows
                if not p.is_archived
                and pv.status == "published"
                and (pv.track_slug or _DIFF_TO_TRACK.get(pv.difficulty)) == track.slug
            )
            track_slug_typed: TrackSlug = track.slug  # type: ignore[assignment]
            track_coverage.append(
                AdminTrackCoverageItem(
                    track_slug=track_slug_typed,
                    title_en=track.title_en,
                    title_bn=track.title_bn,
                    lesson_count=l_cnt,
                    problem_count=p_cnt,
                    focus_skills=list(track.recommended_focus_skills or []),
                )
            )

        lessons_published = sum(1 for pub_ver_id, _ts in lesson_rows if pub_ver_id is not None)

        recent_audits = [
            AdminAuditLogItem(
                id=log.id,
                actor_user_id=log.actor_user_id,
                actor_email=prof.email if prof else None,
                actor_name=prof.full_name if prof else None,
                action=log.action,
                target_type=log.target_type,
                target_id=log.target_id,
                metadata=dict(log.metadata_json or {}),
                request_id=log.request_id,
                created_at=log.created_at,
            )
            for log, prof in audit_rows
        ]

        return AdminDashboardOverview(
            problems_total=len(problem_rows),
            problems_published=published,
            problems_draft=draft,
            problems_validated=validated,
            problems_in_review=in_review,
            problems_approved=approved,
            problems_archived=archived,
            problems_intermediate_or_advanced=inter_adv,
            lessons_published=lessons_published,
            lessons_total=len(lesson_rows),
            diagnostic_published=diagnostic_published,
            diagnostic_stretch_count=diagnostic_stretch,
            knowledge_approved=knowledge_approved,
            knowledge_total=knowledge_total,
            skill_nodes_count=skill_nodes_count,
            students_count=platform_counts["students_count"],
            teachers_count=platform_counts["teachers_count"],
            admins_count=platform_counts["admins_count"],
            courses_total=platform_counts["courses_total"],
            courses_active=platform_counts["courses_active"],
            enrollments_active=platform_counts["enrollments_active"],
            assignments_published=platform_counts["assignments_published"],
            review_queue=review_queue,
            track_coverage=track_coverage,
            recent_audit_logs=recent_audits,
        )

    async def list_audit_logs(
        self,
        *,
        action_prefix: str | None = None,
        target_type: str | None = None,
        limit: int = 40,
        offset: int = 0,
    ) -> PaginatedResponse[AdminAuditLogItem]:
        rows, total = await self._repo.list_audit_logs(
            action_prefix=action_prefix,
            target_type=target_type,
            limit=limit,
            offset=offset,
        )
        items = [
            AdminAuditLogItem(
                id=log.id,
                actor_user_id=log.actor_user_id,
                actor_email=prof.email if prof else None,
                actor_name=prof.full_name if prof else None,
                action=log.action,
                target_type=log.target_type,
                target_id=log.target_id,
                metadata=dict(log.metadata_json or {}),
                request_id=log.request_id,
                created_at=log.created_at,
            )
            for log, prof in rows
        ]
        return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)
