"use client";

import {
  AlertCircle,
  ArrowRight,
  Calendar,
  CheckCircle2,
  Circle,
  Clock,
  Loader2,
  RefreshCw,
} from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import {
  regenerateDailyPlan,
  updateDailyPlanTaskStatus,
} from "@/lib/api-client";
import type {
  DailyLearningPlanView,
  DailyPlanWorkspaceView,
  DailyTaskStatus,
} from "@/types/growth";

interface DailyPlanClientProps {
  accessToken: string;
  initialWorkspace: DailyPlanWorkspaceView;
  initialLanguage?: "en" | "bn";
}

const TIME_PRESETS = [20, 30, 45, 60, 90];

const TASK_TYPE_VARIANT: Record<
  string,
  "teal" | "indigo" | "amber" | "neutral"
> = {
  retention: "teal",
  diagnostic: "indigo",
  lesson: "indigo",
  debugging: "amber",
  transfer: "teal",
  problem: "neutral",
};

export function DailyPlanClient({
  accessToken,
  initialWorkspace,
  initialLanguage = "en",
}: DailyPlanClientProps) {
  const [lang, setLang] = useState<"en" | "bn">(initialLanguage);
  const [workspace, setWorkspace] =
    useState<DailyPlanWorkspaceView>(initialWorkspace);
  const [minutes, setMinutes] = useState<number>(
    initialWorkspace.active_plan.available_minutes,
  );
  const [regenerating, setRegenerating] = useState(false);
  const [updatingTaskId, setUpdatingTaskId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const isBn = lang === "bn";

  const plan: DailyLearningPlanView = workspace.active_plan;

  async function handleRegenerate() {
    setError(null);
    setRegenerating(true);
    try {
      const updated = await regenerateDailyPlan(accessToken, minutes);
      setWorkspace(updated);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not regenerate daily plan.",
      );
    } finally {
      setRegenerating(false);
    }
  }

  async function handleToggleTask(taskId: string, nextStatus: DailyTaskStatus) {
    setError(null);
    setUpdatingTaskId(taskId);
    try {
      const updatedPlan = await updateDailyPlanTaskStatus(
        accessToken,
        taskId,
        nextStatus,
      );
      setWorkspace((prev) => ({
        ...prev,
        active_plan: updatedPlan,
        history: prev.history.map((h) =>
          h.id === updatedPlan.id
            ? {
                ...h,
                completed_tasks: updatedPlan.completed_tasks,
                total_tasks: updatedPlan.total_tasks,
              }
            : h,
        ),
      }));
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not update task status.",
      );
    } finally {
      setUpdatingTaskId(null);
    }
  }

  return (
    <div className="tf-animate-enter space-y-6" lang={lang}>
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0 flex-1">
            <p className="inline-flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-teal-700">
              <Calendar className="h-4 w-4" aria-hidden="true" />
              <span>
                {isBn ? "অ্যাডাপ্টিভ দৈনিক পরিকল্পনা" : "Adaptive Daily Learning Plan"}
              </span>
            </p>
            <h1 className="mt-1.5 text-2xl font-bold text-slate-900 sm:text-3xl">
              {isBn
                ? `আজকের অধ্যয়ন পরিকল্পনা (${plan.plan_date})`
                : `Today's Study Plan (${plan.plan_date})`}
            </h1>
            <p className="mt-2 max-w-2xl text-base leading-relaxed text-slate-600">
              {isBn ? plan.generation_reason_bn : plan.generation_reason_en}
            </p>
          </div>

          <div
            role="group"
            aria-label="Daily plan language"
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

        {/* Study time budget & Regenerate controls */}
        <div className="mt-5 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 bg-slate-50 p-4">
          <div className="flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-700">
              <Clock className="h-3.5 w-3.5 text-indigo-600" aria-hidden="true" />
              {isBn ? "অধ্যয়নের সময়:" : "Available study time:"}
            </span>
            <div className="flex flex-wrap gap-1.5">
              {TIME_PRESETS.map((preset) => (
                <button
                  key={preset}
                  type="button"
                  onClick={() => setMinutes(preset)}
                  aria-pressed={minutes === preset}
                  className={`rounded-lg px-2.5 py-1 text-xs font-semibold transition ${
                    minutes === preset
                      ? "bg-indigo-600 text-white"
                      : "border border-slate-300 bg-white text-slate-700 hover:bg-slate-100"
                  }`}
                >
                  {preset}m
                </button>
              ))}
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <Badge variant="indigo">
              v{plan.version_number} · {plan.completed_tasks}/{plan.total_tasks}{" "}
              {isBn ? "সম্পন্ন" : "completed"}
            </Badge>
            <button
              type="button"
              onClick={() => void handleRegenerate()}
              disabled={regenerating}
              className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3.5 py-2 text-xs font-semibold text-white transition hover:bg-indigo-500 disabled:opacity-60"
            >
              {regenerating ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
              ) : (
                <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
              )}
              <span>{isBn ? "প্ল্যান পুনর্গঠন করো" : "Regenerate Plan"}</span>
            </button>
          </div>
        </div>

        {error ? (
          <div
            role="alert"
            className="mt-4 flex items-center gap-2 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-800"
          >
            <AlertCircle className="h-4 w-4 shrink-0" aria-hidden="true" />
            <span>{error}</span>
          </div>
        ) : null}
      </section>

      {/* Active Plan Task List */}
      <section aria-label="Daily Plan Tasks" className="space-y-3">
        {plan.tasks.map((task) => {
          const isDone = task.status === "completed";
          const isBusy = updatingTaskId === task.id;
          return (
            <article
              key={task.id}
              className={`rounded-2xl border p-5 shadow-sm transition ${
                isDone
                  ? "border-teal-200 bg-teal-50/40"
                  : "border-slate-200 bg-white"
              }`}
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="flex min-w-0 flex-1 items-start gap-3">
                  <button
                    type="button"
                    disabled={isBusy}
                    onClick={() =>
                      void handleToggleTask(
                        task.id,
                        isDone ? "pending" : "completed",
                      )
                    }
                    aria-label={
                      isDone
                        ? `Mark ${task.title_en} pending`
                        : `Mark ${task.title_en} completed`
                    }
                    className="mt-0.5 shrink-0 text-indigo-600 hover:text-indigo-800 disabled:opacity-50"
                  >
                    {isBusy ? (
                      <Loader2 className="h-5 w-5 animate-spin" />
                    ) : isDone ? (
                      <CheckCircle2 className="h-5 w-5 text-teal-600" />
                    ) : (
                      <Circle className="h-5 w-5 text-slate-400" />
                    )}
                  </button>

                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant={TASK_TYPE_VARIANT[task.task_type] ?? "neutral"}>
                        {task.task_type}
                      </Badge>
                      <span className="text-xs font-medium text-slate-500">
                        ~{task.estimated_minutes} min
                      </span>
                      {task.skill_slug ? (
                        <span className="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-[11px] text-slate-600">
                          {task.skill_slug}
                        </span>
                      ) : null}
                    </div>
                    <h2
                      className={`mt-1.5 text-base font-bold ${
                        isDone ? "text-slate-500 line-through" : "text-slate-900"
                      }`}
                    >
                      {isBn ? task.title_bn : task.title_en}
                    </h2>
                    <p className="mt-1 text-sm text-slate-600">
                      {isBn ? task.reason_bn : task.reason_en}
                    </p>
                  </div>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  <Link
                    href={task.href}
                    className="inline-flex items-center gap-1 rounded-lg bg-slate-900 px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-slate-700"
                  >
                    <span>{isBn ? "শুরু করো" : "Open Task"}</span>
                    <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
                  </Link>
                </div>
              </div>
            </article>
          );
        })}
      </section>

      {/* Plan Regeneration History */}
      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="text-sm font-bold text-slate-900">
          {isBn ? "পূর্ববর্তী পরিকল্পনার ইতিহাস" : "Plan Generation History"}
        </h2>
        <div className="mt-3 overflow-x-auto">
          <table className="w-full min-w-[460px] text-left text-xs">
            <thead>
              <tr className="border-b border-slate-200 text-slate-500">
                <th className="py-2 pr-3 font-semibold">Date</th>
                <th className="py-2 pr-3 font-semibold">Version</th>
                <th className="py-2 pr-3 font-semibold">Budget</th>
                <th className="py-2 pr-3 font-semibold">Tasks</th>
                <th className="py-2 font-semibold">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {workspace.history.map((item) => (
                <tr key={item.id}>
                  <td className="py-2 pr-3 font-medium text-slate-800">
                    {item.plan_date}
                  </td>
                  <td className="py-2 pr-3 font-mono text-slate-600">
                    v{item.version_number}
                  </td>
                  <td className="py-2 pr-3 text-slate-600">
                    {item.available_minutes}m ({item.total_estimated_minutes}m est.)
                  </td>
                  <td className="py-2 pr-3 text-slate-700">
                    {item.completed_tasks} / {item.total_tasks}
                  </td>
                  <td className="py-2">
                    <Badge variant={item.is_active ? "teal" : "neutral"}>
                      {item.is_active ? "Active" : "Archived"}
                    </Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
