import { BookOpen, Bug, Cpu, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { SystemStatusCard } from "@/components/system-status-card";

const workflowSteps = [
  {
    icon: BookOpen,
    title: "Evidence-Based Placement",
    description:
      "Topic-specific diagnostics distinguish syntax fluency from debugging, recursion, and logic gaps.",
  },
  {
    icon: Bug,
    title: "Real Sandboxed Execution",
    description:
      "Every run and submission executes inside an isolated Judge0 sandbox with verified public and hidden tests.",
  },
  {
    icon: Cpu,
    title: "Hybrid Socratic Mentoring",
    description:
      "An owned ML error classifier, approved RAG knowledge base, and bounded Socratic tutor guide without leaking answers.",
  },
  {
    icon: ShieldCheck,
    title: "Independent Verification",
    description:
      "Mastery updates only after explanation, unseen transfer solving, and delayed retention checks.",
  },
];

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="bg-[#0b1221] text-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-2.5">
            <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 text-sm font-bold text-white">
              CM
            </span>
            <span className="text-base font-semibold tracking-tight">
              CodeMentor AI
            </span>
          </div>
          <div className="flex items-center gap-3">
            <Link
              href="/login"
              className="rounded-lg px-3.5 py-2 text-sm font-medium text-slate-200 transition hover:bg-slate-800 hover:text-white"
            >
              Sign in
            </Link>
            <Link
              href="/register"
              className="rounded-lg bg-indigo-600 px-3.5 py-2 text-sm font-semibold text-white transition hover:bg-indigo-500"
            >
              Get started
            </Link>
          </div>
        </div>

        <div className="mx-auto max-w-6xl px-6 py-16 sm:py-20">
          <p className="text-sm font-semibold uppercase tracking-wider text-teal-300">
            Think First. Code Better.
          </p>
          <h1 className="mt-3 max-w-3xl text-3xl font-bold tracking-tight text-white sm:text-5xl">
            Adaptive programming and debugging education grounded in real
            execution evidence.
          </h1>
          <p className="mt-5 max-w-2xl text-base leading-relaxed text-slate-300 sm:text-lg">
            CodeMentor AI helps learners from absolute beginners to advanced
            programmers diagnose concrete misconceptions, debug real code, and
            prove independent transfer—built for Students, Teachers, and Admins.
          </p>
        </div>
      </header>

      <main className="mx-auto max-w-6xl space-y-12 px-6 py-12">
        <SystemStatusCard />

        <section aria-labelledby="pillars-heading">
          <h2
            id="pillars-heading"
            className="text-xl font-semibold text-slate-900"
          >
            Core Educational Architecture
          </h2>
          <p className="mt-1 text-sm text-slate-600">
            Built incrementally across verified engineering phases—no simulated
            execution or placeholder metrics.
          </p>

          <div className="mt-6 grid gap-6 sm:grid-cols-2">
            {workflowSteps.map((step) => {
              const Icon = step.icon;
              return (
                <article
                  key={step.title}
                  className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm"
                >
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-slate-900 text-teal-300">
                    <Icon className="h-5 w-5" aria-hidden="true" />
                  </div>
                  <h3 className="mt-4 text-base font-semibold text-slate-900">
                    {step.title}
                  </h3>
                  <p className="mt-2 text-sm leading-relaxed text-slate-600">
                    {step.description}
                  </p>
                </article>
              );
            })}
          </div>
        </section>
      </main>
    </div>
  );
}
