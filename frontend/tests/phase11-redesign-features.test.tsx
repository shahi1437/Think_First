import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { NotificationCenter } from "@/components/notification-center";
import { DebuggingTimelinePanel } from "@/features/growth/debugging-timeline-panel";
import { VerifiedProgressPanel } from "@/features/growth/verified-progress-panel";
import type {
  DebuggingTimelineResponseView,
  VerifiedLearningProgressView,
} from "@/types/growth";

const mockFetchNotifications = vi.fn();
const mockMarkRead = vi.fn();
const mockMarkAllRead = vi.fn();

vi.mock("@/lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api-client")>();
  return {
    ...actual,
    fetchNotifications: (...args: unknown[]) => mockFetchNotifications(...args),
    markNotificationRead: (...args: unknown[]) => mockMarkRead(...args),
    markAllNotificationsRead: (...args: unknown[]) => mockMarkAllRead(...args),
  };
});

afterEach(() => {
  vi.clearAllMocks();
});

describe("Phase 11 Redesign Features", () => {
  it("renders NotificationCenter unread badge, opens panel, marks one read, and marks all read", async () => {
    const sampleItems = [
      {
        id: "notif-1",
        recipient_role: "student" as const,
        category: "announcement" as const,
        title: "CS101: Lab 2 Reminder",
        body: "Submit before Friday 18:00 UTC.",
        href: "/student/classes",
        is_read: false,
        read_at: null,
        metadata: {},
        created_at: new Date().toISOString(),
      },
      {
        id: "notif-2",
        recipient_role: "student" as const,
        category: "grading" as const,
        title: "Grade published: Loops Lab 1",
        body: "Awarded 92 / 100.",
        href: "/student/assignments/a1",
        is_read: false,
        read_at: null,
        metadata: {},
        created_at: new Date().toISOString(),
      },
    ];

    mockFetchNotifications.mockResolvedValue({
      items: sampleItems,
      total: 2,
      unread_count: 2,
      limit: 25,
      offset: 0,
    });
    mockMarkRead.mockResolvedValue({
      ...sampleItems[0],
      is_read: true,
      read_at: new Date().toISOString(),
    });
    mockMarkAllRead.mockResolvedValue({
      marked_count: 1,
      unread_count: 0,
    });

    render(<NotificationCenter accessToken="tok-123" activeRole="student" />);

    const badge = await screen.findByTestId("notification-unread-badge");
    expect(badge).toHaveTextContent("2");

    fireEvent.click(screen.getByTestId("notification-bell-button"));
    expect(
      await screen.findByTestId("notification-center-panel"),
    ).toBeInTheDocument();
    expect(screen.getByText("CS101: Lab 2 Reminder")).toBeInTheDocument();
    expect(screen.getByText("Grade published: Loops Lab 1")).toBeInTheDocument();

    const markButtons = screen.getAllByRole("button", { name: "Mark read" });
    fireEvent.click(markButtons[0]);
    await waitFor(() => {
      expect(mockMarkRead).toHaveBeenCalledWith("tok-123", "notif-1");
    });

    fireEvent.click(screen.getByTestId("notification-mark-all-read"));
    await waitFor(() => {
      expect(mockMarkAllRead).toHaveBeenCalledWith("tok-123", "student");
    });
    expect(
      screen.queryByTestId("notification-unread-badge"),
    ).not.toBeInTheDocument();
  });

  it("renders VerifiedProgressPanel separating verified achievements from estimated progress", () => {
    const progress: VerifiedLearningProgressView = {
      problems_attempted: 3,
      problems_solved_verified: 2,
      total_submissions: 5,
      accepted_submissions: 3,
      languages_used: [
        {
          language_slug: "python",
          problems_attempted: 2,
          problems_solved_verified: 2,
          lessons_completed: 4,
          total_submissions: 4,
        },
        {
          language_slug: "cpp",
          problems_attempted: 1,
          problems_solved_verified: 0,
          lessons_completed: 0,
          total_submissions: 1,
        },
      ],
      concepts_mastered_verified: ["loops", "conditionals"],
      concepts_in_progress: ["recursion"],
      assignments_completed_verified: 1,
      assignments_total: 2,
      average_published_grade_pct: 92.5,
      transfer_verifications_passed: 1,
      retention_checks_passed: 1,
      consistency_active_days_14d: 4,
      daily_activity_14d: Array.from({ length: 14 }, (_, idx) => ({
        day: `2026-11-${String(idx + 1).padStart(2, "0")}`,
        submissions_count: idx === 13 ? 2 : 0,
        accepted_count: idx === 13 ? 1 : 0,
        lessons_completed: idx === 12 ? 1 : 0,
      })),
      improvement_trend: "improving",
      early_acceptance_rate_pct: 33.3,
      recent_acceptance_rate_pct: 100.0,
      estimated_lessons_completed: 4,
      estimated_diagnostic_sessions: 1,
      estimated_guided_skills_count: 1,
      methodology_note:
        "Verified achievements require passing isolated sandbox execution or published instructor grades.",
    };

    render(<VerifiedProgressPanel progress={progress} language="en" />);

    expect(screen.getByTestId("verified-progress-panel")).toBeInTheDocument();
    expect(
      screen.getByTestId("verified-achievements-group"),
    ).toBeInTheDocument();
    expect(screen.getByTestId("estimated-progress-group")).toBeInTheDocument();
    expect(screen.getByText("Improving")).toBeInTheDocument();
    expect(screen.getByText("Avg grade: 92.5%")).toBeInTheDocument();
    expect(screen.getByText("loops")).toBeInTheDocument();
    expect(screen.getByText("recursion")).toBeInTheDocument();
    expect(screen.getByText("Python 3")).toBeInTheDocument();
    expect(screen.getByText("C++")).toBeInTheDocument();
  });

  it("renders DebuggingTimelinePanel with full real chronological steps and empty state", () => {
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
          outcome_status: "verified_transfer",
          attempts_count: 2,
          hints_used: 1,
          diagnoses_count: 1,
          started_at: "2026-11-27T10:00:00Z",
          latest_event_at: "2026-11-27T10:15:00Z",
          steps: [
            {
              id: "s1",
              step_kind: "problem_started",
              title: "Problem started: Sum of Range 1..N",
              detail: "Language: python · 2 runs",
              code_excerpt: "def solve(n): pass",
              verdict_or_status: "started",
              metadata: {},
              occurred_at: "2026-11-27T10:00:00Z",
            },
            {
              id: "s2",
              step_kind: "error_diagnosed",
              title: "ML error diagnosis: loop_boundary_error",
              detail: "Confidence 87%",
              code_excerpt: null,
              verdict_or_status: "loop_boundary_error",
              metadata: {},
              occurred_at: "2026-11-27T10:02:00Z",
            },
            {
              id: "s3",
              step_kind: "ai_hint",
              title: "Progressive AI Hint #1",
              detail: "Check whether range(1, n) includes n.",
              code_excerpt: null,
              verdict_or_status: "hint_1",
              metadata: {},
              occurred_at: "2026-11-27T10:04:00Z",
            },
            {
              id: "s4",
              step_kind: "successful_execution",
              title: "Accepted sandbox execution",
              detail: "3/3 tests passed",
              code_excerpt: "print(sum(range(1, n + 1)))",
              verdict_or_status: "accepted",
              metadata: {},
              occurred_at: "2026-11-27T10:08:00Z",
            },
          ],
        },
      ],
    };

    const { rerender } = render(
      <DebuggingTimelinePanel timeline={timeline} language="en" />,
    );

    expect(screen.getByTestId("ai-debugging-timeline")).toBeInTheDocument();
    expect(screen.getByText("Sum of Range 1..N")).toBeInTheDocument();
    expect(screen.getByText("Verified Transfer")).toBeInTheDocument();
    expect(screen.getAllByTestId("debugging-timeline-step")).toHaveLength(4);
    expect(
      screen.getByText("print(sum(range(1, n + 1)))"),
    ).toBeInTheDocument();

    rerender(
      <DebuggingTimelinePanel
        timeline={{
          journeys: [],
          total_journeys: 0,
          solved_journeys: 0,
          limit: 10,
          offset: 0,
        }}
      />,
    );
    expect(
      screen.getByText("No debugging journeys recorded yet"),
    ).toBeInTheDocument();
  });
});
