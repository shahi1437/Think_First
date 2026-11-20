import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { AdminDashboardClient } from "@/features/admin/admin-dashboard-client";
import { AdminProblemStudio } from "@/features/admin/problem-studio";
import type { AdminDashboardOverview } from "@/types/admin";
import type { AdminProblemListItem } from "@/types/problems";

vi.mock("@/lib/api-client", async () => {
  const actual = await vi.importActual("@/lib/api-client");
  return {
    ...actual,
    fetchAdminProblemDetail: vi.fn(),
    validateAdminProblem: vi.fn(),
  };
});

describe("Phase 8 Admin Dashboard & Advanced Studio", () => {
  it("renders real DB overview metrics, review queue, track coverage, and audit trail", () => {
    const overview: AdminDashboardOverview = {
      problems_total: 18,
      problems_published: 16,
      problems_draft: 1,
      problems_validated: 1,
      problems_in_review: 1,
      problems_approved: 0,
      problems_archived: 0,
      problems_intermediate_or_advanced: 12,
      lessons_published: 24,
      lessons_total: 24,
      diagnostic_published: 26,
      diagnostic_stretch_count: 8,
      knowledge_approved: 16,
      knowledge_total: 16,
      skill_nodes_count: 18,
      review_queue: [
        {
          problem_id: "00000000-0000-0000-0000-000000000111",
          version_id: "00000000-0000-0000-0000-000000000112",
          slug: "adv-graph-check",
          title: "Advanced BFS Hop Count",
          difficulty: "advanced",
          mode: "coding",
          status: "in_review",
          version_number: 2,
          updated_at: "2026-11-20T12:00:00Z",
        },
      ],
      track_coverage: [
        {
          track_slug: "intermediate",
          title_en: "Intermediate",
          title_bn: "ইন্টারমিডিয়েট ট্র্যাক",
          lesson_count: 8,
          problem_count: 6,
          focus_skills: ["searching_sorting", "dictionaries_strings"],
        },
      ],
      recent_audit_logs: [
        {
          id: "00000000-0000-0000-0000-000000000201",
          actor_user_id: "00000000-0000-0000-0000-000000000001",
          actor_email: "admin@thinkfirst.test",
          actor_name: "Lead Admin",
          action: "problem.published",
          target_type: "problem_version",
          target_id: "v1",
          metadata: {},
          request_id: "req-1",
          created_at: "2026-11-20T12:00:00Z",
        },
      ],
    };

    render(<AdminDashboardClient adminName="Lead Admin" overview={overview} />);

    expect(
      screen.getByText(/Curriculum & Assessment Control Center/i),
    ).toBeInTheDocument();
    expect(screen.getByText(/12 Intermediate & Advanced/i)).toBeInTheDocument();
    expect(screen.getByText(/Advanced BFS Hop Count/i)).toBeInTheDocument();
    expect(screen.getByText(/problem.published/i)).toBeInTheDocument();
    expect(screen.getByText(/8 lessons/i)).toBeInTheDocument();
  });

  it("renders full governance controls and filters in Admin Problem Studio", () => {
    const items: AdminProblemListItem[] = [
      {
        problem_id: "00000000-0000-0000-0000-000000000301",
        slug: "inter-two-sum-pairs",
        latest_version_id: "00000000-0000-0000-0000-000000000302",
        latest_version_number: 1,
        title: "Two-Sum Pair Count in O(n)",
        difficulty: "intermediate",
        track_slug: "intermediate",
        mode: "coding",
        status: "published",
        topics: ["dictionaries"],
        is_published: true,
        is_archived: false,
        updated_at: "2026-11-20T12:00:00Z",
      },
    ];

    render(
      <AdminProblemStudio accessToken="token-123" initialProblems={items} />,
    );

    expect(
      screen.getByText(/Author, Validate, Review & Publish Problems/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Two-Sum Pair Count in O\(n\)/i),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /Submit Review/i }),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Reject/i })).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /^Publish$/i }),
    ).toBeInTheDocument();
  });
});
