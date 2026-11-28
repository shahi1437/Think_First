"use client";

import {
  AlertTriangle,
  ArrowRight,
  Compass,
  RotateCcw,
  ShieldCheck,
  Target,
} from "lucide-react";
import Link from "next/link";
import type { VerifiedLearningProgressView } from "@/types/growth";
import type { LearningDashboardView } from "@/types/learning";

interface PersonalizedLearningHubProps {
  dashboard: LearningDashboardView;
  verifiedProgress?: VerifiedLearningProgressView | null;
  retentionSummary?: {
    dueCount: number;
    scheduledCount: number;
    retainedSkillsCount: number;
  };
  dailyPlanSummary?: {
    completedTasks: number;
    totalTasks: number;
    availableMinutes: number;
    versionNumber: number;
  };
  language?: "en" | "bn";
}

export function PersonalizedLearningHub({
  dashboard,
  verifiedProgress = null,
  retentionSummary,
  dailyPlanSummary,
  language = "en",
}: PersonalizedLearningHubProps) {
  const isBn = language === "bn";
  const primary = dashboard.journey?.primary_action ?? null;
  const topRec = dashboard.recommendations[0] ?? null;

  // 1. What should I learn next?
  const nextTitle = primary
    ? isBn
      ? primary.title_bn
      : primary.title_en
    : (topRec?.title ?? (isBn ? "গাইডেড লেসন শুরু করো" : "Start next guided lesson"));
  const nextHref = primary?.href ?? topRec?.href ?? "/student/lessons";

  // 2. Which concept is weak / developing?
  const masteredSlugs = new Set(
    dashboard.skill_graph.nodes
      .filter((n) =>
        ["independent", "transferred", "retained"].includes(n.state),
      )
      .map((n) => n.slug),
  );
  const weakNodes = dashboard.skill_graph.nodes.filter((n) =>
    ["introduced", "guided"].includes(n.state),
  );
  const nextUnobserved = dashboard.skill_graph.nodes.find(
    (n) =>
      n.state === "unobserved" &&
      (n.prerequisites.length === 0 ||
        n.prerequisites.every((prereq) => masteredSlugs.has(prereq))),
  );
  const weakFocusNode = weakNodes[0] ?? nextUnobserved ?? null;

  // 3. Which problem should I solve?
  const problemRec = dashboard.recommendations.find(
    (r) =>
      r.recommendation_type === "problem" ||
      r.recommendation_type === "transfer_challenge",
  );
  const solveHref = problemRec?.href ?? "/student/problems";
  const solveLabel = problemRec
    ? problemRec.title
    : weakFocusNode
      ? isBn
        ? `${weakFocusNode.title_bn} ভিত্তিক প্রবলেম অনুশীলন`
        : `Practice ${weakFocusNode.title_en} in Problem Bank`
      : isBn
        ? "অ্যাডাপ্টিভ প্রবলেম ব্যাংক দেখো"
        : "Explore Adaptive Problem Bank";

  // 4. What progress have I made?
  const solvedProblems = verifiedProgress?.problems_solved_verified ?? 0;
  const masteredSkills =
    verifiedProgress?.concepts_mastered_verified.length ??
    dashboard.skill_graph.nodes.filter((n) =>
      ["independent", "transferred", "retained"].includes(n.state),
    ).length;

  // 5. What should I practice again?
  const dueRetention = retentionSummary?.dueCount ?? 0;
  const remainingPlanTasks = dailyPlanSummary
    ? Math.max(0, dailyPlanSummary.totalTasks - dailyPlanSummary.completedTasks)
    : 0;

  const cards = [
    {
      id: "q-next",
      question: isBn ? "১. এখন কী শিখব?" : "1. What should I learn next?",
      answer: nextTitle,
      detail: primary
        ? isBn
          ? primary.reason_bn
          : primary.reason_en
        : isBn
          ? "তোমার Skill Graph অনুযায়ী পরবর্তী ধাপ"
          : "Selected from your Skill Graph & prerequisites",
      href: nextHref,
      cta: isBn ? "এখন শুরু করো" : "Open step",
      Icon: Compass,
      accent: "text-teal-700",
    },
    {
      id: "q-weak",
      question: isBn ? "২. কোন কনসেপ্ট দুর্বল?" : "2. Which concept is weak?",
      answer: weakFocusNode
        ? isBn
          ? weakFocusNode.title_bn
          : weakFocusNode.title_en
        : isBn
          ? "কোনো দুর্বল কনসেপ্ট চিহ্নিত হয়নি"
          : "No weak concept flagged yet",
      detail: weakFocusNode
        ? isBn
          ? `বর্তমান অবস্থা: ${weakFocusNode.state} (${weakFocusNode.evidence_count} প্রমাণ)`
          : `Current state: ${weakFocusNode.state} (${weakFocusNode.evidence_count} evidence record(s))`
        : isBn
          ? "ডায়াগনস্টিক বা অনুশীলন সম্পন্ন করে যাচাই করো"
          : "Complete a diagnostic or problem to measure concepts",
      href: "/student/dna",
      cta: isBn ? "লার্নিং ডিএনএ দেখো" : "Inspect DNA",
      Icon: AlertTriangle,
      accent: "text-amber-700",
    },
    {
      id: "q-problem",
      question: isBn
        ? "৩. কোন প্রবলেম সমাধান করব?"
        : "3. Which problem should I solve?",
      answer: solveLabel,
      detail: problemRec
        ? isBn
          ? problemRec.reason_bn
          : problemRec.reason_en
        : isBn
          ? "তোমার দুর্বল কনসেপ্ট ও অগ্রগতি অনুযায়ী সুপারিশ"
          : "Matched to developing skills & progressive difficulty",
      href: solveHref,
      cta: isBn ? "প্রবলেম খোলো" : "Solve now",
      Icon: Target,
      accent: "text-slate-900",
    },
    {
      id: "q-progress",
      question: isBn ? "৪. কতটুকু অগ্রগতি হয়েছে?" : "4. What progress have I made?",
      answer: isBn
        ? `${solvedProblems} প্রবলেম · ${masteredSkills} যাচাইকৃত দক্ষতা`
        : `${solvedProblems} solved · ${masteredSkills} verified skill(s)`,
      detail: isBn
        ? `${dashboard.lessons_completed}/${dashboard.lessons_total} লেসন সম্পন্ন · ${verifiedProgress?.consistency_active_days_14d ?? 0}/১৪ দিন সক্রিয়`
        : `${dashboard.lessons_completed}/${dashboard.lessons_total} lessons passed · ${verifiedProgress?.consistency_active_days_14d ?? 0}/14 active days`,
      href: "/student/history",
      cta: isBn ? "টাইমলাইন দেখো" : "View timeline",
      Icon: ShieldCheck,
      accent: "text-emerald-700",
    },
    {
      id: "q-repeat",
      question: isBn
        ? "৫. কোনটি আবার অনুশীলন করব?"
        : "5. What should I practice again?",
      answer:
        dueRetention > 0
          ? isBn
            ? `${dueRetention}টি ২৪-ঘণ্টা রিটেনশন যাচাই বাকি`
            : `${dueRetention} spaced retention check(s) due`
          : remainingPlanTasks > 0
            ? isBn
              ? `আজকের প্ল্যানে ${remainingPlanTasks}টি কাজ বাকি`
              : `${remainingPlanTasks} daily plan task(s) remaining`
            : isBn
              ? "সব নির্ধারিত রিটেনশন সম্পন্ন"
              : "All scheduled reviews up to date",
      detail: isBn
        ? "২৪ ঘণ্টা পর হিন্ট ছাড়া কোড চালিয়ে স্থায়ী দক্ষতা যাচাই করো"
        : "Pass zero-hint Judge0 checks after 24h to lock in retention",
      href: dueRetention > 0 ? "/student/retention" : "/student/daily-plan",
      cta:
        dueRetention > 0
          ? isBn
            ? "রিটেনশন শুরু করো"
            : "Start review"
          : isBn
            ? "দৈনিক প্ল্যান দেখো"
            : "Open daily plan",
      Icon: RotateCcw,
      accent: "text-teal-700",
    },
  ];

  return (
    <section
      aria-label="Unified Personalized Learning Coach"
      data-testid="personalized-learning-hub"
      className="rounded-2xl border border-slate-200 bg-white p-6"
    >
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-4">
        <div>
          <p className="text-xs font-semibold text-teal-700">
            {isBn
              ? "সমন্বিত ব্যক্তিগত শেখার গাইড"
              : "Unified Personalized Learning Engine"}
          </p>
          <h2 className="mt-0.5 text-lg font-bold tracking-tight text-slate-950">
            {isBn
              ? "তোমার ৫টি মূল প্রশ্নের প্রমাণভিত্তিক উত্তর"
              : "Five Evidence-Based Answers for Your Next Session"}
          </h2>
        </div>
        <span className="text-xs text-slate-500">
          {isBn
            ? "Learning DNA · Skill Graph · Daily Plan · Retention থেকে সংযুক্ত"
            : "Synthesized from Learning DNA, Skill Graph, Daily Plan & Retention"}
        </span>
      </div>

      <div className="mt-4 grid gap-3.5 sm:grid-cols-2 lg:grid-cols-5">
        {cards.map((card) => {
          const Icon = card.Icon;
          return (
            <article
              key={card.id}
              data-testid={card.id}
              className="flex flex-col justify-between rounded-xl border border-slate-200 bg-[#f7f8fa] p-4"
            >
              <div>
                <div className="flex items-center gap-1.5 text-xs font-medium text-slate-500">
                  <Icon
                    className={`h-3.5 w-3.5 shrink-0 ${card.accent}`}
                    aria-hidden="true"
                  />
                  <span>{card.question}</span>
                </div>
                <p className="mt-2 text-sm font-bold leading-snug text-slate-950 tabular-nums">
                  {card.answer}
                </p>
                <p className="mt-1.5 text-xs leading-relaxed text-slate-600">
                  {card.detail}
                </p>
              </div>
              <Link
                href={card.href}
                className="mt-3 inline-flex items-center gap-1 text-xs font-semibold text-teal-700 hover:text-teal-900 hover:underline"
              >
                <span>{card.cta}</span>
                <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
              </Link>
            </article>
          );
        })}
      </div>
    </section>
  );
}
