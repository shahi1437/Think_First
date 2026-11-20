"use client";

import {
  AlertCircle,
  ArrowLeft,
  BookCheck,
  CheckCircle2,
  Clock,
  Loader2,
  Play,
  RotateCcw,
} from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { CodeEditor } from "@/features/workspace/code-editor";
import {
  markLessonReadingComplete,
  runLessonGuidedExercise,
} from "@/lib/api-client";
import type {
  LessonDetailView,
  LessonExerciseRunResponse,
} from "@/types/learning";

interface LessonViewerProps {
  accessToken: string;
  initialLesson: LessonDetailView;
  initialLanguage?: "en" | "bn";
  usePlainEditor?: boolean;
  onMarkReading?: (lessonId: string) => Promise<LessonDetailView>;
  onRunExercise?: (
    lessonId: string,
    code: string,
  ) => Promise<LessonExerciseRunResponse>;
}

export function LessonViewer({
  accessToken,
  initialLesson,
  initialLanguage = "en",
  usePlainEditor = false,
  onMarkReading,
  onRunExercise,
}: LessonViewerProps) {
  const [lesson, setLesson] = useState<LessonDetailView>(initialLesson);
  const [lang, setLang] = useState<"en" | "bn">(initialLanguage);
  const [code, setCode] = useState<string>(
    initialLesson.last_code ?? initialLesson.guided_exercise.starter_code,
  );
  const [markingRead, setMarkingRead] = useState(false);
  const [running, setRunning] = useState(false);
  const [runResult, setRunResult] = useState<LessonExerciseRunResponse | null>(
    null,
  );
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const isBn = lang === "bn";

  async function handleMarkReading() {
    setErrorMsg(null);
    setMarkingRead(true);
    try {
      const updated = onMarkReading
        ? await onMarkReading(lesson.lesson_id)
        : await markLessonReadingComplete(accessToken, lesson.lesson_id);
      setLesson(updated);
    } catch (err) {
      setErrorMsg(
        err instanceof Error ? err.message : "Could not save reading progress.",
      );
    } finally {
      setMarkingRead(false);
    }
  }

  async function handleRunExercise() {
    setErrorMsg(null);
    setRunning(true);
    try {
      const res = onRunExercise
        ? await onRunExercise(lesson.lesson_id, code)
        : await runLessonGuidedExercise(accessToken, lesson.lesson_id, code);
      setRunResult(res);
      setLesson((prev) => ({
        ...prev,
        reading_completed: true,
        exercise_passed: prev.exercise_passed || res.exercise_passed,
        progress_status: res.progress_status,
        exercise_attempts: prev.exercise_attempts + 1,
        last_verdict: res.verdict,
      }));
    } catch (err) {
      setErrorMsg(
        err instanceof Error
          ? err.message
          : "Guided exercise execution failed on Judge0.",
      );
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="space-y-5 overflow-x-hidden" lang={lang}>
      {/* Top Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm">
        <div className="flex flex-wrap items-center gap-3">
          <Link
            href="/student/lessons"
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-2.5 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
          >
            <ArrowLeft className="h-3.5 w-3.5" aria-hidden="true" />
            <span>Lessons</span>
          </Link>
          <h1 className="text-base font-bold text-slate-900 sm:text-lg">
            {isBn ? lesson.title_bn : lesson.title_en}
          </h1>
          <Badge
            variant={
              lesson.progress_status === "completed"
                ? "emerald"
                : lesson.reading_completed
                  ? "indigo"
                  : "neutral"
            }
          >
            <span className="capitalize">
              {lesson.progress_status.replaceAll("_", " ")}
            </span>
          </Badge>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <span className="inline-flex items-center gap-1 text-xs text-slate-500">
            <Clock className="h-3.5 w-3.5" aria-hidden="true" />
            <span>{lesson.estimated_minutes} min</span>
          </span>
          <div
            role="group"
            aria-label="Lesson language"
            className="inline-flex rounded-lg border border-slate-200 bg-slate-50 p-0.5 text-xs"
          >
            <button
              type="button"
              onClick={() => setLang("en")}
              aria-pressed={lang === "en"}
              className={`rounded-md px-2.5 py-1 font-semibold ${
                lang === "en"
                  ? "bg-indigo-600 text-white"
                  : "text-slate-600 hover:bg-slate-200/70"
              }`}
            >
              English
            </button>
            <button
              type="button"
              onClick={() => setLang("bn")}
              aria-pressed={lang === "bn"}
              className={`rounded-md px-2.5 py-1 font-semibold ${
                lang === "bn"
                  ? "bg-indigo-600 text-white"
                  : "text-slate-600 hover:bg-slate-200/70"
              }`}
            >
              বাংলা
            </button>
          </div>
        </div>
      </div>

      {/* Main Split: Concept & Interactive Examples vs Real Judge0 Guided Exercise */}
      <div className="grid gap-5 lg:grid-cols-12">
        {/* Left: Concept Explanation + Examples */}
        <article className="min-w-0 space-y-5 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm lg:col-span-6">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-indigo-700">
              {isBn ? "ধারণা ও ব্যাখ্যা" : "Concept Explanation"}
            </p>
            <div className="mt-2 whitespace-pre-line text-sm leading-relaxed text-slate-800">
              {isBn ? lesson.content_bn_md : lesson.content_en_md}
            </div>
          </div>

          {lesson.learning_objectives.length > 0 ? (
            <div className="border-t border-slate-100 pt-4">
              <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                Learning Objectives
              </h2>
              <ul className="mt-2 list-disc space-y-1 pl-5 text-xs text-slate-700">
                {lesson.learning_objectives.map((obj) => (
                  <li key={obj}>{obj}</li>
                ))}
              </ul>
            </div>
          ) : null}

          {lesson.interactive_examples.length > 0 ? (
            <div className="space-y-3 border-t border-slate-100 pt-4">
              <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                {isBn ? "ইন্টারঅ্যাক্টিভ উদাহরণ" : "Interactive Worked Examples"}
              </h2>
              {lesson.interactive_examples.map((ex, idx) => (
                <div
                  key={idx}
                  className="rounded-xl border border-slate-200 bg-slate-50 p-3.5 text-xs"
                >
                  <p className="font-semibold text-slate-900">{ex.title}</p>
                  <pre className="mt-2 overflow-x-auto rounded-lg bg-slate-900 p-3 font-mono text-slate-100">
                    {ex.code}
                  </pre>
                  <div className="mt-2 grid gap-2 sm:grid-cols-2">
                    <div>
                      <span className="font-medium text-slate-500">Input:</span>
                      <pre className="mt-0.5 rounded bg-white p-2 font-mono text-slate-800">
                        {ex.input_data || "(none)"}
                      </pre>
                    </div>
                    <div>
                      <span className="font-medium text-slate-500">
                        Expected Output:
                      </span>
                      <pre className="mt-0.5 rounded bg-white p-2 font-mono text-slate-800">
                        {ex.expected_output}
                      </pre>
                    </div>
                  </div>
                  <p className="mt-2 text-slate-700">
                    {isBn ? ex.explanation_bn : ex.explanation_en}
                  </p>
                </div>
              ))}
            </div>
          ) : null}

          <div className="flex flex-wrap items-center justify-between gap-2 border-t border-slate-100 pt-4">
            <p className="text-[11px] text-slate-500">
              {isBn
                ? "পড়া শেষ করলে Skill Graph-এ 'Introduced' হিসেবে সংরক্ষিত হবে; সম্পূর্ণ করতে ডানপাশের Judge0 অনুশীলন পাস করো।"
                : "Marking reading complete records 'Introduced' only—pass the Judge0 guided exercise to complete this lesson."}
            </p>
            <button
              type="button"
              disabled={markingRead || lesson.reading_completed}
              onClick={() => {
                void handleMarkReading();
              }}
              className="inline-flex items-center gap-1.5 rounded-lg border border-indigo-200 bg-indigo-50 px-3 py-1.5 text-xs font-semibold text-indigo-800 transition hover:bg-indigo-100 disabled:opacity-60"
            >
              {markingRead ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <BookCheck className="h-3.5 w-3.5" aria-hidden="true" />
              )}
              <span>
                {lesson.reading_completed
                  ? "Reading Completed"
                  : "Mark Reading Complete"}
              </span>
            </button>
          </div>
        </article>

        {/* Right: Guided Practice Exercise + Real Judge0 Execution */}
        <section
          aria-label="Guided Judge0 practice"
          className="min-w-0 space-y-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm lg:col-span-6"
        >
          <div className="space-y-1.5">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 className="text-sm font-bold text-slate-900">
                {isBn
                  ? "নির্দেশিত প্র্যাকটিস (আসল Judge0 এক্সিকিউশন)"
                  : "Guided Exercise (Real Judge0 Execution)"}
              </h2>
              <Badge variant="teal">Skill: {lesson.skill_slug}</Badge>
            </div>
            <p className="text-xs leading-relaxed text-slate-700">
              {isBn
                ? lesson.guided_exercise.prompt_bn
                : lesson.guided_exercise.prompt_en}
            </p>
          </div>

          <div className="overflow-hidden rounded-xl border border-slate-200">
            <div className="flex flex-wrap items-center justify-between gap-2 bg-slate-900 px-3.5 py-2 text-xs text-white">
              <span className="font-semibold">Python 3 Guided Practice</span>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setCode(lesson.guided_exercise.starter_code)}
                  className="inline-flex items-center gap-1 rounded border border-slate-700 px-2 py-1 text-slate-300 hover:bg-slate-800"
                >
                  <RotateCcw className="h-3 w-3" aria-hidden="true" />
                  <span>Reset</span>
                </button>
                <button
                  type="button"
                  disabled={running || !code.trim()}
                  onClick={() => {
                    void handleRunExercise();
                  }}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-teal-600 px-3 py-1 font-semibold text-white hover:bg-teal-500 disabled:opacity-60"
                >
                  {running ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <Play className="h-3.5 w-3.5" aria-hidden="true" />
                  )}
                  <span>{running ? "Running Judge0..." : "Run Guided Exercise"}</span>
                </button>
              </div>
            </div>
            <CodeEditor
              language="python"
              value={code}
              onChange={setCode}
              usePlainTextarea={usePlainEditor}
            />
          </div>

          {errorMsg ? (
            <div
              role="alert"
              className="flex items-start gap-2 rounded-lg border border-rose-200 bg-rose-50 p-3 text-xs text-rose-900"
            >
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-rose-600" />
              <span>{errorMsg}</span>
            </div>
          ) : null}

          {runResult ? (
            <div
              role="status"
              className={`space-y-3 rounded-xl border p-4 text-xs ${
                runResult.exercise_passed
                  ? "border-emerald-300 bg-emerald-50/70"
                  : "border-amber-200 bg-amber-50/70"
              }`}
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2 font-bold text-slate-900">
                  <CheckCircle2
                    className={`h-4 w-4 ${
                      runResult.exercise_passed
                        ? "text-emerald-700"
                        : "text-amber-700"
                    }`}
                  />
                  <span>
                    {runResult.exercise_passed
                      ? "Lesson Completed! Guided Exercise Passed"
                      : `Not Passed Yet (${runResult.verdict})`}
                  </span>
                </div>
                <Badge
                  variant={runResult.exercise_passed ? "emerald" : "amber"}
                >
                  {runResult.passed_tests} / {runResult.total_tests} tests · Skill:{" "}
                  {runResult.skill_state_after}
                </Badge>
              </div>

              <div className="space-y-2">
                {runResult.case_results.map((cr, idx) => (
                  <div
                    key={idx}
                    className="rounded-lg border border-slate-200 bg-white p-2.5"
                  >
                    <div className="flex items-center justify-between font-semibold">
                      <span>{cr.name}</span>
                      <Badge variant={cr.passed ? "emerald" : "rose"}>
                        {cr.verdict}
                      </Badge>
                    </div>
                    <div className="mt-1.5 grid gap-2 sm:grid-cols-2">
                      <div>
                        <span className="text-[11px] text-slate-500">
                          Expected:
                        </span>
                        <pre className="rounded bg-slate-50 p-1.5 font-mono text-slate-800">
                          {cr.expected_output}
                        </pre>
                      </div>
                      <div>
                        <span className="text-[11px] text-slate-500">
                          Actual:
                        </span>
                        <pre className="rounded bg-slate-50 p-1.5 font-mono text-slate-800">
                          {cr.actual_output ?? "(empty)"}
                        </pre>
                      </div>
                    </div>
                    {cr.stderr ? (
                      <pre className="mt-1.5 overflow-x-auto rounded bg-rose-50 p-1.5 font-mono text-rose-900">
                        {cr.stderr}
                      </pre>
                    ) : null}
                  </div>
                ))}
              </div>

              {runResult.exercise_passed ? (
                <div className="flex flex-wrap gap-2 pt-1">
                  <Link
                    href="/student"
                    className="inline-flex items-center rounded-lg bg-indigo-600 px-3 py-1.5 font-semibold text-white hover:bg-indigo-500"
                  >
                    View Updated Skill Graph &amp; Next Recommendation →
                  </Link>
                </div>
              ) : null}
            </div>
          ) : null}
        </section>
      </div>
    </div>
  );
}
