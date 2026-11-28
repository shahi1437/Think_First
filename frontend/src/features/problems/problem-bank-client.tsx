"use client";

import { useQuery } from "@tanstack/react-query";
import {
  AlertCircle,
  ArrowRight,
  Bug,
  CheckCircle2,
  Clock,
  Code2,
  Loader2,
  Search,
  Sparkles,
} from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { fetchProblems } from "@/lib/api-client";
import type {
  Difficulty,
  ProblemCompletionStatus,
  ProblemMode,
  StudentProblemListItem,
} from "@/types/problems";

interface ProblemBankClientProps {
  accessToken: string;
  initialProblems: StudentProblemListItem[];
  initialTotal: number;
  activeLanguageSlug?: string;
}

const difficultyVariant: Record<
  Difficulty,
  "emerald" | "teal" | "amber" | "rose"
> = {
  beginner: "emerald",
  basic: "teal",
  intermediate: "amber",
  advanced: "rose",
};

export function ProblemBankClient({
  accessToken,
  initialProblems,
  initialTotal,
  activeLanguageSlug,
}: ProblemBankClientProps) {
  const [search, setSearch] = useState("");
  const [mode, setMode] = useState<ProblemMode | "">("");
  const [difficulty, setDifficulty] = useState<Difficulty | "">("");
  const [languageFilter, setLanguageFilter] = useState<string>("");
  const [topicFilter, setTopicFilter] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<
    ProblemCompletionStatus | ""
  >("");
  const [recommendedOnly, setRecommendedOnly] = useState(false);

  const availableTopics = useMemo(() => {
    const set = new Set<string>();
    for (const p of initialProblems) {
      for (const t of p.topics) set.add(t);
    }
    return Array.from(set).sort();
  }, [initialProblems]);

  const isFiltered = Boolean(
    search.trim() ||
      mode ||
      difficulty ||
      languageFilter ||
      topicFilter ||
      statusFilter ||
      recommendedOnly,
  );

  const { data, isLoading, isError, error } = useQuery({
    queryKey: [
      "problems",
      search.trim(),
      mode,
      difficulty,
      languageFilter,
      topicFilter,
      statusFilter,
      recommendedOnly,
    ],
    queryFn: () =>
      fetchProblems(accessToken, {
        search: search.trim() || undefined,
        mode: mode || undefined,
        difficulty: difficulty || undefined,
        language: languageFilter || undefined,
        topic: topicFilter || undefined,
        completion_status: statusFilter || undefined,
        recommended_only: recommendedOnly || undefined,
        limit: 40,
      }),
    initialData: !isFiltered
      ? { items: initialProblems, total: initialTotal }
      : undefined,
  });

  const items = data?.items ?? [];
  const solvedCount = initialProblems.filter(
    (p) => p.completion_status === "solved",
  ).length;
  const recommendedCount = initialProblems.filter(
    (p) => p.is_recommended,
  ).length;

  function clearAllFilters() {
    setSearch("");
    setMode("");
    setDifficulty("");
    setLanguageFilter("");
    setTopicFilter("");
    setStatusFilter("");
    setRecommendedOnly(false);
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4 rounded-2xl border border-slate-200 bg-white p-6">
        <div>
          <p className="text-xs font-semibold text-teal-700">
            Smart Adaptive Problem Bank
          </p>
          <h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-950">
            Practice &amp; Debugging Challenges
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            Every challenge runs in an isolated sandbox with verified public and
            hidden tests, ranked using your real Skill Graph and execution
            history.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2 text-xs tabular-nums">
          <span className="rounded-md border border-emerald-200 bg-emerald-50 px-2.5 py-1 font-medium text-emerald-800">
            {solvedCount} solved
          </span>
          <span className="rounded-md border border-teal-200 bg-teal-50 px-2.5 py-1 font-medium text-teal-800">
            {recommendedCount} recommended
          </span>
          <span className="rounded-md border border-slate-200 bg-slate-50 px-2.5 py-1 font-medium text-slate-600">
            Showing {items.length} of {data?.total ?? 0}
          </span>
        </div>
      </div>

      {/* Filters & Weak-Concept Adaptive Toggle */}
      <div className="space-y-3 rounded-2xl border border-slate-200 bg-white p-4">
        <div className="grid gap-3 sm:grid-cols-12">
          <div className="relative sm:col-span-4">
            <Search
              className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400"
              aria-hidden="true"
            />
            <input
              type="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by title, slug, or concept..."
              aria-label="Search problems"
              className="w-full rounded-lg border border-slate-300 bg-white py-2 pl-9 pr-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-teal-600 focus:outline-none"
            />
          </div>

          <div className="sm:col-span-2">
            <select
              aria-label="Filter by programming language"
              value={languageFilter}
              onChange={(e) => setLanguageFilter(e.target.value)}
              className="w-full rounded-lg border border-slate-300 bg-white px-2.5 py-2 text-sm text-slate-900 focus:border-teal-600 focus:outline-none"
            >
              <option value="">
                All languages
                {activeLanguageSlug
                  ? ` (${activeLanguageSlug.toUpperCase()})`
                  : ""}
              </option>
              <option value="python">Python 3</option>
              <option value="javascript">JavaScript (Node.js)</option>
              <option value="c">C (GCC)</option>
              <option value="cpp">C++ (GCC)</option>
              <option value="java">Java (OpenJDK)</option>
            </select>
          </div>

          <div className="sm:col-span-2">
            <select
              aria-label="Filter by topic"
              data-testid="problem-topic-filter"
              value={topicFilter}
              onChange={(e) => setTopicFilter(e.target.value)}
              className="w-full rounded-lg border border-slate-300 bg-white px-2.5 py-2 text-sm text-slate-900 focus:border-teal-600 focus:outline-none"
            >
              <option value="">All topics</option>
              {availableTopics.map((t) => (
                <option key={t} value={t}>
                  #{t}
                </option>
              ))}
            </select>
          </div>

          <div className="sm:col-span-2">
            <select
              aria-label="Filter by difficulty"
              value={difficulty}
              onChange={(e) => setDifficulty(e.target.value as Difficulty | "")}
              className="w-full rounded-lg border border-slate-300 bg-white px-2.5 py-2 text-sm text-slate-900 focus:border-teal-600 focus:outline-none"
            >
              <option value="">All difficulties</option>
              <option value="beginner">Beginner</option>
              <option value="basic">Basic</option>
              <option value="intermediate">Intermediate</option>
              <option value="advanced">Advanced</option>
            </select>
          </div>

          <div className="sm:col-span-2">
            <select
              aria-label="Filter by completion status"
              data-testid="problem-status-filter"
              value={statusFilter}
              onChange={(e) =>
                setStatusFilter(
                  e.target.value as ProblemCompletionStatus | "",
                )
              }
              className="w-full rounded-lg border border-slate-300 bg-white px-2.5 py-2 text-sm text-slate-900 focus:border-teal-600 focus:outline-none"
            >
              <option value="">All statuses</option>
              <option value="unattempted">Not Started</option>
              <option value="attempted">In Progress</option>
              <option value="solved">Solved</option>
            </select>
          </div>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-2 border-t border-slate-100 pt-3">
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              aria-pressed={recommendedOnly}
              data-testid="problem-recommended-toggle"
              onClick={() => setRecommendedOnly((prev) => !prev)}
              className={`inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-semibold transition-colors ${
                recommendedOnly
                  ? "border-teal-700 bg-teal-700 text-white"
                  : "border-teal-200 bg-teal-50 text-teal-800 hover:bg-teal-100"
              }`}
            >
              <Sparkles className="h-3.5 w-3.5" aria-hidden="true" />
              <span>Recommended for Weak Concepts</span>
            </button>

            <select
              aria-label="Filter by mode"
              value={mode}
              onChange={(e) => setMode(e.target.value as ProblemMode | "")}
              className="rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1.5 text-xs font-medium text-slate-700 focus:border-teal-600 focus:outline-none"
            >
              <option value="">All modes</option>
              <option value="coding">Normal Coding</option>
              <option value="debugging">Debugging Mode</option>
            </select>
          </div>

          {isFiltered ? (
            <button
              type="button"
              onClick={clearAllFilters}
              className="text-xs font-medium text-slate-500 hover:text-slate-900 hover:underline"
            >
              Reset filters
            </button>
          ) : null}
        </div>
      </div>

      {isLoading ? (
        <div
          role="status"
          aria-live="polite"
          className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white p-8 text-sm text-slate-600"
        >
          <Loader2
            className="h-5 w-5 animate-spin text-teal-700"
            aria-hidden="true"
          />
          <span>Loading published problems...</span>
        </div>
      ) : isError ? (
        <div
          role="alert"
          className="flex items-start gap-3 rounded-xl border border-rose-200 bg-rose-50 p-5 text-sm text-rose-900"
        >
          <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-rose-600" />
          <div>
            <p className="font-semibold">Unable to load problems</p>
            <p className="mt-1">
              {error instanceof Error ? error.message : "Unknown error"}
            </p>
          </div>
        </div>
      ) : items.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-300 bg-white p-10 text-center">
          <p className="text-sm font-semibold text-slate-900">
            No matching problems found
          </p>
          <p className="mt-1 text-sm text-slate-600">
            Try clearing your search or selecting a different topic, status, or
            difficulty filter.
          </p>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {items.map((problem) => (
            <article
              key={problem.problem_id}
              data-testid="problem-bank-card"
              className={`flex flex-col justify-between rounded-xl border bg-white p-5 transition-colors ${
                problem.is_recommended
                  ? "border-teal-300 hover:border-teal-400"
                  : "border-slate-200 hover:border-slate-300"
              }`}
            >
              <div>
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex flex-wrap items-center gap-1.5">
                    <Badge
                      variant={problem.mode === "debugging" ? "indigo" : "teal"}
                    >
                      {problem.mode === "debugging" ? (
                        <Bug className="h-3 w-3" aria-hidden="true" />
                      ) : (
                        <Code2 className="h-3 w-3" aria-hidden="true" />
                      )}
                      <span className="capitalize">{problem.mode}</span>
                    </Badge>
                    <Badge variant={difficultyVariant[problem.difficulty]}>
                      <span className="capitalize">{problem.difficulty}</span>
                    </Badge>
                    {problem.supported_languages.map((lang) => (
                      <Badge key={lang} variant="neutral">
                        <span className="uppercase">{lang}</span>
                      </Badge>
                    ))}
                  </div>

                  {problem.completion_status === "solved" ? (
                    <span className="inline-flex items-center gap-1 rounded-md border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-[11px] font-semibold text-emerald-800">
                      <CheckCircle2 className="h-3 w-3" aria-hidden="true" />
                      Solved
                    </span>
                  ) : problem.completion_status === "attempted" ? (
                    <span className="inline-flex items-center gap-1 rounded-md border border-amber-200 bg-amber-50 px-2 py-0.5 text-[11px] font-semibold text-amber-800 tabular-nums">
                      <Clock className="h-3 w-3" aria-hidden="true" />
                      {problem.attempts_count} attempt(s)
                    </span>
                  ) : null}
                </div>

                <h2 className="mt-3 text-lg font-semibold text-slate-950">
                  {problem.title}
                </h2>

                {problem.is_recommended && problem.recommendation_reason ? (
                  <p className="mt-2 inline-flex items-center gap-1.5 rounded-md border border-teal-200 bg-teal-50/70 px-2.5 py-1 text-xs font-medium text-teal-900">
                    <Sparkles className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                    <span>{problem.recommendation_reason}</span>
                  </p>
                ) : null}

                <div className="mt-3 flex flex-wrap gap-1.5">
                  {problem.topics.map((topic) => (
                    <button
                      key={topic}
                      type="button"
                      onClick={() => setTopicFilter(topic)}
                      className="rounded-md bg-slate-100 px-2 py-0.5 text-xs text-slate-600 hover:bg-teal-50 hover:text-teal-800"
                    >
                      #{topic}
                    </button>
                  ))}
                  {problem.skills
                    .filter((s) => !problem.topics.includes(s))
                    .slice(0, 3)
                    .map((sk) => (
                      <span
                        key={sk}
                        className="rounded-md border border-slate-200 bg-white px-2 py-0.5 font-mono text-[11px] text-slate-500"
                      >
                        {sk}
                      </span>
                    ))}
                </div>
              </div>

              <div className="mt-5 flex items-center justify-between border-t border-slate-100 pt-4">
                <span className="font-mono text-xs text-slate-400">
                  {problem.slug}
                </span>
                <Link
                  href={`/student/problems/${problem.problem_id}`}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-[#0b1221] px-3.5 py-2 text-xs font-semibold text-white transition-colors hover:bg-slate-800"
                >
                  <span>
                    {problem.mode === "debugging"
                      ? "Open Debugger"
                      : problem.completion_status === "solved"
                        ? "Review Solution"
                        : "Solve Problem"}
                  </span>
                  <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
                </Link>
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
