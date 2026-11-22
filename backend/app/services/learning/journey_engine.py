"""Central deterministic Learning Journey Engine.

Computes a single authoritative `primary_action` (CONTINUE LEARNING), optional
`resume_activity`, and ranked `secondary_actions` from persisted database evidence
for any student and programming language without storing redundant progress counters.

Priority Policy (documented, deterministic, explainable):
  0. Incomplete onboarding -> /student/onboarding
  1. Urgent teacher assignment (revision requested or deadline within 72h)
  2. Unfinished active learning activity (in-progress diagnostic or in-progress lesson)
  3. Due spaced retention verification (>=24h interval elapsed)
  4. Entry assessment (Beginner: 2 foundation lessons -> Short Readiness Check;
     Experienced: Full 8-Domain Adaptive Diagnostic)
  5. Diagnostic gap remediation (prerequisite-ready lesson targeting weak domain)
  6. Next prerequisite-ready guided lesson in active track
  7. Eligible unlocked Independent Transfer Verification challenge
  8. Adaptive coding / debugging practice problem matching language & readiness
  9. Active Daily Plan task / next milestone / optional reassessment (never dead-end)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from app.repositories.classroom import ClassroomRepository
from app.repositories.growth import GrowthRepository
from app.repositories.identity import UserRecord
from app.repositories.learning import LearningRepository
from app.repositories.mentor import MentorRepository
from app.repositories.problems import ProblemRepository
from app.schemas.learning import (
    DiagnosticSessionView,
    JourneyActionView,
    JourneyStage,
    LearningJourneyView,
    LessonSummaryView,
    SkillGraphView,
    StudentTrackStatus,
    TrackSlug,
)
from app.services.learning.diagnostics_service import DiagnosticAssessmentService
from app.services.learning.lessons_service import (
    LessonsAndTracksService,
    resolve_user_language,
)
from app.services.learning.skill_graph import STATE_RANK, SkillGraphService

LANGUAGE_LABELS: dict[str, str] = {
    "python": "Python 3",
    "javascript": "JavaScript",
    "c": "C",
    "cpp": "C++",
    "java": "Java",
}

DOMAIN_TO_SKILL: dict[str, str] = {
    "variables": "variables",
    "syntax_runtime_debugging": "debugging_basics",
    "conditions": "conditions",
    "loop_boundaries": "loops",
    "arrays_lists": "lists",
    "indexing": "indexing",
    "functions": "functions",
    "mixed_logic": "mixed_problem_solving",
}

FOUNDATION_LESSONS_TARGET = 2
URGENT_ASSIGNMENT_WINDOW_HOURS = 72


@dataclass(slots=True)
class UrgentAssignmentCandidate:
    assignment_id: str
    course_code: str
    title: str
    workflow_status: str
    due_at: datetime | None
    is_overdue: bool
    allow_late: bool


@dataclass(slots=True)
class TransferCandidate:
    source_problem_id: str
    source_problem_slug: str
    source_problem_title: str
    transfer_problem_title: str
    skill_focus: str


@dataclass(slots=True)
class PracticeProblemCandidate:
    problem_id: str
    slug: str
    title: str
    mode: str
    difficulty: str


@dataclass(slots=True)
class DueRetentionCandidate:
    schedule_id: str
    skill_slug: str
    problem_slug: str
    interval_hours: int


@dataclass(slots=True)
class JourneyDecisionInput:
    """Pure, serializable snapshot of authoritative persisted student evidence."""

    language_slug: str
    onboarding_completed: bool
    programming_experience: str
    starting_preference: str
    active_track_slug: TrackSlug
    lessons: list[LessonSummaryView] = field(default_factory=list)
    skill_states: dict[str, str] = field(default_factory=dict)
    diag_sessions: list[DiagnosticSessionView] = field(default_factory=list)
    urgent_assignments: list[UrgentAssignmentCandidate] = field(default_factory=list)
    due_retentions: list[DueRetentionCandidate] = field(default_factory=list)
    unlocked_transfers: list[TransferCandidate] = field(default_factory=list)
    unsolved_problems: list[PracticeProblemCandidate] = field(default_factory=list)
    pending_daily_tasks_count: int = 0
    now: datetime = field(default_factory=lambda: datetime.now(UTC))


def _lang_label(slug: str) -> str:
    return LANGUAGE_LABELS.get(slug, slug.capitalize())


def _is_beginner_entry(experience: str, starting_preference: str) -> bool:
    return experience in ("none", "beginner") and starting_preference == "guided_beginner"


def decide_learning_journey(ctx: JourneyDecisionInput) -> LearningJourneyView:
    """Pure deterministic 9-priority decision function — easily auditable and unit-tested."""
    lang = ctx.language_slug
    lang_name = _lang_label(lang)

    completed_lessons = [lsn for lsn in ctx.lessons if lsn.progress_status == "completed"]
    in_progress_lessons = [lsn for lsn in ctx.lessons if lsn.progress_status == "in_progress"]
    incomplete_lessons = [lsn for lsn in ctx.lessons if lsn.progress_status != "completed"]

    in_progress_diag = next((d for d in ctx.diag_sessions if d.status == "in_progress"), None)
    completed_diags = [d for d in ctx.diag_sessions if d.status == "completed"]
    full_diags = [d for d in completed_diags if d.assessment_mode == "full"]
    latest_diag = completed_diags[0] if completed_diags else None

    foundation_done = min(len(completed_lessons), FOUNDATION_LESSONS_TARGET)
    readiness_unlocked = len(completed_lessons) >= FOUNDATION_LESSONS_TARGET
    beginner_entry = _is_beginner_entry(ctx.programming_experience, ctx.starting_preference)

    # Priority 0: Incomplete onboarding
    if not ctx.onboarding_completed:
        onboarding_action = JourneyActionView(
            action_type="onboarding",
            target_id="student-onboarding",
            target_slug="onboarding",
            href="/student/onboarding",
            cta_label_en="Complete Quick Setup",
            cta_label_bn="দ্রুত সেটআপ সম্পন্ন করো",
            title_en="Personalize Your Learning Path",
            title_bn="তোমার শেখার পথ নির্ধারণ করো",
            reason_en="Tell us your language, experience, and daily study goal so we can tailor your starting path.",
            reason_bn="তোমার ভাষা, অভিজ্ঞতা ও দৈনিক সময় জানালে আমরা সঠিক ধাপ থেকে শুরু করতে সাহায্য করব।",
            evidence_factors=["onboarding_incomplete"],
            priority=0,
            urgency="urgent",
            estimated_minutes=2,
        )
        return LearningJourneyView(
            language_slug=lang,
            onboarding_completed=False,
            active_track_slug=ctx.active_track_slug,
            journey_stage="onboarding",
            foundation_lessons_completed=0,
            foundation_lessons_target=FOUNDATION_LESSONS_TARGET,
            readiness_check_unlocked=False,
            diagnostic_completed=False,
            full_diagnostic_completed=False,
            primary_action=onboarding_action,
            resume_activity=None,
            secondary_actions=[],
        )

    candidates: list[JourneyActionView] = []
    resume_activity: JourneyActionView | None = None

    # Priority 1: Urgent Teacher Assignments (revision requested OR deadline <= 72h)
    for asg in ctx.urgent_assignments[:2]:
        is_rev = asg.workflow_status == "revision_requested"
        due_note_en = ""
        due_note_bn = ""
        if is_rev:
            due_note_en = f"Instructor requested a revision on {asg.course_code} — address feedback and resubmit."
            due_note_bn = (
                f"{asg.course_code} কোর্সের শিক্ষক সংশোধনের অনুরোধ করেছেন — ফিডব্যাক দেখে পুনরায় জমা দাও।"
            )
        elif asg.due_at is not None:
            hours_left = max(int((asg.due_at - ctx.now).total_seconds() // 3600), 0)
            if asg.is_overdue:
                due_note_en = (
                    f"Past deadline ({asg.course_code}); late submissions are still accepted."
                )
                due_note_bn = (
                    f"সময়সীমা পেরিয়ে গেছে ({asg.course_code}); বিলম্বে জমা দেওয়ার সুযোগ এখনো খোলা আছে।"
                )
            else:
                due_note_en = f"Due in ~{hours_left}h for {asg.course_code}. Prioritized so you stay ahead of class deadlines."
                due_note_bn = f"{asg.course_code}-এর জমা দেওয়ার সময় বাকি ~{hours_left} ঘণ্টা। ক্লাসের সময়সীমার আগে সম্পন্ন করো।"
        else:
            due_note_en = f"Active class assignment in {asg.course_code} awaits your submission."
            due_note_bn = f"{asg.course_code} কোর্সের অ্যাসাইনমেন্টটি এখনো জমা দেওয়া হয়নি।"

        candidates.append(
            JourneyActionView(
                action_type="assignment",
                target_id=asg.assignment_id,
                target_slug=asg.assignment_id,
                href=f"/student/assignments/{asg.assignment_id}",
                cta_label_en="Open Assignment",
                cta_label_bn="অ্যাসাইনমেন্ট খোলো",
                title_en=f"{asg.course_code}: {asg.title}",
                title_bn=f"{asg.course_code}: {asg.title}",
                reason_en=due_note_en,
                reason_bn=due_note_bn,
                evidence_factors=[
                    f"assignment_status:{asg.workflow_status}",
                    f"course:{asg.course_code}",
                ],
                priority=1,
                urgency="urgent",
                eligibility_note_en="Authorized enrolled classroom assignment",
                eligibility_note_bn="অনুমোদিত ক্লাসরুম অ্যাসাইনমেন্ট",
                estimated_minutes=20,
            )
        )

    # Priority 2: Unfinished Active Learning Activity (Resume Diagnostic or In-Progress Lesson)
    if in_progress_diag is not None:
        is_readiness = in_progress_diag.assessment_mode == "readiness"
        diag_href = (
            "/student/diagnostic?mode=readiness"
            if is_readiness
            else "/student/diagnostic?mode=full"
        )
        diag_resume = JourneyActionView(
            action_type="diagnostic_resume",
            target_id=str(in_progress_diag.id),
            target_slug="diagnostic-resume",
            href=diag_href,
            cta_label_en="Resume Check" if is_readiness else "Resume Diagnostic",
            cta_label_bn="যাচাই চালিয়ে যাও" if is_readiness else "ডায়াগনস্টিক চালিয়ে যাও",
            title_en=(
                f"Resume {lang_name} Short Readiness Check"
                if is_readiness
                else f"Resume {lang_name} Adaptive Diagnostic"
            ),
            title_bn=(
                f"{lang_name} সংক্ষিপ্ত প্রস্তুতি যাচাই চালিয়ে যাও"
                if is_readiness
                else f"{lang_name} অ্যাডাপ্টিভ ডায়াগনস্টিক চালিয়ে যাও"
            ),
            reason_en=(
                f"You already answered {in_progress_diag.answered_count} check(s) with "
                f"{in_progress_diag.remaining_count} remaining. Finish to lock in your evidence-based track."
            ),
            reason_bn=(
                f"তুমি ইতিমধ্যে {in_progress_diag.answered_count}টি প্রশ্নের উত্তর দিয়েছ, বাকি "
                f"{in_progress_diag.remaining_count}টি। সম্পন্ন করলে তোমার প্রামাণ্য ট্র্যাক নির্ধারিত হবে।"
            ),
            evidence_factors=[
                f"diagnostic_in_progress:{in_progress_diag.answered_count}_answered",
                f"mode:{in_progress_diag.assessment_mode}",
            ],
            priority=2,
            urgency="recommended",
            estimated_minutes=max(in_progress_diag.remaining_count * 2, 3),
        )
        resume_activity = diag_resume
        candidates.append(diag_resume)

    if in_progress_lessons:
        active_lsn = in_progress_lessons[0]
        lsn_resume = JourneyActionView(
            action_type="lesson_resume",
            target_id=str(active_lsn.lesson_id),
            target_slug=active_lsn.slug,
            href=f"/student/lessons/{active_lsn.slug}",
            cta_label_en="Resume Lesson",
            cta_label_bn="লেসন চালিয়ে যাও",
            title_en=f"Finish Lesson: {active_lsn.title_en}",
            title_bn=f"লেসন সম্পন্ন করো: {active_lsn.title_bn}",
            reason_en=(
                "You already started this lesson — pass the guided sandbox exercise to mark it complete."
                if active_lsn.reading_completed
                else "Continue where you left off and pass the guided coding exercise."
            ),
            reason_bn=(
                "তুমি এই লেসনটি পড়া শেষ করেছ — এখন গাইডেড কোড অনুশীলন পাস করে লেসনটি সম্পন্ন করো।"
                if active_lsn.reading_completed
                else "যেখান থেকে থেমেছিলে সেখান থেকেই শুরু করো এবং গাইডেড অনুশীলন পাস করো।"
            ),
            evidence_factors=[
                "lesson_in_progress",
                f"reading_completed:{str(active_lsn.reading_completed).lower()}",
                f"attempts:{active_lsn.exercise_attempts}",
            ],
            priority=2,
            urgency="recommended",
            eligibility_note_en="Guided exercise required for completion",
            eligibility_note_bn="সম্পন্ন করতে গাইডেড অনুশীলন পাস করতে হবে",
            estimated_minutes=active_lsn.estimated_minutes,
        )
        if resume_activity is None:
            resume_activity = lsn_resume
        candidates.append(lsn_resume)

    # Priority 3: Due Spaced Retention Verification (>=24h elapsed)
    if ctx.due_retentions:
        sched = ctx.due_retentions[0]
        candidates.append(
            JourneyActionView(
                action_type="retention_check",
                target_id=sched.schedule_id,
                target_slug=sched.problem_slug,
                href="/student/retention",
                cta_label_en="Verify Retention",
                cta_label_bn="রিটেনশন যাচাই করো",
                title_en=f"Due {lang_name} Retention Check ({sched.skill_slug.replace('_', ' ')})",
                title_bn=f"{lang_name} রিটেনশন যাচাই ({sched.skill_slug.replace('_', ' ')})",
                reason_en=(
                    f"{len(ctx.due_retentions)} spaced revision check(s) reached the {sched.interval_hours}h window. "
                    "Pass a real sandbox check to advance your Skill Graph to Retained."
                ),
                reason_bn=(
                    f"{len(ctx.due_retentions)}টি স্পেসড রিভিশন চেকের {sched.interval_hours} ঘণ্টার সময় পূর্ণ হয়েছে। "
                    "আসল স্যান্ডবক্স পাস করে Retained অর্জন করো।"
                ),
                evidence_factors=[
                    f"retention_due:{len(ctx.due_retentions)}",
                    f"skill:{sched.skill_slug}",
                ],
                priority=3,
                urgency="recommended",
                estimated_minutes=12,
            )
        )

    # Priority 4: Entry Assessment (Beginner Foundation-First vs Experienced Full Diagnostic)
    if latest_diag is None and in_progress_diag is None:
        if not beginner_entry:
            candidates.append(
                JourneyActionView(
                    action_type="diagnostic_full",
                    target_id=f"diagnostic-full-{lang}",
                    target_slug="diagnostic-full",
                    href="/student/diagnostic?mode=full",
                    cta_label_en="Start Adaptive Diagnostic",
                    cta_label_bn="অ্যাডাপ্টিভ ডায়াগনস্টিক শুরু করো",
                    title_en=f"8-Domain {lang_name} Adaptive Diagnostic",
                    title_bn=f"৮-ডোমেইন {lang_name} অ্যাডাপ্টিভ ডায়াগনস্টিক",
                    reason_en=(
                        f"Your onboarding shows prior experience ({ctx.programming_experience}). "
                        f"Take the {lang_name} diagnostic so your track placement is grounded in real evidence."
                    ),
                    reason_bn=(
                        f"তোমার পূর্ব অভিজ্ঞতা ({ctx.programming_experience}) থাকায় আসল প্রমাণের ভিত্তিতে "
                        f"সঠিক {lang_name} ট্র্যাক নির্ধারণ করতে ডায়াগনস্টিক টেস্ট দাও।"
                    ),
                    evidence_factors=[
                        "no_diagnostic_yet",
                        f"experience:{ctx.programming_experience}",
                        f"language:{lang}",
                    ],
                    priority=4,
                    urgency="recommended",
                    estimated_minutes=10,
                )
            )
        elif readiness_unlocked:
            candidates.append(
                JourneyActionView(
                    action_type="diagnostic_readiness",
                    target_id=f"diagnostic-readiness-{lang}",
                    target_slug="diagnostic-readiness",
                    href="/student/diagnostic?mode=readiness",
                    cta_label_en="Take Short Readiness Check",
                    cta_label_bn="সংক্ষিপ্ত প্রস্তুতি যাচাই দাও",
                    title_en=f"Short {lang_name} Foundation Readiness Check",
                    title_bn=f"{lang_name} সংক্ষিপ্ত ফাউন্ডেশন প্রস্তুতি যাচাই",
                    reason_en=(
                        f"Great start! You completed {len(completed_lessons)} foundation lesson(s). "
                        "Take a quick 4-question readiness check to confirm your best learning track."
                    ),
                    reason_bn=(
                        f"দারুণ শুরু! তুমি {len(completed_lessons)}টি ফাউন্ডেশন লেসন সম্পন্ন করেছ। "
                        "এখন ৪টি প্রশ্নের সংক্ষিপ্ত যাচাই দিয়ে তোমার উপযুক্ত ট্র্যাক নিশ্চিত করো।"
                    ),
                    evidence_factors=[
                        f"foundation_lessons_completed:{len(completed_lessons)}",
                        "readiness_check_unlocked",
                    ],
                    priority=4,
                    urgency="recommended",
                    estimated_minutes=5,
                )
            )

    # Identify diagnostic gap skills
    gap_skills: set[str] = set()
    if latest_diag is not None:
        for ev in latest_diag.domain_evidence:
            if ev.evidence_status in ("gap_detected", "guided_needed"):
                gap_skills.add(DOMAIN_TO_SKILL.get(ev.domain_slug, ev.domain_slug))

    ready_incomplete = [lsn for lsn in incomplete_lessons if lsn.prerequisites_met]
    gap_lessons = [lsn for lsn in ready_incomplete if lsn.skill_slug in gap_skills]
    track_lessons = [
        lsn
        for lsn in ready_incomplete
        if ctx.active_track_slug in lsn.track_slugs and lsn not in gap_lessons
    ]
    fallback_lessons = [
        lsn for lsn in ready_incomplete if lsn not in gap_lessons and lsn not in track_lessons
    ]

    # Priority 5: Diagnostic Gap Remediation Lesson
    for lsn in gap_lessons[:2]:
        cur_state = ctx.skill_states.get(lsn.skill_slug, "unobserved")
        candidates.append(
            JourneyActionView(
                action_type="lesson_remediation",
                target_id=str(lsn.lesson_id),
                target_slug=lsn.slug,
                href=f"/student/lessons/{lsn.slug}",
                cta_label_en="Fix Skill Gap",
                cta_label_bn="ঘাটতি পূরণ করো",
                title_en=lsn.title_en,
                title_bn=lsn.title_bn,
                reason_en=(
                    f"Diagnostic detected a gap in '{lsn.skill_slug.replace('_', ' ')}' "
                    f"(skill state: {cur_state}). All prerequisites are satisfied."
                ),
                reason_bn=(
                    f"ডায়াগনস্টিকে '{lsn.title_bn}' বিষয়ে ঘাটতি পাওয়া গেছে এবং পূর্বশর্ত সম্পন্ন হয়েছে।"
                ),
                evidence_factors=[
                    "diagnostic_gap",
                    f"skill_state:{lsn.skill_slug}={cur_state}",
                    "prerequisites_satisfied",
                ],
                priority=5,
                urgency="recommended",
                estimated_minutes=lsn.estimated_minutes,
            )
        )

    # Priority 6: Next Prerequisite-Ready Guided Lesson in Active Track
    ordered_lessons = (track_lessons + fallback_lessons)[:2]
    for lsn in ordered_lessons:
        cur_state = ctx.skill_states.get(lsn.skill_slug, "unobserved")
        is_foundation_intro = beginner_entry and not readiness_unlocked and latest_diag is None
        candidates.append(
            JourneyActionView(
                action_type="lesson",
                target_id=str(lsn.lesson_id),
                target_slug=lsn.slug,
                href=f"/student/lessons/{lsn.slug}",
                cta_label_en=(
                    f"Start Foundation Lesson {len(completed_lessons) + 1}"
                    if is_foundation_intro
                    else "Start Guided Lesson"
                ),
                cta_label_bn=(
                    f"ফাউন্ডেশন লেসন {len(completed_lessons) + 1} শুরু করো"
                    if is_foundation_intro
                    else "গাইডেড লেসন শুরু করো"
                ),
                title_en=lsn.title_en,
                title_bn=lsn.title_bn,
                reason_en=(
                    f"Gentle beginner start in {lang_name}: complete {FOUNDATION_LESSONS_TARGET} "
                    f"introductory lessons ({foundation_done}/{FOUNDATION_LESSONS_TARGET} done) before your short readiness check."
                    if is_foundation_intro
                    else f"Next prerequisite-ready {lang_name} lesson in your "
                    f"{ctx.active_track_slug.replace('_', ' ')} track (skill state: {cur_state})."
                ),
                reason_bn=(
                    f"{lang_name}-এ সহজ সূচনা: সংক্ষিপ্ত প্রস্তুতি যাচাইয়ের আগে "
                    f"{FOUNDATION_LESSONS_TARGET}টি প্রাথমিক লেসন সম্পন্ন করো ({foundation_done}/{FOUNDATION_LESSONS_TARGET} সম্পন্ন)।"
                    if is_foundation_intro
                    else f"তোমার {ctx.active_track_slug.replace('_', ' ')} ট্র্যাকের পরবর্তী পূর্বশর্ত-সম্পন্ন {lang_name} লেসন।"
                ),
                evidence_factors=[
                    "foundation_onboarding_path"
                    if is_foundation_intro
                    else f"track:{ctx.active_track_slug}",
                    f"skill_state:{lsn.skill_slug}={cur_state}",
                    "prerequisites_satisfied",
                ],
                priority=6,
                urgency="recommended",
                eligibility_note_en="Prerequisites satisfied · Real sandbox exercise",
                eligibility_note_bn="পূর্বশর্ত সম্পন্ন · আসল স্যান্ডবক্স অনুশীলন",
                estimated_minutes=lsn.estimated_minutes,
            )
        )

    # Priority 7: Eligible Unlocked Independent Transfer Verification Challenge
    for tr in ctx.unlocked_transfers[:2]:
        candidates.append(
            JourneyActionView(
                action_type="transfer_verification",
                target_id=tr.source_problem_id,
                target_slug=tr.source_problem_slug,
                href=f"/student/problems/{tr.source_problem_id}?tab=verify",
                cta_label_en="Verify Independently",
                cta_label_bn="স্বাধীন যাচাই শুরু করো",
                title_en=f"Transfer Check: {tr.transfer_problem_title}",
                title_bn=f"ট্রান্সফার যাচাই: {tr.transfer_problem_title}",
                reason_en=(
                    f"You solved '{tr.source_problem_title}' in the sandbox! Pass this unseen "
                    "zero-hint challenge to advance your Skill Graph to Transferred."
                ),
                reason_bn=(
                    f"তুমি '{tr.source_problem_title}' সমাধান করেছ! হিন্ট ছাড়া এই নতুন চ্যালেঞ্জ পাস করে "
                    "Skill Graph-এ Transferred অর্জন করো।"
                ),
                evidence_factors=[
                    f"accepted_source:{tr.source_problem_slug}",
                    "transfer_unlocked_unverified",
                    f"skill:{tr.skill_focus}",
                ],
                priority=7,
                urgency="recommended",
                eligibility_note_en="Zero-hint independent transfer unlocked",
                eligibility_note_bn="শূন্য-হিন্ট স্বাধীন ট্রান্সফার আনলকড",
                estimated_minutes=15,
            )
        )

    # Priority 8: Adaptive Coding / Debugging Practice Problem
    loops_rank = STATE_RANK.get(ctx.skill_states.get("loops", "unobserved"), 0)
    vars_rank = STATE_RANK.get(ctx.skill_states.get("variables", "unobserved"), 0)
    ready_for_practice = (
        ctx.active_track_slug != "absolute_beginner"
        or len(completed_lessons) >= 1
        or loops_rank >= 1
        or vars_rank >= 1
    )
    if ready_for_practice and ctx.unsolved_problems:
        prob = ctx.unsolved_problems[0]
        candidates.append(
            JourneyActionView(
                action_type="problem",
                target_id=prob.problem_id,
                target_slug=prob.slug,
                href=f"/student/problems/{prob.problem_id}",
                cta_label_en="Practice Debugging" if prob.mode == "debugging" else "Solve Problem",
                cta_label_bn="ডিবাগিং অনুশীলন" if prob.mode == "debugging" else "সমস্যা সমাধান করো",
                title_en=prob.title,
                title_bn=prob.title,
                reason_en=(
                    f"Apply your {lang_name} skills in a real sandbox challenge ({prob.difficulty}, "
                    f"{prob.mode}) with error diagnosis and Socratic AI Mentor support."
                ),
                reason_bn=(
                    f"আসল স্যান্ডবক্স, এরর ডায়াগনোসিস ও Socratic AI Mentor-সহ {lang_name}-এ "
                    f"বাস্তব সমস্যা ({prob.difficulty}) সমাধান করো।"
                ),
                evidence_factors=[
                    f"problem_mode:{prob.mode}",
                    f"difficulty:{prob.difficulty}",
                    f"language:{lang}",
                ],
                priority=8,
                urgency="recommended",
                estimated_minutes=15,
            )
        )

    # Priority 9: Active Daily Plan or Milestone / Optional Reassessment (NEVER dead-end)
    if ctx.pending_daily_tasks_count > 0:
        candidates.append(
            JourneyActionView(
                action_type="daily_plan",
                target_id=f"daily-plan-{lang}",
                target_slug="daily-plan",
                href="/student/daily-plan",
                cta_label_en="Open Today's Plan",
                cta_label_bn="আজকের প্ল্যান খোলো",
                title_en=f"Complete Today's {lang_name} Learning Plan",
                title_bn=f"আজকের {lang_name} শেখার প্ল্যান সম্পন্ন করো",
                reason_en=(
                    f"You have {ctx.pending_daily_tasks_count} scheduled task(s) left in today's "
                    "adaptive study plan."
                ),
                reason_bn=(
                    f"আজকের অ্যাডাপ্টিভ স্টাডি প্ল্যানে তোমার {ctx.pending_daily_tasks_count}টি কাজ বাকি আছে।"
                ),
                evidence_factors=[f"daily_tasks_pending:{ctx.pending_daily_tasks_count}"],
                priority=9,
                urgency="optional",
                estimated_minutes=15,
            )
        )

    if not candidates:
        candidates.append(
            JourneyActionView(
                action_type="milestone_complete",
                target_id=f"milestone-{lang}",
                target_slug="milestone-complete",
                href="/student/problems" if full_diags else "/student/diagnostic?mode=full",
                cta_label_en="Explore Problem Bank" if full_diags else "Take Full 8-Domain Check",
                cta_label_bn="প্রবলেম ব্যাংক দেখো" if full_diags else "৮-ডোমেইন পূর্ণ যাচাই দাও",
                title_en=(
                    f"All Guided {lang_name} Lessons Complete — Keep Sharpening!"
                    if len(incomplete_lessons) == 0
                    else f"Continue Growing in {lang_name}"
                ),
                title_bn=(
                    f"{lang_name}-এর সব গাইডেড লেসন সম্পন্ন — এবার আরও অনুশীলন করো!"
                    if len(incomplete_lessons) == 0
                    else f"{lang_name}-এ শেখা চালিয়ে যাও"
                ),
                reason_en=(
                    "Challenge yourself with debugging problems, transfer verification, or an updated diagnostic check."
                ),
                reason_bn=(
                    "ডিবাগিং সমস্যা, স্বাধীন ট্রান্সফার যাচাই অথবা নতুন ডায়াগনস্টিক দিয়ে দক্ষতা আরও শাণিত করো।"
                ),
                evidence_factors=[
                    f"lessons_completed:{len(completed_lessons)}/{len(ctx.lessons)}",
                    f"language:{lang}",
                ],
                priority=9,
                urgency="optional",
                estimated_minutes=15,
            )
        )

    # Deduplicate by (action_type, href) while preserving priority order
    seen_keys: set[tuple[str, str]] = set()
    deduped: list[JourneyActionView] = []
    for item in sorted(candidates, key=lambda a: a.priority):
        key = (item.action_type, item.href)
        if key not in seen_keys:
            seen_keys.add(key)
            deduped.append(item)

    primary = deduped[0]
    secondary = deduped[1:4]

    # Determine transparent Journey Stage
    stage: JourneyStage
    if beginner_entry and not readiness_unlocked and latest_diag is None:
        stage = "foundation_lessons"
    elif beginner_entry and readiness_unlocked and latest_diag is None:
        stage = "readiness_check"
    elif latest_diag is None:
        stage = "diagnostic_placement"
    elif ctx.due_retentions:
        stage = "retention_growth"
    elif ctx.unlocked_transfers or any(
        st in ("independent", "transferred", "retained") for st in ctx.skill_states.values()
    ):
        stage = "independent_mastery"
    else:
        stage = "guided_practice"

    return LearningJourneyView(
        language_slug=lang,
        onboarding_completed=True,
        active_track_slug=ctx.active_track_slug,
        journey_stage=stage,
        foundation_lessons_completed=foundation_done,
        foundation_lessons_target=FOUNDATION_LESSONS_TARGET,
        readiness_check_unlocked=readiness_unlocked,
        diagnostic_completed=latest_diag is not None,
        full_diagnostic_completed=len(full_diags) > 0,
        urgent_assignments_count=len(ctx.urgent_assignments),
        due_retentions_count=len(ctx.due_retentions),
        unlocked_transfers_count=len(ctx.unlocked_transfers),
        primary_action=primary,
        resume_activity=resume_activity,
        secondary_actions=secondary,
    )


class LearningJourneyService:
    """Authoritative async orchestrator gathering live persisted evidence for the Journey Engine."""

    def __init__(
        self,
        *,
        learning_repo: LearningRepository,
        problem_repo: ProblemRepository,
        mentor_repo: MentorRepository,
        growth_repo: GrowthRepository,
        classroom_repo: ClassroomRepository,
        lessons_service: LessonsAndTracksService,
        diagnostics_service: DiagnosticAssessmentService,
        skill_graph_service: SkillGraphService,
    ) -> None:
        self._learning_repo = learning_repo
        self._problem_repo = problem_repo
        self._mentor_repo = mentor_repo
        self._growth_repo = growth_repo
        self._classroom_repo = classroom_repo
        self._lessons = lessons_service
        self._diagnostics = diagnostics_service
        self._skill_graph = skill_graph_service

    async def evaluate(
        self,
        user: UserRecord,
        *,
        language_slug: str | None = None,
        track_status: StudentTrackStatus | None = None,
        lessons: list[LessonSummaryView] | None = None,
        skill_graph: SkillGraphView | None = None,
        diag_sessions: list[DiagnosticSessionView] | None = None,
    ) -> LearningJourneyView:
        lang = resolve_user_language(user, language_slug)
        prefs = user.preferences
        experience = prefs.programming_experience if prefs else "none"
        start_pref = prefs.starting_preference if prefs else "guided_beginner"

        if not user.onboarding_completed:
            return decide_learning_journey(
                JourneyDecisionInput(
                    language_slug=lang,
                    onboarding_completed=False,
                    programming_experience=experience,
                    starting_preference=start_pref,
                    active_track_slug="absolute_beginner",
                )
            )

        if track_status is None:
            track_status = await self._lessons.get_track_status(user, language_slug=lang)
        if lessons is None:
            lessons = await self._lessons.list_lessons(user=user, language_slug=lang)
        if skill_graph is None:
            skill_graph = await self._skill_graph.get_student_skill_graph(
                user.id, language_slug=lang
            )
        if diag_sessions is None:
            diag_sessions = await self._diagnostics.list_my_sessions(user=user, language_slug=lang)

        now = datetime.now(UTC)
        urgent_assignments = await self._load_urgent_assignments(user.id, now)
        due_retentions = await self._load_due_retentions(user.id, lang, now)
        unlocked_transfers, unsolved_problems = await self._load_problems_and_transfers(
            user.id, lang
        )
        pending_daily = await self._count_pending_daily_tasks(user.id, lang)

        return decide_learning_journey(
            JourneyDecisionInput(
                language_slug=lang,
                onboarding_completed=True,
                programming_experience=experience,
                starting_preference=start_pref,
                active_track_slug=track_status.selected_track_slug,
                lessons=lessons,
                skill_states={n.slug: n.state for n in skill_graph.nodes},
                diag_sessions=diag_sessions,
                urgent_assignments=urgent_assignments,
                due_retentions=due_retentions,
                unlocked_transfers=unlocked_transfers,
                unsolved_problems=unsolved_problems,
                pending_daily_tasks_count=pending_daily,
                now=now,
            )
        )

    async def _load_urgent_assignments(
        self, student_id: UUID, now: datetime
    ) -> list[UrgentAssignmentCandidate]:
        memberships = await self._classroom_repo.list_student_memberships(student_id)
        active_course_ids = [c.id for m, c in memberships if m.status == "active"]
        if not active_course_ids:
            return []
        asgs = await self._classroom_repo.list_assignments_for_courses(
            active_course_ids, published_only=True
        )
        if not asgs:
            return []
        subs_map = await self._classroom_repo.list_submissions_for_student(
            student_id=student_id, assignment_ids=[a.id for a in asgs]
        )
        cutoff = now + timedelta(hours=URGENT_ASSIGNMENT_WINDOW_HOURS)
        urgent: list[UrgentAssignmentCandidate] = []
        for asg in asgs:
            if asg.opens_at is not None and now < asg.opens_at:
                continue
            sub = subs_map.get(asg.id)
            wf_status = sub.status if sub is not None else "not_started"
            if wf_status in ("submitted", "resubmitted", "graded"):
                continue
            is_overdue = bool(asg.due_at is not None and now > asg.due_at)
            if is_overdue and not asg.allow_late_submissions and wf_status != "revision_requested":
                continue
            approaching = bool(asg.due_at is not None and asg.due_at <= cutoff)
            if wf_status == "revision_requested" or approaching:
                urgent.append(
                    UrgentAssignmentCandidate(
                        assignment_id=str(asg.id),
                        course_code=asg.course.code,
                        title=asg.title,
                        workflow_status=wf_status,
                        due_at=asg.due_at,
                        is_overdue=is_overdue,
                        allow_late=asg.allow_late_submissions,
                    )
                )
        urgent.sort(
            key=lambda x: (
                0 if x.workflow_status == "revision_requested" else 1,
                x.due_at or datetime.max.replace(tzinfo=UTC),
            )
        )
        return urgent

    async def _load_due_retentions(
        self, student_id: UUID, language_slug: str, now: datetime
    ) -> list[DueRetentionCandidate]:
        schedules = await self._growth_repo.list_retention_schedules(
            student_id, language_slug=language_slug
        )
        due: list[DueRetentionCandidate] = []
        for sched in schedules:
            if sched.status in ("passed_retained", "retained"):
                continue
            if sched.status == "due" or (sched.due_at is not None and sched.due_at <= now):
                due.append(
                    DueRetentionCandidate(
                        schedule_id=str(sched.id),
                        skill_slug=sched.skill_slug,
                        problem_slug=str(sched.problem_id),
                        interval_hours=sched.interval_hours,
                    )
                )
        return due

    async def _load_problems_and_transfers(
        self, student_id: UUID, language_slug: str
    ) -> tuple[list[TransferCandidate], list[PracticeProblemCandidate]]:
        problems, _ = await self._problem_repo.list_published_problems(
            language=language_slug, limit=20, offset=0
        )
        if not problems:
            problems, _ = await self._problem_repo.list_published_problems(limit=20, offset=0)
        candidates = [(p, pv) for p, pv in problems if not p.slug.startswith("transfer-")]
        cand_ids = [p.id for p, _ in candidates]
        accepted_ids = await self._mentor_repo.list_accepted_submit_problem_ids(
            student_id=student_id, problem_ids=cand_ids
        )
        links_map = await self._mentor_repo.list_active_verification_links_by_source(cand_ids)

        unlocked_transfers: list[TransferCandidate] = []
        unsolved_problems: list[PracticeProblemCandidate] = []
        for prob, ver in candidates:
            if prob.id in accepted_ids:
                link_tuple = links_map.get(prob.id)
                if link_tuple is not None:
                    link, _, transfer_ver = link_tuple
                    latest_att = await self._mentor_repo.get_latest_verification_attempt(
                        student_id=student_id, verification_link_id=link.id
                    )
                    if latest_att is None or latest_att.outcome != "verified_independent":
                        unlocked_transfers.append(
                            TransferCandidate(
                                source_problem_id=str(prob.id),
                                source_problem_slug=prob.slug,
                                source_problem_title=ver.title,
                                transfer_problem_title=transfer_ver.title,
                                skill_focus=link.skill_focus,
                            )
                        )
            else:
                unsolved_problems.append(
                    PracticeProblemCandidate(
                        problem_id=str(prob.id),
                        slug=prob.slug,
                        title=ver.title,
                        mode=ver.mode,
                        difficulty=ver.difficulty,
                    )
                )

        # Prefer debugging problems first for guided habit building
        unsolved_problems.sort(key=lambda p: (0 if p.mode == "debugging" else 1, p.difficulty))
        return unlocked_transfers, unsolved_problems

    async def _count_pending_daily_tasks(self, student_id: UUID, language_slug: str) -> int:
        plan = await self._growth_repo.get_active_daily_plan(
            student_id=student_id, plan_date=date.today(), language_slug=language_slug
        )
        if plan is None:
            return 0
        return sum(1 for t in plan.tasks if t.status == "pending")


def build_post_lesson_next_action(
    *,
    lessons: list[LessonSummaryView],
    current_lesson_slug: str,
    language_slug: str,
    user: UserRecord,
    has_completed_diagnostic: bool,
) -> JourneyActionView:
    """Compute immediate next recommended action right after a student passes a guided lesson."""
    lang_name = _lang_label(language_slug)
    completed_cnt = sum(1 for lsn in lessons if lsn.progress_status == "completed")
    prefs = user.preferences
    beginner_entry = _is_beginner_entry(
        prefs.programming_experience if prefs else "none",
        prefs.starting_preference if prefs else "guided_beginner",
    )

    if (
        beginner_entry
        and completed_cnt >= FOUNDATION_LESSONS_TARGET
        and not has_completed_diagnostic
    ):
        return JourneyActionView(
            action_type="diagnostic_readiness",
            target_id=f"diagnostic-readiness-{language_slug}",
            target_slug="diagnostic-readiness",
            href="/student/diagnostic?mode=readiness",
            cta_label_en="Take Short Readiness Check →",
            cta_label_bn="সংক্ষিপ্ত প্রস্তুতি যাচাই শুরু করো →",
            title_en=f"Short {lang_name} Readiness Check Unlocked!",
            title_bn=f"{lang_name} সংক্ষিপ্ত প্রস্তুতি যাচাই আনলকড!",
            reason_en=(
                f"You completed {completed_cnt} foundation lessons. Confirm your track with a quick "
                "4-question readiness check before advancing."
            ),
            reason_bn=(
                f"তুমি {completed_cnt}টি ফাউন্ডেশন লেসন সম্পন্ন করেছ। পরবর্তী ধাপের আগে চারটি প্রশ্নের "
                "সংক্ষিপ্ত যাচাই দিয়ে তোমার ট্র্যাক নিশ্চিত করো।"
            ),
            evidence_factors=[
                f"foundation_lessons_completed:{completed_cnt}",
                "readiness_check_unlocked",
            ],
            priority=4,
            urgency="recommended",
            estimated_minutes=5,
        )

    next_lsn = next(
        (
            lsn
            for lsn in lessons
            if lsn.slug != current_lesson_slug
            and lsn.progress_status != "completed"
            and lsn.prerequisites_met
        ),
        None,
    )
    if next_lsn is not None:
        return JourneyActionView(
            action_type="lesson",
            target_id=str(next_lsn.lesson_id),
            target_slug=next_lsn.slug,
            href=f"/student/lessons/{next_lsn.slug}",
            cta_label_en=f"Next Lesson: {next_lsn.title_en}",
            cta_label_bn=f"পরবর্তী লেসন: {next_lsn.title_bn}",
            title_en=next_lsn.title_en,
            title_bn=next_lsn.title_bn,
            reason_en=f"Continue straight to your next prerequisite-ready {lang_name} lesson.",
            reason_bn=f"পরবর্তী পূর্বশর্ত-সম্পন্ন {lang_name} লেসনে এগিয়ে যাও।",
            evidence_factors=["lesson_completed", "prerequisites_satisfied"],
            priority=6,
            urgency="recommended",
            estimated_minutes=next_lsn.estimated_minutes,
        )

    return JourneyActionView(
        action_type="problem",
        target_id="problem-bank",
        target_slug="problems",
        href="/student/problems",
        cta_label_en=f"Practice {lang_name} Problems →",
        cta_label_bn=f"{lang_name} প্রবলেম অনুশীলন করো →",
        title_en=f"Apply {lang_name} in Practice Problems",
        title_bn=f"{lang_name} বাস্তব সমস্যায় প্রয়োগ করো",
        reason_en="All ready guided lessons are done — apply your knowledge in real sandbox coding challenges.",
        reason_bn="প্রস্তুত গাইডেড লেসনগুলো সম্পন্ন হয়েছে — এখন আসল স্যান্ডবক্স কোডিং সমস্যায় দক্ষতা যাচাই করো।",
        evidence_factors=["guided_lessons_completed"],
        priority=8,
        urgency="recommended",
        estimated_minutes=15,
    )
