import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { DiagnosticWorkspace } from "@/features/learning/diagnostic-workspace";
import { LearningDashboardClient } from "@/features/learning/learning-dashboard-client";
import { LessonViewer } from "@/features/learning/lesson-viewer";
import { TransferVerificationPanel } from "@/features/verification/transfer-verification-panel";
import type {
  DiagnosticSessionView,
  LearningDashboardView,
  LessonDetailView,
  LessonExerciseRunResponse,
} from "@/types/learning";
import type {
  TransferChallengeSummary,
  VerificationAttemptView,
} from "@/types/mentor";
import type { StudentProblemDetail } from "@/types/problems";

const pushMock = vi.fn();
const refreshMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: pushMock,
    refresh: refreshMock,
  }),
}));

const fetchProblemDetailMock = vi.fn<() => Promise<StudentProblemDetail>>();

vi.mock("@/lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api-client")>();
  return {
    ...actual,
    fetchProblemDetail: (...args: unknown[]) =>
      fetchProblemDetailMock(...(args as [])),
  };
});

describe("Phase 4 Adaptive Learning Journey & Multi-Language Transfer", () => {
  it("renders authoritative Continue Learning CTA, Beginner Foundation Strip, and Resume Activity bar on Dashboard", () => {
    const dashboard: LearningDashboardView = {
      language_slug: "python",
      track_status: {
        language_slug: "python",
        selected_track_slug: "absolute_beginner",
        recommended_track_slug: "absolute_beginner",
        recommendation_source: "onboarding_initial",
        recommendation_reason:
          "Starting with structured foundation lessons before the readiness check.",
        diagnostic_completed: false,
        tracks: [
          {
            slug: "absolute_beginner",
            title_en: "Absolute Beginner",
            title_bn: "সম্পূর্ণ নতুন",
            summary_en: "Start from variables & print",
            summary_bn: "ভেরিয়েবল থেকে শুরু",
            target_audience_en: "First-time learners",
            target_audience_bn: "নতুন শিক্ষার্থী",
            display_order: 1,
            recommended_focus_skills: ["variables", "conditions"],
          },
        ],
      },
      lessons_completed: 1,
      lessons_total: 24,
      diagnostic_sessions_completed: 0,
      latest_diagnostic: null,
      skill_graph: {
        language_slug: "python",
        nodes: [],
        recent_transitions: [],
        state_legend: [],
      },
      recommendations: [],
      journey: {
        language_slug: "python",
        onboarding_completed: true,
        active_track_slug: "absolute_beginner",
        journey_stage: "foundation_lessons",
        foundation_lessons_completed: 1,
        foundation_lessons_target: 2,
        readiness_check_unlocked: false,
        diagnostic_completed: false,
        full_diagnostic_completed: false,
        urgent_assignments_count: 0,
        due_retentions_count: 0,
        unlocked_transfers_count: 0,
        primary_action: {
          action_type: "lesson",
          target_id: "lesson-2",
          target_slug: "python-conditions-intro",
          href: "/student/lessons/python-conditions-intro",
          cta_label_en: "Continue Lesson 2",
          cta_label_bn: "লেসন ২ চালিয়ে যাও",
          title_en: "Foundation Lesson 2: Input & Conditions",
          title_bn: "ফাউন্ডেশন লেসন ২: ইনপুট ও শর্ত",
          reason_en:
            "Complete 1 more foundation lesson to unlock your quick 4-domain Readiness Check.",
          reason_bn:
            "আর ১টি ফাউন্ডেশন লেসন সম্পন্ন করলেই শর্ট রেডিনেস চেক খুলে যাবে।",
          evidence_factors: ["foundation_progress:1/2"],
          priority: 4,
          urgency: "recommended",
          eligibility_note_en: "",
          eligibility_note_bn: "",
          estimated_minutes: 10,
        },
        resume_activity: {
          action_type: "lesson_resume",
          target_id: "lesson-1",
          target_slug: "python-variables-intro",
          href: "/student/lessons/python-variables-intro",
          cta_label_en: "Resume",
          cta_label_bn: "চালিয়ে যাও",
          title_en: "Resume: Variables & Output",
          title_bn: "চালিয়ে যাও: ভেরিয়েবল",
          reason_en: "Pick up right where you paused.",
          reason_bn: "যেখানে থেমেছিলে সেখান থেকেই শুরু করো।",
          evidence_factors: ["in_progress"],
          priority: 2,
          urgency: "recommended",
          eligibility_note_en: "",
          eligibility_note_bn: "",
          estimated_minutes: 8,
        },
        secondary_actions: [],
      },
    };

    render(
      <LearningDashboardClient
        accessToken="token-123"
        studentName="Amina"
        initialDashboard={dashboard}
      />,
    );

    const primaryCta = screen.getByTestId("continue-learning-cta");
    expect(primaryCta).toHaveAttribute(
      "href",
      "/student/lessons/python-conditions-intro",
    );
    expect(primaryCta).toHaveTextContent("Continue Lesson 2");

    expect(screen.getByText(/Beginner Foundation Path/i)).toBeInTheDocument();
    expect(screen.getByText(/1\/2 intro lessons/i)).toBeInTheDocument();

    const resumeCta = screen.getByTestId("resume-activity-cta");
    expect(resumeCta).toHaveAttribute(
      "href",
      "/student/lessons/python-variables-intro",
    );
  });

  it("renders both Short Readiness Check and Full 8-Domain Diagnostic options and passes readiness mode", async () => {
    const startedSession: DiagnosticSessionView = {
      id: "11111111-1111-1111-1111-111111111111",
      language_slug: "python",
      assessment_mode: "readiness",
      status: "in_progress",
      explanation_language: "en",
      answered_count: 0,
      remaining_count: 4,
      adaptive_followups_added: 0,
      recommended_track_slug: null,
      recommendation_rationale: null,
      domain_evidence: [],
      started_at: "2026-11-22T10:00:00Z",
      completed_at: null,
      current_question: {
        id: "22222222-2222-2222-2222-222222222222",
        slug: "py-var-1",
        language_slug: "python",
        domain_slug: "variables",
        skill_slug: "variables",
        difficulty: "foundation",
        question_type: "mcq",
        prompt_en: "What is printed by x = 3; print(x + 2)?",
        prompt_bn: "x = 3; print(x + 2) কী প্রিন্ট করবে?",
        code_snippet: "x = 3\nprint(x + 2)",
        options: [
          { id: "a", text_en: "5", text_bn: "5" },
          { id: "b", text_en: "32", text_bn: "32" },
        ],
        starter_code: null,
      },
    };
    const startSpy = vi.fn().mockResolvedValue(startedSession);

    render(
      <DiagnosticWorkspace
        accessToken="token-123"
        initialHistory={[]}
        activeLanguageSlug="python"
        recommendedMode="readiness"
        onStartSession={startSpy}
      />,
    );

    expect(
      screen.getByText(/Short Python 3 Foundation Readiness Check/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Full 8-Domain Python 3 Adaptive Diagnostic/i),
    ).toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("button", { name: /Start Short Readiness Check/i }),
    );

    await waitFor(() => {
      expect(startSpy).toHaveBeenCalledWith("en", "readiness");
    });
    expect(
      screen.getByText(/What is printed by x = 3; print\(x \+ 2\)\?/i),
    ).toBeInTheDocument();
  });

  it("uses dynamic active language (JavaScript) in TransferVerificationPanel instead of hardcoded Python 3", async () => {
    const jsTransferProblem: StudentProblemDetail = {
      problem_id: "33333333-3333-3333-3333-333333333333",
      version_id: "44444444-4444-4444-4444-444444444444",
      version_number: 1,
      slug: "transfer-min-temperature",
      title: "Minimum Temperature Reading",
      statement_md: "Print the minimum value from a list of temperatures.",
      difficulty: "beginner",
      track_slug: "absolute_beginner",
      mode: "coding",
      topics: ["loops"],
      skills: ["loop_boundaries"],
      prerequisites: [],
      learning_objectives: ["Track minimum across array"],
      examples: [],
      time_limit_ms: 2000,
      memory_limit_kb: 262144,
      variants: [
        {
          language_slug: "python",
          display_name: "Python 3",
          monaco_language: "python",
          starter_code: "n = int(input())\nprint(min(map(int, input().split())))",
          buggy_starter_code: null,
          debugging_prompt: null,
        },
        {
          language_slug: "javascript",
          display_name: "JavaScript (Node.js)",
          monaco_language: "javascript",
          starter_code:
            "const fs = require('fs');\nconsole.log(fs.readFileSync(0,'utf8'));",
          buggy_starter_code: null,
          debugging_prompt: null,
        },
      ],
      public_test_cases: [],
      hidden_test_count: 3,
    };
    fetchProblemDetailMock.mockResolvedValueOnce(jsTransferProblem);

    const attemptResult: VerificationAttemptView = {
      id: "55555555-5555-5555-5555-555555555555",
      verification_link_id: "66666666-6666-6666-6666-666666666666",
      transfer_problem_id: "33333333-3333-3333-3333-333333333333",
      transfer_submission_id: "77777777-7777-7777-7777-777777777777",
      hints_used: 0,
      student_explanation: "Iterates through all values and tracks min.",
      outcome: "verified_independent",
      verdict: "accepted",
      passed_tests: 4,
      total_tests: 4,
      summary_message: "Verified independent transfer in JavaScript!",
      created_at: "2026-11-22T10:15:00Z",
    };
    const submitSpy = vi.fn().mockResolvedValue(attemptResult);

    const challenge: TransferChallengeSummary = {
      verification_link_id: "66666666-6666-6666-6666-666666666666",
      source_problem_id: "88888888-8888-8888-8888-888888888888",
      transfer_problem_id: "33333333-3333-3333-3333-333333333333",
      transfer_problem_slug: "transfer-min-temperature",
      transfer_problem_title: "Minimum Temperature Reading",
      skill_focus: "loop_boundaries",
      max_hints_allowed: 0,
      instructions_md: "Solve independently without hints.",
      unlocked: true,
      unlock_reason: "Unlocked after accepted solution.",
      latest_attempt: null,
    };

    render(
      <TransferVerificationPanel
        accessToken="token-123"
        challenge={challenge}
        latestAcceptedSubmissionId="99999999-9999-9999-9999-999999999999"
        activeLanguageSlug="javascript"
        usePlainEditor
        onSubmitAttempt={submitSpy}
      />,
    );

    await waitFor(() => {
      expect(
        screen.getByText(/Minimum Temperature Reading/i),
      ).toBeInTheDocument();
      expect(
        screen.getByText(/Transfer Challenge Editor \(JavaScript/i),
      ).toBeInTheDocument();
    });

    fireEvent.change(
      screen.getByLabelText(/Explain your independent solution/i),
      {
        target: {
          value: "Scans every temperature once and keeps the minimum.",
        },
      },
    );
    fireEvent.click(
      screen.getByRole("button", { name: /Submit Independent Verification/i }),
    );

    await waitFor(() => {
      expect(submitSpy).toHaveBeenCalledWith(
        "66666666-6666-6666-6666-666666666666",
        expect.objectContaining({
          language_slug: "javascript",
        }),
      );
    });
  });

  it("renders 4-step progress strip and Next Recommended Activity CTA after passing a guided lesson exercise", async () => {
    const lesson: LessonDetailView = {
      lesson_id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
      version_id: "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
      slug: "python-variables-intro",
      language_slug: "python",
      skill_slug: "variables",
      display_order: 1,
      title_en: "Variables & First Output",
      title_bn: "ভেরিয়েবল ও প্রথম আউটপুট",
      summary_en: "Store values in variables and print them cleanly.",
      summary_bn: "ভেরিয়েবলে মান সংরক্ষণ ও প্রিন্ট করা।",
      estimated_minutes: 8,
      prerequisite_lesson_slugs: [],
      track_slugs: ["absolute_beginner"],
      prerequisites_met: true,
      progress_status: "in_progress",
      reading_completed: true,
      exercise_passed: false,
      exercise_attempts: 0,
      last_verdict: null,
      content_en_md: "Variables hold named data values.",
      content_bn_md: "ভেরিয়েবল ডেটা সংরক্ষণ করে।",
      learning_objectives: ["Declare variables", "Print output"],
      interactive_examples: [],
      guided_exercise: {
        prompt_en: "Print the sum of 4 and 6.",
        prompt_bn: "৪ এবং ৬ এর যোগফল প্রিন্ট করো।",
        starter_code: "print(4 + 6)\n",
        language_slug: "python",
        test_cases: [
          { name: "Sum 10", input_data: "", expected_output: "10" },
        ],
      },
      last_code: "print(4 + 6)\n",
      completed_at: null,
    };

    const runResult: LessonExerciseRunResponse = {
      lesson_id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
      verdict: "accepted",
      passed_tests: 1,
      total_tests: 1,
      exercise_passed: true,
      progress_status: "completed",
      skill_state_after: "guided",
      execution_provider: "judge0",
      case_results: [
        {
          name: "Sum 10",
          input_data: "",
          expected_output: "10",
          actual_output: "10",
          stderr: "",
          verdict: "accepted",
          passed: true,
        },
      ],
      next_recommended_action: {
        action_type: "lesson",
        target_id: "cccccccc-cccc-cccc-cccc-cccccccccccc",
        target_slug: "python-conditions-intro",
        href: "/student/lessons/python-conditions-intro",
        cta_label_en: "Next: Lesson 2",
        cta_label_bn: "পরবর্তী: লেসন ২",
        title_en: "Lesson 2: Input & Conditions",
        title_bn: "লেসন ২: ইনপুট ও শর্ত",
        reason_en: "Continue to your second foundation lesson.",
        reason_bn: "দ্বিতীয় ফাউন্ডেশন লেসনে যাও।",
        evidence_factors: ["foundation_progress:1/2"],
        priority: 4,
        urgency: "recommended",
        eligibility_note_en: "",
        eligibility_note_bn: "",
        estimated_minutes: 10,
      },
    };
    const runSpy = vi.fn().mockResolvedValue(runResult);

    render(
      <LessonViewer
        accessToken="token-123"
        initialLesson={lesson}
        usePlainEditor
        onRunExercise={runSpy}
      />,
    );

    expect(screen.getByText(/Understand Concept/i)).toBeInTheDocument();
    expect(screen.getByText(/Run Guided Code/i)).toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("button", { name: /Run Guided Exercise/i }),
    );

    await waitFor(() => {
      const nextCta = screen.getByTestId("lesson-next-activity-cta");
      expect(nextCta).toHaveAttribute(
        "href",
        "/student/lessons/python-conditions-intro",
      );
      expect(nextCta).toHaveTextContent("Next: Lesson 2");
    });
  });
});
