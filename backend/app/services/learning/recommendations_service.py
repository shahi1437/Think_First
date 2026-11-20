"""Explainable prerequisite-based Adaptive Recommendations & Learning Dashboard service.

Connects real evidence across Phases 2-5:
- Onboarding preferences
- Diagnostic assessment results (8 domains)
- Beginner lesson completion & Judge0 guided exercises
- Phase 3 coding/debugging submissions
- Phase 4 AI Mentor hint usage & Transfer Verification outcomes

Uses deterministic, auditable prerequisite rules — never fabricates AI personalization claims.
"""

from __future__ import annotations

from app.repositories.identity import UserRecord
from app.repositories.learning import LearningRepository
from app.repositories.mentor import MentorRepository
from app.repositories.problems import ProblemRepository
from app.schemas.learning import (
    LearningDashboardView,
    RecommendationItemView,
)
from app.services.learning.diagnostics_service import DiagnosticAssessmentService
from app.services.learning.lessons_service import LessonsAndTracksService
from app.services.learning.skill_graph import STATE_RANK, SkillGraphService


class AdaptiveRecommendationService:
    """Generates explainable prerequisite-based next lessons, diagnostics, and practice items."""

    def __init__(
        self,
        *,
        learning_repo: LearningRepository,
        problem_repo: ProblemRepository,
        mentor_repo: MentorRepository,
        lessons_service: LessonsAndTracksService,
        diagnostics_service: DiagnosticAssessmentService,
        skill_graph_service: SkillGraphService,
    ) -> None:
        self._learning_repo = learning_repo
        self._problem_repo = problem_repo
        self._mentor_repo = mentor_repo
        self._lessons = lessons_service
        self._diagnostics = diagnostics_service
        self._skill_graph = skill_graph_service

    async def compute_recommendations(self, user: UserRecord) -> list[RecommendationItemView]:
        track_status = await self._lessons.get_track_status(user)
        lessons = await self._lessons.list_lessons(user=user)
        skill_graph = await self._skill_graph.get_student_skill_graph(user.id)
        diag_sessions = await self._diagnostics.list_my_sessions(user=user)
        completed_diags = [s for s in diag_sessions if s.status == "completed"]
        latest_diag = completed_diags[0] if completed_diags else None

        skill_state_map = {n.slug: n.state for n in skill_graph.nodes}
        recommendations: list[RecommendationItemView] = []
        priority = 1

        # 1. If student has NOT completed an 8-domain diagnostic yet, recommend it cleanly
        if latest_diag is None:
            recommendations.append(
                RecommendationItemView(
                    recommendation_type="diagnostic_assessment",
                    target_id="diagnostic-8-domain",
                    target_slug="diagnostic-assessment",
                    title="8-Domain Adaptive Diagnostic Assessment",
                    priority=priority,
                    reason_en=(
                        "No diagnostic evidence recorded yet. Complete the adaptive 8-domain check "
                        "so your starting track is grounded in observed evidence rather than self-report."
                    ),
                    reason_bn=(
                        "এখনো কোনো ডায়াগনস্টিক প্রমাণ নেই। নিজের অনুমান নয়, বরং আসল দক্ষতা যাচাই করে "
                        "সঠিক ট্র্যাক নির্ধারণ করতে ৮-ডোমেইন ডায়াগনস্টিক টেস্ট দাও।"
                    ),
                    evidence_factors=[
                        "onboarding_only_no_diagnostic",
                        f"current_track:{track_status.selected_track_slug}",
                    ],
                    href="/student/diagnostic",
                )
            )
            priority += 1

        # 2. Identify highest-priority incomplete lesson whose prerequisites are satisfied,
        #    prioritizing domains with diagnostic gaps first!
        gap_skills: set[str] = set()
        if latest_diag is not None:
            domain_to_skill = {
                "variables": "variables",
                "syntax_runtime_debugging": "debugging_basics",
                "conditions": "conditions",
                "loop_boundaries": "loops",
                "arrays_lists": "lists",
                "indexing": "indexing",
                "functions": "functions",
                "mixed_logic": "mixed_problem_solving",
            }
            for ev in latest_diag.domain_evidence:
                if ev.evidence_status in ("gap_detected", "guided_needed"):
                    gap_skills.add(domain_to_skill.get(ev.domain_slug, ev.domain_slug))

        incomplete_lessons = [lsn for lsn in lessons if lsn.progress_status != "completed"]
        ready_gap_lessons = [
            lsn
            for lsn in incomplete_lessons
            if lsn.prerequisites_met and lsn.skill_slug in gap_skills
        ]
        ready_track_lessons = [
            lsn
            for lsn in incomplete_lessons
            if lsn.prerequisites_met
            and track_status.selected_track_slug in lsn.track_slugs
            and lsn not in ready_gap_lessons
        ]
        ready_fallback_lessons = [
            lsn
            for lsn in incomplete_lessons
            if lsn.prerequisites_met
            and lsn not in ready_gap_lessons
            and lsn not in ready_track_lessons
        ]

        ordered_next_lessons = (ready_gap_lessons + ready_track_lessons + ready_fallback_lessons)[
            :2
        ]

        for lsn in ordered_next_lessons:
            is_gap = lsn.skill_slug in gap_skills
            cur_state = skill_state_map.get(lsn.skill_slug, "unobserved")
            reason_en = (
                f"Diagnostic detected a gap in '{lsn.skill_slug.replace('_', ' ')}' "
                f"(current skill state: {cur_state}). All prerequisites are satisfied."
                if is_gap
                else f"Next prerequisite-ready lesson in your {track_status.selected_track_slug.replace('_', ' ')} "
                f"track (current skill state: {cur_state})."
            )
            reason_bn = (
                f"ডায়াগনস্টিকে '{lsn.title_bn}' বিষয়ে ঘাটতি পাওয়া গেছে এবং পূর্বশর্ত সম্পন্ন হয়েছে।"
                if is_gap
                else f"তোমার নির্বাচিত ট্র্যাকের পরবর্তী পূর্বশর্ত-সম্পন্ন লেসন: {lsn.title_bn}।"
            )
            recommendations.append(
                RecommendationItemView(
                    recommendation_type="lesson",
                    target_id=str(lsn.lesson_id),
                    target_slug=lsn.slug,
                    title=lsn.title_en,
                    priority=priority,
                    reason_en=reason_en,
                    reason_bn=reason_bn,
                    evidence_factors=[
                        f"skill_state:{lsn.skill_slug}={cur_state}",
                        "prerequisites_satisfied",
                        "diagnostic_gap" if is_gap else f"track:{track_status.selected_track_slug}",
                    ],
                    href=f"/student/lessons/{lsn.slug}",
                )
            )
            priority += 1

        # 3. Connect Phase 3 & Phase 4 Debugging + Transfer Verification problems
        problems, _ = await self._problem_repo.list_published_problems(limit=20, offset=0)
        for prob, ver in problems:
            if len(recommendations) >= 4:
                break
            if prob.slug.startswith("transfer-"):
                continue
            accepted = await self._mentor_repo.has_accepted_submit(
                student_id=user.id, problem_id=prob.id
            )
            link_tuple = await self._mentor_repo.get_verification_link_for_source_problem(prob.id)

            if accepted is not None and link_tuple is not None:
                link, _, transfer_ver = link_tuple
                latest_att = await self._mentor_repo.get_latest_verification_attempt(
                    student_id=user.id, verification_link_id=link.id
                )
                if latest_att is None or latest_att.outcome != "verified_independent":
                    recommendations.append(
                        RecommendationItemView(
                            recommendation_type="transfer_challenge",
                            target_id=str(prob.id),
                            target_slug=prob.slug,
                            title=transfer_ver.title,
                            priority=priority,
                            reason_en=(
                                f"You fixed '{ver.title}' on Judge0! Complete its unlocked zero-hint "
                                "transfer challenge to advance your Skill Graph to Transferred."
                            ),
                            reason_bn=(
                                f"তুমি '{ver.title}' Judge0-তে সমাধান করেছ! Skill Graph-এ Transferred "
                                "অর্জনের জন্য হিন্ট ছাড়া নতুন ট্রান্সফার চ্যালেঞ্জটি সমাধান করো।"
                            ),
                            evidence_factors=[
                                f"accepted_source:{prob.slug}",
                                "transfer_unlocked_unverified",
                            ],
                            href=f"/student/problems/{prob.id}",
                        )
                    )
                    priority += 1
                    continue

            # Recommend debugging problem if loops/variables are at least introduced or track >= basic
            if accepted is None and ver.mode == "debugging":
                loops_rank = STATE_RANK.get(skill_state_map.get("loops", "unobserved"), 0)
                if loops_rank >= 1 or track_status.selected_track_slug != "absolute_beginner":
                    recommendations.append(
                        RecommendationItemView(
                            recommendation_type="problem",
                            target_id=str(prob.id),
                            target_slug=prob.slug,
                            title=ver.title,
                            priority=priority,
                            reason_en=(
                                f"Practice real Judge0 debugging with ML diagnosis & Socratic Mentor "
                                f"on '{ver.title}' to build independent debugging evidence."
                            ),
                            reason_bn=(
                                f"আসল Judge0, ML ডায়াগনোসিস এবং Socratic AI Mentor-এর সাহায্যে '{ver.title}' "
                                "ডিবাগ করে স্বাধীন দক্ষতার প্রমাণ তৈরি করো।"
                            ),
                            evidence_factors=[
                                "unsolved_debugging_problem",
                                f"track:{track_status.selected_track_slug}",
                            ],
                            href=f"/student/problems/{prob.id}",
                        )
                    )
                    priority += 1

        await self._learning_repo.replace_student_recommendations(
            student_id=user.id,
            items=[
                {
                    "recommendation_type": r.recommendation_type,
                    "target_id": r.target_id,
                    "target_slug": r.target_slug,
                    "title": r.title,
                    "priority": r.priority,
                    "reason_en": r.reason_en,
                    "reason_bn": r.reason_bn,
                    "evidence_factors": r.evidence_factors,
                }
                for r in recommendations
            ],
        )
        return recommendations

    async def get_dashboard(self, user: UserRecord) -> LearningDashboardView:
        track_status = await self._lessons.get_track_status(user)
        lessons = await self._lessons.list_lessons(user=user)
        skill_graph = await self._skill_graph.get_student_skill_graph(user.id)
        diag_sessions = await self._diagnostics.list_my_sessions(user=user)
        completed_diags = [s for s in diag_sessions if s.status == "completed"]
        recommendations = await self.compute_recommendations(user)

        return LearningDashboardView(
            track_status=track_status,
            lessons_completed=sum(1 for lsn in lessons if lsn.progress_status == "completed"),
            lessons_total=len(lessons),
            diagnostic_sessions_completed=len(completed_diags),
            latest_diagnostic=completed_diags[0] if completed_diags else None,
            skill_graph=skill_graph,
            recommendations=recommendations,
        )
