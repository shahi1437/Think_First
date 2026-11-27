import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { DebuggingTimelinePanel } from "@/features/growth/debugging-timeline-panel";
import { PersonalizedLearningHub } from "@/features/learning/personalized-learning-hub";
import { ProblemBankClient } from "@/features/problems/problem-bank-client";
import { TeacherClassDetailClient } from "@/features/teacher/teacher-class-detail-client";
import { computeLineDiff } from "@/lib/code-diff";
import type {
  TeacherCourseDetailView,
  TeacherStudentPerformanceView,
} from "@/types/classroom";
import type {
  DebuggingTimelineResponseView,
  VerifiedLearningProgressView,
} from "@/types/growth";
import type { LearningDashboardView } from "@/types/learning";
import type { StudentProblemListItem } from "@/types/problems";

const mockFetchProblems = vi.fn();
const mockFetchTeacherStudentPerformance = vi.fn();

vi.mock("@/lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api-client")>();
  return {
    ...actual,
    fetchProblems: (...args: unknown[]) => mockFetchProblems(...args),
    fetchTeacherStudentPerformance: (...args: unknown[]) =>
      mockFetchTeacherStudentPerformance(...args),
  };
});

afterEach(() => {
  vi.clearAllMocks();
});

function renderWithQueryClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>,
  );
}

