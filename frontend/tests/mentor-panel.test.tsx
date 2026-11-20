import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";
import { MentorPanel } from "@/features/mentor/mentor-panel";
import { TransferVerificationPanel } from "@/features/verification/transfer-verification-panel";
import type {
  MentorSessionDetail,
  TransferChallengeSummary,
  VerificationAttemptView,
} from "@/types/mentor";

const mockSession: MentorSessionDetail = {
  id: "11111111-1111-4111-8111-111111111111",
  problem_id: "22222222-2222-4222-8222-222222222222",
  problem_version_id: "33333333-3333-4333-8333-333333333333",
  latest_submission_id: "44444444-4444-4444-8444-444444444444",
  current_state: "asking_question",
  explanation_language: "en",
  learner_level: "beginner",
  hints_used: 0,
  max_hints: 3,
  provider_mode: "deterministic_fallback",
  latest_diagnosis: {
    id: "55555555-5555-4555-8555-555555555555",
    submission_id: "44444444-4444-4444-8444-444444444444",
    model_version: "error_classifier_v1",
    predicted_error_code: "loop_boundary_error",
    predicted_display_name: "Loop Boundary / Off-By-One Error",
    confidence: 0.48,
    is_low_confidence: true,
    uncertainty_note:
      "Model confidence is below 55% — verify the loop endpoint by hand.",
    top_candidates: [
      {
        error_code: "loop_boundary_error",
        display_name: "Loop Boundary / Off-By-One Error",
        probability: 0.48,
      },
      {
        error_code: "logic_error",
        display_name: "General Logic Error",
        probability: 0.31,
      },
      {
        error_code: "initialization_error",
        display_name: "Variable Initialization Error",
        probability: 0.12,
      },
    ],
  },
  latest_citations: [
    {
      chunk_id: "66666666-6666-4666-8666-666666666666",
      document_id: "77777777-7777-4777-8777-777777777777",
      document_slug: "py-loops-and-boundaries",
      source_title: "Loops & Off-By-One Boundary Reasoning",
      source_name: "CodeMentor Python Foundations Guide",
      source_version: "1.0",
      topic: "loops",
      heading: "How Python range(start, stop, step) Works",
      excerpt: "Python range(start, stop) stops one integer before stop.",
      similarity: 0.72,
    },
  ],
  turns: [
    {
      id: "88888888-8888-4888-8888-888888888888",
      turn_index: 1,
      role: "mentor",
      state_after: "asking_question",
      message_text:
        "Trace the first and last value of your loop variable on the failing case.",
      structured_payload: { safety_blocked: false },
      citations: [],
      provider_mode: "deterministic_fallback",
      created_at: "2026-11-20T00:00:00Z",
    },
  ],
  transfer_unlocked: false,
  verification_link_id: "99999999-9999-4999-8999-999999999999",
  created_at: "2026-11-20T00:00:00Z",
  updated_at: "2026-11-20T00:00:00Z",
};

function MentorPanelHarness({
  onStart,
  onTurn,
}: {
  onStart: () => Promise<MentorSessionDetail>;
  onTurn: (
    sessionId: string,
    payload: {
      action: "diagnose" | "respond" | "request_hint";
      requested_hint_level?: 1 | 2 | 3;
      explanation_language?: "en" | "bn";
      student_message?: string;
    },
  ) => Promise<MentorSessionDetail>;
}) {
  const [session, setSession] = useState<MentorSessionDetail | null>(null);
  return (
    <MentorPanel
      accessToken="fake-token"
      problemId={mockSession.problem_id}
      latestSubmissionId={mockSession.latest_submission_id ?? null}
      latestVerdict="wrong_answer"
      session={session}
      onSessionChange={setSession}
      onStartSession={onStart}
      onSendTurn={onTurn}
    />
  );
}

