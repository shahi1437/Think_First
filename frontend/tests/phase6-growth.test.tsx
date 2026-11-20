import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { DailyPlanClient } from "@/features/growth/daily-plan-client";
import { LearningDnaClient } from "@/features/growth/learning-dna-client";
import { LearningHistoryClient } from "@/features/growth/learning-history-client";
import { RetentionClient } from "@/features/growth/retention-client";
import type {
  DailyPlanWorkspaceView,
  LearningDnaProfileView,
  LearningHistoryResponseView,
  RetentionOverviewView,
} from "@/types/growth";

const mockDnaProfile: LearningDnaProfileView = {
  snapshot_id: "snap-1",
  computed_at: "2026-11-20T08:00:00Z",
  selected_track_slug: "basic_university",
  dimensions: [
    {
      dimension: "tracing",
      label_en: "Code Tracing & Prediction",
      label_bn: "কোড ট্রেসিং ও পূর্বাভাস",
      evidence_band: "developing",
      evidence_count: 3,
      factual_metrics: { diagnostic_trace_correct: 2, predictions_written: 1 },
      summary_en: "2/3 diagnostic trace items correct, 1 prediction written.",
      summary_bn: "২/৩টি ডায়াগনস্টিক ট্রেস সঠিক।",
      uncertainty_note: "Grounded in recorded trace responses.",
    },
    {
      dimension: "coding",
      label_en: "Python Implementation",
      label_bn: "পাইথন কোড রচনা",
      evidence_band: "verified",
      evidence_count: 4,
      factual_metrics: { judge0_accepted_submits: 2 },
      summary_en: "2 Judge0 accepted submits.",
      summary_bn: "২টি Judge0 সাবমিট পাস হয়েছে।",
      uncertainty_note: "Based strictly on executed Judge0 results.",
    },
    {
      dimension: "retention",
      label_en: "Long-Term Retention",
      label_bn: "দীর্ঘমেয়াদী দক্ষতা সংরক্ষণ",
      evidence_band: "unobserved",
      evidence_count: 0,
      factual_metrics: { retained_verifications_passed: 0 },
      summary_en: "0 spaced retention checks passed.",
      summary_bn: "০টি রিটেনশন যাচাই পাস হয়েছে।",
      uncertainty_note: "Never marked Retained before 24h.",
    },
  ],
  skill_state_summary: {
    unobserved: 7,
    introduced: 1,
    guided: 1,
    independent: 1,
    transferred: 0,
    retained: 0,
  },
  strengths: ["Python Implementation"],
  growth_areas: ["Long-Term Retention"],
  source_counts: {
    judge0_submissions: 4,
    transfer_attempts: 0,
    retention_attempts: 0,
  },
  methodology_note_en: "Deterministic, evidence-gated Learning DNA.",
  methodology_note_bn: "প্রমাণ-ভিত্তিক Learning DNA।",
  recent_snapshots: [],
};

const mockDailyPlan: DailyPlanWorkspaceView = {
  active_plan: {
    id: "plan-1",
    plan_date: "2026-11-20",
    version_number: 1,
    is_active: true,
    selected_track_slug: "basic_university",
    available_minutes: 45,
    total_estimated_minutes: 30,
    completed_tasks: 0,
    total_tasks: 2,
    generation_reason_en: "Tailored for basic university track (45 min budget).",
    generation_reason_bn: "৪৫ মিনিটের জন্য সাজানো।",
    tasks: [
      {
        id: "task-1",
        task_order: 1,
        task_type: "lesson",
        skill_slug: "loops",
        target_id: "lsn-1",
        target_slug: "loops-and-boundaries",
        title_en: "Lesson: Loops & Boundaries",
        title_bn: "লেসন: লুপ ও সীমা",
        reason_en: "Targets diagnostic gap in loops.",
        reason_bn: "লুপে ঘাটতি পূরণ করবে।",
        href: "/student/lessons/loops-and-boundaries",
        estimated_minutes: 15,
        status: "pending",
        completed_at: null,
        completion_evidence_ref: null,
      },
      {
        id: "task-2",
        task_order: 2,
        task_type: "retention",
        skill_slug: "variables",
        target_id: "ret-1",
        target_slug: "debug-range-sum-off-by-one",
        title_en: "Retention Check: Variables",
        title_bn: "রিটেনশন যাচাই: ভেরিয়েবল",
        reason_en: "Spaced 24h verification.",
        reason_bn: "২৪ ঘণ্টার রিটেনশন যাচাই।",
        href: "/student/retention",
        estimated_minutes: 15,
        status: "pending",
        completed_at: null,
        completion_evidence_ref: null,
      },
    ],
    created_at: "2026-11-20T08:00:00Z",
    updated_at: "2026-11-20T08:00:00Z",
  },
  history: [
    {
      id: "plan-1",
      plan_date: "2026-11-20",
      version_number: 1,
      is_active: true,
      available_minutes: 45,
      total_estimated_minutes: 30,
      completed_tasks: 0,
      total_tasks: 2,
      created_at: "2026-11-20T08:00:00Z",
    },
  ],
};

