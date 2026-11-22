"use client";

import { useQuery } from "@tanstack/react-query";
import {
  AlertCircle,
  ArrowRight,
  Bug,
  Code2,
  Loader2,
  Search,
} from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { fetchProblems } from "@/lib/api-client";
import type {
  Difficulty,
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

  const isFiltered = Boolean(
    search.trim() || mode || difficulty || languageFilter,
  );

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["problems", search.trim(), mode, difficulty, languageFilter],
    queryFn: () =>
      fetchProblems(accessToken, {
        search: search.trim() || undefined,
        mode: mode || undefined,
        difficulty: difficulty || undefined,
        language: languageFilter || undefined,
        limit: 30,
      }),
    initialData: !isFiltered
      ? { items: initialProblems, total: initialTotal }
      : undefined,
  });

  const items = data?.items ?? [];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-teal-700">
            Smart Adaptive Problem Bank
          </p>
          <h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-900">
            Practice &amp; Debugging Challenges
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            Every challenge runs in an isolated Judge0 sandbox with verified
            public and hidden test suites.
          </p>
        </div>
        <p className="text-xs font-medium text-slate-500">
          Showing {items.length} of {data?.total ?? 0} published problems
        </p>
      </div>

      {/* Filters */}
      <div className="grid gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:grid-cols-12">
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
            className="w-full rounded-lg border border-slate-300 bg-white py-2 pl-9 pr-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-indigo-600 focus:outline-none"
          />
        </div>

        <div className="sm:col-span-3">
          <select
            aria-label="Filter by programming language"
            value={languageFilter}
            onChange={(e) => setLanguageFilter(e.target.value)}
            className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:border-indigo-600 focus:outline-none"
          >
            <option value="">
              All languages
              {activeLanguageSlug ? ` (Active: ${activeLanguageSlug.toUpperCase()})` : ""}
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
            aria-label="Filter by mode"
            value={mode}
            onChange={(e) => setMode(e.target.value as ProblemMode | "")}
            className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:border-indigo-600 focus:outline-none"
          >
            <option value="">All modes</option>
            <option value="coding">Normal Coding</option>
            <option value="debugging">Debugging Mode</option>
          </select>
        </div>

        <div className="sm:col-span-3">
          <select
            aria-label="Filter by difficulty"
            value={difficulty}
            onChange={(e) => setDifficulty(e.target.value as Difficulty | "")}
            className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:border-indigo-600 focus:outline-none"
          >
            <option value="">All difficulties</option>
            <option value="beginner">Beginner</option>
            <option value="basic">Basic</option>
            <option value="intermediate">Intermediate</option>
            <option value="advanced">Advanced</option>
          </select>
        </div>
      </div>

      {isLoading ? (
        <div className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white p-8 text-sm text-slate-600">
          <Loader2
            className="h-5 w-5 animate-spin text-indigo-600"
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
            Try clearing your search or selecting a different difficulty/mode
            filter.
          </p>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {items.map((problem) => (
            <article
              key={problem.problem_id}
              className="flex flex-col justify-between rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition hover:border-indigo-300"
            >
              <div>
                <div className="flex flex-wrap items-center gap-2">
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

                <h2 className="mt-3 text-lg font-semibold text-slate-900">
                  {problem.title}
                </h2>

                <div className="mt-3 flex flex-wrap gap-1.5">
                  {problem.topics.map((topic) => (
                    <span
                      key={topic}
                      className="rounded-md bg-slate-100 px-2 py-0.5 text-xs text-slate-600"
                    >
                      #{topic}
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
                  className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3.5 py-2 text-xs font-semibold text-white transition hover:bg-indigo-700"
                >
                  <span>
                    {problem.mode === "debugging"
                      ? "Open Debugger"
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
