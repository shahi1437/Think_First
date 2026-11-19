import Link from "next/link";
import type { ReactNode } from "react";
import { LogoutButton } from "@/components/logout-button";
import type { RoleName, UserMeResponse } from "@/types/identity";

interface NavLink {
  href: string;
  label: string;
}

interface AppShellProps {
  user: UserMeResponse;
  activeRole: RoleName;
  navLinks: NavLink[];
  children: ReactNode;
}

export function AppShell({
  user,
  activeRole,
  navLinks,
  children,
}: AppShellProps) {
  return (
    <div className="min-h-screen overflow-x-hidden bg-slate-50 text-slate-900">
      <header className="bg-[#0b1221] text-white">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-4 py-4 sm:px-6">
          <div className="flex flex-wrap items-center gap-4 sm:gap-6">
            <Link href="/" className="flex items-center gap-2.5">
              <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 text-sm font-bold text-white">
                CM
              </span>
              <span className="text-base font-semibold tracking-tight">
                CodeMentor AI
              </span>
            </Link>

            <nav
              aria-label="Primary navigation"
              className="flex flex-wrap items-center gap-x-4 gap-y-1.5"
            >
              {navLinks.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className="text-sm font-medium text-slate-300 transition hover:text-white"
                >
                  {item.label}
                </Link>
              ))}
              {user.roles.includes("teacher") && activeRole !== "teacher" ? (
                <Link
                  href="/teacher"
                  className="text-sm font-medium text-teal-300 transition hover:text-teal-200"
                >
                  Teacher Portal
                </Link>
              ) : null}
              {user.roles.includes("admin") && activeRole !== "admin" ? (
                <Link
                  href="/admin"
                  className="text-sm font-medium text-indigo-300 transition hover:text-indigo-200"
                >
                  Admin Studio
                </Link>
              ) : null}
            </nav>
          </div>

          <div className="flex items-center gap-3">
            <span className="rounded-full border border-teal-400/30 bg-teal-500/10 px-2.5 py-0.5 text-xs font-medium capitalize text-teal-200">
              {activeRole}
            </span>
            <span className="hidden text-xs text-slate-300 sm:inline">
              {user.full_name || user.email}
            </span>
            <LogoutButton />
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-6 sm:px-6 sm:py-8">{children}</main>
    </div>
  );
}
