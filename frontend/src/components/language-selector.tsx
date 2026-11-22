"use client";

import { CheckCircle2, Code2, Loader2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";
import { selectActiveLanguage } from "@/lib/api-client";
import { getLanguageShortLabel } from "@/lib/languages";
import type {
  LanguageProgressOverview,
  LanguageSlug,
} from "@/types/learning";

interface LanguageSelectorProps {
  accessToken: string;
  initialOverview: LanguageProgressOverview;
  explanationLanguage?: "en" | "bn";
  compact?: boolean;
  onLanguageChanged?: (nextOverview: LanguageProgressOverview) => void;
}

export function LanguageSelector({
  accessToken,
  initialOverview,
  explanationLanguage = "en",
  compact = false,
  onLanguageChanged,
}: LanguageSelectorProps) {
  const router = useRouter();
  const [overview, setOverview] =
    useState<LanguageProgressOverview>(initialOverview);
  const [switchingSlug, setSwitchingSlug] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  const isBn = explanationLanguage === "bn";

  async function handleSelect(slug: string) {
    if (slug === overview.active_language_slug || switchingSlug !== null) return;
    setErrorMsg(null);
    setSwitchingSlug(slug);
    try {
      const updated = await selectActiveLanguage(
        accessToken,
        slug as LanguageSlug,
      );
      setOverview(updated);
      onLanguageChanged?.(updated);
      startTransition(() => {
        router.refresh();
      });
    } catch (err) {
      setErrorMsg(
        err instanceof Error
          ? err.message
          : "Could not switch programming language right now.",
      );
    } finally {
      setSwitchingSlug(null);
    }
  }

  return (
    <section
      aria-label="Programming language selector"
      className={`rounded-2xl border border-slate-200 bg-white shadow-sm ${
        compact ? "p-4" : "p-5"
      }`}
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Code2 className="h-4 w-4 text-indigo-600" aria-hidden="true" />
          <p className="text-sm font-bold text-slate-900">
            {isBn
              ? "প্রোগ্রামিং ভাষা নির্বাচন করো (প্রতিটি ভাষার আলাদা অগ্রগতি)"
              : "Active Programming Language (Independent Progress Per Language)"}
          </p>
        </div>
        <span className="text-xs font-medium text-slate-500">
          {isPending || switchingSlug
            ? isBn
              ? "ভাষা পরিবর্তন হচ্ছে..."
              : "Updating workspace..."
            : isBn
              ? "একই অ্যাকাউন্টে ৫টি ভাষা শিখতে পারো"
              : "Switch anytime — all progress stays saved per language"}
        </span>
      </div>

      {errorMsg ? (
        <p role="alert" className="mt-2 text-xs font-medium text-rose-700">
          {errorMsg}
        </p>
      ) : null}

      <div
        role="tablist"
        aria-label="Supported programming languages"
        className="mt-3 grid gap-2.5 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5"
      >
        {overview.languages.map((lang) => {
          const isActive = lang.slug === overview.active_language_slug;
          const isBusy = switchingSlug === lang.slug;
          return (
            <button
              key={lang.slug}
              type="button"
              role="tab"
              aria-selected={isActive}
              data-testid={`lang-tab-${lang.slug}`}
              disabled={switchingSlug !== null}
              onClick={() => {
                void handleSelect(lang.slug);
              }}
              className={`flex flex-col items-start justify-between rounded-xl border px-3.5 py-2.5 text-left transition focus:outline-none focus:ring-2 focus:ring-indigo-500 ${
                isActive
                  ? "border-indigo-600 bg-indigo-50/70 ring-1 ring-indigo-600"
                  : "border-slate-200 bg-slate-50/50 hover:border-indigo-300 hover:bg-white"
              } disabled:cursor-wait disabled:opacity-75`}
            >
              <div className="flex w-full items-center justify-between gap-2">
                <span
                  className={`text-sm font-bold ${
                    isActive ? "text-indigo-950" : "text-slate-900"
                  }`}
                >
                  {getLanguageShortLabel(lang.slug)}
                </span>
                {isBusy ? (
                  <Loader2
                    className="h-3.5 w-3.5 animate-spin text-indigo-600"
                    aria-hidden="true"
                  />
                ) : isActive ? (
                  <CheckCircle2
                    className="h-4 w-4 text-indigo-600"
                    aria-hidden="true"
                  />
                ) : null}
              </div>

              <div className="mt-1.5 flex w-full items-center justify-between text-[11px] text-slate-600">
                <span className="font-medium">
                  {lang.lessons_completed}/{lang.lessons_total}{" "}
                  {isBn ? "লেসন" : "lessons"}
                </span>
                {lang.diagnostic_sessions_completed > 0 ? (
                  <span className="rounded bg-emerald-100 px-1.5 py-0.5 font-semibold text-emerald-800">
                    {isBn ? "ডায়াগনস্টিক ✓" : "Diag ✓"}
                  </span>
                ) : null}
              </div>
            </button>
          );
        })}
      </div>
    </section>
  );
}
