"use client";

import {
  AlertCircle,
  ArrowRight,
  CheckCircle2,
  GitBranch,
  History,
  Info,
} from "lucide-react";
import { useMemo, useState } from "react";
import { Badge } from "@/components/ui/badge";
import type { SkillGraphView, SkillState } from "@/types/learning";

interface SkillGraphPanelProps {
  graph: SkillGraphView;
  language?: "en" | "bn";
}

const STATE_BADGE: Record<
  SkillState,
  {
    labelEn: string;
    labelBn: string;
    variant: "neutral" | "indigo" | "teal" | "emerald" | "amber";
    border: string;
  }
> = {
  unobserved: {
    labelEn: "Not Yet Observed",
    labelBn: "পর্যবেক্ষিত হয়নি",
    variant: "neutral",
    border: "border-slate-200 bg-slate-50/70",
  },
  introduced: {
    labelEn: "Introduced",
    labelBn: "পরিচিত হয়েছে",
    variant: "amber",
    border: "border-amber-200 bg-amber-50/40",
  },
  guided: {
    labelEn: "Guided",
    labelBn: "নির্দেশিত",
    variant: "indigo",
    border: "border-indigo-200 bg-indigo-50/40",
  },
  independent: {
    labelEn: "Independent",
    labelBn: "স্বাধীন",
    variant: "teal",
    border: "border-teal-200 bg-teal-50/40",
  },
  transferred: {
    labelEn: "Transferred",
    labelBn: "ট্রান্সফার প্রমাণিত",
    variant: "emerald",
    border: "border-emerald-300 bg-emerald-50/60",
  },
  retained: {
    labelEn: "Retained",
    labelBn: "দীর্ঘমেয়াদী",
    variant: "emerald",
    border: "border-emerald-400 bg-emerald-50",
  },
};