describe("Phase 12 Remaining Features Completion", () => {
  it("computes deterministic LCS line-by-line diffs cleanly", () => {
    const before = "n = int(input())\nprint(sum(range(1, n)))";
    const after = "n = int(input())\nprint(sum(range(1, n + 1)))\n# done";
    const diff = computeLineDiff(before, after);

    expect(diff.unchangedCount).toBe(1);
    expect(diff.removedCount).toBe(1);
    expect(diff.addedCount).toBe(2);
    expect(diff.lines.some((l) => l.kind === "removed" && l.text.includes("range(1, n)"))).toBe(true);
    expect(diff.lines.some((l) => l.kind === "added" && l.text.includes("range(1, n + 1)"))).toBe(true);
  });

  it("renders PersonalizedLearningHub answering all 5 core student questions in EN and BN", () => {
    const dashboard: LearningDashboardView = {
      language_slug: "python",
      track_status: {
        selected_track_slug: "basic_university",
        recommended_track_slug: "basic_university",
        recommendation_source: "diagnostic_evidence",
        recommendation_reason: "Solid syntax, developing loops",
        diagnostic_completed: true,
        tracks: [],
      },
      lessons_completed: 3,
      lessons_total: 8,
      diagnostic_sessions_completed: 1,
      latest_diagnostic: null,
      skill_graph: {
        nodes: [
          {
            slug: "variables_types",
            title_en: "Variables & Types",
            title_bn: "ভ্যারিয়েবল ও টাইপ",
            description_en: "Variables",
            description_bn: "ভ্যারিয়েবল",
            domain_slug: "variables",
            tier: 1,
            display_order: 1,
            prerequisites: [],
            state: "independent",
            evidence_count: 3,
            uncertainty_note: "",
          },
          {
            slug: "loop_boundaries",
            title_en: "Loop Boundaries",
            title_bn: "লুপের সীমানা",
            description_en: "Loops",
            description_bn: "লুপ",
            domain_slug: "loop_boundaries",
            tier: 2,
            display_order: 2,
            prerequisites: ["variables_types"],
            state: "guided",
            evidence_count: 2,
            uncertainty_note: "",
          },
        ],
        recent_transitions: [],
        state_legend: [],
      },
      recommendations: [
        {
          recommendation_type: "problem",
          target_id: "p1",
          target_slug: "sum-range",
          title: "Sum of Range 1..N",
          priority: 1,
          reason_en: "Targets developing Loop Boundaries skill",
          reason_bn: "লুপের সীমানা শক্তিশালী করতে সহায়ক",
          evidence_factors: ["loop_boundaries"],
          href: "/student/problems/sum-range",
        },
      ],
      journey: {
        language_slug: "python",
        onboarding_completed: true,
        active_track_slug: "basic_university",
        journey_stage: "guided_practice",
        foundation_lessons_completed: 2,
        foundation_lessons_target: 2,
        readiness_check_unlocked: true,
        diagnostic_completed: true,
        full_diagnostic_completed: true,
        urgent_assignments_count: 0,
        due_retentions_count: 1,
        unlocked_transfers_count: 0,
        primary_action: {
          action_type: "lesson",
          target_id: "l4",
          target_slug: "for-loops",
          href: "/student/lessons/for-loops",
          cta_label_en: "Start Lesson",
          cta_label_bn: "লেসন শুরু করো",
          title_en: "Master Loop Ranges",
          title_bn: "লুপ রেঞ্জ আয়ত্ত করো",
          reason_en: "Fixes off-by-one loop errors",
          reason_bn: "লুপের অফ-বাই-ওয়ান ত্রুটি ঠিক করে",
          evidence_factors: ["loop_boundaries"],
          priority: 1,
          urgency: "recommended",
          eligibility_note_en: "",
          eligibility_note_bn: "",
          estimated_minutes: 15,
        },
        resume_activity: null,
        secondary_actions: [],
      },
    };

    const verifiedProgress: VerifiedLearningProgressView = {
      problems_attempted: 4,
      problems_solved_verified: 3,
      total_submissions: 7,
      accepted_submissions: 4,
      languages_used: [],
      concepts_mastered_verified: ["variables_types"],
      concepts_in_progress: ["loop_boundaries"],
      assignments_completed_verified: 1,
      assignments_total: 1,
      average_published_grade_pct: 90,
      transfer_verifications_passed: 1,
      retention_checks_passed: 0,
      consistency_active_days_14d: 5,
      daily_activity_14d: [],
      improvement_trend: "improving",
      early_acceptance_rate_pct: 50,
      recent_acceptance_rate_pct: 100,
      estimated_lessons_completed: 3,
      estimated_diagnostic_sessions: 1,
      estimated_guided_skills_count: 1,
      methodology_note: "Verified from sandbox runs.",
    };

    const { rerender } = render(
      <PersonalizedLearningHub
        dashboard={dashboard}
        verifiedProgress={verifiedProgress}
        retentionSummary={{ dueCount: 1, scheduledCount: 2, retainedSkillsCount: 0 }}
        dailyPlanSummary={{ completedTasks: 1, totalTasks: 3, availableMinutes: 30, versionNumber: 1 }}
        language="en"
      />,
    );

    expect(screen.getByTestId("personalized-learning-hub")).toBeInTheDocument();
    expect(screen.getByTestId("q-next")).toHaveTextContent("Master Loop Ranges");
    expect(screen.getByTestId("q-weak")).toHaveTextContent("Loop Boundaries");
    expect(screen.getByTestId("q-problem")).toHaveTextContent("Sum of Range 1..N");
    expect(screen.getByTestId("q-progress")).toHaveTextContent("3 solved · 1 verified skill(s)");
    expect(screen.getByTestId("q-repeat")).toHaveTextContent("1 spaced retention check(s) due");

    rerender(
      <PersonalizedLearningHub
        dashboard={dashboard}
        verifiedProgress={verifiedProgress}
        retentionSummary={{ dueCount: 1, scheduledCount: 2, retainedSkillsCount: 0 }}
        dailyPlanSummary={{ completedTasks: 1, totalTasks: 3, availableMinutes: 30, versionNumber: 1 }}
        language="bn"
      />,
    );

    expect(screen.getByTestId("q-next")).toHaveTextContent("লুপ রেঞ্জ আয়ত্ত করো");
    expect(screen.getByTestId("q-weak")).toHaveTextContent("লুপের সীমানা");
  });

  it("supports Adaptive Problem Bank topic, completion status, and weak-concept recommendation filters", async () => {
    const initialProblems: StudentProblemListItem[] = [
      {
        problem_id: "prob-1",
        version_id: "ver-1",
        slug: "sum-range",
        title: "Sum of Range 1..N",
        difficulty: "beginner",
        track_slug: "basic_university",
        mode: "coding",
        topics: ["loops", "math"],
        skills: ["loop_boundaries"],
        supported_languages: ["python", "cpp"],
        published_at: "2026-11-01T00:00:00Z",
        completion_status: "attempted",
        attempts_count: 2,
        is_recommended: true,
        recommendation_reason: "Matches developing skill: loops",
      },
      {
        problem_id: "prob-2",
        version_id: "ver-2",
        slug: "array-max",
        title: "Maximum in Array",
        difficulty: "basic",
        track_slug: "basic_university",
        mode: "coding",
        topics: ["arrays"],
        skills: ["array_traversal"],
        supported_languages: ["python"],
        published_at: "2026-11-01T00:00:00Z",
        completion_status: "solved",
        attempts_count: 1,
        is_recommended: false,
        recommendation_reason: null,
      },
    ];

    mockFetchProblems.mockResolvedValue({
      items: [initialProblems[0]],
      total: 1,
    });

    renderWithQueryClient(
      <ProblemBankClient
        accessToken="tok-student"
        initialProblems={initialProblems}
        initialTotal={2}
        activeLanguageSlug="python"
      />,
    );

    expect(screen.getByText("Sum of Range 1..N")).toBeInTheDocument();
    expect(screen.getByText("Matches developing skill: loops")).toBeInTheDocument();
    expect(screen.getAllByText("Solved").length).toBeGreaterThanOrEqual(2);

    fireEvent.click(screen.getByTestId("problem-recommended-toggle"));
    await waitFor(() => {
      expect(mockFetchProblems).toHaveBeenCalledWith(
        "tok-student",
        expect.objectContaining({ recommended_only: true }),
      );
    });
  });

  it("replays a debugging journey step-by-step with interactive Next/Previous and inline diff", () => {
    const timeline: DebuggingTimelineResponseView = {
      total_journeys: 1,
      solved_journeys: 1,
      limit: 10,
      offset: 0,
      journeys: [
        {
          problem_id: "prob-1",
          problem_slug: "sum-range",
          problem_title: "Sum of Range 1..N",
          language_slug: "python",
          href: "/student/problems/sum-range",
          outcome_status: "solved",
          attempts_count: 2,
          hints_used: 1,
          diagnoses_count: 1,
          started_at: "2026-11-27T10:00:00Z",
          latest_event_at: "2026-11-27T10:10:00Z",
          steps: [
            {
              id: "s1",
              step_kind: "initial_attempt",
              title: "Initial Attempt",
              detail: "Wrong answer on test 2",
              code_excerpt: "n = int(input())\nprint(sum(range(1, n)))",
              verdict_or_status: "wrong_answer",
              metadata: {},
              occurred_at: "2026-11-27T10:00:00Z",
            },
            {
              id: "s2",
              step_kind: "ai_hint",
              title: "Progressive AI Hint #1",
              detail: "Does range(1, n) include n?",
              code_excerpt: null,
              verdict_or_status: "hint_1",
              metadata: {},
              occurred_at: "2026-11-27T10:04:00Z",
            },
            {
              id: "s3",
              step_kind: "successful_execution",
              title: "Accepted Sandbox Run",
              detail: "3/3 tests passed",
              code_excerpt: "n = int(input())\nprint(sum(range(1, n + 1)))",
              verdict_or_status: "accepted",
              metadata: {},
              occurred_at: "2026-11-27T10:08:00Z",
            },
          ],
        },
      ],
    };

    render(<DebuggingTimelinePanel timeline={timeline} language="en" />);

    fireEvent.click(screen.getByTestId("debugging-replay-toggle"));
    const stage = screen.getByTestId("debugging-replay-stage");
    expect(stage).toBeInTheDocument();
    expect(stage).toHaveTextContent("Step 1 of 3");

    fireEvent.click(screen.getByRole("button", { name: /Next/i }));
    expect(stage).toHaveTextContent("Step 2 of 3");
    expect(stage).toHaveTextContent("Progressive AI Hint #1");

    fireEvent.click(screen.getByRole("button", { name: /Next/i }));
    expect(stage).toHaveTextContent("Step 3 of 3");
    expect(screen.getByTestId("debugging-replay-diff")).toBeInTheDocument();
  });

  it("loads and renders individual student performance drill-down on TeacherClassDetailClient", async () => {
    const initialDetail: TeacherCourseDetailView = {
      course: {
        id: "course-1",
        teacher_id: "teacher-1",
        teacher_name: "Prof. Rahman",
        code: "CS101",
        title: "Intro to Programming",
        term: "Fall 2026",
        description: "Foundations",
        enrollment_policy: "open_with_code",
        allow_student_leave: true,
        status: "active",
        active_students_count: 1,
        pending_students_count: 0,
        assignments_count: 1,
        created_at: "2026-11-01T00:00:00Z",
        updated_at: "2026-11-01T00:00:00Z",
      },
      invitations: [],
      roster: [
        {
          membership_id: "mem-1",
          student_id: "stu-1",
          full_name: "Amina Rahman",
          email: "amina@example.com",
          status: "active",
          joined_at: "2026-11-02T00:00:00Z",
          submissions_count: 3,
          accepted_attempts_count: 2,
          hints_used_total: 1,
        },
      ],
      assignments: [],
      analytics: {
        active_students: 1,
        total_attempts: 3,
        accepted_attempts: 2,
        verdict_breakdown: [],
        common_misconceptions: [],
        skill_gaps: [],
        total_hints_used: 1,
        verified_independent_transfers: 1,
        students_needing_support: [],
      },
    };

    const perfPayload: TeacherStudentPerformanceView = {
      course_id: "course-1",
      course_code: "CS101",
      course_title: "Intro to Programming",
      student_id: "stu-1",
      full_name: "Amina Rahman",
      email: "amina@example.com",
      membership_status: "active",
      total_assignment_attempts: 3,
      accepted_assignment_attempts: 2,
      hints_used_total: 1,
      verified_transfers_count: 1,
      verified_skills: ["variables_types"],
      developing_skills: ["loop_boundaries"],
      common_misconceptions: [{ error_code: "off_by_one_loop", occurrences: 2 }],
      assignments: [
        {
          assignment_id: "asg-1",
          title: "Loops Lab 1",
          due_at: null,
          workflow_status: "graded",
          attempts_used: 2,
          latest_verdict: "accepted",
          marks_awarded: 92,
          max_marks: 100,
          grade_status: "published",
          submitted_at: "2026-11-20T10:00:00Z",
        },
      ],
    };

    mockFetchTeacherStudentPerformance.mockResolvedValue(perfPayload);

    render(
      <TeacherClassDetailClient
        accessToken="tok-teacher"
        initialDetail={initialDetail}
      />,
    );

    fireEvent.click(
      screen.getByRole("button", { name: "Inspect performance for Amina Rahman" }),
    );

    const panel = await screen.findByTestId("teacher-student-drilldown");
    expect(panel).toBeInTheDocument();
    expect(mockFetchTeacherStudentPerformance).toHaveBeenCalledWith(
      "tok-teacher",
      "course-1",
      "stu-1",
    );
    expect(panel).toHaveTextContent("Amina Rahman — Student Drill-Down");
    expect(panel).toHaveTextContent("variables_types");
    expect(panel).toHaveTextContent("loop_boundaries");
    expect(panel).toHaveTextContent("off_by_one_loop (2)");
    expect(panel).toHaveTextContent("92 / 100 (published)");

    fireEvent.click(
      screen.getByRole("button", { name: "Close student performance panel" }),
    );
    expect(
      screen.queryByTestId("teacher-student-drilldown"),
    ).not.toBeInTheDocument();
  });
});