const mockHistory: LearningHistoryResponseView = {
  items: [
    {
      id: "submission:1",
      category: "submission",
      title_en: "Judge0 Submit: Debug Inclusive Range Sum",
      title_bn: "Judge0 submit: Debug Inclusive Range Sum",
      summary_en: "Verdict: accepted (5/5 tests passed)",
      summary_bn: "ফলাফল: accepted (5/5 টেস্ট পাস)",
      verdict_or_status: "accepted",
      skill_slug: "loops",
      href: "/student/problems/p-1",
      metadata: {},
      occurred_at: "2026-11-20T08:10:00Z",
    },
  ],
  total: 1,
  limit: 50,
  offset: 0,
  category_counts: { submission: 1 },
};

const mockRetention: RetentionOverviewView = {
  schedules: [
    {
      id: "sched-1",
      skill_slug: "loops",
      skill_title_en: "Loops & Boundaries",
      skill_title_bn: "লুপ ও সীমা",
      problem_id: "prob-1",
      problem_slug: "debug-range-sum-off-by-one",
      problem_title: "Debug: Inclusive Range Sum",
      starter_code: "print(0)",
      source_evidence_type: "phase4_transfer",
      source_verified_at: "2026-11-19T06:00:00Z",
      due_at: "2026-11-20T06:00:00Z",
      interval_hours: 24,
      status: "due",
      is_due_now: true,
      hours_until_eligible: 0,
      last_attempt_at: null,
      created_at: "2026-11-19T06:00:00Z",
    },
  ],
  recent_attempts: [],
  due_count: 1,
  retained_skills_count: 0,
  policy_note_en: "Retention requires >= 24 hours elapsed and full Judge0 pass.",
  policy_note_bn: "২৪ ঘণ্টা পর Judge0 পাস করলে Retained হবে।",
};

describe("Phase 6 Adaptive Growth Components", () => {
  it("renders Learning DNA evidence bands and supports Bangla toggle", () => {
    render(
      <LearningDnaClient accessToken="tok" initialProfile={mockDnaProfile} />,
    );
    expect(screen.getByText(/Code Tracing & Prediction/i)).toBeInTheDocument();
    expect(screen.getByText(/Verified Evidence/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Unobserved/i).length).toBeGreaterThanOrEqual(1);

    fireEvent.click(screen.getByRole("button", { name: "বাংলা" }));
    expect(screen.getByText(/কোড ট্রেসিং ও পূর্বাভাস/i)).toBeInTheDocument();
  });

  it("renders Adaptive Daily Plan with real links and time budget controls", () => {
    render(
      <DailyPlanClient accessToken="tok" initialWorkspace={mockDailyPlan} />,
    );
    expect(screen.getByText(/Lesson: Loops & Boundaries/i)).toBeInTheDocument();
    expect(screen.getByText(/Retention Check: Variables/i)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /Regenerate Plan/i }),
    ).toBeInTheDocument();
  });

  it("renders Persistent Learning History and Retention Verification cleanly", () => {
    render(
      <LearningHistoryClient accessToken="tok" initialHistory={mockHistory} />,
    );
    expect(
      screen.getByText(/Judge0 Submit: Debug Inclusive Range Sum/i),
    ).toBeInTheDocument();

    render(
      <RetentionClient accessToken="tok" initialOverview={mockRetention} />,
    );
    expect(
      screen.getByText(/Prove Long-Term Retention with Delayed Judge0 Checks/i),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /Submit Retention Check to Judge0/i }),
    ).toBeInTheDocument();
  });
});
