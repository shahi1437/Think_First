import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { CodingWorkspace } from "@/features/workspace/coding-workspace";
import { ApiClientError } from "@/lib/api-client";
import type {
  ExecutionAvailability,
  RevisionResponse,
  StudentProblemDetail,
  SubmissionResponse,
} from "@/types/problems";

const debugProblem: StudentProblemDetail = {
  problem_id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
  version_id: "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
  version_number: 1,
  slug: "debug-range-sum-off-by-one",
  title: "Debug: Inclusive Range Sum",
  statement_md: "Fix the inclusive range sum bug.",
  difficulty: "beginner",
  mode: "debugging",
  topics: ["loops"],
  skills: ["loop-boundaries"],
  prerequisites: ["variables"],
  learning_objectives: ["Fix off-by-one range bugs"],
  examples: [{ input: "3 5", output: "12", explanation: "3+4+5=12" }],
  time_limit_ms: 2000,
  memory_limit_kb: 131072,
  variants: [
    {
      language_slug: "python",
      display_name: "Python 3",
      monaco_language: "python",
      starter_code: "for i in range(a, b): pass",
      buggy_starter_code: "for i in range(a, b): pass",
      debugging_prompt: "Trace range(3, 5) before clicking Run.",
    },
  ],
  public_test_cases: [
    {
      id: "cccccccc-cccc-cccc-cccc-cccccccccccc",
      ordinal: 1,
      name: "Small positive range",
      input_data: "3 5",
      expected_output: "12",
    },
  ],
  hidden_test_count: 3,
};

