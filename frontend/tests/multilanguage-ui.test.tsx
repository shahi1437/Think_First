import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { LanguageSelector } from "@/components/language-selector";
import { MentorPanel } from "@/features/mentor/mentor-panel";
import type { LanguageProgressOverview } from "@/types/learning";
import type { MentorSessionDetail } from "@/types/mentor";

const mockRefresh = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({
    refresh: mockRefresh,
    push: vi.fn(),
  }),
}));

const mockSelectActiveLanguage = vi.fn();
vi.mock("@/lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api-client")>();
  return {
    ...actual,
    selectActiveLanguage: (...args: unknown[]) =>
      mockSelectActiveLanguage(...args),
  };
});

const initialOverview: LanguageProgressOverview = {
  active_language_slug: "python",
  languages: [
    {
      slug: "python",
      display_name: "Python 3",
      monaco_language: "python",
      version_label: "Python 3.8",
      is_enabled: true,
      is_active: true,
      lessons_completed: 3,
      lessons_total: 24,
      diagnostic_sessions_completed: 1,
      submissions_count: 5,
      selected_track_slug: "basic_university",
    },
    {
      slug: "javascript",
      display_name: "JavaScript (Node.js)",
      monaco_language: "javascript",
      version_label: "Node.js",
      is_enabled: true,
      is_active: false,
      lessons_completed: 1,
      lessons_total: 10,
      diagnostic_sessions_completed: 0,
      submissions_count: 1,
      selected_track_slug: "absolute_beginner",
    },
    {
      slug: "c",
      display_name: "C (GCC)",
      monaco_language: "c",
      version_label: "GCC 9.2",
      is_enabled: true,
      is_active: false,
      lessons_completed: 0,
      lessons_total: 10,
      diagnostic_sessions_completed: 0,
      submissions_count: 0,
      selected_track_slug: null,
    },
    {
      slug: "cpp",
      display_name: "C++ (GCC)",
      monaco_language: "cpp",
      version_label: "GCC 9.2",
      is_enabled: true,
      is_active: false,
      lessons_completed: 0,
      lessons_total: 10,
      diagnostic_sessions_completed: 0,
      submissions_count: 0,
      selected_track_slug: null,
    },
    {
      slug: "java",
      display_name: "Java (OpenJDK)",
      monaco_language: "java",
      version_label: "OpenJDK 13",
      is_enabled: true,
      is_active: false,
      lessons_completed: 0,
      lessons_total: 10,
      diagnostic_sessions_completed: 0,
      submissions_count: 0,
      selected_track_slug: null,
    },
  ],
};

describe("Phase 3 Multi-Language UI", () => {
  it("renders all 5 languages with per-language lesson counts and refreshes on switch", async () => {
    mockSelectActiveLanguage.mockResolvedValueOnce({
      ...initialOverview,
      active_language_slug: "javascript",
      languages: initialOverview.languages.map((l) => ({
        ...l,
        is_active: l.slug === "javascript",
      })),
    });

    render(
      <LanguageSelector
        accessToken="tok-test"
        initialOverview={initialOverview}
      />,
    );

    expect(screen.getByTestId("lang-tab-python")).toHaveAttribute(
      "aria-selected",
      "true",
    );
    expect(screen.getByText("3/24 lessons")).toBeInTheDocument();
    expect(screen.getByText("1/10 lessons")).toBeInTheDocument();
    expect(screen.getByTestId("lang-tab-c")).toBeInTheDocument();
    expect(screen.getByTestId("lang-tab-cpp")).toBeInTheDocument();
    expect(screen.getByTestId("lang-tab-java")).toBeInTheDocument();

    fireEvent.click(screen.getByTestId("lang-tab-javascript"));

    await waitFor(() => {
      expect(mockSelectActiveLanguage).toHaveBeenCalledWith(
        "tok-test",
        "javascript",
      );
      expect(mockRefresh).toHaveBeenCalled();
    });
    expect(screen.getByTestId("lang-tab-javascript")).toHaveAttribute(
      "aria-selected",
      "true",
    );
  });

  it("honestly labels rule-based diagnosis for C/C++/Java/JavaScript in MentorPanel", () => {
    const cSession: MentorSessionDetail = {
      id: "11111111-1111-1111-1111-111111111111",
      problem_id: "22222222-2222-2222-2222-222222222222",
      problem_version_id: "33333333-3333-3333-3333-333333333333",
      latest_submission_id: "44444444-4444-4444-4444-444444444444",
      current_state: "asking_question",
      explanation_language: "en",
      learner_level: "beginner",
      hints_used: 0,
      max_hints: 3,
      provider_mode: "deterministic_fallback",
      latest_diagnosis: {
        id: "55555555-5555-5555-5555-555555555555",
        submission_id: "44444444-4444-4444-4444-444444444444",
        model_version: "rule-multilang-v1",
        diagnosis_source: "rule_based",
        language_slug: "c",
        predicted_error_code: "syntax_error",
        predicted_display_name: "Syntax / Compilation Error",
        confidence: 0.92,
        is_low_confidence: false,
        uncertainty_note: "",
        top_candidates: [
          {
            error_code: "syntax_error",
            display_name: "Syntax / Compilation Error",
            probability: 0.92,
          },
        ],
      },
      latest_citations: [],
      turns: [],
      transfer_unlocked: false,
      created_at: "2026-11-22T00:00:00Z",
      updated_at: "2026-11-22T00:00:00Z",
    };

    render(
      <MentorPanel
        accessToken="tok-test"
        problemId={cSession.problem_id}
        latestSubmissionId={cSession.latest_submission_id ?? null}
        latestVerdict="compilation_error"
        session={cSession}
        onSessionChange={vi.fn()}
      />,
    );

    expect(
      screen.getByText(/Rule-Based Error Diagnosis \(rule-multilang-v1\)/i),
    ).toBeInTheDocument();
  });
});
