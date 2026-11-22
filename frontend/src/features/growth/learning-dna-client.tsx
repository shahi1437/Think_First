"use client";

import {
  Activity,
  AlertCircle,
  CheckCircle2,
  Dna,
  Loader2,
  RefreshCw,
  ShieldCheck,
} from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { fetchLearningDnaProfile } from "@/lib/api-client";
import type { DnaEvidenceBand, LearningDnaProfileView } from "@/types/growth";

interface LearningDnaClientProps {
  accessToken: string;
  initialProfile: LearningDnaProfileView;
  initialLanguage?: "en" | "bn";
}

const BAND_META: Record<
  DnaEvidenceBand,
  {
    labelEn: string;
    labelBn: string;
    variant: "neutral" | "amber" | "indigo" | "teal";
    barClass: string;
    barWidth: string;
  }
> = {
  unobserved: {
    labelEn: "Unobserved",
    labelBn: "এখনো পর্যবেক্ষিত নয়",
    variant: "neutral",
    barClass: "bg-slate-300",
    barWidth: "w-[8%]",
  },
  emerging: {
    labelEn: "Emerging Evidence",
    labelBn: "প্রাথমিক প্রমাণ",
    variant: "amber",
    barClass: "bg-amber-500",
    barWidth: "w-1/3",
  },
  developing: {
    labelEn: "Developing",
    labelBn: "বিকাশমান",
    variant: "indigo",
    barClass: "bg-indigo-500",
    barWidth: "w-2/3",
  },
  verified: {
    labelEn: "Verified Evidence",
    labelBn: "যাচাইকৃত দক্ষতা",
    variant: "teal",
    barClass: "bg-teal-600",
    barWidth: "w-full",
  },
};