export function SkillGraphPanel({
  graph,
  language = "en",
}: SkillGraphPanelProps) {
  const [selectedSlug, setSelectedSlug] = useState<string>(
    graph.nodes[0]?.slug ?? "",
  );
  const isBn = language === "bn";

  const { nodes } = graph;
  const tiers = useMemo(() => {
    const grouped = new Map<number, typeof nodes>();
    for (const node of nodes) {
      const list = grouped.get(node.tier) ?? [];
      list.push(node);
      grouped.set(node.tier, list);
    }
    return Array.from(grouped.entries()).sort((a, b) => a[0] - b[0]);
  }, [nodes]);

  const titleBySlug = useMemo(() => {
    const m = new Map<string, string>();
    for (const n of nodes) {
      m.set(n.slug, isBn ? n.title_bn : n.title_en);
    }
    return m;
  }, [nodes, isBn]);

  const selectedNode =
    graph.nodes.find((n) => n.slug === selectedSlug) ?? graph.nodes[0] ?? null;

  return (
    <section
      aria-label="Prerequisite-aware Skill Graph"
      className="space-y-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
      lang={language}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <GitBranch className="h-4 w-4 text-indigo-600" aria-hidden="true" />
            <h2 className="text-base font-bold text-slate-900">
              {isBn
                ? "দক্ষতা গ্রাফ (Prerequisite Skill Graph)"
                : "Prerequisite-Aware Skill Graph"}
            </h2>
          </div>
          <p className="mt-1 text-xs text-slate-600">
            {isBn
              ? "প্রতিটি ধাপ কেবল আসল Judge0 এক্সিকিউশন, ডায়াগনস্টিক ও ট্রান্সফার প্রমাণের ভিত্তিতে আপডেট হয়—কোনো বানানো শতাংশ নয়।"
              : "Every state reflects direct diagnostic, Judge0 execution, or transfer evidence—Introduced is not mastery, and Retained requires later re-verification."}
          </p>
        </div>

        <div className="flex flex-wrap gap-1.5">
          {(
            [
              "unobserved",
              "introduced",
              "guided",
              "independent",
              "transferred",
              "retained",
            ] as const
          ).map((st) => (
            <Badge key={st} variant={STATE_BADGE[st].variant}>
              {isBn ? STATE_BADGE[st].labelBn : STATE_BADGE[st].labelEn}
            </Badge>
          ))}
        </div>
      </div>

      {/* Tiered DAG Visualization */}
      <div className="space-y-3">
        {tiers.map(([tierNum, tierNodes]) => (
          <div
            key={tierNum}
            className="rounded-xl border border-slate-100 bg-slate-50/60 p-3"
          >
            <p className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
              Tier {tierNum}
            </p>
            <div className="grid gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
              {tierNodes.map((node) => {
                const style = STATE_BADGE[node.state];
                const isSelected = selectedNode?.slug === node.slug;
                return (
                  <button
                    key={node.slug}
                    type="button"
                    onClick={() => setSelectedSlug(node.slug)}
                    aria-pressed={isSelected}
                    className={`min-w-0 rounded-xl border p-3 text-left transition ${style.border} ${
                      isSelected
                        ? "ring-2 ring-indigo-600 ring-offset-1"
                        : "hover:border-indigo-300"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <span className="text-xs font-bold text-slate-900">
                        {isBn ? node.title_bn : node.title_en}
                      </span>
                      <Badge variant={style.variant}>
                        {isBn ? style.labelBn : style.labelEn}
                      </Badge>
                    </div>
                    <p className="mt-1.5 text-[11px] text-slate-600">
                      {node.evidence_count === 0
                        ? isBn
                          ? "এখনো প্রমাণ নেই"
                          : "0 direct evidence records"
                        : `${node.evidence_count} evidence record${node.evidence_count === 1 ? "" : "s"}`}
                    </p>
                    {node.prerequisites.length > 0 ? (
                      <div className="mt-2 flex flex-wrap items-center gap-1 text-[10px] text-slate-500">
                        <span className="font-semibold">Prereqs:</span>
                        {node.prerequisites.map((p) => (
                          <span
                            key={p}
                            className="rounded bg-white/90 px-1.5 py-0.5 text-slate-700 ring-1 ring-slate-200"
                          >
                            {titleBySlug.get(p) ?? p}
                          </span>
                        ))}
                      </div>
                    ) : null}
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      {/* Selected Node Transparency & Uncertainty Inspector */}
      {selectedNode ? (
        <div className="rounded-xl border border-indigo-200 bg-indigo-50/40 p-4 text-xs">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <Info className="h-4 w-4 text-indigo-700" aria-hidden="true" />
              <h3 className="font-bold text-indigo-950">
                {isBn ? selectedNode.title_bn : selectedNode.title_en}
              </h3>
            </div>
            <Badge variant={STATE_BADGE[selectedNode.state].variant}>
              {isBn
                ? STATE_BADGE[selectedNode.state].labelBn
                : STATE_BADGE[selectedNode.state].labelEn}
            </Badge>
          </div>
          <p className="mt-1.5 text-slate-700">
            {isBn ? selectedNode.description_bn : selectedNode.description_en}
          </p>
          <div className="mt-2 flex items-start gap-1.5 rounded-lg border border-indigo-200/80 bg-white p-2.5 text-slate-700">
            {selectedNode.state === "unobserved" ||
            selectedNode.state === "introduced" ? (
              <AlertCircle
                className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-600"
                aria-hidden="true"
              />
            ) : (
              <CheckCircle2
                className="mt-0.5 h-3.5 w-3.5 shrink-0 text-teal-600"
                aria-hidden="true"
              />
            )}
            <span>
              <strong>Evidence &amp; Uncertainty:</strong>{" "}
              {selectedNode.uncertainty_note}
            </span>
          </div>
        </div>
      ) : null}

      {/* Recent Audited Transitions */}
      {graph.recent_transitions.length > 0 ? (
        <div className="border-t border-slate-100 pt-3">
          <div className="mb-2 flex items-center gap-1.5 text-xs font-semibold text-slate-600">
            <History className="h-3.5 w-3.5" aria-hidden="true" />
            <span>Recent Skill Evidence Transitions</span>
          </div>
          <ul className="space-y-1.5 text-xs">
            {graph.recent_transitions.slice(0, 5).map((tr) => (
              <li
                key={tr.id}
                className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-slate-50 px-3 py-2"
              >
                <div className="flex flex-wrap items-center gap-1.5">
                  <span className="font-semibold text-slate-800">
                    {titleBySlug.get(tr.skill_slug) ?? tr.skill_slug}
                  </span>
                  <span className="text-slate-500">{tr.from_state}</span>
                  <ArrowRight className="h-3 w-3 text-slate-400" />
                  <Badge variant="indigo">{tr.to_state}</Badge>
                </div>
                <span className="text-slate-600">{tr.reason}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}
