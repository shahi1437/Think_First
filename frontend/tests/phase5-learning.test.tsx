import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { DiagnosticWorkspace } from "@/features/learning/diagnostic-workspace";
import { LessonViewer } from "@/features/learning/lesson-viewer";
import { SkillGraphPanel } from "@/features/learning/skill-graph-panel";
import type {
  DiagnosticSessionView,
  LessonDetailView,
  LessonExerciseRunResponse,
  SkillGraphView,
} from "@/types/learning";

const mockGraph: SkillGraphView = {
  nodes: [
    {
      slug: "programming_basics",
      title_en: "Programming Basics",
      title_bn: "প্রোগ্রামিংয়ের মূল ধারণা",
      description_en: "Sequential execution and print().",
      description_bn: "ধাপে ধাপে কোড চলা।",
      domain_slug: "variables",
      tier: 1,
      display_order: 1,
      prerequisites: [],
      state: "guided",
      evidence_count: 2,
      uncertainty_note: "Guided exercise passed; independent transfer pending.",
      last_evidence_type: "lesson_guided_judge0",
      last_evidence_at: "2026-11-20T00:00:00Z",
    },
    {
      slug: "variables",
      title_en: "Variables & Data Types",
      title_bn: "ভেরিয়েবল ও ডেটা টাইপ",
      description_en: "Safe initialization and types.",
      description_bn: "সঠিক ইনিশিয়ালাইজেশন।",
      domain_slug: "variables",
      tier: 1,
      display_order: 2,
      prerequisites: ["programming_basics"],
      state: "unobserved",
      evidence_count: 0,
      uncertainty_note: "Not yet observed: complete diagnostic or guided exercise.",
      last_evidence_type: null,
      last_evidence_at: null,
    },
  ],
  recent_transitions: [
    {
      id: "11111111-1111-4111-8111-111111111111",
      skill_slug: "programming_basics",
      from_state: "introduced",
      to_state: "guided",
      evidence_source: "lesson_guided_judge0",
      reason: "Passed guided Judge0 exercise (1/1).",
      created_at: "2026-11-20T00:00:00Z",
    },
  ],
  state_legend: [],
};

const mockLesson: LessonDetailView = {
  lesson_id: "22222222-2222-4222-8222-222222222222",
  version_id: "33333333-3333-4333-8333-333333333333",
  slug: "intro-to-programming",
  skill_slug: "programming_basics",
  display_order: 1,
  title_en: "Introduction to Programming & Python Execution",
  title_bn: "প্রোগ্রামিং পরিচিতি ও Python কীভাবে কোড চালায়",
  summary_en: "Understand sequential execution.",
  summary_bn: "ধাপে ধাপে প্রোগ্রাম চলা।",
  content_en_md: "## What Is a Program?\nOrdered instructions.",
  content_bn_md: "## প্রোগ্রাম কী?\nধারাবাহিক নির্দেশনা।",
  learning_objectives: ["Trace top-to-bottom Python execution"],
  prerequisite_lesson_slugs: [],
  track_slugs: ["absolute_beginner"],
  estimated_minutes: 10,
  progress_status: "not_started",
  reading_completed: false,
  exercise_passed: false,
  exercise_attempts: 0,
  prerequisites_met: true,
  interactive_examples: [
    {
      title: "Sequential print",
      code: 'print("Hello")',
      input_data: "",
      expected_output: "Hello",
      explanation_en: "Prints Hello.",
      explanation_bn: "Hello প্রিন্ট করে।",
    },
  ],
  guided_exercise: {
    prompt_en: "Print CodeMentor and 42.",
    prompt_bn: "CodeMentor এবং 42 প্রিন্ট করো।",
    language_slug: "python",
    starter_code: 'print("CodeMentor")\n',
    test_cases: [
      { name: "Exact output", input_data: "", expected_output: "CodeMentor\n42" },
    ],
  },
};

