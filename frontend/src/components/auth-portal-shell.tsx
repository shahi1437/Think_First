import { CheckCircle2, type LucideIcon } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";
import { PublicFooter } from "@/components/public-footer";
import { PublicNavbar } from "@/components/public-navbar";

interface AuthPortalShellProps {
  badge: string;
  title: string;
  subtitle: string;
  icon: LucideIcon;
  accent?: "teal" | "indigo" | "slate";
  highlights?: string[];
  children: ReactNode;
  footerLinks?: Array<{ href: string; label: string }>;
}

const ACCENT_MAP = {
  teal: "bg-teal-50 text-teal-700 border-teal-200",
  indigo: "bg-indigo-50 text-indigo-700 border-indigo-200",
  slate: "bg-slate-100 text-slate-800 border-slate-200",
};

const DEFAULT_HIGHLIGHTS: Record<"teal" | "indigo" | "slate", string[]> = {
  teal: [
    "Learn Python with interactive lessons and guided exercises",
    "Practice coding problems with real test feedback",
    "Review error diagnostics and track your skill mastery",
  ],
  indigo: [
    "Manage assigned classes and enrollment invitations",
    "Publish coding assignments with clear grading rubrics",
    "Review student submissions, diagnostics, and class progress",
  ],
  slate: [
    "Manage platform users and verified role permissions",
    "Oversee courses, curriculum standards, and problem banks",
    "Monitor live database, execution, and AI service health",
  ],
};

export function AuthPortalShell({
  badge,
  title,
  subtitle,
  icon: Icon,
  accent = "teal",
  highlights,
  children,
  footerLinks = [],
}: AuthPortalShellProps) {
  const panelHighlights = highlights ?? DEFAULT_HIGHLIGHTS[accent];

  return (
    <div className="flex min-h-screen flex-col bg-[#f7f8fa] text-slate-900">
      <PublicNavbar />

      <main className="flex flex-1 items-center justify-center px-4 py-10 sm:px-6 sm:py-14">
        <div className="w-full max-w-5xl space-y-6">
          <div className="grid overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm lg:grid-cols-12">
            {/* Left Informational Brand Panel */}
            <aside className="flex flex-col justify-between bg-[#0b1221] p-8 text-white sm:p-10 lg:col-span-5">
              <div className="space-y-5">
                <div className="inline-flex h-11 w-11 items-center justify-center rounded-xl border border-teal-400/25 bg-teal-400/10 text-teal-300">
                  <Icon className="h-5 w-5" aria-hidden="true" />
                </div>

                <div>
                  <p className="text-xs font-medium text-teal-300">
                    Think First. Code Better.
                  </p>
                  <h2 className="mt-2 text-2xl font-bold tracking-tight text-white">
                    {title}
                  </h2>
                  <p className="mt-2.5 text-sm leading-relaxed text-slate-300">
                    {subtitle}
                  </p>
                </div>

                <ul className="space-y-3 pt-2 text-sm text-slate-200">
                  {panelHighlights.map((item) => (
                    <li key={item} className="flex items-start gap-2.5">
                      <CheckCircle2
                        className="mt-0.5 h-4 w-4 shrink-0 text-teal-300"
                        aria-hidden="true"
                      />
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="relative mt-8 border-t border-slate-800 pt-5 text-xs text-slate-400">
                Protected by verified session authentication and strict
                role-based access control.
              </div>
            </aside>

            {/* Right Form Area */}
            <div className="p-7 sm:p-10 lg:col-span-7">
              <div className="mb-7">
                <div className="flex items-center justify-between gap-2">
                  <span
                    className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-semibold ${ACCENT_MAP[accent]}`}
                  >
                    <Icon className="h-3.5 w-3.5" aria-hidden="true" />
                    <span>{badge}</span>
                  </span>
                  <span className="text-xs font-semibold text-slate-400">
                    Think_First · CodeMentor AI
                  </span>
                </div>

                <h1 className="mt-4 text-3xl font-bold tracking-tight text-slate-900 sm:text-[34px]">
                  {title}
                </h1>
                <p className="mt-2 text-base leading-relaxed text-slate-600">
                  {subtitle}
                </p>
              </div>

              {children}
            </div>
          </div>

          {footerLinks.length > 0 ? (
            <div className="flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-sm text-slate-600">
              {footerLinks.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className="font-medium text-slate-700 transition hover:text-indigo-700 hover:underline"
                >
                  {item.label}
                </Link>
              ))}
            </div>
          ) : null}
        </div>
      </main>

      <PublicFooter />
    </div>
  );
}
