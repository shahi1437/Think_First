"""Deterministic, evidence-based Learning DNA profile service.

Computes 6 core programming competency dimensions strictly from real persisted evidence:
1. Tracing   (diagnostic trace checks, output predictions, lesson concept reading)
2. Coding    (Judge0 submissions, lesson Judge0 guided exercises, diagnostic code checks)
3. Debugging (debugging-mode Judge0 fixes, ML error diagnoses, iterative code revisions)
4. Testing   (public run checks before submit, total Judge0 test cases passed, edge-case passes)
5. Transfer  (Phase 4 unseen zero-hint transfer verifications & Skill Graph transferred states)
6. Retention (spaced later Judge0 retention checks >= 24h & Skill Graph retained states)

Never fabricates numeric mastery percentages or IQ/ability marks.
"""

from __future__ import annotations

from app.repositories.growth import GrowthRepository
from app.repositories.identity import UserRecord
from app.schemas.growth import (
    DnaEvidenceBand,
    LearningDnaDimensionView,
    LearningDnaProfileView,
    LearningDnaSnapshotSummaryView,
)
from app.services.learning.lessons_service import (
    LessonsAndTracksService,
    resolve_user_language,
)
from app.services.learning.skill_graph import SkillGraphService


def classify_evidence_band(
    *, evidence_count: int, verified_count: int, developing_count: int
) -> DnaEvidenceBand:
    """Pure deterministic band classifier — never over-claims mastery from zero evidence."""
    if evidence_count <= 0:
        return "unobserved"
    if verified_count >= 1:
        return "verified"
    if developing_count >= 1 or evidence_count >= 3:
        return "developing"
    return "emerging"