describe("Phase 5 Learning UI Components", () => {
  it("renders SkillGraphPanel with prerequisite nodes, uncertainty notes, and honest transitions", () => {
    render(<SkillGraphPanel graph={mockGraph} language="en" />);
    expect(screen.getByText(/Prerequisite-Aware Skill Graph/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Programming Basics/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/Guided exercise passed; independent transfer pending/i)).toBeInTheDocument();
    expect(screen.getByText(/Passed guided Judge0 exercise \(1\/1\)/i)).toBeInTheDocument();
  });

  it("supports bilingual toggle and Judge0 guided exercise submission in LessonViewer", async () => {
    const mockRunRes: LessonExerciseRunResponse = {
      lesson_id: mockLesson.lesson_id,
      verdict: "accepted",
      passed_tests: 1,
      total_tests: 1,
      exercise_passed: true,
      progress_status: "completed",
      skill_state_after: "guided",
      case_results: [
        {
          name: "Exact output",
          input_data: "",
          expected_output: "CodeMentor\n42",
          actual_output: "CodeMentor\n42",
          verdict: "accepted",
          passed: true,
        },
      ],
    };
    const onRun = vi.fn().mockResolvedValue(mockRunRes);

    render(
      <LessonViewer
        accessToken="fake"
        initialLesson={mockLesson}
        usePlainEditor
        onRunExercise={onRun}
      />,
    );

    // Switch to Bangla and verify Bangla title renders
    fireEvent.click(screen.getByRole("button", { name: "বাংলা" }));
    expect(screen.getByText(/প্রোগ্রামিং পরিচিতি/i)).toBeInTheDocument();

    // Run guided exercise -> asserts Judge0 verified completion
    fireEvent.click(screen.getByRole("button", { name: /Run Guided Exercise/i }));
    await waitFor(() => {
      expect(onRun).toHaveBeenCalledTimes(1);
    });
    expect(
      await screen.findByText(/Lesson Completed! Guided Exercise Passed/i),
    ).toBeInTheDocument();
  });

  it("runs adaptive diagnostic flow and renders evidence-based track placement", async () => {
    const activeSession: DiagnosticSessionView = {
      id: "44444444-4444-4444-8444-444444444444",
      status: "in_progress",
      explanation_language: "en",
      answered_count: 0,
      remaining_count: 1,
      adaptive_followups_added: 0,
      current_question: {
        id: "55555555-5555-4555-8555-555555555555",
        slug: "diag-var-core-1",
        domain_slug: "variables",
        skill_slug: "variables",
        difficulty: "core",
        question_type: "mcq",
        prompt_en: "Why does best = 0 fail on negative numbers?",
        prompt_bn: "কেন best = 0 ব্যর্থ হয়?",
        options: [
          { id: "a", text_en: "0 > negative numbers", text_bn: "0 বড়" },
          { id: "b", text_en: "Syntax error", text_bn: "সিনট্যাক্স এরর" },
        ],
        language_slug: "python",
      },
      domain_evidence: [],
      started_at: "2026-11-20T00:00:00Z",
    };

    const completedSession: DiagnosticSessionView = {
      ...activeSession,
      status: "completed",
      answered_count: 1,
      remaining_count: 0,
      current_question: null,
      recommended_track_slug: "basic_university",
      recommendation_rationale:
        "Recommended Basic University track based on observed diagnostic evidence.",
      domain_evidence: [
        {
          domain_slug: "variables",
          observed_attempts: 1,
          observed_correct: 1,
          execution_verified: false,
          evidence_status: "demonstrated_basic",
          note_en: "Answered 1/1 checks correctly.",
          note_bn: "১/১ সঠিক।",
        },
      ],
    };

    const onStart = vi.fn().mockResolvedValue(activeSession);
    const onSubmit = vi.fn().mockResolvedValue(completedSession);

    render(
      <DiagnosticWorkspace
        accessToken="fake"
        initialHistory={[]}
        usePlainEditor
        onStartSession={onStart}
        onSubmitAnswer={onSubmit}
      />,
    );

    fireEvent.click(
      screen.getByRole("button", { name: /Start Adaptive Diagnostic/i }),
    );
    expect(
      await screen.findByText(/Why does best = 0 fail on negative numbers/i),
    ).toBeInTheDocument();

    fireEvent.click(screen.getByLabelText("0 > negative numbers"));
    fireEvent.click(screen.getByRole("button", { name: /Submit Answer/i }));

    expect(
      await screen.findByText(/Diagnostic Completed — Evidence-Based Track Placement/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Recommended Track:\s*basic university/i),
    ).toBeInTheDocument();
  });
});