describe("Phase 4 MentorPanel & TransferVerificationPanel", () => {
  it("renders ML diagnosis, low-confidence uncertainty alert, RAG citation, fallback badge, and progressive hint flow", async () => {
    const onStart = vi.fn().mockResolvedValue(mockSession);
    const onTurn = vi.fn().mockResolvedValue({
      ...mockSession,
      hints_used: 1,
      current_state: "giving_hint",
      turns: [
        ...mockSession.turns,
        {
          id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
          turn_index: 2,
          role: "mentor",
          state_after: "giving_hint",
          message_text:
            "Hint (Level 1): Check whether your loop stop bound includes the endpoint.",
          structured_payload: { safety_blocked: false },
          citations: [],
          provider_mode: "deterministic_fallback",
          created_at: "2026-11-20T00:01:00Z",
        },
      ],
    });

    render(<MentorPanelHarness onStart={onStart} onTurn={onTurn} />);

    fireEvent.click(
      screen.getByRole("button", { name: /Start AI Diagnosis/i }),
    );

    const matches = await screen.findAllByText(
      /Loop Boundary \/ Off-By-One Error/i,
    );
    expect(matches.length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/Low-confidence prediction/i)).toBeInTheDocument();
    expect(
      screen.getByText(/Deterministic Socratic Fallback/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Loops & Off-By-One Boundary Reasoning/i),
    ).toBeInTheDocument();

    // Request progressive Hint 1
    fireEvent.click(screen.getByRole("button", { name: "Hint 1" }));
    await waitFor(() => {
      expect(onTurn).toHaveBeenCalledWith(
        mockSession.id,
        expect.objectContaining({
          action: "request_hint",
          requested_hint_level: 1,
        }),
      );
    });
    expect(
      await screen.findByText(/Hint \(Level 1\): Check whether your loop stop/i),
    ).toBeInTheDocument();

    // Switch to Bangla language toggle
    fireEvent.click(screen.getByRole("button", { name: "বাংলা" }));
    expect(
      screen.getByText(/তোমার ধারণা বা ট্রেস এখানে লেখো/i),
    ).toBeInTheDocument();
  });

  it("shows locked state before debugging fix passes and renders factual verified outcome after transfer submit", async () => {
    const lockedChallenge: TransferChallengeSummary = {
      verification_link_id: "99999999-9999-4999-8999-999999999999",
      source_problem_id: "22222222-2222-4222-8222-222222222222",
      transfer_problem_id: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
      transfer_problem_title: "Transfer Challenge: Inclusive Step Range Sum",
      transfer_problem_slug: "transfer-step-range-sum",
      skill_focus: "loops:inclusive_boundary",
      max_hints_allowed: 0,
      instructions_md: "Solve without AI hints.",
      unlocked: false,
      unlock_reason:
        "Locked until your fix passes Submit Code on Judge0.",
      latest_attempt: null,
    };

    const { rerender } = render(
      <TransferVerificationPanel
        accessToken="fake-token"
        challenge={lockedChallenge}
        latestAcceptedSubmissionId={null}
        usePlainEditor
      />,
    );
    expect(
      screen.getByText(/Independent Transfer Verification \(Locked\)/i),
    ).toBeInTheDocument();

    const verifiedAttempt: VerificationAttemptView = {
      id: "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
      verification_link_id: lockedChallenge.verification_link_id,
      transfer_problem_id: lockedChallenge.transfer_problem_id,
      transfer_submission_id: "dddddddd-dddd-4ddd-8ddd-dddddddddddd",
      hints_used: 0,
      student_explanation: "Used end + 1 so the upper bound is included.",
      outcome: "verified_independent",
      verdict: "accepted",
      passed_tests: 4,
      total_tests: 4,
      summary_message:
        "Independent transfer verified: passed 4/4 Judge0 tests with 0 hints.",
      created_at: "2026-11-20T00:05:00Z",
    };

    rerender(
      <TransferVerificationPanel
        accessToken="fake-token"
        challenge={{
          ...lockedChallenge,
          unlocked: true,
          latest_attempt: verifiedAttempt,
        }}
        latestAcceptedSubmissionId="eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee"
        usePlainEditor
      />,
    );

    expect(
      screen.getByText(/Zero-Hint Independent Check \(0 hints\)/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Verified Independent Understanding/i),
    ).toBeInTheDocument();
    expect(screen.getByText(/4 \/ 4 Judge0 tests/i)).toBeInTheDocument();
  });
});
