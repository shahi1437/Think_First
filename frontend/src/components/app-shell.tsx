import Link from "next/link";
import type { ReactNode } from "react";
import { LogoutButton } from "@/components/logout-button";
import { NavLinks } from "@/components/nav-links";
import { getAuthorizedPortals } from "@/lib/auth/roles";
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

            <NavLinks
              navLinks={navLinks}
              activeRole={activeRole}
              authorizedPortals={getAuthorizedPortals(user.roles)}
            />
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
