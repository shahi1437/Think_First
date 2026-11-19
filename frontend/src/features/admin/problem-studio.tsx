"use client";

import {
  AlertCircle,
  CheckCircle2,
  FlaskConical,
  Loader2,
  Plus,
  RefreshCw,
  Rocket,
  ShieldCheck,
  Trash2,
} from "lucide-react";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import {
  approveAdminProblem,
  createAdminProblem,
  fetchAdminProblemDetail,
  fetchAdminProblems,
  publishAdminProblem,
  syncAdminLanguages,
  updateAdminProblem,
  validateAdminProblem,
} from "@/lib/api-client";
import type {
  AdminProblemDetail,
  AdminProblemListItem,
  AdminValidationReport,
  Difficulty,
  ProblemMode,
  ProblemStatus,
} from "@/types/problems";

interface EditableTestCase {
  ordinal: number;
  name: string;
  input_data: string;
  expected_output: string;
  is_hidden: boolean;
}

interface AdminProblemStudioProps {
  accessToken: string;
  initialProblems: AdminProblemListItem[];
}

const statusVariant: Record<
  ProblemStatus,
  "neutral" | "amber" | "indigo" | "teal" | "emerald"
> = {
  draft: "neutral",
  validated: "teal",
  in_review: "amber",
  approved: "indigo",
  published: "emerald",
  archived: "neutral",
};

const defaultTestCases: EditableTestCase[] = [
  {
    ordinal: 1,
    name: "Sample public test",
    input_data: "5",
    expected_output: "10",
    is_hidden: false,
  },
  {
    ordinal: 2,
    name: "Hidden edge case",
    input_data: "-3",
    expected_output: "-6",
    is_hidden: true,
  },
];

