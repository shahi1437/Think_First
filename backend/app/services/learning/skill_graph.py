"""Evidence-based prerequisite-aware Skill Graph service.

Enforces honest pedagogical state transitions:
  unobserved -> introduced -> guided -> independent -> transferred -> retained

Key invariants:
- Self-reported onboarding experience NEVER sets skill mastery.
- `introduced` (reading a lesson or attempting a diagnostic) is explicitly NOT mastery.
- Accepted code with AI hints or guided lesson exercise yields `guided`, not `transferred`.
- `independent` requires zero-hint Judge0 execution evidence (diagnostic execution or 0-hint submit).
- `transferred` requires Phase 4 `verified_independent` unseen transfer challenge proof.
- `retained` is NEVER claimed immediately — requires later re-verification (>= 24h after first verification).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.repositories.learning import LearningRepository
from app.repositories.mentor import MentorRepository
from app.repositories.problems import ProblemRepository
from app.schemas.learning import (
    SkillGraphView,
    SkillNodeStateView,
    SkillState,
    SkillTransitionView,
)

STATE_RANK: dict[str, int] = {
    "unobserved": 0,
    "introduced": 1,
    "guided": 2,
    "independent": 3,
    "transferred": 4,
    "retained": 5,
}

SKILL_STATE_LEGEND: list[dict[str, str]] = [
    {
        "state": "unobserved",
        "label_en": "Not Yet Observed",
        "label_bn": "এখনো পর্যবেক্ষিত হয়নি",
        "meaning": "No direct execution or assessment evidence recorded yet.",
    },
    {
        "state": "introduced",
        "label_en": "Introduced",
        "label_bn": "পরিচিত হয়েছে",
        "meaning": "Concept exposed via lesson reading or diagnostic attempt (NOT mastery).",
    },
    {
        "state": "guided",
        "label_en": "Guided",
        "label_bn": "নির্দেশিত অনুশীলন",
        "meaning": "Passed guided Judge0 exercise or solved with AI Mentor hints.",
    },
    {
        "state": "independent",
        "label_en": "Independent",
        "label_bn": "স্বাধীন সমাধান",
        "meaning": "Verified via zero-hint Judge0 execution (transfer not yet proven).",
    },
    {
        "state": "transferred",
        "label_en": "Transferred",
        "label_bn": "নতুন সমস্যায় প্রয়োগ",
        "meaning": "Passed an unseen Phase 4 Transfer Challenge on Judge0 with 0 hints.",
    },
    {
        "state": "retained",
        "label_en": "Retained",
        "label_bn": "দীর্ঘমেয়াদী দক্ষতা",
        "meaning": "Re-verified independently at least 24 hours after initial verification.",
    },
]

# Maps Phase 3/4 problem topics/skills & verification skill_focus to Skill Graph node slugs
SKILL_FOCUS_TO_NODE: dict[str, str] = {
    "loop-boundary-reasoning": "loops",
    "loop-boundaries": "loops",
    "loops": "loops",
    "accumulator-initialization": "variables",
    "variable-initialization": "variables",
    "variables": "variables",
    "conditionals": "conditions",
    "conditions": "conditions",
    "lists": "lists",
    "arrays": "lists",
    "indexing": "indexing",
    "functions": "functions",
    "debugging": "debugging_basics",
    "syntax": "debugging_basics",
    "logic": "mixed_problem_solving",
    "nested-loops": "nested_control_flow",
    "nested_control_flow": "nested_control_flow",
    "dictionaries": "dictionaries_strings",
    "strings": "dictionaries_strings",
    "dictionaries_strings": "dictionaries_strings",
    "searching": "searching_sorting",
    "sorting": "searching_sorting",
    "binary-search": "searching_sorting",
    "searching_sorting": "searching_sorting",
    "edge-cases": "input_validation_edge_cases",
    "complexity": "input_validation_edge_cases",
    "input_validation_edge_cases": "input_validation_edge_cases",
    "recursion": "recursion_fundamentals",
    "recursion_fundamentals": "recursion_fundamentals",
    "graphs": "data_structures_graphs",
    "bfs": "data_structures_graphs",
    "dfs": "data_structures_graphs",
    "data_structures_graphs": "data_structures_graphs",
    "dynamic-programming": "dynamic_programming",
    "dp": "dynamic_programming",
    "dynamic_programming": "dynamic_programming",
    "stateful-debugging": "stateful_debugging_optimization",
    "stateful_debugging_optimization": "stateful_debugging_optimization",
}


class SkillGraphService:
    """Manages prerequisite DAG queries and evidence-based skill state transitions."""

    def __init__(
        self,
        *,
        learning_repo: LearningRepository,
        mentor_repo: MentorRepository,
        problem_repo: ProblemRepository,
    ) -> None:
        self._learning_repo = learning_repo
        self._mentor_repo = mentor_repo
        self._problem_repo = problem_repo

    async def record_evidence(
        self,
        *,
        student_id: UUID,
        skill_slug: str,
        target_state: SkillState,
        evidence_source: str,
        evidence_ref_id: str | None,
        reason: str,
        uncertainty_note: str,
    ) -> SkillState:
        """Advance (never over-claim) a student's skill state using factual evidence."""
        existing = await self._learning_repo.get_student_skill_state(
            student_id=student_id, skill_slug=skill_slug
        )
        current_state: SkillState = (
            existing.state if existing is not None else "unobserved"  # type: ignore[assignment]
        )
        now = datetime.now(UTC)

        # Retained can ONLY occur if already transferred/independent AND >= 24h after first verification
        final_state: SkillState = current_state
        if STATE_RANK[target_state] > STATE_RANK[current_state]:
            if target_state == "retained":
                if (
                    existing is not None
                    and existing.first_verified_at is not None
                    and (now - existing.first_verified_at) >= timedelta(hours=24)
                ):
                    final_state = "retained"
                else:
                    final_state = current_state
            else:
                final_state = target_state
        elif (
            target_state in ("independent", "transferred")
            and current_state == "transferred"
            and existing is not None
            and existing.first_verified_at is not None
            and (now - existing.first_verified_at) >= timedelta(hours=24)
        ):
            final_state = "retained"
            uncertainty_note = (
                "Re-verified independently more than 24 hours after first verification."
            )

        updated = await self._learning_repo.upsert_skill_state(
            student_id=student_id,
            skill_slug=skill_slug,
            new_state=final_state,
            uncertainty_note=uncertainty_note,
            evidence_source=evidence_source,
            evidence_ref_id=evidence_ref_id,
            reason=reason,
            increment_evidence=True,
            mark_verified=final_state in ("independent", "transferred", "retained"),
        )
        return updated.state  # type: ignore[return-value]

    async def sync_phase3_and_phase4_evidence(self, student_id: UUID) -> None:
        """Project existing Phase 3 Judge0 & Phase 4 Transfer Verification evidence into Skill Graph."""
        attempts = await self._mentor_repo.list_verification_attempts(student_id=student_id)
        for att in attempts:
            if att.outcome != "verified_independent":
                continue
            link_tuple = await self._mentor_repo.get_verification_link_by_id(
                att.verification_link_id
            )
            if link_tuple is None:
                continue
            link = link_tuple[0]
            node_slug = SKILL_FOCUS_TO_NODE.get(link.skill_focus, "mixed_problem_solving")
            existing = await self._learning_repo.get_student_skill_state(
                student_id=student_id, skill_slug=node_slug
            )
            if existing is None or STATE_RANK[existing.state] < STATE_RANK["transferred"]:
                await self.record_evidence(
                    student_id=student_id,
                    skill_slug=node_slug,
                    target_state="transferred",
                    evidence_source="phase4_transfer_verification",
                    evidence_ref_id=str(att.id),
                    reason=(
                        f"Passed unseen Transfer Challenge ({att.passed_tests}/{att.total_tests} "
                        f"Judge0 tests) with {att.hints_used} hints."
                    ),
                    uncertainty_note=(
                        "Transfer verified independently on an unseen challenge; "
                        "long-term retention requires later re-verification."
                    ),
                )

    async def get_student_skill_graph(self, student_id: UUID) -> SkillGraphView:
        await self.sync_phase3_and_phase4_evidence(student_id)

        nodes = await self._learning_repo.list_skill_nodes()
        prereq_rows = await self._learning_repo.list_skill_prerequisites()
        states = await self._learning_repo.list_student_skill_states(student_id)
        transitions = await self._learning_repo.list_skill_transitions(
            student_id=student_id, limit=15
        )

        prereq_map: dict[str, list[str]] = {}
        for edge in prereq_rows:
            prereq_map.setdefault(edge.skill_slug, []).append(edge.prerequisite_slug)

        state_map = {s.skill_slug: s for s in states}

        node_views: list[SkillNodeStateView] = []
        for node in nodes:
            st = state_map.get(node.slug)
            node_views.append(
                SkillNodeStateView(
                    slug=node.slug,
                    title_en=node.title_en,
                    title_bn=node.title_bn,
                    description_en=node.description_en,
                    description_bn=node.description_bn,
                    domain_slug=node.domain_slug,
                    tier=node.tier,
                    display_order=node.display_order,
                    prerequisites=sorted(prereq_map.get(node.slug, [])),
                    state=st.state if st else "unobserved",
                    evidence_count=st.evidence_count if st else 0,
                    uncertainty_note=(
                        st.uncertainty_note
                        if st
                        else "Not yet observed: complete a diagnostic or guided exercise for evidence."
                    ),
                    last_evidence_type=st.last_evidence_type if st else None,
                    last_evidence_at=st.last_evidence_at if st else None,
                )
            )

        transition_views = [
            SkillTransitionView(
                id=t.id,
                skill_slug=t.skill_slug,
                from_state=t.from_state,
                to_state=t.to_state,
                evidence_source=t.evidence_source,
                reason=t.reason,
                created_at=t.created_at,
            )
            for t in transitions
        ]

        return SkillGraphView(
            nodes=node_views,
            recent_transitions=transition_views,
            state_legend=SKILL_STATE_LEGEND,
        )