export function LearningDnaClient({
  accessToken,
  initialProfile,
  initialLanguage = "en",
}: LearningDnaClientProps) {
  const [lang, setLang] = useState<"en" | "bn">(initialLanguage);
  const [profile, setProfile] = useState<LearningDnaProfileView>(initialProfile);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const isBn = lang === "bn";

  async function handleRefresh() {
    setError(null);
    setRefreshing(true);
    try {
      const updated = await fetchLearningDnaProfile(accessToken);
      setProfile(updated);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not refresh Learning DNA.",
      );
    } finally {
      setRefreshing(false);
    }
  }

  return (
    <div className="tf-animate-enter space-y-6" lang={lang}>
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0 flex-1">
            <p className="inline-flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-indigo-700">
              <Dna className="h-4 w-4" aria-hidden="true" />
              <span>{isBn ? "লার্নিং ডিএনএ প্রোফাইল" : "Evidence-Based Learning DNA"}</span>
            </p>
            <h1 className="mt-1.5 text-2xl font-bold text-slate-900 sm:text-3xl">
              {isBn
                ? "তোমার বাস্তব প্রোগ্রামিং দক্ষতার প্রোফাইল"
                : "Your Observed Programming Competency Profile"}
            </h1>
            <p className="mt-2 max-w-2xl text-base leading-relaxed text-slate-600">
              {isBn ? profile.methodology_note_bn : profile.methodology_note_en}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <div
              role="group"
              aria-label="Learning DNA language"
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

            <button
              type="button"
              onClick={() => void handleRefresh()}
              disabled={refreshing}
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-700 transition hover:bg-slate-50 disabled:opacity-60"
            >
              {refreshing ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
              ) : (
                <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
              )}
              <span>{isBn ? "প্রোফাইল রিফ্রেশ করো" : "Recompute Snapshot"}</span>
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

        {/* Evidence Source Counters */}
        <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-xl border border-slate-200 bg-slate-50 p-3.5">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
              {isBn ? "সক্রিয় ট্র্যাক" : "Active Track"}
            </p>
            <p className="mt-1 text-sm font-bold capitalize text-indigo-900">
              {profile.selected_track_slug.replaceAll("_", " ")}
            </p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-slate-50 p-3.5">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
              {isBn ? "Judge0 সাবমিশন" : "Judge0 Executions"}
            </p>
            <p className="mt-1 text-lg font-bold text-slate-900">
              {profile.source_counts.judge0_submissions ?? 0}
            </p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-slate-50 p-3.5">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
              {isBn ? "স্বাধীন ট্রান্সফার" : "Transfer Attempts"}
            </p>
            <p className="mt-1 text-lg font-bold text-slate-900">
              {profile.source_counts.transfer_attempts ?? 0}
            </p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-slate-50 p-3.5">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
              {isBn ? "রিটেনশন যাচাই" : "Retention Checks"}
            </p>
            <p className="mt-1 text-lg font-bold text-slate-900">
              {profile.source_counts.retention_attempts ?? 0}
            </p>
          </div>
        </div>
      </section>

      {/* 6 Core Learning DNA Dimensions */}
      <section aria-label="Six Learning DNA Dimensions">
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {profile.dimensions.map((dim) => {
            const band = BAND_META[dim.evidence_band];
            return (
              <article
                key={dim.dimension}
                className="flex flex-col justify-between rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
              >
                <div>
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <h2 className="text-base font-bold text-slate-900">
                      {isBn ? dim.label_bn : dim.label_en}
                    </h2>
                    <Badge variant={band.variant}>
                      {isBn ? band.labelBn : band.labelEn}
                    </Badge>
                  </div>

                  {/* Evidence band bar (categorical, never fabricated % score) */}
                  <div
                    className="mt-3 h-2 w-full overflow-hidden rounded-full bg-slate-100"
                    aria-hidden="true"
                  >
                    <div
                      className={`h-full rounded-full transition-all ${band.barClass} ${band.barWidth}`}
                    />
                  </div>

                  <p className="mt-3 text-sm text-slate-700">
                    {isBn ? dim.summary_bn : dim.summary_en}
                  </p>

                  <dl className="mt-3 grid grid-cols-2 gap-2 rounded-xl bg-slate-50 p-2.5 text-xs">
                    {Object.entries(dim.factual_metrics).map(([key, val]) => (
                      <div key={key} className="min-w-0">
                        <dt className="truncate text-[10px] font-medium uppercase text-slate-500">
                          {key.replaceAll("_", " ")}
                        </dt>
                        <dd className="font-bold text-slate-900">{String(val)}</dd>
                      </div>
                    ))}
                  </dl>
                </div>

                <p className="mt-3 border-t border-slate-100 pt-2.5 text-[11px] text-slate-500">
                  {dim.uncertainty_note}
                </p>
              </article>
            );
          })}
        </div>
      </section>

      {/* Strengths, Growth Areas & Authoritative Skill Graph Distribution */}
      <section className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="flex items-center gap-2 text-sm font-bold text-slate-900">
            <ShieldCheck className="h-4 w-4 text-teal-600" aria-hidden="true" />
            <span>
              {isBn ? "যাচাইকৃত শক্তি ও উন্নতির ক্ষেত্র" : "Verified Strengths & Focus Areas"}
            </span>
          </h2>
          <div className="mt-3 space-y-3 text-xs">
            <div>
              <p className="font-semibold text-teal-800">
                {isBn ? "যাচাইকৃত শক্তি" : "Verified Strengths"}
              </p>
              {profile.strengths.length > 0 ? (
                <div className="mt-1.5 flex flex-wrap gap-1.5">
                  {profile.strengths.map((s) => (
                    <Badge key={s} variant="teal">
                      <CheckCircle2 className="h-3 w-3" aria-hidden="true" />
                      <span>{s}</span>
                    </Badge>
                  ))}
                </div>
              ) : (
                <p className="mt-1 text-slate-500">
                  {isBn
                    ? "এখনো কোনো ডাইমেনশন যাচাইকৃত হয়নি — লেসন, Judge0 সাবমিশন বা ট্রান্সফার সম্পন্ন করো।"
                    : "None verified yet — complete a guided lesson, Judge0 submission, or transfer challenge."}
                </p>
              )}
            </div>

            <div>
              <p className="font-semibold text-amber-800">
                {isBn ? "পরবর্তী মনোযোগের ক্ষেত্র" : "Priority Growth Areas"}
              </p>
              <div className="mt-1.5 flex flex-wrap gap-1.5">
                {profile.growth_areas.map((g) => (
                  <Badge key={g} variant="amber">
                    {g}
                  </Badge>
                ))}
              </div>
            </div>
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="flex items-center gap-2 text-sm font-bold text-slate-900">
            <Activity className="h-4 w-4 text-indigo-600" aria-hidden="true" />
            <span>
              {isBn
                ? "Skill Graph অবস্থার সারসংক্ষেপ"
                : "Authoritative Skill Graph Distribution"}
            </span>
          </h2>
          <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3">
            {Object.entries(profile.skill_state_summary).map(([st, count]) => (
              <div
                key={st}
                className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2"
              >
                <p className="text-[11px] font-medium capitalize text-slate-500">
                  {st}
                </p>
                <p className="text-lg font-bold text-slate-900">{count}</p>
              </div>
            ))}
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            <Link
              href="/student/daily-plan"
              className="rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-indigo-500"
            >
              {isBn ? "দৈনিক পরিকল্পনা দেখো" : "Open Adaptive Daily Plan"}
            </Link>
            <Link
              href="/student/retention"
              className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50"
            >
              {isBn ? "রিটেনশন যাচাই" : "Open Retention Verification"}
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