describe("CodingWorkspace", () => {
  it("supports Debugging Mode workflow, real Run/Submit actions, and hidden-test masking", async () => {
    const mockRunResult: SubmissionResponse = {
      id: "dddddddd-dddd-dddd-dddd-dddddddddddd",
      problem_id: debugProblem.problem_id,
      problem_version_id: debugProblem.version_id,
      language_slug: "python",
      submission_kind: "run",
      source_code: "for i in range(a, b): pass",
      prediction_text: "It will print 7 because 5 is excluded.",
      explanation_text: null,
      status: "completed",
      verdict: "wrong_answer",
      passed_tests: 0,
      total_tests: 1,
      runtime_ms: 24,
      memory_kb: 3200,
      execution_evidence: { overall_verdict: "wrong_answer" },
      results: [
        {
          ordinal: 1,
          name: "Small positive range",
          is_hidden: false,
          verdict: "wrong_answer",
          input_data: "3 5",
          expected_output: "12",
          stdout: "7",
          stderr: null,
          compile_output: null,
          runtime_ms: 24,
          memory_kb: 3200,
        },
      ],
      created_at: new Date().toISOString(),
    };

    const mockSubmitResult: SubmissionResponse = {
      ...mockRunResult,
      id: "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
      submission_kind: "submit",
      verdict: "accepted",
      passed_tests: 2,
      total_tests: 2,
      results: [
        {
          ordinal: 1,
          name: "Small positive range",
          is_hidden: false,
          verdict: "accepted",
          input_data: "3 5",
          expected_output: "12",
          stdout: "12",
          stderr: null,
          compile_output: null,
          runtime_ms: 21,
          memory_kb: 3100,
        },
        {
          ordinal: 2,
          name: "Hidden Test #2",
          is_hidden: true,
          verdict: "accepted",
          input_data: null,
          expected_output: null,
          stdout: null,
          stderr: null,
          compile_output: null,
          runtime_ms: 19,
          memory_kb: 3100,
        },
      ],
    };

    const executeSpy = vi
      .fn()
      .mockResolvedValueOnce(mockRunResult)
      .mockResolvedValueOnce(mockSubmitResult);

    const saveSpy = vi.fn().mockResolvedValue({
      id: "ffffffff-ffff-ffff-ffff-ffffffffffff",
      problem_version_id: debugProblem.version_id,
      language_slug: "python",
      source_code: "for i in range(a, b + 1): pass",
      prediction_text: "It will print 7 because 5 is excluded.",
      explanation_text: "Changed range upper bound to b + 1.",
      revision_type: "manual",
      created_at: new Date().toISOString(),
    } satisfies RevisionResponse);

    render(
      <CodingWorkspace
        accessToken="token-123"
        problem={debugProblem}
        initialSubmissions={[]}
        initialRevisions={[]}
        usePlainEditor
        onExecuteCode={executeSpy}
        onSaveRevision={saveSpy}
      />,
    );

    // 7-step debugging workflow visible
    expect(screen.getByText("Predict")).toBeInTheDocument();
    expect(screen.getByText("Investigate")).toBeInTheDocument();
    expect(screen.getByText("Verify")).toBeInTheDocument();

    // Fill prediction & Run Code
    fireEvent.change(screen.getByLabelText(/Output prediction/i), {
      target: { value: "It will print 7 because 5 is excluded." },
    });
    fireEvent.click(screen.getByRole("button", { name: /Run Code/i }));

    await waitFor(() => {
      expect(screen.getByText("0 / 1 tests passed")).toBeInTheDocument();
    });
    expect(executeSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        submission_kind: "run",
        prediction_text: "It will print 7 because 5 is excluded.",
      }),
    );

    // Explain & Fix code & Submit
    fireEvent.change(screen.getByLabelText(/Bug explanation/i), {
      target: { value: "Changed range upper bound to b + 1." },
    });
    fireEvent.change(screen.getByRole("textbox", { name: /^Code editor$/i }), {
      target: { value: "for i in range(a, b + 1): pass" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Submit Code/i }));

    await waitFor(() => {
      expect(screen.getByText("2 / 2 tests passed")).toBeInTheDocument();
    });
    expect(
      screen.getByText(/Hidden test input and expected output remain private/i),
    ).toBeInTheDocument();

    // Manual save revision
    fireEvent.click(screen.getByRole("button", { name: /^Save$/i }));
    await waitFor(() => {
      expect(saveSpy).toHaveBeenCalledWith(
        expect.objectContaining({ revision_type: "manual" }),
      );
    });
  });

  it("renders Queued -> Running -> Completed async execution, compiler/runtime errors, and offline unavailable state", async () => {
    const baseSub: SubmissionResponse = {
      id: "11111111-1111-1111-1111-111111111111",
      problem_id: debugProblem.problem_id,
      problem_version_id: debugProblem.version_id,
      language_slug: "python",
      submission_kind: "run",
      source_code: "print(12)",
      prediction_text: null,
      explanation_text: null,
      status: "queued",
      verdict: "pending",
      passed_tests: 0,
      total_tests: 1,
      runtime_ms: null,
      memory_kb: null,
      execution_provider: "judge0",
      execution_evidence: {},
      results: [],
      created_at: new Date().toISOString(),
    };

    const runningSub: SubmissionResponse = { ...baseSub, status: "running" };
    const completedCompileErr: SubmissionResponse = {
      ...baseSub,
      status: "completed",
      verdict: "compilation_error",
      results: [
        {
          ordinal: 1,
          name: "Small positive range",
          is_hidden: false,
          verdict: "compilation_error",
          input_data: "3 5",
          expected_output: "12",
          stdout: null,
          stderr: "ZeroDivisionError: division by zero",
          compile_output: "main.cpp:3: error: expected ';'",
          runtime_ms: 12,
          memory_kb: 2048,
        },
      ],
    };

    const executeSpy = vi.fn().mockResolvedValueOnce(baseSub);
    const pollSpy = vi
      .fn()
      .mockResolvedValueOnce(runningSub)
      .mockResolvedValueOnce(completedCompileErr);

    const onlineStatus: ExecutionAvailability = {
      mode: "worker_queue",
      available: true,
      worker_online: true,
      active_workers: 1,
      queue_depth: 0,
      last_heartbeat_at: new Date().toISOString(),
      message: "Local Judge0 Code Runner is online.",
    };

    render(
      <CodingWorkspace
        accessToken="token-123"
        problem={debugProblem}
        initialSubmissions={[]}
        initialRevisions={[]}
        initialExecutionStatus={onlineStatus}
        usePlainEditor
        onExecuteCode={executeSpy}
        onPollSubmission={pollSpy}
      />,
    );

    expect(screen.getByText("Runner Online")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Run Code/i }));

    await waitFor(() => {
      expect(screen.getByText("Queued")).toBeInTheDocument();
    });

    await waitFor(
      () => {
        expect(screen.getByText("Completed")).toBeInTheDocument();
      },
      { timeout: 5000 },
    );
    expect(screen.getAllByText("Compilation Error").length).toBeGreaterThan(0);
    expect(
      screen.getByText("main.cpp:3: error: expected ';'"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("ZeroDivisionError: division by zero"),
    ).toBeInTheDocument();

    // Verify offline 503 renders Execution Unavailable without permanent spinner
    executeSpy.mockRejectedValueOnce(
      new ApiClientError(
        "Code execution is currently unavailable because the local Judge0 runner is offline.",
        503,
        "EXECUTION_SERVICE_UNAVAILABLE",
      ),
    );
    fireEvent.click(screen.getByRole("button", { name: /Run Code/i }));
    await waitFor(() => {
      expect(
        screen.getByText(/local Judge0 runner is offline/i),
      ).toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: /Run Code/i })).not.toBeDisabled();
  });
});