class LearningDnaService:
    """Computes and persists evidence-backed Learning DNA profiles."""

    def __init__(
        self,
        *,
        growth_repo: GrowthRepository,
        lessons_service: LessonsAndTracksService,
        skill_graph_service: SkillGraphService,
    ) -> None:
        self._growth_repo = growth_repo
        self._lessons = lessons_service
        self._skill_graph = skill_graph_service

    async def compute_and_persist_profile(
        self, user: UserRecord, *, language_slug: str | None = None
    ) -> LearningDnaProfileView:
        lang = resolve_user_language(user, language_slug)
        track_status = await self._lessons.get_track_status(user, language_slug=lang)
        skill_graph = await self._skill_graph.get_student_skill_graph(user.id, language_slug=lang)

        submissions = await self._growth_repo.list_student_submissions_all(
            student_id=user.id, language_slug=lang
        )
        revisions = await self._growth_repo.list_student_revisions(
            student_id=user.id, language_slug=lang
        )
        diagnoses = await self._growth_repo.list_student_diagnoses(student_id=user.id)
        hints = await self._growth_repo.list_student_hint_events(student_id=user.id)
        diag_responses = await self._growth_repo.list_student_diagnostic_responses(
            student_id=user.id, language_slug=lang
        )
        lesson_rows = await self._growth_repo.list_student_lesson_progress_with_meta(
            student_id=user.id, language_slug=lang
        )
        verifications = await self._growth_repo.list_student_verification_attempts_all(
            student_id=user.id
        )
        retention_schedules = await self._growth_repo.list_retention_schedules(
            user.id, language_slug=lang
        )
        retention_attempts = await self._growth_repo.list_retention_attempts(
            student_id=user.id, language_slug=lang
        )

        # Skill Graph state counts (authoritative)
        skill_state_summary: dict[str, int] = {
            "unobserved": 0,
            "introduced": 0,
            "guided": 0,
            "independent": 0,
            "transferred": 0,
            "retained": 0,
        }
        for node in skill_graph.nodes:
            skill_state_summary[node.state] = skill_state_summary.get(node.state, 0) + 1

        # 1. TRACING dimension
        trace_diag = [r for r in diag_responses if r.question_type in ("trace", "mcq")]
        trace_diag_correct = sum(1 for r in trace_diag if r.is_correct)
        predictions_written = sum(
            1 for rev, _ in revisions if (rev.prediction_text or "").strip()
        ) + sum(1 for sub, _, _ in submissions if (sub.prediction_text or "").strip())
        lessons_read = sum(1 for prog, _, _ in lesson_rows if prog.reading_completed)
        tracing_ev = len(trace_diag) + predictions_written + lessons_read
        tracing_band = classify_evidence_band(
            evidence_count=tracing_ev,
            verified_count=1 if (trace_diag_correct >= 4 and predictions_written >= 1) else 0,
            developing_count=1 if (trace_diag_correct >= 2 or predictions_written >= 1) else 0,
        )

        # 2. CODING dimension
        accepted_submits = [
            sub
            for sub, _, _ in submissions
            if sub.submission_kind == "submit" and sub.verdict == "accepted"
        ]
        lessons_passed = sum(1 for prog, _, _ in lesson_rows if prog.exercise_passed)
        diag_code_passed = sum(
            1 for r in diag_responses if r.question_type == "code_execution" and r.is_correct
        )
        coding_ev = len(submissions) + lessons_passed + diag_code_passed
        coding_band = classify_evidence_band(
            evidence_count=coding_ev,
            verified_count=len(accepted_submits) + diag_code_passed,
            developing_count=lessons_passed,
        )

        # 3. DEBUGGING dimension
        debug_subs = [(sub, prob, ver) for sub, prob, ver in submissions if ver.mode == "debugging"]
        debug_accepted = [
            sub
            for sub, _, _ in debug_subs
            if sub.submission_kind == "submit" and sub.verdict == "accepted"
        ]
        explanations_written = sum(
            1 for rev, _ in revisions if (rev.explanation_text or "").strip()
        ) + sum(1 for sub, _, _ in submissions if (sub.explanation_text or "").strip())
        debug_ev = len(debug_subs) + len(diagnoses) + len(revisions)
        debug_band = classify_evidence_band(
            evidence_count=debug_ev,
            verified_count=len(debug_accepted),
            developing_count=len(diagnoses) + (1 if explanations_written > 0 else 0),
        )

        # 4. TESTING dimension
        public_runs = [sub for sub, _, _ in submissions if sub.submission_kind == "run"]
        hidden_submits = [sub for sub, _, _ in submissions if sub.submission_kind == "submit"]
        total_tests_passed = sum(sub.passed_tests for sub, _, _ in submissions)
        total_tests_run = sum(sub.total_tests for sub, _, _ in submissions)
        full_hidden_passes = sum(
            1 for sub in hidden_submits if sub.verdict == "accepted" and sub.total_tests > 0
        )
        testing_ev = len(public_runs) + len(hidden_submits)
        testing_band = classify_evidence_band(
            evidence_count=testing_ev,
            verified_count=1 if (len(public_runs) >= 1 and full_hidden_passes >= 1) else 0,
            developing_count=len(public_runs),
        )

        # 5. TRANSFER dimension
        verified_transfers = [v for v in verifications if v.outcome == "verified_independent"]
        zero_hint_transfers = [v for v in verified_transfers if v.hints_used == 0]
        transferred_nodes = skill_state_summary["transferred"] + skill_state_summary["retained"]
        transfer_ev = len(verifications) + transferred_nodes
        transfer_band = classify_evidence_band(
            evidence_count=transfer_ev,
            verified_count=len(zero_hint_transfers) + transferred_nodes,
            developing_count=len(verifications),
        )

        # 6. RETENTION dimension
        verified_retentions = [a for a in retention_attempts if a.outcome == "retained_verified"]
        early_retentions = [a for a in retention_attempts if a.outcome == "passed_too_early"]
        retained_nodes = skill_state_summary["retained"]
        retention_ev = len(retention_attempts) + len(retention_schedules)
        retention_band = classify_evidence_band(
            evidence_count=retention_ev,
            verified_count=len(verified_retentions) + retained_nodes,
            developing_count=len(early_retentions),
        )

        dimensions: list[LearningDnaDimensionView] = [
            LearningDnaDimensionView(
                dimension="tracing",
                label_en="Code Tracing & Prediction",
                label_bn="কোড ট্রেসিং ও পূর্বাভাস",
                evidence_band=tracing_band,
                evidence_count=tracing_ev,
                factual_metrics={
                    "diagnostic_trace_correct": trace_diag_correct,
                    "diagnostic_trace_total": len(trace_diag),
                    "predictions_written": predictions_written,
                    "lessons_read": lessons_read,
                },
                summary_en=(
                    f"{trace_diag_correct}/{len(trace_diag)} diagnostic concept/trace items correct, "
                    f"{predictions_written} output predictions recorded, {lessons_read} lessons read."
                ),
                summary_bn=(
                    f"ডায়াগনস্টিক ট্রেস/ধারণা {trace_diag_correct}/{len(trace_diag)} সঠিক, "
                    f"{predictions_written}টি আউটপুট পূর্বাভাস এবং {lessons_read}টি লেসন পড়া হয়েছে।"
                ),
                uncertainty_note=(
                    "No tracing evidence yet — complete a diagnostic or write an output prediction before running code."
                    if tracing_ev == 0
                    else "Grounded in recorded trace responses and pre-run output predictions."
                ),
            ),
            LearningDnaDimensionView(
                dimension="coding",
                label_en="Python Implementation",
                label_bn="পাইথন কোড রচনা",
                evidence_band=coding_band,
                evidence_count=coding_ev,
                factual_metrics={
                    "judge0_submissions_total": len(submissions),
                    "judge0_accepted_submits": len(accepted_submits),
                    "guided_lesson_exercises_passed": lessons_passed,
                    "diagnostic_code_checks_passed": diag_code_passed,
                },
                summary_en=(
                    f"{len(accepted_submits)} Judge0 accepted submits, {lessons_passed} guided lesson "
                    f"exercises passed, {diag_code_passed} diagnostic Judge0 checks passed."
                ),
                summary_bn=(
                    f"Judge0-তে {len(accepted_submits)}টি সম্পূর্ণ সাবমিট পাস, {lessons_passed}টি গাইডেড "
                    f"লেসন অনুশীলন এবং {diag_code_passed}টি ডায়াগনস্টিক কোড চেক সফল হয়েছে।"
                ),
                uncertainty_note=(
                    "No Judge0 coding runs recorded yet."
                    if coding_ev == 0
                    else "Based strictly on executed Judge0 results across lessons, diagnostics, and problems."
                ),
            ),
            LearningDnaDimensionView(
                dimension="debugging",
                label_en="Systematic Debugging",
                label_bn="পদ্ধতিগত ডিবাগিং",
                evidence_band=debug_band,
                evidence_count=debug_ev,
                factual_metrics={
                    "debugging_fixes_accepted": len(debug_accepted),
                    "ml_diagnoses_reviewed": len(diagnoses),
                    "code_revisions_saved": len(revisions),
                    "mentor_hints_used": len(hints),
                },
                summary_en=(
                    f"{len(debug_accepted)} debugging problems fixed on Judge0, {len(diagnoses)} ML error "
                    f"diagnoses inspected, {len(revisions)} revisions saved, {len(hints)} AI hints used."
                ),
                summary_bn=(
                    f"Judge0-তে {len(debug_accepted)}টি ডিবাগিং সমস্যা ঠিক করা হয়েছে, {len(diagnoses)}টি ML "
                    f"ত্রুটি বিশ্লেষণ, {len(revisions)}টি রিভিশন এবং {len(hints)}টি AI হিন্ট ব্যবহৃত হয়েছে।"
                ),
                uncertainty_note=(
                    "Open a Debugging problem in the Problem Bank to generate real debugging evidence."
                    if debug_ev == 0
                    else "Reflects real Judge0 debugging iterations, ML error diagnoses, and hint reliance."
                ),
            ),
            LearningDnaDimensionView(
                dimension="testing",
                label_en="Verification & Edge-Case Testing",
                label_bn="টেস্টিং ও এজ-কেস যাচাই",
                evidence_band=testing_band,
                evidence_count=testing_ev,
                factual_metrics={
                    "public_run_checks": len(public_runs),
                    "full_hidden_submits": len(hidden_submits),
                    "tests_passed_total": total_tests_passed,
                    "tests_executed_total": total_tests_run,
                },
                summary_en=(
                    f"{len(public_runs)} public Run checks and {len(hidden_submits)} hidden-suite Submits "
                    f"({total_tests_passed}/{total_tests_run} total Judge0 test cases passed)."
                ),
                summary_bn=(
                    f"{len(public_runs)}টি পাবলিক Run এবং {len(hidden_submits)}টি হিডেন-টেস্ট Submit "
                    f"(মোট {total_tests_passed}/{total_tests_run}টি Judge0 টেস্ট পাস)।"
                ),
                uncertainty_note=(
                    "No public or hidden test suite runs recorded yet."
                    if testing_ev == 0
                    else "Derived from actual Judge0 public Run and full hidden-test Submit ratios."
                ),
            ),
            LearningDnaDimensionView(
                dimension="transfer",
                label_en="Independent Transfer",
                label_bn="স্বাধীন প্রয়োগ (ট্রান্সফার)",
                evidence_band=transfer_band,
                evidence_count=transfer_ev,
                factual_metrics={
                    "verified_independent_transfers": len(verified_transfers),
                    "zero_hint_transfers": len(zero_hint_transfers),
                    "transfer_attempts_total": len(verifications),
                    "skill_nodes_transferred": transferred_nodes,
                },
                summary_en=(
                    f"{len(verified_transfers)} unseen Transfer Challenges verified independently on Judge0 "
                    f"({len(zero_hint_transfers)} with 0 AI hints); {transferred_nodes} Skill Graph nodes transferred."
                ),
                summary_bn=(
                    f"{len(verified_transfers)}টি নতুন ট্রান্সফার চ্যালেঞ্জ স্বাধীনভাবে পাস "
                    f"({len(zero_hint_transfers)}টি শূন্য হিন্টে); Skill Graph-এ {transferred_nodes}টি দক্ষতা Transferred।"
                ),
                uncertainty_note=(
                    "Transfer is never inferred from guided solves — pass an unlocked Phase 4 Transfer Challenge with 0 hints."
                    if len(verified_transfers) == 0
                    else "Proven by zero-hint unseen Judge0 transfer verification."
                ),
            ),
            LearningDnaDimensionView(
                dimension="retention",
                label_en="Long-Term Retention",
                label_bn="দীর্ঘমেয়াদী দক্ষতা সংরক্ষণ",
                evidence_band=retention_band,
                evidence_count=retention_ev,
                factual_metrics={
                    "retained_verifications_passed": len(verified_retentions),
                    "early_practice_passes": len(early_retentions),
                    "scheduled_checks_total": len(retention_schedules),
                    "skill_nodes_retained": retained_nodes,
                },
                summary_en=(
                    f"{len(verified_retentions)} spaced (>=24h) retention checks passed on Judge0, "
                    f"{len(retention_schedules)} retention checks tracked, {retained_nodes} Skill Graph nodes retained."
                ),
                summary_bn=(
                    f"২৪ ঘণ্টা পর {len(verified_retentions)}টি রিটেনশন যাচাই পাস হয়েছে, "
                    f"{len(retention_schedules)}টি রিটেনশন সূচি আছে এবং {retained_nodes}টি দক্ষতা Retained।"
                ),
                uncertainty_note=(
                    "Skills are NEVER marked Retained immediately — complete a scheduled retention check >=24h after initial verification."
                    if len(verified_retentions) == 0
                    else "Backed by real delayed Judge0 re-verification >=24h after initial mastery."
                ),
            ),
        ]

        strengths = [d.label_en for d in dimensions if d.evidence_band == "verified"]
        growth_areas = [
            d.label_en for d in dimensions if d.evidence_band in ("unobserved", "emerging")
        ]
        source_counts = {
            "diagnostic_responses": len(diag_responses),
            "lessons_with_progress": len(lesson_rows),
            "judge0_submissions": len(submissions),
            "code_revisions": len(revisions),
            "ml_diagnoses": len(diagnoses),
            "mentor_hints": len(hints),
            "transfer_attempts": len(verifications),
            "retention_attempts": len(retention_attempts),
        }

        recent = await self._growth_repo.list_dna_snapshots(
            student_id=user.id, limit=6, language_slug=lang
        )
        latest_snap = recent[0] if recent else None
        if (
            latest_snap is not None
            and latest_snap.selected_track_slug == track_status.selected_track_slug
            and dict(latest_snap.source_counts or {}) == source_counts
            and dict(latest_snap.skill_state_summary or {}) == skill_state_summary
        ):
            snap = latest_snap
        else:
            snap = await self._growth_repo.create_dna_snapshot(
                student_id=user.id,
                language_slug=lang,
                selected_track_slug=track_status.selected_track_slug,
                dimensions_json=[d.model_dump() for d in dimensions],
                skill_state_summary=skill_state_summary,
                strengths=strengths,
                growth_areas=growth_areas,
                source_counts=source_counts,
            )
            recent = [snap, *recent[:5]]

        return LearningDnaProfileView(
            snapshot_id=snap.id,
            language_slug=lang,
            computed_at=snap.computed_at,
            selected_track_slug=track_status.selected_track_slug,
            dimensions=dimensions,
            skill_state_summary=skill_state_summary,
            strengths=strengths,
            growth_areas=growth_areas,
            source_counts=source_counts,
            methodology_note_en=(
                "Learning DNA uses deterministic, evidence-gated bands (Unobserved, Emerging, Developing, Verified) "
                "computed from real diagnostics, Judge0 executions, ML debugging revisions, 0-hint transfers, "
                "and >=24h retention checks. Self-reported skill never inflates these bands."
            ),
            methodology_note_bn=(
                "Learning DNA কোনো অনুমানভিত্তিক নম্বর তৈরি করে না; এটি ডায়াগনস্টিক, Judge0 এক্সিকিউশন, "
                "ডিবাগিং রিভিশন, শূন্য-হিন্ট ট্রান্সফার এবং ২৪ ঘণ্টা পরের রিটেনশন প্রমাণের ওপর ভিত্তি করে নির্ণীত।"
            ),
            recent_snapshots=[
                LearningDnaSnapshotSummaryView(
                    id=s.id,
                    selected_track_slug=s.selected_track_slug,
                    computed_at=s.computed_at,
                    strengths=list(s.strengths or []),
                    growth_areas=list(s.growth_areas or []),
                )
                for s in recent
            ],
        )