export function AdminProblemStudio({
  accessToken,
  initialProblems,
}: AdminProblemStudioProps) {
  const [problems, setProblems] =
    useState<AdminProblemListItem[]>(initialProblems);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedDetail, setSelectedDetail] =
    useState<AdminProblemDetail | null>(null);

  // Authoring form state
  const [slug, setSlug] = useState("");
  const [title, setTitle] = useState("");
  const [statementMd, setStatementMd] = useState("");
  const [difficulty, setDifficulty] = useState<Difficulty>("beginner");
  const [mode, setMode] = useState<ProblemMode>("coding");
  const [topicsCsv, setTopicsCsv] = useState("loops, conditionals");
  const [starterCode, setStarterCode] = useState(
    'n = int(input())\n# Write your solution\n',
  );
  const [buggyStarterCode, setBuggyStarterCode] = useState("");
  const [debuggingPrompt, setDebuggingPrompt] = useState("");
  const [referenceSolution, setReferenceSolution] = useState(
    "n = int(input())\nprint(n * 2)\n",
  );
  const [expectedBugSummary, setExpectedBugSummary] = useState("");
  const [testCases, setTestCases] =
    useState<EditableTestCase[]>(defaultTestCases);

  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [validationReport, setValidationReport] =
    useState<AdminValidationReport | null>(null);

  async function refreshList() {
    const res = await fetchAdminProblems(accessToken);
    setProblems(res.items);
  }

  function startNewDraft() {
    setSelectedId(null);
    setSelectedDetail(null);
    setValidationReport(null);
    setFeedback(null);
    setErrorMsg(null);
    setSlug("");
    setTitle("");
    setStatementMd("");
    setDifficulty("beginner");
    setMode("coding");
    setTopicsCsv("loops, conditionals");
    setStarterCode("n = int(input())\n# Write your solution\n");
    setBuggyStarterCode("");
    setDebuggingPrompt("");
    setReferenceSolution("n = int(input())\nprint(n * 2)\n");
    setExpectedBugSummary("");
    setTestCases(defaultTestCases);
  }

  async function selectProblem(problemId: string) {
    setBusyAction("load");
    setErrorMsg(null);
    setFeedback(null);
    setValidationReport(null);
    try {
      const detail = await fetchAdminProblemDetail(accessToken, problemId);
      setSelectedId(detail.problem_id);
      setSelectedDetail(detail);
      setSlug(detail.slug);
      setTitle(detail.title);
      setStatementMd(detail.statement_md);
      setDifficulty(detail.difficulty);
      setMode(detail.mode);
      setTopicsCsv(detail.topics.join(", "));
      const py = detail.variants[0];
      if (py) {
        setStarterCode(py.starter_code);
        setBuggyStarterCode(py.buggy_starter_code ?? "");
        setDebuggingPrompt(py.debugging_prompt ?? "");
        setReferenceSolution(py.reference_solution);
        setExpectedBugSummary(py.expected_bug_summary ?? "");
      }
      setTestCases(
        detail.test_cases.map((tc) => ({
          ordinal: tc.ordinal,
          name: tc.name,
          input_data: tc.input_data,
          expected_output: tc.expected_output,
          is_hidden: tc.is_hidden,
        })),
      );
    } catch (err) {
      setErrorMsg(
        err instanceof Error ? err.message : "Failed to load problem.",
      );
    } finally {
      setBusyAction(null);
    }
  }

  function buildPayload(includeSlug: boolean) {
    const topics = topicsCsv
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    const variant: Record<string, unknown> = {
      language_slug: "python",
      starter_code: starterCode,
      reference_solution: referenceSolution,
    };
    if (mode === "debugging") {
      variant.buggy_starter_code = buggyStarterCode || starterCode;
      variant.debugging_prompt = debuggingPrompt || null;
      variant.expected_bug_summary = expectedBugSummary || null;
    }

    const base: Record<string, unknown> = {
      title: title.trim(),
      statement_md: statementMd.trim(),
      difficulty,
      mode,
      topics,
      skills: topics,
      prerequisites: [],
      learning_objectives: [],
      examples: testCases
        .filter((tc) => !tc.is_hidden)
        .slice(0, 2)
        .map((tc) => ({
          input: tc.input_data,
          output: tc.expected_output,
          explanation: tc.name,
        })),
      variants: [variant],
      test_cases: testCases.map((tc, idx) => ({
        ordinal: idx + 1,
        name: tc.name.trim() || `Test #${idx + 1}`,
        input_data: tc.input_data,
        expected_output: tc.expected_output,
        is_hidden: tc.is_hidden,
        weight: 1,
      })),
    };
    if (includeSlug) {
      base.slug = slug.trim().toLowerCase();
    }
    return base;
  }

  async function handleSaveDraft() {
    setBusyAction("save");
    setErrorMsg(null);
    setFeedback(null);
    try {
      const saved = selectedId
        ? await updateAdminProblem(accessToken, selectedId, buildPayload(false))
        : await createAdminProblem(accessToken, buildPayload(true));
      setSelectedId(saved.problem_id);
      setSelectedDetail(saved);
      setFeedback(
        `Saved version v${saved.version_number} (${saved.status}). Run Judge0 validation before publishing.`,
      );
      await refreshList();
    } catch (err) {
      setErrorMsg(
        err instanceof Error ? err.message : "Failed to save problem draft.",
      );
    } finally {
      setBusyAction(null);
    }
  }

  async function handleValidate() {
    if (!selectedId) return;
    setBusyAction("validate");
    setErrorMsg(null);
    setFeedback(null);
    try {
      const report = await validateAdminProblem(accessToken, selectedId);
      setValidationReport(report);
      const reloaded = await fetchAdminProblemDetail(accessToken, selectedId);
      setSelectedDetail(reloaded);
      await refreshList();
      setFeedback(
        report.passed
          ? "Automated Judge0 validation PASSED. Problem is ready for approval and publication."
          : "Automated Judge0 validation FAILED. Inspect variant errors below.",
      );
    } catch (err) {
      setErrorMsg(
        err instanceof Error ? err.message : "Judge0 validation failed.",
      );
    } finally {
      setBusyAction(null);
    }
  }

  async function handleApprove() {
    if (!selectedId) return;
    setBusyAction("approve");
    setErrorMsg(null);
    try {
      const updated = await approveAdminProblem(
        accessToken,
        selectedId,
        "Approved in Admin Problem Studio.",
      );
      setSelectedDetail(updated);
      await refreshList();
      setFeedback("Problem approved by reviewer.");
    } catch (err) {
      setErrorMsg(
        err instanceof Error ? err.message : "Approval action failed.",
      );
    } finally {
      setBusyAction(null);
    }
  }

  async function handlePublish() {
    if (!selectedId) return;
    setBusyAction("publish");
    setErrorMsg(null);
    try {
      const updated = await publishAdminProblem(
        accessToken,
        selectedId,
        "Published to Student Problem Bank.",
      );
      setSelectedDetail(updated);
      await refreshList();
      setFeedback(
        `Version v${updated.version_number} published live to the Student Problem Bank.`,
      );
    } catch (err) {
      setErrorMsg(
        err instanceof Error ? err.message : "Publish action failed.",
      );
    } finally {
      setBusyAction(null);
    }
  }

  async function handleSyncLanguages() {
    setBusyAction("sync");
    setErrorMsg(null);
    try {
      const res = await syncAdminLanguages(accessToken);
      setFeedback(
        `Synced ${res.synced_count} language runtimes from live Judge0 registry.`,
      );
    } catch (err) {
      setErrorMsg(
        err instanceof Error
          ? err.message
          : "Unable to sync languages from Judge0.",
      );
    } finally {
      setBusyAction(null);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-indigo-700">
            Admin Problem Studio
          </p>
          <h1 className="mt-1 text-2xl font-bold text-slate-900">
            Author, Validate &amp; Publish Problems
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            Workflow: Draft → Automated Judge0 Validation → Human Review →
            Publish. Untested problems cannot be published.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            disabled={busyAction !== null}
            onClick={() => {
              void handleSyncLanguages();
            }}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-xs font-semibold text-slate-800 hover:bg-slate-50 disabled:opacity-60"
          >
            <RefreshCw
              className={`h-3.5 w-3.5 ${busyAction === "sync" ? "animate-spin" : ""}`}
            />
            <span>Sync Judge0 Languages</span>
          </button>

          <button
            type="button"
            onClick={startNewDraft}
            className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3.5 py-2 text-xs font-semibold text-white hover:bg-indigo-700"
          >
            <Plus className="h-3.5 w-3.5" />
            <span>New Problem</span>
          </button>
        </div>
      </div>

      {errorMsg ? (
        <div
          role="alert"
          className="flex items-start gap-2.5 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-900"
        >
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-rose-600" />
          <span>{errorMsg}</span>
        </div>
      ) : null}

      {feedback ? (
        <div
          role="status"
          className="flex items-start gap-2.5 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-950"
        >
          <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-700" />
          <span>{feedback}</span>
        </div>
      ) : null}

      <div className="grid gap-6 lg:grid-cols-12">
        {/* Left Catalog List */}
        <aside className="space-y-3 lg:col-span-4">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Problem Catalog ({problems.length})
          </h2>
          <div className="space-y-2">
            {problems.map((item) => (
              <button
                key={item.problem_id}
                type="button"
                onClick={() => {
                  void selectProblem(item.problem_id);
                }}
                className={`w-full rounded-xl border p-3.5 text-left transition ${
                  selectedId === item.problem_id
                    ? "border-indigo-500 bg-indigo-50/50"
                    : "border-slate-200 bg-white hover:border-slate-300"
                }`}
              >
                <div className="flex items-center justify-between gap-2">
                  <Badge variant={statusVariant[item.status]}>
                    <span className="capitalize">{item.status}</span>
                  </Badge>
                  <span className="font-mono text-[11px] text-slate-400">
                    v{item.latest_version_number}
                  </span>
                </div>
                <p className="mt-2 text-sm font-semibold text-slate-900">
                  {item.title}
                </p>
                <p className="mt-0.5 font-mono text-xs text-slate-500">
                  {item.slug} · {item.mode}
                </p>
              </button>
            ))}
          </div>
        </aside>

        {/* Right Editor & Governance Panel */}
        <section className="space-y-5 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm lg:col-span-8">
          {/* Governance Action Bar */}
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-4">
            <div className="flex items-center gap-2">
              <h2 className="text-base font-semibold text-slate-900">
                {selectedDetail
                  ? `Editing v${selectedDetail.version_number}`
                  : "Create New Problem Draft"}
              </h2>
              {selectedDetail ? (
                <Badge variant={statusVariant[selectedDetail.status]}>
                  <span className="capitalize">{selectedDetail.status}</span>
                </Badge>
              ) : null}
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                disabled={busyAction !== null}
                onClick={() => {
                  void handleSaveDraft();
                }}
                className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-800 hover:bg-slate-50 disabled:opacity-50"
              >
                {busyAction === "save" ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : null}
                <span>Save Draft</span>
              </button>

              <button
                type="button"
                disabled={!selectedId || busyAction !== null}
                onClick={() => {
                  void handleValidate();
                }}
                className="inline-flex items-center gap-1.5 rounded-lg bg-teal-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-teal-700 disabled:opacity-50"
              >
                {busyAction === "validate" ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <FlaskConical className="h-3.5 w-3.5" />
                )}
                <span>Validate via Judge0</span>
              </button>

              <button
                type="button"
                disabled={
                  !selectedDetail ||
                  selectedDetail.status !== "validated" ||
                  busyAction !== null
                }
                onClick={() => {
                  void handleApprove();
                }}
                className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
              >
                <ShieldCheck className="h-3.5 w-3.5" />
                <span>Approve</span>
              </button>

              <button
                type="button"
                disabled={
                  !selectedDetail ||
                  !["validated", "approved"].includes(selectedDetail.status) ||
                  busyAction !== null
                }
                onClick={() => {
                  void handlePublish();
                }}
                className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-emerald-700 disabled:opacity-50"
              >
                <Rocket className="h-3.5 w-3.5" />
                <span>Publish</span>
              </button>
            </div>
          </div>

          {validationReport ? (
            <div
              className={`rounded-xl border p-4 text-xs ${
                validationReport.passed
                  ? "border-emerald-200 bg-emerald-50 text-emerald-950"
                  : "border-rose-200 bg-rose-50 text-rose-950"
              }`}
            >
              <p className="font-semibold">
                Judge0 Validation Report:{" "}
                {validationReport.passed ? "PASSED" : "FAILED"}
              </p>
              {validationReport.variant_results.map((vr) => (
                <div key={vr.language_slug} className="mt-2 space-y-1">
                  <p>
                    <strong className="uppercase">{vr.language_slug}</strong>:
                    Reference passed {vr.reference_passed}/{vr.total_tests}{" "}
                    tests
                    {vr.buggy_starter_tested
                      ? ` · Buggy starter failed as expected: ${vr.buggy_starter_failed_as_expected ? "Yes" : "No"}`
                      : ""}
                  </p>
                  {vr.errors.map((errLine) => (
                    <p key={errLine} className="text-rose-700">
                      • {errLine}
                    </p>
                  ))}
                </div>
              ))}
            </div>
          ) : null}

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="block text-xs font-medium text-slate-700">
                Slug (lowercase kebab-case)
              </label>
              <input
                type="text"
                value={slug}
                disabled={Boolean(selectedId)}
                onChange={(e) => setSlug(e.target.value)}
                placeholder="sum-of-even-numbers"
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm disabled:bg-slate-100"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-700">
                Title
              </label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Problem title"
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-700">
                Mode
              </label>
              <select
                value={mode}
                onChange={(e) => setMode(e.target.value as ProblemMode)}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              >
                <option value="coding">Normal Coding</option>
                <option value="debugging">Debugging Mode</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-700">
                Difficulty
              </label>
              <select
                value={difficulty}
                onChange={(e) => setDifficulty(e.target.value as Difficulty)}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              >
                <option value="beginner">Beginner</option>
                <option value="basic">Basic</option>
                <option value="intermediate">Intermediate</option>
                <option value="advanced">Advanced</option>
              </select>
            </div>

            <div className="sm:col-span-2">
              <label className="block text-xs font-medium text-slate-700">
                Topics (comma-separated)
              </label>
              <input
                type="text"
                value={topicsCsv}
                onChange={(e) => setTopicsCsv(e.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
            </div>

            <div className="sm:col-span-2">
              <label className="block text-xs font-medium text-slate-700">
                Problem Statement (Markdown)
              </label>
              <textarea
                rows={4}
                value={statementMd}
                onChange={(e) => setStatementMd(e.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
            </div>

            <div className="sm:col-span-2">
              <label className="block text-xs font-medium text-slate-700">
                Python Starter Code (visible to students)
              </label>
              <textarea
                rows={4}
                value={starterCode}
                onChange={(e) => setStarterCode(e.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-300 bg-slate-50 px-3 py-2 font-mono text-xs"
              />
            </div>

            {mode === "debugging" ? (
              <>
                <div className="sm:col-span-2">
                  <label className="block text-xs font-medium text-indigo-800">
                    Validated Buggy Starter Code (must fail at least 1 test)
                  </label>
                  <textarea
                    rows={4}
                    value={buggyStarterCode}
                    onChange={(e) => setBuggyStarterCode(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-indigo-200 bg-indigo-50/40 px-3 py-2 font-mono text-xs"
                  />
                </div>
                <div className="sm:col-span-2">
                  <label className="block text-xs font-medium text-indigo-800">
                    Student Debugging Prompt
                  </label>
                  <input
                    type="text"
                    value={debuggingPrompt}
                    onChange={(e) => setDebuggingPrompt(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-indigo-200 px-3 py-2 text-sm"
                  />
                </div>
              </>
            ) : null}

            <div className="sm:col-span-2">
              <label className="block text-xs font-medium text-rose-800">
                Private Reference Solution (Admin-only, never exposed to
                students)
              </label>
              <textarea
                rows={4}
                value={referenceSolution}
                onChange={(e) => setReferenceSolution(e.target.value)}
                className="mt-1 w-full rounded-lg border border-rose-200 bg-rose-50/30 px-3 py-2 font-mono text-xs"
              />
            </div>
          </div>

          {/* Test Cases Editor */}
          <div className="space-y-3 border-t border-slate-100 pt-4">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-600">
                Public &amp; Hidden Test Cases ({testCases.length})
              </h3>
              <button
                type="button"
                onClick={() =>
                  setTestCases((prev) => [
                    ...prev,
                    {
                      ordinal: prev.length + 1,
                      name: `Test #${prev.length + 1}`,
                      input_data: "",
                      expected_output: "",
                      is_hidden: true,
                    },
                  ])
                }
                className="inline-flex items-center gap-1 rounded-md border border-slate-300 px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50"
              >
                <Plus className="h-3 w-3" />
                <span>Add Test Case</span>
              </button>
            </div>

            <div className="space-y-3">
              {testCases.map((tc, index) => (
                <div
                  key={index}
                  className="rounded-xl border border-slate-200 bg-slate-50/60 p-3 text-xs"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <input
                      type="text"
                      value={tc.name}
                      onChange={(e) =>
                        setTestCases((prev) =>
                          prev.map((item, i) =>
                            i === index
                              ? { ...item, name: e.target.value }
                              : item,
                          ),
                        )
                      }
                      className="rounded border border-slate-300 bg-white px-2.5 py-1 font-medium text-slate-800"
                    />
                    <div className="flex items-center gap-3">
                      <label className="inline-flex items-center gap-1.5 text-slate-700">
                        <input
                          type="checkbox"
                          checked={tc.is_hidden}
                          onChange={(e) =>
                            setTestCases((prev) =>
                              prev.map((item, i) =>
                                i === index
                                  ? { ...item, is_hidden: e.target.checked }
                                  : item,
                              ),
                            )
                          }
                        />
                        <span>Hidden test</span>
                      </label>
                      {testCases.length > 2 ? (
                        <button
                          type="button"
                          onClick={() =>
                            setTestCases((prev) =>
                              prev.filter((_, i) => i !== index),
                            )
                          }
                          aria-label={`Remove ${tc.name}`}
                          className="text-rose-600 hover:text-rose-800"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      ) : null}
                    </div>
                  </div>
                  <div className="mt-2 grid gap-2 sm:grid-cols-2">
                    <div>
                      <span className="text-[11px] text-slate-500">stdin</span>
                      <textarea
                        rows={2}
                        value={tc.input_data}
                        onChange={(e) =>
                          setTestCases((prev) =>
                            prev.map((item, i) =>
                              i === index
                                ? { ...item, input_data: e.target.value }
                                : item,
                            ),
                          )
                        }
                        className="mt-1 w-full rounded border border-slate-300 bg-white p-2 font-mono"
                      />
                    </div>
                    <div>
                      <span className="text-[11px] text-slate-500">
                        expected stdout
                      </span>
                      <textarea
                        rows={2}
                        value={tc.expected_output}
                        onChange={(e) =>
                          setTestCases((prev) =>
                            prev.map((item, i) =>
                              i === index
                                ? { ...item, expected_output: e.target.value }
                                : item,
                            ),
                          )
                        }
                        className="mt-1 w-full rounded border border-slate-300 bg-white p-2 font-mono"
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
