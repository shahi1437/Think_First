"use client";

import {
  AlertCircle,
  Brain,
  CheckCircle2,
  Database,
  FlaskConical,
  Loader2,
  Plus,
} from "lucide-react";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import {
  createAdminDiagnostic,
  fetchAdminDiagnostics,
  updateAdminDiagnosticStatus,
  updateAdminKnowledgeStatus,
  upsertAdminKnowledgeDoc,
  validateAdminDiagnostic,
} from "@/lib/api-client";
import type {
  AdminDiagnosticQuestionDetail,
  KnowledgeDocumentItem,
} from "@/types/admin";

interface DiagnosticsKnowledgeClientProps {
  accessToken: string;
  initialQuestions: AdminDiagnosticQuestionDetail[];
  initialKnowledgeDocs: KnowledgeDocumentItem[];
}

const DOMAINS = [
  "variables",
  "syntax_runtime_debugging",
  "conditions",
  "loop_boundaries",
  "arrays_lists",
  "indexing",
  "functions",
  "mixed_logic",
] as const;

export function DiagnosticsKnowledgeClient({
  accessToken,
  initialQuestions,
  initialKnowledgeDocs,
}: DiagnosticsKnowledgeClientProps) {
  const [questions, setQuestions] =
    useState<AdminDiagnosticQuestionDetail[]>(initialQuestions);
  const [docs, setDocs] =
    useState<KnowledgeDocumentItem[]>(initialKnowledgeDocs);

  // Diagnostic creation state
  const [qSlug, setQSlug] = useState("");
  const [domainSlug, setDomainSlug] = useState<string>("mixed_logic");
  const [skillSlug, setSkillSlug] = useState("data_structures_graphs");
  const [qDiff, setQDiff] = useState<"foundation" | "core" | "stretch">(
    "stretch",
  );
  const [qType, setQType] = useState<"mcq" | "code_execution">("mcq");
  const [promptEn, setPromptEn] = useState("");
  const [promptBn, setPromptBn] = useState("");
  const [correctOpt, setCorrectOpt] = useState("b");
  const [explanationEn, setExplanationEn] = useState("");
  const [explanationBn, setExplanationBn] = useState("");
  const [starterCode, setStarterCode] = useState(
    "n = int(input())\nprint(n)\n",
  );
  const [testIn, setTestIn] = useState("5");
  const [testOut, setTestOut] = useState("5");

  // Knowledge Doc state
  const [kSlug, setKSlug] = useState("");
  const [kTitle, setKTitle] = useState("");
  const [kTopic, setKTopic] = useState("algorithms");
  const [kErrorsCsv, setKErrorsCsv] = useState("logic_error");
  const [kSource, setKSource] = useState("CodeMentor Admin Curriculum Guide");
  const [kContentMd, setKContentMd] = useState("");

  const [busyKey, setBusyKey] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  async function handleCreateDiagnostic(publish: boolean) {
    setBusyKey("create-diag");
    setErrorMsg(null);
    setFeedback(null);
    try {
      await createAdminDiagnostic(accessToken, {
        slug: qSlug.trim().toLowerCase(),
        domain_slug: domainSlug,
        skill_slug: skillSlug.trim(),
        difficulty: qDiff,
        question_type: qType,
        prompt_en: promptEn.trim(),
        prompt_bn: promptBn.trim() || promptEn.trim(),
        options:
          qType === "mcq"
            ? [
                { id: "a", text_en: "Option A", text_bn: "বিকল্প ক" },
                { id: "b", text_en: "Option B", text_bn: "বিকল্প খ" },
                { id: "c", text_en: "Option C", text_bn: "বিকল্প গ" },
              ]
            : [],
        starter_code: qType === "code_execution" ? starterCode : null,
        correct_option_id: qType === "mcq" ? correctOpt : null,
        explanation_en: explanationEn.trim(),
        explanation_bn: explanationBn.trim() || explanationEn.trim(),
        evaluation_tests:
          qType === "code_execution"
            ? [{ name: "Primary Check", input_data: testIn, expected_output: testOut }]
            : [],
        publish,
      });
      const reloaded = await fetchAdminDiagnostics(accessToken);
      setQuestions(reloaded);
      setQSlug("");
      setPromptEn("");
      setPromptBn("");
      setExplanationEn("");
      setExplanationBn("");
      setFeedback("Created diagnostic item with Admin-only private answer key.");
    } catch (err) {
      setErrorMsg(
        err instanceof Error ? err.message : "Failed to create diagnostic item.",
      );
    } finally {
      setBusyKey(null);
    }
  }

  async function handleValidateDiag(qId: string) {
    setBusyKey(`val-diag-${qId}`);
    setErrorMsg(null);
    setFeedback(null);
    try {
      const res = await validateAdminDiagnostic(accessToken, qId);
      setFeedback(
        res.passed
          ? `Diagnostic Judge0/Schema validation PASSED (${res.passed_tests}/${res.total_tests}).`
          : `Diagnostic validation FAILED: ${res.errors.join("; ")}`,
      );
    } catch (err) {
      setErrorMsg(
        err instanceof Error ? err.message : "Failed to validate diagnostic.",
      );
    } finally {
      setBusyKey(null);
    }
  }

  async function handleDiagStatus(
    qId: string,
    status: "published" | "archived" | "draft",
  ) {
    setBusyKey(`diag-status-${qId}`);
    setErrorMsg(null);
    setFeedback(null);
    try {
      const updated = await updateAdminDiagnosticStatus(
        accessToken,
        qId,
        status,
      );
      setQuestions((prev) => prev.map((q) => (q.id === qId ? updated : q)));
      setFeedback(`Diagnostic '${updated.slug}' updated to ${updated.status}.`);
    } catch (err) {
      setErrorMsg(
        err instanceof Error ? err.message : "Failed to update diagnostic status.",
      );
    } finally {
      setBusyKey(null);
    }
  }

  async function handleUpsertKnowledge(statusVal: "draft" | "approved") {
    setBusyKey("upsert-rag");
    setErrorMsg(null);
    setFeedback(null);
    try {
      const saved = await upsertAdminKnowledgeDoc(accessToken, {
        slug: kSlug.trim().toLowerCase(),
        title: kTitle.trim(),
        language_slug: "python",
        topic: kTopic.trim(),
        error_codes: kErrorsCsv
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
        source_name: kSource.trim(),
        source_version: "2.0",
        content_md: kContentMd.trim(),
        status: statusVal,
      });
      setDocs((prev) => {
        const without = prev.filter((d) => d.id !== saved.id);
        return [saved, ...without];
      });
      setKSlug("");
      setKTitle("");
      setKContentMd("");
      setFeedback(
        `Saved RAG document '${saved.slug}' (${saved.chunk_count} pgvector chunks, status: ${saved.status}).`,
      );
    } catch (err) {
      setErrorMsg(
        err instanceof Error ? err.message : "Failed to save RAG document.",
      );
    } finally {
      setBusyKey(null);
    }
  }

  async function handleKnowledgeStatus(
    docId: string,
    status: "approved" | "archived" | "draft",
  ) {
    setBusyKey(`rag-status-${docId}`);
    setErrorMsg(null);
    try {
      const updated = await updateAdminKnowledgeStatus(
        accessToken,
        docId,
        status,
      );
      setDocs((prev) => prev.map((d) => (d.id === docId ? updated : d)));
      setFeedback(`RAG doc '${updated.slug}' set to ${updated.status}.`);
    } catch (err) {
      setErrorMsg(
        err instanceof Error ? err.message : "Failed to update doc status.",
      );
    } finally {
      setBusyKey(null);
    }
  }

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-wider text-indigo-700">
          Assessment &amp; RAG Knowledge Governance
        </p>
        <h1 className="mt-1 text-2xl font-bold text-slate-900">
          Diagnostic Bank &amp; Approved Mentor Knowledge Base
        </h1>
        <p className="mt-1 text-sm text-slate-600">
          Private diagnostic answer keys &amp; hidden execution checks stay
          strictly isolated under Admin RLS. Only approved RAG documents are
          retrievable by the Socratic Mentor.
        </p>
      </section>

      {errorMsg ? (
        <div
          role="alert"
          className="flex items-center gap-2 rounded-xl border border-rose-200 bg-rose-50 p-4 text-xs text-rose-900"
        >
          <AlertCircle className="h-4 w-4 shrink-0 text-rose-600" />
          <span>{errorMsg}</span>
        </div>
      ) : null}

      {feedback ? (
        <div
          role="status"
          className="flex items-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-xs text-emerald-950"
        >
          <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-700" />
          <span>{feedback}</span>
        </div>
      ) : null}

      {/* Diagnostic Question Authoring */}
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="flex items-center gap-2 text-base font-bold text-slate-900">
          <Brain className="h-4 w-4 text-indigo-600" />
          <span>Diagnostic Question Bank ({questions.length})</span>
        </h2>

        <div className="mt-4 grid gap-3 rounded-xl border border-slate-200 bg-slate-50 p-4 text-xs sm:grid-cols-4">
          <input
            type="text"
            value={qSlug}
            onChange={(e) => setQSlug(e.target.value)}
            placeholder="diag-slug-kebab"
            className="rounded-lg border border-slate-300 bg-white px-3 py-2"
          />
          <select
            value={domainSlug}
            onChange={(e) => setDomainSlug(e.target.value)}
            className="rounded-lg border border-slate-300 bg-white px-2.5 py-2"
          >
            {DOMAINS.map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>
          <select
            value={qDiff}
            onChange={(e) =>
              setQDiff(e.target.value as "foundation" | "core" | "stretch")
            }
            className="rounded-lg border border-slate-300 bg-white px-2.5 py-2"
          >
            <option value="foundation">foundation</option>
            <option value="core">core</option>
            <option value="stretch">stretch</option>
          </select>
          <select
            value={qType}
            onChange={(e) =>
              setQType(e.target.value as "mcq" | "code_execution")
            }
            className="rounded-lg border border-slate-300 bg-white px-2.5 py-2"
          >
            <option value="mcq">mcq</option>
            <option value="code_execution">code_execution</option>
          </select>

          <input
            type="text"
            value={skillSlug}
            onChange={(e) => setSkillSlug(e.target.value)}
            placeholder="skill_slug"
            className="rounded-lg border border-slate-300 bg-white px-3 py-2"
          />
          <input
            type="text"
            value={promptEn}
            onChange={(e) => setPromptEn(e.target.value)}
            placeholder="Prompt (English)"
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 sm:col-span-2"
          />
          <input
            type="text"
            value={promptBn}
            onChange={(e) => setPromptBn(e.target.value)}
            placeholder="Prompt (বাংলা)"
            className="rounded-lg border border-slate-300 bg-white px-3 py-2"
          />
          <input
            type="text"
            value={explanationEn}
            onChange={(e) => setExplanationEn(e.target.value)}
            placeholder="Private Answer Explanation (EN)"
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 sm:col-span-2"
          />
          <input
            type="text"
            value={explanationBn}
            onChange={(e) => setExplanationBn(e.target.value)}
            placeholder="Private Answer Explanation (বাংলা)"
            className="rounded-lg border border-slate-300 bg-white px-3 py-2"
          />
          {qType === "mcq" ? (
            <input
              type="text"
              value={correctOpt}
              onChange={(e) => setCorrectOpt(e.target.value)}
              placeholder="Correct option ID (e.g. b)"
              className="rounded-lg border border-slate-300 bg-white px-3 py-2"
            />
          ) : (
            <>
              <input
                type="text"
                value={starterCode}
                onChange={(e) => setStarterCode(e.target.value)}
                placeholder="Starter code"
                className="rounded-lg border border-slate-300 bg-white px-3 py-2 font-mono sm:col-span-2"
              />
              <input
                type="text"
                value={testIn}
                onChange={(e) => setTestIn(e.target.value)}
                placeholder="Eval stdin"
                className="rounded-lg border border-slate-300 bg-white px-3 py-2 font-mono"
              />
              <input
                type="text"
                value={testOut}
                onChange={(e) => setTestOut(e.target.value)}
                placeholder="Eval expected stdout"
                className="rounded-lg border border-slate-300 bg-white px-3 py-2 font-mono"
              />
            </>
          )}
          <div className="flex justify-end gap-2 sm:col-span-4">
            <button
              type="button"
              disabled={busyKey !== null || !qSlug.trim() || !promptEn.trim()}
              onClick={() => void handleCreateDiagnostic(false)}
              className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 font-semibold"
            >
              Save Draft
            </button>
            <button
              type="button"
              disabled={busyKey !== null || !qSlug.trim() || !promptEn.trim()}
              onClick={() => void handleCreateDiagnostic(true)}
              className="inline-flex items-center gap-1 rounded-lg bg-indigo-600 px-3.5 py-1.5 font-semibold text-white"
            >
              <Plus className="h-3.5 w-3.5" />
              <span>Publish Diagnostic Item</span>
            </button>
          </div>
        </div>

        <div className="mt-4 space-y-2">
          {questions.map((q) => (
            <div
              key={q.id}
              className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 p-3.5 text-xs"
            >
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge
                    variant={q.status === "published" ? "emerald" : "neutral"}
                  >
                    {q.status}
                  </Badge>
                  <Badge variant="indigo">{q.domain_slug}</Badge>
                  <Badge variant="amber">{q.difficulty}</Badge>
                  <Badge variant="teal">{q.question_type}</Badge>
                  <span className="font-mono text-[11px] text-slate-500">
                    {q.slug}
                  </span>
                </div>
                <p className="mt-1 font-semibold text-slate-900">
                  {q.prompt_en}
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                {q.question_type === "code_execution" ? (
                  <button
                    type="button"
                    disabled={busyKey !== null}
                    onClick={() => void handleValidateDiag(q.id)}
                    className="inline-flex items-center gap-1 rounded-lg border border-teal-300 bg-teal-50 px-2.5 py-1.5 font-semibold text-teal-800"
                  >
                    {busyKey === `val-diag-${q.id}` ? (
                      <Loader2 className="h-3 w-3 animate-spin" />
                    ) : (
                      <FlaskConical className="h-3 w-3" />
                    )}
                    <span>Judge0 Check</span>
                  </button>
                ) : null}
                {q.status !== "published" ? (
                  <button
                    type="button"
                    onClick={() => void handleDiagStatus(q.id, "published")}
                    className="rounded-lg bg-emerald-600 px-3 py-1.5 font-semibold text-white"
                  >
                    Publish
                  </button>
                ) : (
                  <button
                    type="button"
                    onClick={() => void handleDiagStatus(q.id, "archived")}
                    className="rounded-lg border border-slate-300 px-3 py-1.5 font-semibold text-slate-700"
                  >
                    Archive
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* RAG Knowledge Base */}
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="flex items-center gap-2 text-base font-bold text-slate-900">
          <Database className="h-4 w-4 text-teal-600" />
          <span>Approved Mentor RAG Knowledge Base ({docs.length})</span>
        </h2>

        <div className="mt-4 grid gap-3 rounded-xl border border-slate-200 bg-slate-50 p-4 text-xs sm:grid-cols-3">
          <input
            type="text"
            value={kSlug}
            onChange={(e) => setKSlug(e.target.value)}
            placeholder="doc-slug-kebab"
            className="rounded-lg border border-slate-300 bg-white px-3 py-2"
          />
          <input
            type="text"
            value={kTitle}
            onChange={(e) => setKTitle(e.target.value)}
            placeholder="Document Title"
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 sm:col-span-2"
          />
          <input
            type="text"
            value={kTopic}
            onChange={(e) => setKTopic(e.target.value)}
            placeholder="Topic (e.g. recursion, graphs)"
            className="rounded-lg border border-slate-300 bg-white px-3 py-2"
          />
          <input
            type="text"
            value={kErrorsCsv}
            onChange={(e) => setKErrorsCsv(e.target.value)}
            placeholder="Error taxonomy codes CSV"
            className="rounded-lg border border-slate-300 bg-white px-3 py-2"
          />
          <input
            type="text"
            value={kSource}
            onChange={(e) => setKSource(e.target.value)}
            placeholder="Source attribution"
            className="rounded-lg border border-slate-300 bg-white px-3 py-2"
          />
          <textarea
            rows={3}
            value={kContentMd}
            onChange={(e) => setKContentMd(e.target.value)}
            placeholder="Conceptual explanation in Markdown (no hidden test keys)"
            className="rounded-lg border border-slate-300 bg-white p-2 sm:col-span-3"
          />
          <div className="flex justify-end gap-2 sm:col-span-3">
            <button
              type="button"
              disabled={busyKey !== null || !kSlug.trim() || !kContentMd.trim()}
              onClick={() => void handleUpsertKnowledge("draft")}
              className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 font-semibold"
            >
              Save Draft
            </button>
            <button
              type="button"
              disabled={busyKey !== null || !kSlug.trim() || !kContentMd.trim()}
              onClick={() => void handleUpsertKnowledge("approved")}
              className="rounded-lg bg-teal-600 px-3.5 py-1.5 font-semibold text-white"
            >
              Approve &amp; Index pgvector
            </button>
          </div>
        </div>

        <div className="mt-4 space-y-2">
          {docs.map((doc) => (
            <div
              key={doc.id}
              className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 p-3.5 text-xs"
            >
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <Badge
                    variant={doc.status === "approved" ? "emerald" : "neutral"}
                  >
                    {doc.status}
                  </Badge>
                  <Badge variant="indigo">{doc.topic}</Badge>
                  <span className="font-mono text-[11px] text-slate-500">
                    {doc.slug} · {doc.chunk_count} chunk(s)
                  </span>
                </div>
                <p className="mt-1 font-bold text-slate-900">{doc.title}</p>
                <p className="text-[11px] text-slate-500">
                  Source: {doc.source_name} v{doc.source_version}
                </p>
              </div>
              <div className="flex items-center gap-2">
                {doc.status !== "approved" ? (
                  <button
                    type="button"
                    onClick={() =>
                      void handleKnowledgeStatus(doc.id, "approved")
                    }
                    className="rounded-lg bg-emerald-600 px-3 py-1.5 font-semibold text-white"
                  >
                    Approve
                  </button>
                ) : (
                  <button
                    type="button"
                    onClick={() =>
                      void handleKnowledgeStatus(doc.id, "archived")
                    }
                    className="rounded-lg border border-slate-300 px-3 py-1.5 font-semibold text-slate-700"
                  >
                    Archive
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
